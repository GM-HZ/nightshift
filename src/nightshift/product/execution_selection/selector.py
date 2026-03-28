from __future__ import annotations

from nightshift.domain import IssueState

from .models import SelectionError, SelectionItem, SelectionResult


def resolve_selected_issues(issue_registry: object, issue_ids: list[str]) -> SelectionResult:
    effective_ids = _dedupe(issue_ids)
    if not effective_ids:
        raise SelectionError("at least one issue id is required")

    items: list[SelectionItem] = []
    for issue_id in effective_ids:
        try:
            record = issue_registry.get_record(issue_id)
        except FileNotFoundError as error:
            raise SelectionError(f"unknown issue_id: {issue_id}") from error

        if record.issue_state != IssueState.ready:
            raise SelectionError(f"issue {issue_id} is not schedulable")

        items.append(SelectionItem(issue_id=record.issue_id, queue_priority=record.queue_priority))

    return SelectionResult(items=tuple(items))


def resolve_all_schedulable_issues(issue_registry: object) -> SelectionResult:
    records = issue_registry.list_schedulable_records()
    return SelectionResult(
        items=tuple(SelectionItem(issue_id=record.issue_id, queue_priority=record.queue_priority) for record in records)
    )


def _dedupe(issue_ids: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for issue_id in issue_ids:
        normalized = issue_id.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered
