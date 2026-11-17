"""O catálogo inteiro funciona sem chave e aceita roteiros de falha semântica."""

import pytest
from pydantic import BaseModel, Field

from projects.correction.agents.errors import LLMUnavailable
from projects.correction.agents.fakes import (
    FakeAgentFactory,
    InvalidFor,
    MissingElsewhere,
    QuoteNotInDocument,
)
from projects.correction.agents.runner import AgentPayload
from projects.correction.agents.specs import Role
from projects.correction.agents.usage import MemoryUsageSink
from projects.correction.metis.config import MetisSettings


def test_fake_covers_every_catalog_method_and_model_role() -> None:
    sink = MemoryUsageSink()
    factory = FakeAgentFactory(usage_sink=sink)
    runners = [
        factory.figure_describer("table"),
        factory.profiler_field(),
        factory.profiler_topic("computação"),
        factory.section_role_classifier(),
        factory.section_reviewer("a", "introduction"),
        factory.section_reviewer("b", "method"),
        factory.cross_checker("c", "results-method"),
        factory.synthesizer("a"),
        factory.whole_document_reviewer("b"),
        factory.reviser("c", "item"),
        factory.judge(factory.models.specs[Role.EVALUATOR_A]),
        factory.judge(factory.models.specs[Role.EVALUATOR_B]),
        factory.meta_reviewer(),
        factory.plagiarism_adjudicator(),
        factory.reference_adjudicator(),
        factory.citation_alignment_judge(),
        factory.integrity_narrator(),
        factory.question_drafter(),
    ]
    assert all(runner.run("dados sintéticos").valid for runner in runners)
    assert len(sink.calls) == len(runners) == len(factory.calls)
    assert {call.role for call in sink.calls} == set(Role)


def test_invalid_n_times_then_valid_and_unavailable() -> None:
    sink = MemoryUsageSink()
    factory = FakeAgentFactory(usage_sink=sink, scripts={Role.FAST: [InvalidFor(2)]})
    runner = factory.profiler_field()
    assert not runner.run("um").valid
    assert not runner.run("dois").valid
    assert runner.run("três").valid
    assert len(sink.calls) == 3
    failed = FakeAgentFactory(usage_sink=sink, scripts={"judge": [LLMUnavailable("sintético")]})
    with pytest.raises(LLMUnavailable):
        failed.judge(failed.models.specs[Role.EVALUATOR_C]).run("teste")
    assert len(sink.calls) == 4 and not sink.calls[-1].success


class Observation(BaseModel):
    quote: str = Field(examples=["Trecho presente."])
    missing: bool


def test_invalid_quote_and_false_missing_stay_structurally_valid() -> None:
    factory = FakeAgentFactory(
        scripts={"sections/introduction": [QuoteNotInDocument(), MissingElsewhere()]}
    )
    runner = factory.section_reviewer("a", "introduction", output_schema=Observation)
    quote = runner.run("Trecho presente.")
    missing = runner.run("O dado existe em outra seção.")
    assert quote.valid and isinstance(quote.content, Observation)
    assert quote.content.quote not in "Trecho presente."
    assert missing.valid and isinstance(missing.content, Observation) and missing.content.missing


def test_prompt_version_excludes_the_article_and_requests_keep_it_as_prefix() -> None:
    factory = FakeAgentFactory()
    runner = factory.profiler_field()
    first = runner.run(AgentPayload("classifique", article="artigo A"))
    second = runner.run(AgentPayload("classifique", article="artigo B"))
    assert first.usage.prompt_version == second.usage.prompt_version
    assert factory.calls[0].payload.text() == "<artigo>\nartigo A\n</artigo>\n\nclassifique"


def test_role_script_is_independent_of_a_shared_model_spec() -> None:
    spec = MetisSettings(_env_file=None).evaluator_a
    config = MetisSettings(_env_file=None, evaluator_a=spec, fast=spec)
    factory = FakeAgentFactory(config=config, scripts={Role.FAST: [InvalidFor(1)]})
    runner = factory.profiler_field()
    assert not runner.run("primeira chamada").valid
    assert runner.run("segunda chamada").valid


def test_dictionary_outside_the_schema_is_reported_as_invalid_output() -> None:
    sink = MemoryUsageSink()
    factory = FakeAgentFactory(usage_sink=sink, scripts={"profiler_field": [{"unexpected": True}]})
    result = factory.profiler_field().run("sintético")
    assert not result.valid and result.content is None
    assert sink.calls[0].error == "InvalidOutput" and not sink.calls[0].success
