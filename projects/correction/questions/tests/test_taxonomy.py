"""A versão representa só o conteúdo da árvore, sem depender da ordem ou da data."""

from typing import Any

import pytest
from pydantic import TypeAdapter

from projects.correction.questions.taxonomy import TaxonomySnapshot
from projects.correction.scholarly.openalex import OpenAlexTopic


def test_version_does_not_depend_on_topic_order(recorded_topics: list[dict[str, Any]]) -> None:
    topics = tuple(TypeAdapter(list[OpenAlexTopic]).validate_python(recorded_topics))
    assert TaxonomySnapshot.from_topics(topics) == TaxonomySnapshot.from_topics(topics[::-1])


def test_conflicting_parent_chain_is_rejected(recorded_topics: list[dict[str, Any]]) -> None:
    recorded_topics[1]["subfield"] = recorded_topics[0]["subfield"]
    topics = tuple(TypeAdapter(list[OpenAlexTopic]).validate_python(recorded_topics))
    with pytest.raises(ValueError, match="parentesco divergente"):
        TaxonomySnapshot.from_topics(topics)
