"""Resolve a Question pela cadeia topic → subfield → field → genérica."""

import math

from projects.correction.metis.config import settings
from projects.correction.pipeline.errors import SetupRequired
from projects.correction.questions.models import Question, TaxonomyNode
from projects.correction.questions.profile import (
    ArticleProfile,
    ResolutionHop,
    ResolutionScope,
    ResolvedQuestion,
)


def resolve_question(
    profile: ArticleProfile, *, method: str, confidence_threshold: float | None = None
) -> ResolvedQuestion:
    threshold = (
        settings.profiling_confidence_threshold
        if confidence_threshold is None
        else confidence_threshold
    )
    if not math.isfinite(threshold) or not 0 <= threshold <= 1:
        raise ValueError("O limiar de confiança deve ficar entre zero e um.")
    if not method.strip():
        raise ValueError("Informe o método de avaliação para resolver a Question.")
    path = TaxonomyNode.path_for_topic(profile.taxonomy_version, profile.area_path[-1].code)
    if tuple(node.code for node in path) != tuple(node.code for node in profile.area_path):
        raise SetupRequired("O caminho do perfil não pertence à versão da taxonomia informada.")
    uncertain = profile.confidence < threshold
    codes = () if uncertain else tuple(node.code for node in reversed(path[1:]))
    candidates = {
        question.taxonomy_node_code: question
        for question in Question.resolution_candidates(
            method=method, taxonomy_version=profile.taxonomy_version, codes=codes
        )
    }
    hops = []
    scopes = (ResolutionScope.TOPIC, ResolutionScope.SUBFIELD, ResolutionScope.FIELD)
    chain = [*zip(scopes, codes, strict=False), (ResolutionScope.GENERIC, None)]
    for scope, code in chain:
        question = candidates.get(code)
        hops.append(ResolutionHop(scope=scope, code=code, matched=question is not None))
        if question is not None:
            return ResolvedQuestion(
                question=question,
                taxonomy_version=profile.taxonomy_version,
                resolution_path=tuple(hops),
                uncertain=uncertain,
            )
    raise SetupRequired("Nenhuma Question validada e ativa disponível, nem a genérica.")
