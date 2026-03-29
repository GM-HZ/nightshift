from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Callable

from nightshift.domain import AttemptState, DeliveryState, IssueState
from nightshift.domain.records import AttemptRecord, IssueRecord
from nightshift.product.delivery.models import DeliveryWriteResult


class DeliveryServiceError(ValueError):
    """Raised when an issue cannot be delivered safely."""


@dataclass(frozen=True, slots=True)
class DeliveryEligibility:
    issue_id: str
    accepted_attempt_id: str
    run_id: str
    snapshot_path: Path


def deliver_issue(
    issue_id: str,
    *,
    issue_registry: Any,
    state_store: Any,
    snapshot_root: Path,
    push_delivery: Callable[..., None],
    create_pr: Callable[..., DeliveryWriteResult],
) -> DeliveryWriteResult:
    issue_record = issue_registry.get_record(issue_id)
    if issue_record.accepted_attempt_id is None:
        raise DeliveryServiceError(f"issue {issue_id} is missing an accepted attempt")

    accepted_attempt = state_store.load_attempt_record(issue_record.accepted_attempt_id)
    eligibility = evaluate_delivery_eligibility(
        issue_record,
        accepted_attempt,
        snapshot_root=snapshot_root,
    )
    snapshot = _load_snapshot(eligibility.snapshot_path)

    try:
        push_delivery(snapshot=snapshot)
        result = create_pr(issue_record=issue_record, snapshot=snapshot)
    except Exception as exc:
        issue_registry.attach_delivery(issue_id, DeliveryState.branch_ready)
        raise DeliveryServiceError(str(exc)) from exc

    issue_registry.attach_delivery(
        issue_id,
        DeliveryState(result.delivery_state),
        delivery_id=result.delivery_id,
        delivery_ref=result.delivery_ref,
    )
    return result


def evaluate_delivery_eligibility(
    issue_record: IssueRecord,
    accepted_attempt: AttemptRecord,
    *,
    snapshot_root: Path,
) -> DeliveryEligibility:
    if issue_record.accepted_attempt_id is None:
        raise DeliveryServiceError(f"issue {issue_record.issue_id} is missing an accepted attempt")

    if issue_record.issue_state != IssueState.done or issue_record.attempt_state != AttemptState.accepted:
        raise DeliveryServiceError(f"issue {issue_record.issue_id} is not deliverable")

    if issue_record.delivery_state not in {DeliveryState.none, DeliveryState.branch_ready}:
        raise DeliveryServiceError(f"issue {issue_record.issue_id} is not deliverable from state {issue_record.delivery_state}")

    if accepted_attempt.attempt_id != issue_record.accepted_attempt_id:
        raise DeliveryServiceError(
            f"issue {issue_record.issue_id} accepted attempt mismatch: record={issue_record.accepted_attempt_id} attempt={accepted_attempt.attempt_id}"
        )

    snapshot_path = (
        snapshot_root
        / "runs"
        / accepted_attempt.run_id
        / "attempts"
        / accepted_attempt.attempt_id
        / "delivery"
        / "snapshot.json"
    )
    if not snapshot_path.exists():
        raise DeliveryServiceError(
            f"missing accepted delivery snapshot for issue {issue_record.issue_id} at {snapshot_path}"
        )

    return DeliveryEligibility(
        issue_id=issue_record.issue_id,
        accepted_attempt_id=accepted_attempt.attempt_id,
        run_id=accepted_attempt.run_id,
        snapshot_path=snapshot_path,
    )


def _load_snapshot(snapshot_path: Path) -> dict[str, object]:
    try:
        payload = json.loads(snapshot_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise DeliveryServiceError(f"failed to read delivery snapshot at {snapshot_path}") from exc
    if not isinstance(payload, dict):
        raise DeliveryServiceError(f"delivery snapshot at {snapshot_path} must be a JSON object")
    return payload
