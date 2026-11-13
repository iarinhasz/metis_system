"""Enums por field, validação do parentesco e orçamento de tentativas do profiler."""

import json
from typing import Any

import pytest
from pydantic import ValidationError

from projects.correction.agents.errors import LLMUnavailable
from projects.correction.agents.factory import AgentFactory
from projects.correction.agents.fakes import FakeAgentFactory, InvalidFor
from projects.correction.agents.models import ModelFactory
from projects.correction.agents.schemas.examples import schema_example
from projects.correction.agents.schemas.profiling import field_choice_schema, topic_choice_schema
from projects.correction.agents.specs import Provider, Role, development_spec
from projects.correction.agents.tests.contract_support import answer
from projects.correction.agents.tests.http_stub import provider_server
from projects.correction.agents.usage import MemoryUsageSink
from projects.correction.attempts.models import LLMCall, Run
from projects.correction.attempts.status import RunStatus, Stage
from projects.correction.metis.config import MetisSettings
from projects.correction.pipeline.errors import InvalidSubmission, SetupRequired
from projects.correction.pipeline.publishing import publish_stage
from projects.correction.pipeline.stages import ProfilingStage, StageContext, StageOutcome
from projects.correction.pipeline.usage import DatabaseUsageSink
from projects.correction.questions.profiler import InvalidProfile, profile_article
from projects.correction.questions.taxonomy import TaxonomyLevel, TaxonomySnapshot
from projects.correction.questions.tests.profiling_helpers import (
    FIELD,
    OTHER_FIELD,
    OTHER_SUBFIELD,
    OTHER_TOPIC,
    PRIVATE_TEXT,
    SUBFIELD,
    SYNTHETIC_SUBFIELD,
    TOPIC,
    article,
    field_answer,
    topic_answer,
)

pytestmark = pytest.mark.django_db


def test_profile_uses_fast_twice_and_returns_an_auditable_path(
    profiling_taxonomy: TaxonomySnapshot,
) -> None:
    sink = MemoryUsageSink()
    factory = FakeAgentFactory(
        usage_sink=sink,
        scripts={
            "profiler_field": [field_answer()],
            "profiler_topic": [topic_answer(secondary=(OTHER_FIELD, OTHER_FIELD, FIELD))],
        },
    )
    profile = profile_article(
        article(), factory=factory, taxonomy_version=profiling_taxonomy.version
    )
    assert [call.name for call in factory.calls] == ["profiler_field", "profiler_topic"]
    assert all(call.role == Role.FAST for call in sink.calls)
    assert profile.taxonomy_version == profiling_taxonomy.version
    assert tuple(node.level for node in profile.area_path) == tuple(TaxonomyLevel)
    assert profile.area_path[1].code == FIELD and profile.area_path[-1].code == TOPIC
    assert profile.confidence == 0.9
    assert profile.language == "pt" and profile.keywords == ("rochas", "geoquímica")
    assert tuple(node.code for node in profile.secondary_areas) == (OTHER_FIELD,)
    assert all(PRIVATE_TEXT in (call.payload.article or "") for call in factory.calls)
    assert all(PRIVATE_TEXT not in call.payload.prompt for call in factory.calls)
    second_options = factory.calls[1].payload.prompt.split("\nÁreas secundárias")[0]
    assert TOPIC in second_options and OTHER_TOPIC not in second_options
    assert profile.model_validate_json(profile.model_dump_json()) == profile


@pytest.mark.parametrize("field", [FIELD, OTHER_FIELD])
def test_dynamic_schemas_and_their_generated_examples_are_valid(field: str) -> None:
    schema = field_choice_schema((field,))
    assert schema_example(schema).field == field
    topic_schema = topic_choice_schema({TOPIC: SUBFIELD}, (FIELD, OTHER_FIELD))
    assert schema_example(topic_schema).topic == TOPIC
    with pytest.raises(ValidationError):
        topic_schema.model_validate(topic_answer(topic=OTHER_TOPIC, subfield=OTHER_SUBFIELD))
    with pytest.raises(ValidationError):
        topic_schema.model_validate(topic_answer(secondary=("inventada",)))


