"""Rascunha uma rubrica a partir de taxonomia e método, sem receber manuscritos."""

import json
import uuid

from projects.correction.agents.factory import AgentFactory
from projects.correction.agents.runner import AgentPayload
from projects.correction.agents.schemas.curation import DraftQuestion
from projects.correction.questions.criteria import get_method
from projects.correction.questions.curation_errors import CurationError
from projects.correction.questions.models import Question, TaxonomyNode
from projects.correction.questions.taxonomy import TaxonomyLevel


def draft_question(
    *,
    method: str,
    taxonomy_node_id: uuid.UUID | None = None,
    factory: AgentFactory | None = None,
    max_attempts: int = 3,
) -> Question:
    config = get_method(method)
    if max_attempts < 1:
        raise ValueError("O orçamento do rascunho deve ser positivo.")
    node = TaxonomyNode.get_for_curation(taxonomy_node_id) if taxonomy_node_id else None
    if node is not None and node.level == TaxonomyLevel.DOMAIN:
        raise CurationError("Escolha um field, subfield ou topic, ou a Question genérica.")
    path = []
    current = node
    while current is not None:
        path.append({"code": current.code, "name": current.name, "level": current.level})
        current = current.parent
    context = {
        "scope": "generic" if node is None else "taxonomy",
        "taxonomy_version": node.taxonomy_version if node else None,
        "area_path": list(reversed(path)),
        "evaluation_method": config.model_dump(mode="json"),
    }
    selected = factory or AgentFactory(str(uuid.uuid7()), "curation")
    runner = selected.question_drafter(output_schema=DraftQuestion)
    prompt = "Contexto de curadoria:\n" + json.dumps(context, ensure_ascii=False)
    for attempt in range(max_attempts):
        hint = (
            ""
            if attempt == 0
            else "\nCorrija a saída: nome e textos não vazios; "
            "uma rubrica por critério, sem repetir chaves."
        )
        result = runner.run(AgentPayload(prompt + hint))
        if result.valid and isinstance(result.content, DraftQuestion):
            return Question.store_draft(result.content, method=method, taxonomy_node=node)
    raise CurationError("O agente não produziu um rascunho válido. Nenhuma Question foi gravada.")
