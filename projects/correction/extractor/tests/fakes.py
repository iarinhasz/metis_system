"""Sessão falsa: a chamada 1 devolve o mapa roteirizado, e cada chamada 2 devolve a próxima
resposta roteirizada para a seção que o prompt pede."""

import re
import threading
import time
from collections import defaultdict

from pydantic import BaseModel

from projects.correction.extractor.config import DocumentConfig
from projects.correction.extractor.schemas import HeadingScan, SectionContent
from projects.correction.extractor.session import DocumentSession, SessionOpener

ASKED_TITLE = re.compile(r'Seção: "([^"]+)"')


class FakeSession:
    def __init__(
        self,
        scan: HeadingScan,
        sections: dict[str, list[SectionContent]],
        *,
        delay_seconds: float = 0.0,
    ) -> None:
        self._scan = scan
        self._sections = {title: list(answers) for title, answers in sections.items()}
        self._delay_seconds = delay_seconds
        self._lock = threading.Lock()
        self._running = 0
        self.max_running = 0
        self.prompts: list[str] = []
        self.calls_per_title: defaultdict[str, int] = defaultdict(int)

    def ask[T: BaseModel](self, prompt: str, output: type[T]) -> T:
        with self._lock:
            self.prompts.append(prompt)
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
        if output is HeadingScan:
            answer: BaseModel = self._scan
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