@pytest.mark.parametrize("step", ["profiler_field", "profiler_topic"])
def test_invalid_output_retries_with_a_reason_without_repeating_the_first_step(
    profiling_taxonomy: TaxonomySnapshot, step: str
) -> None:
    scripts: dict[str, list[object]] = {
        "profiler_field": [field_answer()],
        "profiler_topic": [topic_answer()],
    }
    scripts[step].insert(0, InvalidFor(1))
    factory = FakeAgentFactory(scripts=scripts)
    profile = profile_article(
        article(), factory=factory, taxonomy_version=profiling_taxonomy.version
    )
    calls = [call for call in factory.calls if call.name == step]
    assert len(calls) == 2 and "Resposta anterior recusada" in calls[1].payload.prompt
    assert "json_invalid" in calls[1].payload.prompt
    assert profile.area_path[-1].code == TOPIC
    assert len(factory.calls) == 3


@pytest.mark.parametrize(
    "wrong",
    [
        topic_answer(topic=OTHER_TOPIC, subfield=OTHER_SUBFIELD),
        topic_answer(subfield=SYNTHETIC_SUBFIELD),
        topic_answer(confidence=float("nan")),
        topic_answer(confidence=1.1),
    ],
)
def test_foreign_topic_wrong_pair_and_invalid_confidence_are_retried(
    profiling_taxonomy: TaxonomySnapshot, wrong: dict[str, object]
) -> None:
    sink = MemoryUsageSink()
    factory = FakeAgentFactory(
        usage_sink=sink,
        scripts={"profiler_field": [field_answer()], "profiler_topic": [wrong, topic_answer()]},
    )
    profile = profile_article(
        article(), factory=factory, taxonomy_version=profiling_taxonomy.version
    )
    assert profile.area_path[-1].code == TOPIC
    assert len(factory.calls) == len(sink.calls) == 3
    assert not sink.calls[1].success and sink.calls[1].error == "InvalidOutput"


@pytest.mark.parametrize("unknown_key", [False, True])
def test_feedback_and_final_error_do_not_copy_invalid_manuscript_values(
    profiling_taxonomy: TaxonomySnapshot,
    unknown_key: bool,
) -> None:
    wrong = (
        field_answer() | {PRIVATE_TEXT: "value"}
        if unknown_key
        else field_answer(field=PRIVATE_TEXT)
    )
    factory = FakeAgentFactory(scripts={"profiler_field": [wrong] * 2})
    with pytest.raises(InvalidProfile) as raised:
        profile_article(
            article(), factory=factory, taxonomy_version=profiling_taxonomy.version, max_attempts=2
        )
    assert raised.value.failure_status == RunStatus.ERROR_LLM
    assert PRIVATE_TEXT not in str(raised.value)
    assert PRIVATE_TEXT not in factory.calls[1].payload.prompt
    assert ("extra_forbidden" if unknown_key else "enum") in factory.calls[1].payload.prompt


def test_provider_failure_propagates_for_celery_retry(profiling_taxonomy: TaxonomySnapshot) -> None:
    factory = FakeAgentFactory(scripts={"profiler_field": [LLMUnavailable("503")]})
    with pytest.raises(LLMUnavailable):
        profile_article(article(), factory=factory, taxonomy_version=profiling_taxonomy.version)
    assert len(factory.calls) == 1


def test_missing_taxonomy_is_setup_error_without_calling_agents() -> None:
    factory = FakeAgentFactory()
    with pytest.raises(SetupRequired):
        profile_article(article(), factory=factory, taxonomy_version="desconhecida")
    assert factory.calls == []


