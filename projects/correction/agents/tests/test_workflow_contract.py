"""Contratos do Workflow Agno real com executors sintéticos, sem banco nem provedores externos."""

import subprocess
import sys
from dataclasses import dataclass
from importlib.metadata import version
from threading import Barrier, Event
from uuid import uuid4

import pytest
from agno.run.base import RunStatus
from agno.run.workflow import WorkflowRunOutput
from agno.workflow import Condition, Loop, Parallel, Step, Workflow
from agno.workflow.types import HumanReview, OnError, StepInput, StepOutput
from pydantic import BaseModel


class Choice(BaseModel):
    field: str


@dataclass
class ChooseField:
    value: str
    barrier: Barrier | None = None

    def __call__(self, step_input: StepInput) -> StepOutput:
        assert step_input.input == {"run_id": "sintetico"}
        if self.barrier:
            self.barrier.wait(timeout=5)
        return StepOutput(content=Choice(field=self.value))


def test_installs_agno_3_and_both_sdks_on_python_314() -> None:
    assert sys.version_info[:2] == (3, 14)
    assert version("agno").split(".")[0] == "3"
    assert version("openai") and version("google-genai")


def test_environment_disables_default_telemetry_in_a_fresh_process() -> None:
    subprocess.run(
        [
            sys.executable,
            "-c",
            """
import os
os.environ['AGNO_TELEMETRY'] = 'false'
from agno.agent import Agent
from agno.workflow import Workflow
from agno.workflow.types import StepOutput
from projects.correction.agents.tests.contract_support import answer, model
from projects.correction.agents.tests.http_stub import provider_server

with provider_server() as server:
    server.queue(answer('openai'))
    runner = Agent(model=model('openai', url=server.url))
    runner.run('Teste sintético.')
    assert runner.telemetry is False

workflow = Workflow(steps=[lambda step_input: StepOutput(content='ok')])
workflow.run(input='Teste sintético.')
assert workflow.telemetry is False
""",
        ],
        check=True,
        capture_output=True,
        timeout=60,
    )


def test_callable_executor_keeps_typed_outputs_and_task_id() -> None:
    choice = Choice(field="physics")

    def read(step_input: StepInput) -> StepOutput:
        previous = step_input.get_step_output("choose")
        assert previous is not None and previous.content == choice
        assert isinstance(previous.content, Choice)
        return StepOutput(content=previous.content)

    workflow = Workflow(
        name="typed-contract",
        telemetry=False,
        steps=[
            Step(name="choose", executor=ChooseField("physics"), max_retries=0),
            Step(name="read", executor=read, max_retries=0),
        ],
    )
    task_id = str(uuid4())
    result = workflow.run(input={"run_id": "sintetico"}, run_id=task_id)

    assert isinstance(result, WorkflowRunOutput)
    assert result.status == RunStatus.completed and result.content == choice
    assert result.run_id == task_id
    assert workflow.telemetry is False and workflow.db is None


def test_parallel_preserves_branch_names_and_pydantic_outputs() -> None:
    barrier = Barrier(2)

    def read(step_input: StepInput) -> StepOutput:
        container = step_input.get_step_output("branches")
        assert container is not None and container.steps is not None
        assert [step.step_name for step in container.steps] == ["a", "b"]
        for name in ("a", "b"):
            output = step_input.get_step_output(name)
            assert output is not None and output.content == Choice(field=name)
            assert isinstance(output.content, Choice)
        return StepOutput(content="ok")

    branches = [Step(name=s, executor=ChooseField(s, barrier), max_retries=0) for s in ("a", "b")]
    # A anotação *args do Agno 3.1.12 diz list; em execução ele recebe Steps variádicos.
    parallel = Parallel(*branches, name="branches")  # type: ignore[arg-type]
    workflow = Workflow(
        telemetry=False,
        steps=[
            parallel,
            Step(name="read", executor=read, max_retries=0),
        ],
    )
    assert workflow.run(input={"run_id": "sintetico"}).content == "ok"


