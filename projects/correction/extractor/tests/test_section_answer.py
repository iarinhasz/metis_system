"""Uma seção conferida contra o PDF: nova tentativa com dica e a melhor resposta no fim."""

from pydantic import BaseModel

from projects.correction.extractor.configs import ARTICLE_CONFIG
from projects.correction.extractor.schemas import SectionContent
from projects.correction.extractor.section_answer import ask_section

FIRST = "Filas de mensagens desacoplam produtores e consumidores em sistemas distribuidos."
SECOND = "Medir o tempo de resposta ajuda a dimensionar a quantidade de consumidores necessaria."
FOREIGN = "Este paragrafo pertence a outra secao do artigo e foi copiado no lugar errado."
LOCAL = f"\n{FIRST}\n{SECOND}\n"
PROMPT = 'Seção: "1 Introducao"'


class ScriptedSession:
    """Devolve as respostas na ordem; a última se repete."""

    def __init__(self, *texts: str) -> None:
        self._answers = [SectionContent(text=text, has_footnotes=False) for text in texts]
        self.prompts: list[str] = []

    def ask[T: BaseModel](self, prompt: str, output: type[T]) -> T:
        self.prompts.append(prompt)
        answer = self._answers.pop(0) if len(self._answers) > 1 else self._answers[0]
        assert isinstance(answer, output)
        return answer


def test_a_good_answer_is_asked_once() -> None:
    session = ScriptedSession(f"{FIRST}\n\n{SECOND}")

    answer = ask_section(session, ARTICLE_CONFIG, PROMPT, LOCAL)

    assert (answer.coverage, answer.fidelity) == (1.0, 1.0)
    assert session.prompts == [PROMPT]


def test_retry_quotes_what_was_left_out() -> None:
    session = ScriptedSession(FIRST, f"{FIRST}\n\n{SECOND}")

    answer = ask_section(session, ARTICLE_CONFIG, PROMPT, LOCAL)

    assert answer.content.text == f"{FIRST}\n\n{SECOND}"
    retry = session.prompts[1]
    assert retry.startswith(PROMPT)
    assert "deixou de fora" in retry and f"«{SECOND}»" in retry
    assert "não está nesta seção" not in retry


def test_retry_quotes_the_text_that_is_not_from_the_section() -> None:
    session = ScriptedSession(f"{FIRST}\n\n{SECOND}\n\n{FOREIGN}", f"{FIRST}\n\n{SECOND}")

    answer = ask_section(session, ARTICLE_CONFIG, PROMPT, LOCAL)

    assert answer.fidelity == 1.0
    assert "não está nesta seção" in session.prompts[1]
    assert f"«{FIRST}" in session.prompts[1]


def test_section_without_own_text_stays_empty_instead_of_duplicating() -> None:
    # No PDF, o título seguinte vem logo depois deste: a seção não tem prosa própria.
    session = ScriptedSession(FOREIGN)

    answer = ask_section(session, ARTICLE_CONFIG, PROMPT, "\n")

    assert (answer.content.text, answer.coverage, answer.fidelity) == ("", None, None)
    assert len(session.prompts) == 1 + ARTICLE_CONFIG.check_retries


def test_keeps_the_best_answer_when_every_try_fails() -> None:
    session = ScriptedSession(FIRST, FOREIGN)

    answer = ask_section(session, ARTICLE_CONFIG, PROMPT, LOCAL)

    assert answer.content.text == FIRST
    assert answer.coverage is not None and answer.coverage < ARTICLE_CONFIG.min_coverage


def test_no_retry_when_the_config_says_so() -> None:
    session = ScriptedSession(FIRST)
    config = ARTICLE_CONFIG.model_copy(update={"check_retries": 0})

    ask_section(session, config, PROMPT, LOCAL)

    assert len(session.prompts) == 1


def test_unverifiable_section_is_accepted_as_is() -> None:
    session = ScriptedSession(FOREIGN)

    answer = ask_section(session, ARTICLE_CONFIG, PROMPT, None)

    assert (answer.content.text, answer.coverage, answer.fidelity) == (FOREIGN, None, None)
    assert len(session.prompts) == 1
