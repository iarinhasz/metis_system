"""A resposta de uma seção, conferida contra o texto do PDF: pede, confere e, se reprovada, pede
de novo com uma dica do que deu errado. Fica a melhor resposta.

Repetir o mesmo pedido com temperatura 0 tende a dar a mesma resposta; por isso a nova tentativa
diz ao modelo o que faltou (frases do PDF que não vieram) ou o que sobrou (o começo do texto que
não é da seção).
"""

from dataclasses import dataclass
from typing import Final

from projects.correction.extractor.config import DocumentConfig
from projects.correction.extractor.coverage import coverage, fidelity, missing_sentences
from projects.correction.extractor.errors import InvalidModelAnswer
from projects.correction.extractor.prompts import load_prompt, render_prompt
from projects.correction.extractor.schemas import SectionContent
from projects.correction.extractor.session import DocumentSession

QUOTE_CHARS: Final = 200
MISSING_IN_HINT: Final = 2


@dataclass(frozen=True)
class SectionAnswer:
    content: SectionContent
    coverage: float | None
    fidelity: float | None

    @property
    def score(self) -> float:
        # A pior das duas medidas; sem como verificar, a resposta vale como boa.
        return min((v for v in (self.coverage, self.fidelity) if v is not None), default=1.0)

    def passes(self, config: DocumentConfig) -> bool:
        return (self.coverage is None or self.coverage >= config.min_coverage) and (
            self.fidelity is None or self.fidelity >= config.min_fidelity
        )


def ask_section(
    session: DocumentSession, config: DocumentConfig, prompt: str, local_text: str | None
) -> SectionAnswer:
    best: SectionAnswer | None = None
    hint = ""
    invalid: InvalidModelAnswer | None = None
    for _ in range(config.check_retries + 1):
        try:
            content = session.ask(prompt + hint, SectionContent)
        except InvalidModelAnswer as exc:
            # Resposta vazia ou fora do schema numa seção conta como tentativa falha dela,
            # sem derrubar a extração inteira (o retry do estágio refaria todas as seções).
            invalid = exc
            continue
        answer = SectionAnswer(
            content, coverage(local_text, content.text), fidelity(local_text, content.text)
        )
        if answer.passes(config):
            return answer
        if best is None or answer.score > best.score:
            best = answer
        hint = _retry_hint(answer, local_text, config)
    if best is None:
        assert invalid is not None
        raise invalid
    return _without_foreign_text(best, config)


def _retry_hint(answer: SectionAnswer, local_text: str | None, config: DocumentConfig) -> str:
    hints = []
    if answer.fidelity is not None and answer.fidelity < config.min_fidelity:
        foreign = _quote(answer.content.text)
        hints.append(render_prompt(load_prompt("retry_foreign"), foreign=foreign))
    if answer.coverage is not None and answer.coverage < config.min_coverage:
        missing = missing_sentences(local_text, answer.content.text, limit=MISSING_IN_HINT)
        if missing:
            listed = "\n".join(f"- {_quote(sentence)}" for sentence in missing)
            hints.append(render_prompt(load_prompt("retry_missing"), missing=listed))
    return "".join(f"\n\n{hint}" for hint in hints)


def _without_foreign_text(answer: SectionAnswer, config: DocumentConfig) -> SectionAnswer:
    """Seção sem prosa no PDF que, mesmo depois das tentativas, recebe texto que não está nela
    fica vazia: o texto é de outra seção e estaria duplicado."""
    foreign = answer.fidelity is not None and answer.fidelity < config.min_fidelity
    if answer.coverage is None and foreign:
        return SectionAnswer(SectionContent(text="", has_footnotes=False), None, None)
    return answer


def _quote(text: str) -> str:
    flat = " ".join(text.split())
    cut = "…" if len(flat) > QUOTE_CHARS else ""
    return f"«{flat[:QUOTE_CHARS]}{cut}»"
