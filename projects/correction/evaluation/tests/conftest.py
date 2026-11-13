import pytest

from projects.correction.attempts.models import Run
from projects.correction.attempts.status import Stage
from projects.correction.evaluation.tests.helpers import prepare_evaluated


@pytest.fixture
def evaluated_run(run: Run) -> Run:
    return prepare_evaluated(run)


@pytest.fixture
def consolidating_run(evaluated_run: Run) -> Run:
    claimed = Run.claim_stage(evaluated_run.pk, Stage.CONSOLIDATION, "e5")
    assert claimed is not None
    return claimed
