"""Sessão falsa: a chamada 1 devolve o mapa roteirizado, cada chamada 2 devolve a próxima
resposta roteirizada para a seção que o prompt pede, e a chamada das referências devolve a
próxima resposta roteirizada ou, sem roteiro, cada parágrafo da lista como uma entrada."""

import re
import threading
import time
from collections import defaultdict

from pydantic import BaseModel

from projects.correction.extractor.config import DocumentConfig
from projects.correction.extractor.schemas import (
    DescribedFigure,
    FigureScan,
    HeadingScan,
    ParsedReference,
    ParsedReferences,
    SectionContent,
)
from projects.correction.extractor.session import DocumentSession, SessionOpener

ASKED_TITLE = re.compile(r'Seção: "([^"]+)"')
ASKED_FIGURE = re.compile(r'Figura: "([^"]+)"')
ASKED_CAPTION = re.compile(r"Legenda: (.+)")


def described(text: str = "Um gráfico de linhas.", **fields: object) -> DescribedFigure:
    values: dict[str, object] = {
        "caption_start": "",
        "figure_class": "gráfico de linhas",
        "description": text,
        "data_read": (),
        "supports_claims": None,
        "support_rationale": "",
        "issues": (),
        "table_markdown": None,
    }
    values.update(fields)
    return DescribedFigure.model_validate(values)


REFERENCES_TEXT = re.compile(r"<referencias>\n(.*?)\n</referencias>", re.S)


def raw_entry(raw: str, **fields: object) -> ParsedReference:
    values: dict[str, object] = {
        "raw": raw,
        "marker": None,
        "authors": (),
        "title": None,
        "year": None,
        "venue": None,
        "doi": None,
        "arxiv_id": None,
    }
    values.update(fields)
    return ParsedReference.model_validate(values)


class FakeSession:
    def __init__(
        self,
        scan: HeadingScan,
        sections: dict[str, list[SectionContent]],
        *,
        references: list[ParsedReferences] | None = None,
        figures: list[FigureScan] | None = None,
        descriptions: dict[str, list[DescribedFigure | Exception]] | None = None,
        delay_seconds: float = 0.0,
    ) -> None:
        self._scan = scan
        self._sections = {title: list(answers) for title, answers in sections.items()}
        self._references = list(references or [])
        self._figures = list(figures or [FigureScan(figures=())])
        self._descriptions = {label: list(a) for label, a in (descriptions or {}).items()}
        self.described: list[str] = []
        self._delay_seconds = delay_seconds
        self._lock = threading.Lock()
        self._running = 0
        self.max_running = 0
        self.prompts: list[str] = []
        self.without_document: list[str] = []
        self.calls_per_title: defaultdict[str, int] = defaultdict(int)

    def ask[T: BaseModel](self, prompt: str, output: type[T], *, with_document: bool = True) -> T:
        with self._lock:
            self.prompts.append(prompt)
            if not with_document:
                self.without_document.append(prompt)
            self._running += 1
            self.max_running = max(self.max_running, self._running)
        try:
            time.sleep(self._delay_seconds)
            return self._answer(prompt, output)
        finally:
            with self._lock:
                self._running -= 1

    def opener(self) -> SessionOpener:
        def open_fake(config: DocumentConfig, pdf: bytes) -> DocumentSession:
            del config, pdf
            return self

        return open_fake

    def _answer[T: BaseModel](self, prompt: str, output: type[T]) -> T:
        answer: BaseModel
        if output is HeadingScan:
            answer = self._scan
        elif output is ParsedReferences:
            answer = self._references_answer(prompt)
        elif output is FigureScan:
            with self._lock:
                answer = self._figures.pop(0) if len(self._figures) > 1 else self._figures[0]
        elif output is DescribedFigure:
            answer = self._description_answer(prompt)
        else:
            match = ASKED_TITLE.search(prompt)
            assert match is not None, "o prompt da chamada 2 não diz qual seção quer"
            title = match.group(1)
            with self._lock:
                self.calls_per_title[title] += 1
                answers = self._sections.get(title) or [
                    SectionContent(text="", has_footnotes=False)
                ]
                answer = answers.pop(0) if len(answers) > 1 else answers[0]
        assert isinstance(answer, output)
        return answer

    def _references_answer(self, prompt: str) -> ParsedReferences:
        with self._lock:
            if self._references:
                return self._references.pop(0) if len(self._references) > 1 else self._references[0]
        match = REFERENCES_TEXT.search(prompt)
        assert match is not None, "o prompt das referências não traz a lista"
        paragraphs = [p.strip() for p in match.group(1).split("\n\n") if p.strip()]
        return ParsedReferences(references=tuple(raw_entry(p) for p in paragraphs))

    def _description_answer(self, prompt: str) -> DescribedFigure:
        """A próxima resposta roteirizada para a figura do prompt; sem roteiro, uma genérica.
        Uma exceção no roteiro é levantada, como uma chamada que falhou."""
        match = ASKED_FIGURE.search(prompt)
        assert match is not None, "o prompt da descrição não diz qual figura quer"
        label = match.group(1)
        with self._lock:
            self.described.append(label)
            answers = self._descriptions.get(label) or [described()]
            answer = answers.pop(0) if len(answers) > 1 else answers[0]
        if isinstance(answer, Exception):
            raise answer
        if not answer.caption_start:
            # Sem roteiro para isso, a figura descrita é a certa: o começo da legenda pedida.
            caption = ASKED_CAPTION.search(prompt)
            assert caption is not None
            answer = answer.model_copy(update={"caption_start": caption.group(1)[:60]})
        return answer
