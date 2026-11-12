"""A descrição de cada figura e tabela: uma chamada por figura, em paralelo.

Cada chamada leva o PDF, o rótulo, a página, a legenda e as frases do artigo que citam a figura
(achadas na 1.6). O modelo devolve também o começo da legenda da figura que descreveu: se não
bate com a legenda pedida, ele olhou outra figura (aconteceu: a "Figure 1" descrita com o
conteúdo da "Table 1"), e a chamada é refeita com uma dica. Também é refeita a tabela que vem
sem as linhas de dados (aconteceu: só o cabeçalho); se continuar assim, a descrição fica e o
markdown da tabela sai. Uma figura cuja chamada falha, ou que continua trocada, fica sem
descrição e o estágio segue; só quando todas falham com o modelo fora do ar o erro sobe, para o
Celery tentar de novo.
"""

import re
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from typing import Final

from projects.correction.extractor.article import Figure, FigureDescription, FigureMention
from projects.correction.extractor.config import DocumentConfig
from projects.correction.extractor.coverage import squash
from projects.correction.extractor.errors import InvalidModelAnswer, ModelUnavailable
from projects.correction.extractor.figures import NUMBER
from projects.correction.extractor.prompts import load_prompt, render_prompt
from projects.correction.extractor.schemas import DescribedFigure
from projects.correction.extractor.session import DocumentSession

MAX_MENTIONS: Final = 5
NO_MENTIONS: Final = "(o texto não cita esta figura)"
# Quantas letras do começo da legenda conferir (só letras e dígitos, sem acento e caixa).
CAPTION_START_CHARS: Final = 30
QUOTE_CHARS: Final = 160
# O cabeçalho e pelo menos uma linha de dados.
MIN_TABLE_LINES: Final = 2
# "Figure 1:", "Tabela A.1." no começo: o modelo às vezes devolve a legenda sem ele.
LEADING_LABEL: Final = re.compile(
    rf"^\s*(?:Figures?|Figs?\.|Figuras?|Tables?|Tabs?\.|Tabelas?|Quadros?)\s*{NUMBER}[a-z]?\s*[:.]?",
    re.IGNORECASE,
)


def describe_figures(
    session: DocumentSession,
    config: DocumentConfig,
    figures: Sequence[Figure],
    mentions: Sequence[FigureMention],
) -> tuple[Figure, ...]:
    if not figures or not config.describe_figures:
        return tuple(figures)
    with ThreadPoolExecutor(max_workers=config.max_parallel_calls) as pool:
        outcomes = list(
            pool.map(lambda figure: _describe(session, config, figure, mentions), figures)
        )
    if all(isinstance(outcome, BaseException) for outcome in outcomes):
        unavailable = [o for o in outcomes if isinstance(o, ModelUnavailable)]
        if unavailable:
            raise unavailable[0]
    return tuple(
        figure
        if isinstance(outcome, BaseException)
        else figure.model_copy(update={"description": outcome})
        for figure, outcome in zip(figures, outcomes, strict=True)
    )


def _describe(
    session: DocumentSession,
    config: DocumentConfig,
    figure: Figure,
    mentions: Sequence[FigureMention],
) -> FigureDescription | ModelUnavailable | InvalidModelAnswer:
    """A descrição, ou o erro que deixa esta figura sem descrição (sem derrubar as outras)."""
    prompt = render_prompt(
        config.describe_figure_prompt,
        label=figure.label,
        page=str(figure.page),
        caption=figure.caption,
        mentions=_mentions_text(figure, mentions),
    )
    error: ModelUnavailable | InvalidModelAnswer = InvalidModelAnswer("sem tentativa")
    hint = ""
    partial: DescribedFigure | None = None  # a figura certa, mas a tabela sem as linhas
    for _ in range(config.check_retries + 1):
        try:
            answer = session.ask(prompt + hint, DescribedFigure)
        except InvalidModelAnswer as exc:
            error = exc  # resposta inválida: tenta de novo
            continue
        except ModelUnavailable as exc:
            return exc  # o modelo fora do ar: quem tenta de novo é o Celery
        if not _same_figure(figure.caption, answer.caption_start):
            error = InvalidModelAnswer(f"A descrição de {figure.label} foi de outra figura.")
            seen = " ".join(answer.caption_start.split())[:QUOTE_CHARS]
            hint = "\n\n" + render_prompt(load_prompt("retry_wrong_figure"), seen=f"«{seen}»")
            continue
        if figure.kind == "table" and not _has_rows(answer.table_markdown):
            partial = answer
            hint = "\n\n" + load_prompt("retry_table_rows")
            continue
        return _cleaned(answer)
    if partial is not None:
        return _cleaned(partial.model_copy(update={"table_markdown": None}))
    return error


def _same_figure(caption: str, caption_start: str) -> bool:
    """O começo da legenda devolvido está no começo da legenda pedida, com ou sem o rótulo."""
    asked = squash(LEADING_LABEL.sub("", caption))
    start = squash(LEADING_LABEL.sub("", caption_start))[:CAPTION_START_CHARS]
    return bool(start) and asked.startswith(start)


def _has_rows(markdown: str | None) -> bool:
    """A tabela tem o cabeçalho e pelo menos uma linha de dados (a linha "|---|" não conta)."""
    lines = [line for line in (markdown or "").splitlines() if line.strip()]
    return sum(not set(line) <= set("|-: ") for line in lines) >= MIN_TABLE_LINES


def _mentions_text(figure: Figure, mentions: Sequence[FigureMention]) -> str:
    sentences = list(dict.fromkeys(m.sentence for m in mentions if m.figure_id == figure.id))
    if not sentences:
        return NO_MENTIONS
    return "\n".join(f"- {sentence}" for sentence in sentences[:MAX_MENTIONS])


def _cleaned(answer: DescribedFigure) -> FigureDescription:
    def items(values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(text for text in (" ".join(v.split()) for v in values) if text)

    markdown = (answer.table_markdown or "").strip()
    return FigureDescription(
        figure_class=" ".join(answer.figure_class.split()),
        description=answer.description.strip(),
        data_read=items(answer.data_read),
        supports_claims=answer.supports_claims,
        support_rationale=answer.support_rationale.strip(),
        issues=items(answer.issues),
        table_markdown=markdown or None,
    )
