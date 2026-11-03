"""Estados e transições explícitas da execução do pipeline."""

from dataclasses import dataclass
from enum import StrEnum


class RunStatus(StrEnum):
    RECEIVED = "received"
    EXTRACTING = "extracting"
    EXTRACTED = "extracted"
    PROFILING = "profiling"
    PROFILED = "profiled"
    CHECKING_INTEGRITY = "checking_integrity"
    INTEGRITY_CHECKED = "integrity_checked"
    WAITING_HUMAN_REVIEW = "waiting_human_review"
    EVALUATING = "evaluating"
    EVALUATED = "evaluated"
    CONSOLIDATING = "consolidating"
    DONE = "done"
    REJECTED_INVALID_SUBMISSION = "rejected_invalid_submission"
    CLOSED_BY_REVIEWER = "closed_by_reviewer"
    SUPERSEDED = "superseded"
    WAITING_SETUP = "waiting_setup"
    ERROR_LLM = "error_llm"
    ERROR_EXTERNAL = "error_external"
    ERROR_UNEXPECTED = "error_unexpected"


class Stage(StrEnum):
    EXTRACTION = "extraction"
    PROFILING = "profiling"
    INTEGRITY = "integrity"
    EVALUATION = "evaluation"
    CONSOLIDATION = "consolidation"


class HumanDecision(StrEnum):
    CONTINUE = "continue"
    CLOSE = "close"


@dataclass(frozen=True)
class StageSpec:
    stage: Stage
    checkpoint: RunStatus
    running: RunStatus
    completed: RunStatus


STAGES = (
    StageSpec(Stage.EXTRACTION, RunStatus.RECEIVED, RunStatus.EXTRACTING, RunStatus.EXTRACTED),
    StageSpec(Stage.PROFILING, RunStatus.EXTRACTED, RunStatus.PROFILING, RunStatus.PROFILED),
    StageSpec(
        Stage.INTEGRITY,
        RunStatus.PROFILED,
        RunStatus.CHECKING_INTEGRITY,
        RunStatus.INTEGRITY_CHECKED,
    ),
    StageSpec(
        Stage.EVALUATION,
        RunStatus.INTEGRITY_CHECKED,
        RunStatus.EVALUATING,
        RunStatus.EVALUATED,
    ),
    StageSpec(Stage.CONSOLIDATION, RunStatus.EVALUATED, RunStatus.CONSOLIDATING, RunStatus.DONE),
)

STAGE_BY_NAME = {spec.stage: spec for spec in STAGES}
STAGE_BY_RUNNING_STATUS = {spec.running: spec for spec in STAGES}
CHECKPOINTS = frozenset(spec.checkpoint for spec in STAGES)
RUNNING = frozenset(spec.running for spec in STAGES)
FINAL = frozenset(
    {
        RunStatus.DONE,
        RunStatus.REJECTED_INVALID_SUBMISSION,
        RunStatus.CLOSED_BY_REVIEWER,
        RunStatus.SUPERSEDED,
    }
)
RECOVERABLE = frozenset(
    {
        RunStatus.WAITING_SETUP,
        RunStatus.ERROR_LLM,
        RunStatus.ERROR_EXTERNAL,
        RunStatus.ERROR_UNEXPECTED,
    }
)
STAGE_FAILURES = frozenset(
    {
        RunStatus.REJECTED_INVALID_SUBMISSION,
        *RECOVERABLE,
    }
)

_failures = STAGE_FAILURES
_all_checkpoints = CHECKPOINTS
TRANSITIONS: dict[RunStatus, frozenset[RunStatus]] = {
    RunStatus.RECEIVED: frozenset(
        {RunStatus.EXTRACTING, RunStatus.SUPERSEDED, RunStatus.ERROR_UNEXPECTED}
    ),
    RunStatus.EXTRACTING: frozenset(
        {RunStatus.EXTRACTED, RunStatus.RECEIVED, *_failures, RunStatus.SUPERSEDED}
    ),
    RunStatus.EXTRACTED: frozenset(
        {RunStatus.PROFILING, RunStatus.SUPERSEDED, RunStatus.ERROR_UNEXPECTED}
    ),
    RunStatus.PROFILING: frozenset(
        {RunStatus.PROFILED, RunStatus.EXTRACTED, *_failures, RunStatus.SUPERSEDED}
    ),
    RunStatus.PROFILED: frozenset(
        {RunStatus.CHECKING_INTEGRITY, RunStatus.SUPERSEDED, RunStatus.ERROR_UNEXPECTED}
    ),
    RunStatus.CHECKING_INTEGRITY: frozenset(
        {
            RunStatus.INTEGRITY_CHECKED,
            RunStatus.WAITING_HUMAN_REVIEW,
            RunStatus.PROFILED,
            *_failures,
            RunStatus.SUPERSEDED,
        }
    ),
    RunStatus.INTEGRITY_CHECKED: frozenset(
        {RunStatus.EVALUATING, RunStatus.SUPERSEDED, RunStatus.ERROR_UNEXPECTED}
    ),
    RunStatus.WAITING_HUMAN_REVIEW: frozenset(
        {RunStatus.INTEGRITY_CHECKED, RunStatus.CLOSED_BY_REVIEWER, RunStatus.SUPERSEDED}
    ),
    RunStatus.EVALUATING: frozenset(
        {RunStatus.EVALUATED, RunStatus.INTEGRITY_CHECKED, *_failures, RunStatus.SUPERSEDED}
    ),
    RunStatus.EVALUATED: frozenset(
        {RunStatus.CONSOLIDATING, RunStatus.SUPERSEDED, RunStatus.ERROR_UNEXPECTED}
    ),
    RunStatus.CONSOLIDATING: frozenset(
        {RunStatus.DONE, RunStatus.EVALUATED, *_failures, RunStatus.SUPERSEDED}
    ),
    **{status: frozenset({*_all_checkpoints, RunStatus.SUPERSEDED}) for status in RECOVERABLE},
    **{status: frozenset() for status in FINAL},
}
