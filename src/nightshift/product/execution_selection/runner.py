from __future__ import annotations

from collections.abc import Callable

from nightshift.orchestrator.run_orchestrator import RunOneResult

from .models import BatchRunSummary, SelectionResult


def run_batch(selection: SelectionResult, run_one: Callable[[str], RunOneResult]) -> BatchRunSummary:
    attempted = 0
    accepted = 0
    first_failure_issue_id: str | None = None

    for item in selection.items:
        attempted += 1
        result = run_one(item.issue_id)
        if result.accepted:
            accepted += 1
            continue
        first_failure_issue_id = item.issue_id
        break

    return BatchRunSummary(
        batch_size=len(selection.items),
        issues_attempted=attempted,
        issues_accepted=accepted,
        stopped_early=first_failure_issue_id is not None,
        first_failure_issue_id=first_failure_issue_id,
    )
