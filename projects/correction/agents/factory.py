"""Catálogo e construção de um agente novo a cada execução, também no E1."""

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Literal

from agno.agent import Agent
from agno.media import File
from agno.run.agent import RunOutput
from pydantic import BaseModel

from projects.correction.agents.limits import ProviderLimiter, shared_limiter
from projects.correction.agents.models import ModelFactory
from projects.correction.agents.pricing import Pricing
from projects.correction.agents.prompts import RenderedPrompt, render, render_template
from projects.correction.agents.runner import AgentPayload, AgentRunner, MeasuredRunner
from projects.correction.agents.schemas import PendingOutput
from projects.correction.agents.specs import ModelSpec, Role
from projects.correction.agents.usage import NullUsageSink, UsageSink

if TYPE_CHECKING:
    from projects.correction.metis.config import MetisSettings

type Slot = Literal["a", "b", "c"]


class _PrivateAgnoLogs(logging.Filter):
    """O Agno pode registrar respostas inválidas e mensagens do provedor com o manuscrito."""

    def filter(self, record: logging.LogRecord) -> bool:
        if record.levelno < logging.ERROR:
            return False
        record.msg, record.args, record.exc_info = (
            "Falha na chamada Agno; consulte o registro de uso.",
            (),
            None,
        )
        record.exc_text = None
        return True


logging.getLogger("agno").addFilter(_PrivateAgnoLogs())