def test_missing_abstract_is_invalid_submission(profiling_taxonomy: TaxonomySnapshot) -> None:
    factory = FakeAgentFactory()
    with pytest.raises(InvalidSubmission):
        profile_article(
            article().model_copy(update={"sections": ()}),
            factory=factory,
            taxonomy_version=profiling_taxonomy.version,
        )
    assert not factory.calls


@pytest.mark.parametrize("provider", list(Provider))
def test_real_sdk_respects_the_dynamic_schema_and_retries_foreign_topics(
    profiling_taxonomy: TaxonomySnapshot, provider: Provider
) -> None:
    config = MetisSettings(
        _env_file=None,
        fast=development_spec(
            Role.EVALUATOR_A if provider is Provider.OPENAI else Role.EVALUATOR_B
        ),
    )
    sink = MemoryUsageSink()
    with provider_server() as server:
        server.queue(
            answer(provider.value, json.dumps(field_answer())),
            answer(
                provider.value, json.dumps(topic_answer(topic=OTHER_TOPIC, subfield=OTHER_SUBFIELD))
            ),
            answer(provider.value, json.dumps(topic_answer())),
        )
        models = ModelFactory(
            config.model_specs,
            openai_api_key="sintetica",
            google_api_key="sintetica",
            retries=0,
            client_params={
                provider: {"base_url": f"{server.url}/v1"}
                if provider is Provider.OPENAI
                else {"http_options": {"base_url": server.url}}
            },
        )
        factory = AgentFactory(
            "run-sintetico", Stage.PROFILING, sink, config=config, model_factory=models
        )
        profile = profile_article(
            article(), factory=factory, taxonomy_version=profiling_taxonomy.version
        )
        assert profile.area_path[-1].code == TOPIC
        assert len(server.requests) == len(sink.calls) == 3
        assert not sink.calls[1].success and sink.calls[1].error == "InvalidOutput"


@pytest.mark.parametrize("field_confidence,topic_confidence", [(0.2, 0.9), (0.9, 0.2)])
def test_profile_confidence_is_the_lower_of_both_steps(
    profiling_taxonomy: TaxonomySnapshot, field_confidence: float, topic_confidence: float
) -> None:
    factory = FakeAgentFactory(
        scripts={
            "profiler_field": [field_answer(confidence=field_confidence)],
            "profiler_topic": [topic_answer(confidence=topic_confidence)],
        }
    )
    profile = profile_article(
        article(), factory=factory, taxonomy_version=profiling_taxonomy.version
    )
    assert profile.confidence == min(field_confidence, topic_confidence)


@pytest.mark.parametrize(
    "options",
    [
        {"profiling_max_attempts": 0},
        {"profiling_confidence_threshold": -0.1},
        {"profiling_confidence_threshold": float("nan")},
    ],
)
def test_profiler_settings_are_validated(options: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        MetisSettings(_env_file=None, **options)


@pytest.mark.django_db(transaction=True)
@pytest.mark.usefixtures("eager_celery")
def test_exhausted_invalid_answers_end_the_stage_in_error_llm(
    profiling_taxonomy: TaxonomySnapshot, run: Run, monkeypatch: pytest.MonkeyPatch
) -> None:
    factory = FakeAgentFactory(
        run_id=str(run.pk),
        stage=Stage.PROFILING,
        usage_sink=DatabaseUsageSink(),
        scripts={"profiler_field": [InvalidFor(50)]},
    )

    def execute(self: ProfilingStage, ctx: StageContext) -> StageOutcome:
        profile_article(
            article(), factory=factory, taxonomy_version=profiling_taxonomy.version, max_attempts=2
        )
        return StageOutcome()

    monkeypatch.setattr(ProfilingStage, "execute", execute)
    publish_stage(str(run.pk), Stage.EXTRACTION)
    failed = Run.get_by_id(run.pk)
    assert failed.status == RunStatus.ERROR_LLM and failed.stage == Stage.PROFILING
    assert len(factory.calls) == len(LLMCall.for_run(run.pk)) == 2
    assert PRIVATE_TEXT not in failed.last_error
