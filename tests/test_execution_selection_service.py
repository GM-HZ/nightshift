from __future__ import annotations

from nightshift.product.execution_selection.models import (
    ExecutionSelectionBatchRequest,
    ExecutionSelectionBatchResult,
    ExecutionSelectionBatchSummary,
    ExecutionSelectionOutcome,
)


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
    )

    assert summary.requested == 2
    assert summary.completed == 1
    assert summary.stopped_early is True
    assert summary.last_issue_id == "NS-2"
    assert summary.last_run_id == "RUN-2"


def test_execution_selection_batch_result_wraps_outcomes_and_summary() -> None:
    result = ExecutionSelectionBatchResult(
        outcomes=(
            ExecutionSelectionOutcome(issue_id="NS-1", run_id="RUN-1", accepted=True),
            ExecutionSelectionOutcome(issue_id="NS-2", run_id="RUN-2", accepted=False),
        ),
        summary=ExecutionSelectionBatchSummary(
            requested=2,
            completed=1,
            stopped_early=True,
            last_issue_id="NS-2",
            last_run_id="RUN-2",
        ),
    )

    assert result.outcomes[0].accepted is True
    assert result.outcomes[1].accepted is False
    assert result.summary.completed == 1