@pytest.mark.parametrize("on_error", [OnError.skip, OnError.fail])
def test_step_exception_policy_must_be_explicit(on_error: OnError) -> None:
    calls: list[str] = []
    failure = ValueError("erro sintético")

    def fail(step_input: StepInput) -> StepOutput:
        calls.append("fail")
        raise failure

    def after(step_input: StepInput) -> StepOutput:
        calls.append("after")
        return StepOutput()

    assert Step(name="default", executor=fail).human_review.on_error is OnError.skip

    step = Step(
        name="fail",
        executor=fail,
        max_retries=0,
        human_review=HumanReview(on_error=on_error),
    )
    with pytest.raises(ValueError) as caught:
        step.execute(StepInput(input="teste"))
    assert caught.value is failure and calls == ["fail"]
    calls.clear()

    workflow = Workflow(
        telemetry=False,
        steps=[
            step,
            Step(name="after", executor=after, max_retries=0),
        ],
    )
    if on_error is OnError.fail:
        with pytest.raises(ValueError) as caught:
            workflow.run(input="teste")
        assert caught.value is failure and calls == ["fail"]
    else:
        result = workflow.run(input="teste")
        assert result.status == RunStatus.completed
        assert calls == ["fail", "after"]
        failed = result.step_results[0]
        assert isinstance(failed, StepOutput) and failed.success is False


def test_condition_propagates_errors_with_an_explicit_fail_policy() -> None:
    def fail(step_input: StepInput) -> bool:
        raise ValueError("falha da condição")

    workflow = Workflow(
        telemetry=False,
        steps=[
            Condition(
                name="condition",
                evaluator=fail,
                steps=[],
                human_review=HumanReview(on_error=OnError.fail),
            ),
        ],
    )
    with pytest.raises(ValueError, match="falha da condição"):
        workflow.run(input="teste")


def test_parallel_finishes_siblings_and_reports_the_failed_branch() -> None:
    started, failed, finished = Event(), Event(), Event()

    def fail(step_input: StepInput) -> StepOutput:
        assert started.wait(timeout=5)
        failed.set()
        raise ValueError("falha do ramo")

    def sibling(step_input: StepInput) -> StepOutput:
        started.set()
        assert failed.wait(timeout=5)
        finished.set()
        return StepOutput(content="irmão concluído")

    parallel = Parallel(
        Step(name="fail", executor=fail, max_retries=0),  # type: ignore[arg-type]
        Step(name="sibling", executor=sibling, max_retries=0),  # type: ignore[arg-type]
        name="branches",
    )
    output = parallel.execute(StepInput(input="teste"))
    assert finished.is_set()
    assert output.success is False and output.steps is not None
    assert [item.success for item in output.steps] == [False, True]
    assert output.steps[0].error == "falha do ramo"

    def after(step_input: StepInput) -> StepOutput:
        previous = step_input.get_step_output("branches")
        assert previous is not None and not previous.success
        return StepOutput(content="continuou apesar da falha")

    # O container Parallel não propaga o erro: o executor seguinte precisa conferir os ramos.
    workflow = Workflow(
        telemetry=False,
        steps=[
            parallel,
            Step(name="after", executor=after, max_retries=0),
        ],
    )
    result = workflow.run(input="teste")
    assert result.status == RunStatus.completed
    assert result.content == "continuou apesar da falha"


@pytest.mark.parametrize(
    ("pending", "stop_after", "iterations"), [(False, 2, 0), (True, 1, 1), (True, 9, 2)]
)
def test_condition_and_loop_judge_every_revision(
    pending: bool, stop_after: int, iterations: int
) -> None:
    events: list[str] = []
    checks: list[list[str | None]] = []

    def revise(step_input: StepInput) -> StepOutput:
        events.append("revise")
        return StepOutput(content="revisão")

    def judge(step_input: StepInput) -> StepOutput:
        events.append("judge")
        return StepOutput(content="julgada")

    def condition(step_input: StepInput) -> bool:
        assert step_input.input == "teste"
        return pending

    def end(outputs: list[StepOutput]) -> bool:
        checks.append([item.step_name for item in outputs])
        assert events[-1] == "judge"
        return len(checks) >= stop_after

    workflow = Workflow(
        telemetry=False,
        steps=[
            Condition(
                name="pending",
                evaluator=condition,
                steps=[
                    Loop(
                        name="revisions",
                        max_iterations=2,
                        end_condition=end,
                        steps=[
                            Step(name="revise", executor=revise, max_retries=0),
                            Step(name="judge", executor=judge, max_retries=0),
                        ],
                    ),
                ],
            ),
        ],
    )
    result = workflow.run(input="teste")
    assert result.status == RunStatus.completed
    assert events == ["revise", "judge"] * iterations
    assert checks == [["revise", "judge"]] * iterations
