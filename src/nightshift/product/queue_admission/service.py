from __future__ import annotations

import hashlib
from pathlib import Path

from nightshift.config.models import NightShiftConfig
from nightshift.domain import AttemptState, IssueState
from nightshift.domain.contracts import IssueContract
from nightshift.domain.records import IssueRecord
from nightshift.product.work_orders.materialize import (
    WorkOrderMaterializationError,
    WorkOrderMaterializationProvenance,
    materialize_work_order,
)
from nightshift.product.work_orders.parser import WorkOrderParseError, parse_work_order_markdown

from .models import QueueAdmissionResult, QueueAdmissionStatus, QueueAdmissionSummary


class QueueAdmissionError(ValueError):
    """Raised when queue admission cannot safely freeze and admit an issue."""


def admit_to_queue(
    issue_registry: object,
    issue_ids: list[str],
    *,
    config: NightShiftConfig,
    priority: str | None = None,
) -> QueueAdmissionResult:
    normalized_ids = _dedupe(issue_ids)
    if not normalized_ids:
        raise QueueAdmissionError("at least one issue id is required")

    planned_updates: list[tuple[IssueContract, IssueRecord, str, bool]] = []
    statuses: list[QueueAdmissionStatus] = []

    for issue_id in normalized_ids:
        contract = _freeze_contract_for_issue(issue_registry.root, issue_id, config)
        record = _get_record(issue_registry, issue_id)

        _ensure_queue_admittable(contract, record)

        next_priority = priority or record.queue_priority
        if not next_priority.strip():
            raise QueueAdmissionError("priority override must not be blank")

        already_admitted = record.issue_state == IssueState.ready and record.attempt_state == AttemptState.pending
        draft_admittable = record.issue_state == IssueState.draft and record.attempt_state == AttemptState.pending
        contract_changed = _contract_changed(issue_registry, contract)
        should_update_record = draft_admittable or next_priority != record.queue_priority
        should_save_contract = contract_changed or _contract_missing(issue_registry, contract.issue_id)

        status = "already_admitted"
        if draft_admittable or should_update_record or should_save_contract:
            status = "admitted"

        planned_updates.append((contract, record, next_priority, should_update_record))
        statuses.append(
            QueueAdmissionStatus(
                issue_id=issue_id,
                status=status,
                queue_priority=next_priority,
            )
        )

    for contract, record, next_priority, should_update_record in planned_updates:
        issue_registry.save_contract(contract)
        if should_update_record:
            issue_registry.save_record(_updated_record(record, next_priority))

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


def _freeze_contract_for_issue(repo_root: Path, issue_id: str, config: NightShiftConfig) -> IssueContract:
    work_order_path, markdown = _resolve_work_order(repo_root, issue_id)
    revision = hashlib.sha256(markdown.encode("utf-8")).hexdigest()

    try:
        parsed = parse_work_order_markdown(markdown)
        contract = materialize_work_order(
            parsed,
            config,
            WorkOrderMaterializationProvenance(
                work_order_path=work_order_path.relative_to(repo_root).as_posix(),
                work_order_revision=revision,
            ),
        )
    except (WorkOrderParseError, WorkOrderMaterializationError, ValueError) as exc:
        raise QueueAdmissionError(f"failed to materialize work order for {issue_id}: {exc}") from exc

    if contract.issue_id != issue_id:
        raise QueueAdmissionError(
            f"work order for {issue_id} materialized runtime issue_id={contract.issue_id}; queue admission requires matching issue ids"
        )

    return contract


def _resolve_work_order(repo_root: Path, issue_id: str) -> tuple[Path, str]:
    work_orders_dir = repo_root / ".nightshift" / "work-orders"
    matches: list[Path] = []
    for path in sorted(work_orders_dir.glob("*.md")):
        markdown = path.read_text()
        try:
            parsed = parse_work_order_markdown(markdown)
        except WorkOrderParseError:
            continue
        runtime_issue_id = parsed.frontmatter.execution.issue_id or parsed.frontmatter.work_order_id
        if parsed.frontmatter.status == "approved" and issue_id in {parsed.frontmatter.work_order_id, runtime_issue_id}:
            matches.append(path)

    if not matches:
        raise QueueAdmissionError(f"missing approved work order for issue {issue_id}")

    if len(matches) > 1:
        joined = ", ".join(path.name for path in matches)
        raise QueueAdmissionError(f"multiple approved work orders match issue {issue_id}: {joined}")

    path = matches[0]
    return path, path.read_text()


def _get_record(issue_registry: object, issue_id: str) -> IssueRecord:
    try:
        return issue_registry.get_record(issue_id)
    except FileNotFoundError as exc:
        raise QueueAdmissionError(f"missing record for issue {issue_id}") from exc


def _ensure_queue_admittable(contract: IssueContract, record: IssueRecord) -> None:
    if contract.kind != "execution":
        raise QueueAdmissionError(f"issue {record.issue_id} is not execution-capable")

    if record.issue_state == IssueState.running:
        raise QueueAdmissionError(f"issue {record.issue_id} is currently running")
    if record.issue_state == IssueState.done:
        raise QueueAdmissionError(f"issue {record.issue_id} is already done")
    if record.issue_state == IssueState.blocked:
        raise QueueAdmissionError(f"issue {record.issue_id} is currently blocked")
    if record.issue_state == IssueState.deferred:
        raise QueueAdmissionError(f"issue {record.issue_id} is currently deferred")
    if record.attempt_state != AttemptState.pending:
        raise QueueAdmissionError(f"issue {record.issue_id} is not queue-admittable")

    already_admitted = record.issue_state == IssueState.ready and record.attempt_state == AttemptState.pending
    draft_admittable = record.issue_state == IssueState.draft and record.attempt_state == AttemptState.pending
    if not already_admitted and not draft_admittable:
        raise QueueAdmissionError(f"issue {record.issue_id} is not queue-admittable")


def _updated_record(record: IssueRecord, next_priority: str) -> IssueRecord:
    payload = record.model_dump(mode="json")
    payload.update({"issue_state": IssueState.ready, "queue_priority": next_priority})
    return IssueRecord.model_validate(payload)


def _contract_missing(issue_registry: object, issue_id: str) -> bool:
    try:
        issue_registry.get_contract(issue_id)
    except FileNotFoundError:
        return True
    return False


def _contract_changed(issue_registry: object, contract: IssueContract) -> bool:
    try:
        existing = issue_registry.get_contract(contract.issue_id)
    except FileNotFoundError:
        return True
    return existing != contract


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
