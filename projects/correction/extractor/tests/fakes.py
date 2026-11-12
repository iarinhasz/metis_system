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
    HeadingScan,
    ParsedReference,
    ParsedReferences,
    SectionContent,
)
from projects.correction.extractor.session import DocumentSession, SessionOpener

ASKED_TITLE = re.compile(r'Seção: "([^"]+)"')
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
        delay_seconds: float = 0.0,
    ) -> None:
        self._scan = scan
        self._sections = {title: list(answers) for title, answers in sections.items()}
        self._references = list(references or [])
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
