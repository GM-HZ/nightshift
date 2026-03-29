from __future__ import annotations

from nightshift.product.execution_selection.models import (
    ExecutionSelectionItemResult,
    ExecutionSelectionRequest,
    ExecutionSelectionResult,
    ExecutionSelectionSummary,
)


def test_execution_selection_request_normalizes_issue_ids() -> None:
    request = ExecutionSelectionRequest.model_validate({"issue_ids": ["ISSUE-1", "ISSUE-2"]})

    assert request.issue_ids == ("ISSUE-1", "ISSUE-2")


def test_execution_selection_summary_tracks_counts_and_stop_state() -> None:
    summary = ExecutionSelectionSummary.model_validate(
        {
            "requested": 3,
            "completed": 2,
            "stopped_early": True,
            "last_issue_id": "ISSUE-2",
            "last_run_id": "RUN-2",
        }
    )

    assert summary.requested == 3
    assert summary.completed == 2
    assert summary.stopped_early is True
    assert summary.last_issue_id == "ISSUE-2"
    assert summary.last_run_id == "RUN-2"


def test_execution_selection_result_groups_items_and_summary() -> None:
    result = ExecutionSelectionResult.model_validate(
        {
            "items": [
                {
                    "issue_id": "ISSUE-1",
                    "accepted": True,
                    "run_id": "RUN-1",
                    "attempt_id": "ATTEMPT-1",
                },
                {
                    "issue_id": "ISSUE-2",
                    "accepted": False,
                    "run_id": "RUN-2",
                    "attempt_id": "ATTEMPT-2",
                    "summary": "validation failed",
                },
            ],
            "summary": {
                "requested": 2,
                "completed": 1,
                "stopped_early": True,
                "last_issue_id": "ISSUE-2",
                "last_run_id": "RUN-2",
            },
        }
    )

    assert result.items == (
        ExecutionSelectionItemResult(
            issue_id="ISSUE-1",
            accepted=True,
            run_id="RUN-1",
            attempt_id="ATTEMPT-1",
        ),
        ExecutionSelectionItemResult(
            issue_id="ISSUE-2",
            accepted=False,
            run_id="RUN-2",
            attempt_id="ATTEMPT-2",
            summary="validation failed",
        ),
    )
    assert result.summary.requested == 2
    assert result.summary.completed == 1
    assert result.summary.stopped_early is True
