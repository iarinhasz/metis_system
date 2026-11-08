"""Todo acesso ao banco do app attempts: um Management por model.

API, pipeline e services chamam estes métodos; não usam o ORM direto.
"""

from projects.correction.attempts.queries.articles import ArticleManagement
from projects.correction.attempts.queries.attempts import AttemptManagement
from projects.correction.attempts.queries.health import database_is_available
from projects.correction.attempts.queries.run_events import RunEventManagement
from projects.correction.attempts.queries.runs import (
    InvalidTransition,
    RunConflict,
    RunManagement,
)

__all__ = (
    "ArticleManagement",
    "AttemptManagement",
    "InvalidTransition",
    "RunConflict",
    "RunEventManagement",
    "RunManagement",
    "database_is_available",
)
