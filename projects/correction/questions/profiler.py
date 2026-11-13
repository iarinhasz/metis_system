"""Dois passos com enums fechados e tentativas limitadas, sem persistência do workflow."""

import json

from pydantic import BaseModel, ValidationError

from projects.correction.agents.factory import AgentFactory
from projects.correction.agents.runner import AgentPayload, AgentRunner
from projects.correction.agents.schemas.profiling import field_choice_schema, topic_choice_schema
from projects.correction.attempts.status import RunStatus
from projects.correction.extractor.article import ExtractedArticle
from projects.correction.metis.config import settings
from projects.correction.pipeline.errors import InvalidSubmission, SetupRequired, StageError
from projects.correction.questions.models import TaxonomyNode
from projects.correction.questions.profile import AreaNode, ArticleProfile
from projects.correction.questions.taxonomy import TaxonomyLevel


class InvalidProfile(StageError):
    """O orçamento de respostas inválidas acabou; o estágio termina em error_llm."""

    failure_status = RunStatus.ERROR_LLM


def profile_article(
    article: ExtractedArticle,
    *,
    factory: AgentFactory,
    taxonomy_version: str,
    keywords: tuple[str, ...] = (),
    max_attempts: int | None = None,
) -> ArticleProfile:
    attempts = settings.profiling_max_attempts if max_attempts is None else max_attempts
    if attempts < 1:
        raise ValueError("O profiler precisa de pelo menos uma tentativa por passo.")
    abstract = article.section("abstract")
    if not article.title.strip() or abstract is None or not abstract.text.strip():
        raise InvalidSubmission("O profiler precisa de título e abstract não vazios.")
    fields = TaxonomyNode.fields_for_profiling(taxonomy_version)
    if not fields:
        raise SetupRequired("A versão da taxonomia não tem fields disponíveis.")
    field_nodes = {node.code: node for node in fields}
    manuscript = json.dumps(
        {"title": article.title, "abstract": abstract.text, "keywords": keywords},
        ensure_ascii=False,
    )
    field_schema = field_choice_schema(tuple(field_nodes))
    field_choice = _ask(
        factory.profiler_field(output_schema=field_schema),
        field_schema,
        AgentPayload(
            "Escolha o field entre estas opções:\n"
            + json.dumps([{"code": node.code, "name": node.name} for node in fields]),
            article=manuscript,
        ),
        attempts,
        step="field",
    )
    field = field_nodes[field_choice.field]
    topics = TaxonomyNode.topics_for_field(taxonomy_version, field.code)
    if not topics:
        raise SetupRequired("O field escolhido não tem topics nesta versão da taxonomia.")
    topic_nodes = {node.code: node for node in topics}
    parents = {node.code: node.parent.code for node in topics if node.parent is not None}
    topic_schema = topic_choice_schema(parents, tuple(field_nodes))
    topic_choice = _ask(
        factory.profiler_topic(field.name, output_schema=topic_schema),
        topic_schema,
        AgentPayload(
            "Escolha o topic e seu subfield entre estas opções:\n"
            + json.dumps(
                [
                    {
                        "code": node.code,
                        "name": node.name,
                        "subfield": node.parent.code,
                        "subfield_name": node.parent.name,
                    }
                    for node in topics
                    if node.parent is not None
                ]
            )
            + "\nÁreas secundárias são códigos de fields, entre:\n"
            + json.dumps([{"code": node.code, "name": node.name} for node in fields]),
            article=manuscript,
        ),
        attempts,
        step="topic",
    )
    topic = topic_nodes[topic_choice.topic]
    subfield = topic.parent
    domain = field.parent
    assert subfield is not None and domain is not None
    path = tuple(_area(node) for node in (domain, field, subfield, topic))
    return ArticleProfile(
        taxonomy_version=taxonomy_version,
        area_path=(path[0], path[1], path[2], path[3]),
        field_confidence=field_choice.confidence,
        topic_confidence=topic_choice.confidence,
        confidence=min(field_choice.confidence, topic_choice.confidence),
        paper_type=field_choice.paper_type,
        language=field_choice.language,
        keywords=field_choice.keywords,
        secondary_areas=tuple(
            _area(field_nodes[code])
            for code in dict.fromkeys(topic_choice.secondary_areas)
            if code != field.code
        ),
    )


def _area(node: TaxonomyNode) -> AreaNode:
    return AreaNode(code=node.code, name=node.name, level=TaxonomyLevel(node.level))


def _ask[T: BaseModel](
    runner: AgentRunner[BaseModel],
    schema: type[T],
    payload: AgentPayload,
    attempts: int,
    *,
    step: str,
) -> T:
    hint = ""
    for _ in range(attempts):
        result = runner.run(AgentPayload(payload.prompt + hint, article=payload.article))
        if result.valid and isinstance(result.content, schema):
            return result.content
        try:
            if isinstance(result.raw, str):
                schema.model_validate_json(result.raw)
            else:
                schema.model_validate(result.raw)
        except ValidationError as exc:
            # Somente caminhos e códigos de erro; nunca reproduzir input, texto ou contexto.
            reasons = [
                {
                    "field": ".".join(
                        str(part)
                        if isinstance(part, int) or part in schema.model_fields
                        else "unknown"
                        for part in error["loc"]
                    )
                    or "response",
                    "type": error["type"],
                }
                for error in exc.errors(include_input=False, include_context=False)[:5]
            ]
        else:
            reasons = [{"field": "response", "type": "invalid_output"}]
        hint = (
            "\n\nResposta anterior recusada: "
            + json.dumps(reasons, ensure_ascii=False)
            + ". Corrija estes campos e responda no schema, usando somente as opções fornecidas."
        )
    raise InvalidProfile(f"Classificação de {step} inválida após {attempts} tentativas.")
