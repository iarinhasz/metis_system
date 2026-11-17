"""O E3 de verdade no pipeline: grava o relatório e, com risco alto, para no gate humano."""

import json

import pytest

from projects.correction.attempts.models import Run, RunEvent
from projects.correction.attempts.status import RunStatus, Stage
from projects.correction.integrity.models import IntegrityReport
from projects.correction.integrity.summary import integrity_summary
from projects.correction.integrity.tests.conftest import (
    INSTRUCTION,
    WHITE_TEXT,
    UseExtraction,
    article_with,
)
from projects.correction.integrity.workflow import run_integrity
from projects.correction.pipeline.errors import SetupRequired
from projects.correction.pipeline.publishing import publish_stage

pytestmark = [
    pytest.mark.django_db(transaction=True),
    pytest.mark.usefixtures("pipeline_with_real_integrity"),
]


def checked_event(run: Run) -> RunEvent:
    return next(
        e
        for e in RunEvent.for_run(run.pk)
        if e.stage == Stage.INTEGRITY and e.to_status != RunStatus.CHECKING_INTEGRITY
    )


def test_a_hidden_instruction_stops_the_run_at_the_human_gate(
    run: Run, use_extraction: UseExtraction
) -> None:
    use_extraction(article_with((INSTRUCTION,)))

    publish_stage(str(run.pk), Stage.EXTRACTION)

    assert Run.get_by_id(run.pk).status == RunStatus.WAITING_HUMAN_REVIEW
    report = IntegrityReport.for_run(run.pk)
    assert report is not None and report.risk == "high"
    [found] = IntegrityReport.findings_for(run.pk)
    assert found.kind == "hidden_instruction"
    event = checked_event(run)
    assert event.payload["risk"] == "high" and event.payload["high"] == 1
    assert "IGNORE" not in json.dumps(event.payload)


def test_hidden_text_without_instruction_is_low_risk_and_the_run_goes_on(
    run: Run, use_extraction: UseExtraction
) -> None:
    use_extraction(article_with((WHITE_TEXT,)))

    publish_stage(str(run.pk), Stage.EXTRACTION)

    assert Run.get_by_id(run.pk).status == RunStatus.DONE
    report = IntegrityReport.for_run(run.pk)
    assert report is not None and report.risk == "low"
    assert report.coverage == {"hidden_text": True}
    assert len(IntegrityReport.findings_for(run.pk)) == 1


def test_the_final_report_summary_reads_the_integrity_report(
    run: Run, use_extraction: UseExtraction
) -> None:
    use_extraction(article_with((WHITE_TEXT,)))
    publish_stage(str(run.pk), Stage.EXTRACTION)

    summary = integrity_summary(run.pk)

    assert summary is not None
    assert (summary.status, summary.risk_level) == ("checked", "low")
    assert summary.findings == ("Texto escondido na página 2: da cor do fundo.",)
    assert summary.coverage == {"integrity_stage_implemented": True, "hidden_text": True}


def test_without_a_report_there_is_no_summary(run: Run) -> None:
    assert integrity_summary(run.pk) is None


def test_the_check_needs_the_extraction(run: Run) -> None:
    with pytest.raises(SetupRequired):
        run_integrity(str(run.pk), "task-1")
