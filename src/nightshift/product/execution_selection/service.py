from __future__ import annotations

from typing import Any

from nightshift.orchestrator.run_orchestrator import RunOneResult

from .models import (
    ExecutionSelectionBatchRequest,
    ExecutionSelectionBatchResult,
    ExecutionSelectionBatchSummary,
    ExecutionSelectionOutcome,
)


def execute_selection_batch(
    orchestrator: Any,
    issue_registry: Any,
    request: ExecutionSelectionBatchRequest,
) -> ExecutionSelectionBatchResult:
    issue_ids = _resolve_issue_ids(issue_registry, request)
    outcomes: list[ExecutionSelectionOutcome] = []
    stopped_early = False
    failed_issue_id: str | None = None

    for issue_id in issue_ids:
        run_result = orchestrator.run_one(issue_id)
        if not isinstance(run_result, RunOneResult):
            raise TypeError("run_one must return a RunOneResult")

        outcomes.append(_outcome_from_run_result(run_result))
        if not run_result.accepted:
            stopped_early = True
            failed_issue_id = issue_id
            break

    completed = sum(1 for outcome in outcomes if outcome.accepted)
    last_issue_id = outcomes[-1].issue_id if outcomes else None
    last_run_id = outcomes[-1].run_id if outcomes else None

    return ExecutionSelectionBatchResult(
        outcomes=tuple(outcomes),
        summary=ExecutionSelectionBatchSummary(
            requested=len(issue_ids),
            completed=completed,
            stopped_early=stopped_early,
            last_issue_id=last_issue_id,
            last_run_id=last_run_id,
            failed_issue_id=failed_issue_id,
        ),
    )


def _resolve_issue_ids(issue_registry: Any, request: ExecutionSelectionBatchRequest) -> tuple[str, ...]:
    if request.run_all:
        return tuple(record.issue_id for record in issue_registry.list_schedulable_records())
    return request.issue_ids


def _outcome_from_run_result(run_result: RunOneResult) -> ExecutionSelectionOutcome:
    return ExecutionSelectionOutcome(
        issue_id=run_result.issue_id,
        run_id=run_result.run_id,
        accepted=run_result.accepted,
        attempt_id=run_result.attempt_id,
    )