class AgentFactory:
    def __init__(
        self,
        run_id: str,
        stage: str,
        usage_sink: UsageSink | None = None,
        limiter: ProviderLimiter | None = None,
        *,
        config: MetisSettings | None = None,
        model_factory: ModelFactory | None = None,
        pricing: Pricing | None = None,
        task_id: str | None = None,
    ) -> None:
        if config is None:
            from projects.correction.metis.config import settings

            config = settings
        self.run_id, self.stage, self.task_id = run_id, stage, task_id or run_id
        self.models = model_factory or ModelFactory(
            config.model_specs,
            openai_api_key=config.openai_api_key,
            google_api_key=config.google_api_key or config.gemini_key,
        )
        self.usage_sink = usage_sink if usage_sink is not None else NullUsageSink()
        self.limiter = (
            limiter if limiter is not None else shared_limiter(config.llm_max_concurrency)
        )
        self.pricing = pricing if pricing is not None else Pricing()
        self.prompt_templates: dict[str, str] = {}
        self.prompt_versions: dict[str, str] = {}
        self.on_prompt: Callable[[str, str], None] | None = None

    def _invoke[T: BaseModel](
        self,
        name: str,
        role: Role,
        spec: ModelSpec,
        prompt: RenderedPrompt,
        output_schema: type[T],
        retries: int | None,
    ) -> Callable[[AgentPayload], RunOutput]:
        def invoke(payload: AgentPayload) -> RunOutput:
            agent = Agent(
                model=self.models.build(spec, retries=retries),
                instructions=prompt.text,
                output_schema=output_schema,
                telemetry=False,
                store_media=False,
                retries=0,
                db=None,
                debug_mode=False,
            )
            files = (
                [File(content=payload.document, mime_type=payload.mime_type)]
                if payload.document is not None
                else None
            )
            return agent.run(payload.text(), files=files, run_id=self.task_id)

        return invoke

    def build[T: BaseModel](
        self,
        name: str,
        role: Role,
        output_schema: type[T],
        *,
        prompt: RenderedPrompt | None = None,
        spec: ModelSpec | None = None,
        retries: int | None = None,
        **context: str,
    ) -> AgentRunner[T]:
        selected = spec if spec is not None else self.models.specs[role]
        rendered = prompt or (
            render_template(self.prompt_templates[name], output_schema, **context)
            if name in self.prompt_templates
            else render(name, output_schema, **context)
        )
        self.prompt_versions[name] = rendered.version
        if self.on_prompt is not None:
            self.on_prompt(name, rendered.version)
        return MeasuredRunner(
            self._invoke(name, role, selected, rendered, output_schema, retries),
            output_schema,
            run_id=self.run_id,
            stage=self.stage,
            role=role,
            agent=name,
            spec=selected,
            prompt_version=rendered.version,
            usage_sink=self.usage_sink,
            limiter=self.limiter,
            pricing=self.pricing,
        )

    def figure_describer(
        self, kind: str = "figure", *, output_schema: type[BaseModel] = PendingOutput
    ) -> AgentRunner[BaseModel]:
        return self.build("figure_describer", Role.VISION, output_schema, kind=kind)

    def profiler_field(
        self, *, output_schema: type[BaseModel] = PendingOutput
    ) -> AgentRunner[BaseModel]:
        return self.build("profiler_field", Role.FAST, output_schema)

    def profiler_topic(
        self, field: str, *, output_schema: type[BaseModel] = PendingOutput
    ) -> AgentRunner[BaseModel]:
        return self.build("profiler_topic", Role.FAST, output_schema, field=field)

    def section_role_classifier(
        self, *, output_schema: type[BaseModel] = PendingOutput
    ) -> AgentRunner[BaseModel]:
        return self.build("section_role_classifier", Role.FAST, output_schema)

    def section_reviewer(
        self, slot: Slot, role: str, *, output_schema: type[BaseModel] = PendingOutput
    ) -> AgentRunner[BaseModel]:
        return self.build(f"sections/{role}", self._slot(slot), output_schema)

    def cross_checker(
        self, slot: Slot, kind: str, *, output_schema: type[BaseModel] = PendingOutput
    ) -> AgentRunner[BaseModel]:
        return self.build("cross_checker", self._slot(slot), output_schema, kind=kind)

    def synthesizer(
        self, slot: Slot, *, output_schema: type[BaseModel] = PendingOutput
    ) -> AgentRunner[BaseModel]:
        return self.build("synthesizer", self._slot(slot), output_schema)

    def whole_document_reviewer(
        self, slot: Slot, *, output_schema: type[BaseModel] = PendingOutput
    ) -> AgentRunner[BaseModel]:
        return self.build("whole_document_reviewer", self._slot(slot), output_schema)

    def reviser(
        self, slot: Slot, level: str, *, output_schema: type[BaseModel] = PendingOutput
    ) -> AgentRunner[BaseModel]:
        return self.build("reviser", self._slot(slot), output_schema, level=level)

    def judge(
        self, for_spec: ModelSpec, *, output_schema: type[BaseModel] = PendingOutput
    ) -> AgentRunner[BaseModel]:
        return self.build("judge", self.models.judge_role(for_spec), output_schema)

    def meta_reviewer(
        self, *, output_schema: type[BaseModel] = PendingOutput
    ) -> AgentRunner[BaseModel]:
        return self.build("meta_reviewer", Role.META_REVIEWER, output_schema)

    def plagiarism_adjudicator(
        self, *, output_schema: type[BaseModel] = PendingOutput
    ) -> AgentRunner[BaseModel]:
        return self.build("plagiarism_adjudicator", Role.ADJUDICATOR, output_schema)

    def reference_adjudicator(
        self, *, output_schema: type[BaseModel] = PendingOutput
    ) -> AgentRunner[BaseModel]:
        return self.build("reference_adjudicator", Role.FAST, output_schema)

    def citation_alignment_judge(
        self, *, output_schema: type[BaseModel] = PendingOutput
    ) -> AgentRunner[BaseModel]:
        return self.build("citation_alignment_judge", Role.ADJUDICATOR, output_schema)

    def integrity_narrator(
        self, *, output_schema: type[BaseModel] = PendingOutput
    ) -> AgentRunner[BaseModel]:
        return self.build("integrity_narrator", Role.FAST, output_schema)

    def question_drafter(
        self, *, output_schema: type[BaseModel] = PendingOutput
    ) -> AgentRunner[BaseModel]:
        return self.build("question_drafter", Role.META_REVIEWER, output_schema)

    @staticmethod
    def _slot(slot: Slot) -> Role:
        return Role(f"evaluator_{slot}")
