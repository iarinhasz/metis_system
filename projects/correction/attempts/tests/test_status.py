"""Cobertura estrutural da máquina de estados."""

from projects.correction.attempts.status import (
    CHECKPOINTS,
    FINAL,
    RECOVERABLE,
    RUNNING,
    STAGES,
    TRANSITIONS,
    RunStatus,
)


def test_every_status_has_an_entry() -> None:
    assert set(TRANSITIONS) == set(RunStatus)


def test_final_statuses_have_no_exits() -> None:
    assert all(not TRANSITIONS[status] for status in FINAL)


def test_each_stage_can_start_and_finish() -> None:
    for stage in STAGES:
        assert stage.running in TRANSITIONS[stage.checkpoint]
        assert stage.completed in TRANSITIONS[stage.running]


def test_running_status_can_return_to_its_checkpoint() -> None:
    for stage in STAGES:
        assert stage.checkpoint in TRANSITIONS[stage.running]


def test_recoverable_statuses_reach_every_checkpoint() -> None:
    for status in RECOVERABLE:
        assert CHECKPOINTS <= TRANSITIONS[status]


def test_status_sets_cover_pipeline_states() -> None:
    assert len(RUNNING) == len(STAGES)
