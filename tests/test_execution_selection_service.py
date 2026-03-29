from __future__ import annotations

from dataclasses import dataclass

from nightshift.orchestrator.run_orchestrator import RunOneResult
from nightshift.product.execution_selection.models import (
    ExecutionSelectionBatchRequest,
    ExecutionSelectionBatchResult,
    ExecutionSelectionBatchSummary,
    ExecutionSelectionOutcome,
)
from nightshift.product.execution_selection.service import execute_selection_batch


@dataclass(frozen=True, slots=True)
class FakeSchedulableRecord:
    issue_id: str


class FakeIssueRegistry:
    def __init__(self, schedulable_issue_ids: tuple[str, ...]) -> None:
        self._schedulable_issue_ids = schedulable_issue_ids

    def list_schedulable_records(self) -> list[FakeSchedulableRecord]:
        return [FakeSchedulableRecord(issue_id=issue_id) for issue_id in self._schedulable_issue_ids]


class FakeRunOrchestrator:
    def __init__(self, outcomes: dict[str, RunOneResult]) -> None:
        self.outcomes = outcomes
        self.calls: list[str] = []

    def run_one(self, issue_id: str) -> RunOneResult:
        self.calls.append(issue_id)
        return self.outcomes[issue_id]


def test_execution_selection_batch_request_preserves_issue_order() -> None:
    request = ExecutionSelectionBatchRequest(issue_ids=("NS-2", "NS-1"))

    assert request.issue_ids == ("NS-2", "NS-1")
    assert request.run_all is False


def test_execution_selection_batch_request_supports_run_all() -> None:
    request = ExecutionSelectionBatchRequest(run_all=True)

    assert request.run_all is True
    assert request.issue_ids == ()


def test_execution_selection_batch_summary_tracks_batch_outcome() -> None:
    summary = ExecutionSelectionBatchSummary(
        requested=2,
        completed=1,
        stopped_early=True,
        last_issue_id="NS-2",
        last_run_id="RUN-2",
        failed_issue_id="NS-2",
    )

    assert summary.requested == 2
    assert summary.completed == 1
    assert summary.stopped_early is True
    assert summary.last_issue_id == "NS-2"
    assert summary.last_run_id == "RUN-2"
    assert summary.failed_issue_id == "NS-2"


def test_execution_selection_batch_result_wraps_outcomes_and_summary() -> None:
    result = ExecutionSelectionBatchResult(
        outcomes=(
            ExecutionSelectionOutcome(issue_id="NS-1", run_id="RUN-1", accepted=True, attempt_id="ATTEMPT-1"),
            ExecutionSelectionOutcome(issue_id="NS-2", run_id="RUN-2", accepted=False, attempt_id="ATTEMPT-2"),
        ),
        summary=ExecutionSelectionBatchSummary(
            requested=2,
            completed=1,
            stopped_early=True,
            last_issue_id="NS-2",
            last_run_id="RUN-2",
            failed_issue_id="NS-2",
        ),
    )

    assert result.outcomes[0].accepted is True
    assert result.outcomes[1].accepted is False
    assert result.summary.completed == 1


def test_execute_selection_batch_runs_explicit_issue_ids_in_order() -> None:
    orchestrator = FakeRunOrchestrator(
        {
            "NS-2": RunOneResult(issue_id="NS-2", run_id="RUN-2", attempt_id="ATTEMPT-2", accepted=True),
            "NS-1": RunOneResult(issue_id="NS-1", run_id="RUN-1", attempt_id="ATTEMPT-1", accepted=True),
        }
    )
    registry = FakeIssueRegistry(("NS-1", "NS-2"))

    result = execute_selection_batch(
        orchestrator,
        registry,
        ExecutionSelectionBatchRequest(issue_ids=("NS-2", "NS-1")),
    )

    assert orchestrator.calls == ["NS-2", "NS-1"]
    assert result.summary.requested == 2
    assert result.summary.completed == 2
    assert result.summary.stopped_early is False
    assert result.summary.last_issue_id == "NS-1"
    assert result.summary.last_run_id == "RUN-1"
    assert result.outcomes == (
        ExecutionSelectionOutcome(issue_id="NS-2", run_id="RUN-2", accepted=True, attempt_id="ATTEMPT-2"),
        ExecutionSelectionOutcome(issue_id="NS-1", run_id="RUN-1", accepted=True, attempt_id="ATTEMPT-1"),
    )


def test_execute_selection_batch_uses_schedulable_order_for_run_all() -> None:
    orchestrator = FakeRunOrchestrator(
        {
            "NS-2": RunOneResult(issue_id="NS-2", run_id="RUN-2", attempt_id="ATTEMPT-2", accepted=True),
            "NS-1": RunOneResult(issue_id="NS-1", run_id="RUN-1", attempt_id="ATTEMPT-1", accepted=True),
        }
    )
    registry = FakeIssueRegistry(("NS-2", "NS-1"))

    result = execute_selection_batch(
        orchestrator,
        registry,
        ExecutionSelectionBatchRequest(run_all=True),
    )

    assert orchestrator.calls == ["NS-2", "NS-1"]
    assert result.summary.requested == 2
    assert result.summary.completed == 2
    assert result.summary.stopped_early is False


def test_execute_selection_batch_stops_on_first_rejected_result() -> None:
    orchestrator = FakeRunOrchestrator(
        {
            "NS-1": RunOneResult(issue_id="NS-1", run_id="RUN-1", attempt_id="ATTEMPT-1", accepted=True),
            "NS-2": RunOneResult(issue_id="NS-2", run_id="RUN-2", attempt_id="ATTEMPT-2", accepted=False),
            "NS-3": RunOneResult(issue_id="NS-3", run_id="RUN-3", attempt_id="ATTEMPT-3", accepted=True),
        }
    )
    registry = FakeIssueRegistry(("NS-1", "NS-2", "NS-3"))

    result = execute_selection_batch(
        orchestrator,
        registry,
        ExecutionSelectionBatchRequest(issue_ids=("NS-1", "NS-2", "NS-3")),
    )

    assert orchestrator.calls == ["NS-1", "NS-2"]
    assert result.summary.requested == 3
    assert result.summary.completed == 1
    assert result.summary.stopped_early is True
    assert result.summary.last_issue_id == "NS-2"
    assert result.summary.last_run_id == "RUN-2"
    assert result.summary.failed_issue_id == "NS-2"
    assert result.outcomes == (
        ExecutionSelectionOutcome(issue_id="NS-1", run_id="RUN-1", accepted=True, attempt_id="ATTEMPT-1"),
        ExecutionSelectionOutcome(issue_id="NS-2", run_id="RUN-2", accepted=False, attempt_id="ATTEMPT-2"),
    )
