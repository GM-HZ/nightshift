from __future__ import annotations

from nightshift.domain import AttemptState, IssueState
from nightshift.product.execution_selection.models import SelectionError

from .models import QueueAdmissionResult, QueueAdmissionStatus, QueueAdmissionSummary


def admit_to_queue(issue_registry: object, issue_ids: list[str], *, priority: str | None = None) -> QueueAdmissionResult:
    normalized_ids = _dedupe(issue_ids)
    if not normalized_ids:
        raise SelectionError("at least one issue id is required")

    planned_updates: list[tuple[object, str, bool]] = []
    statuses: list[QueueAdmissionStatus] = []

    for issue_id in normalized_ids:
        try:
            contract = issue_registry.get_contract(issue_id)
        except FileNotFoundError as error:
            raise SelectionError(f"missing contract for issue {issue_id}") from error

        try:
            record = issue_registry.get_record(issue_id)
        except FileNotFoundError as error:
            raise SelectionError(f"missing record for issue {issue_id}") from error

        if contract.kind != "execution":
            raise SelectionError(f"issue {issue_id} is not execution-capable")

        if record.issue_state == IssueState.running:
            raise SelectionError(f"issue {issue_id} is currently running")
        if record.issue_state == IssueState.done:
            raise SelectionError(f"issue {issue_id} is already done")
        if record.issue_state == IssueState.blocked:
            raise SelectionError(f"issue {issue_id} is currently blocked")
        if record.issue_state == IssueState.deferred:
            raise SelectionError(f"issue {issue_id} is currently deferred")

        next_priority = priority or record.queue_priority
        if not next_priority.strip():
            raise SelectionError("priority override must not be blank")

        if record.attempt_state != AttemptState.pending:
            raise SelectionError(f"issue {issue_id} is not queue-admittable")

        already_admitted = record.issue_state == IssueState.ready and record.attempt_state == AttemptState.pending
        draft_admittable = record.issue_state == IssueState.draft and record.attempt_state == AttemptState.pending

        if not already_admitted and not draft_admittable:
            raise SelectionError(f"issue {issue_id} is not queue-admittable")

        status = "already_admitted" if already_admitted and next_priority == record.queue_priority else "admitted"
        if draft_admittable or next_priority != record.queue_priority:
            planned_updates.append((record, next_priority, draft_admittable))
            status = "admitted"
        statuses.append(QueueAdmissionStatus(issue_id=issue_id, status=status, queue_priority=next_priority))

    for record, next_priority, normalize_from_draft in planned_updates:
        if normalize_from_draft:
            payload = record.model_dump(mode="json")
            payload.update({"issue_state": IssueState.ready, "queue_priority": next_priority})
            issue_registry.save_record(type(record).model_validate(payload))
        else:
            issue_registry.set_queue_priority(record.issue_id, next_priority)

    admitted = sum(1 for item in statuses if item.status == "admitted")
    already_admitted = sum(1 for item in statuses if item.status == "already_admitted")
    return QueueAdmissionResult(
        statuses=tuple(statuses),
        summary=QueueAdmissionSummary(
            requested=len(normalized_ids),
            admitted=admitted,
            already_admitted=already_admitted,
        ),
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
