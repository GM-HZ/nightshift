from __future__ import annotations

from pathlib import Path

import pytest

from nightshift.domain import AttemptState, DeliveryState, IssueKind, IssueState
from nightshift.domain.contracts import (
    AttemptLimitsContract,
    IssueContract,
    PassConditionContract,
    TestEditPolicyContract,
    TimeoutsContract,
    VerificationContract,
    VerificationStageContract,
)
from nightshift.domain.records import IssueRecord
from nightshift.product.execution_selection.models import SelectionError
from nightshift.product.queue_admission import admit_to_queue
from nightshift.registry.issue_registry import IssueRegistry


def make_contract(issue_id: str, kind: IssueKind = IssueKind.execution, priority: str = "high") -> IssueContract:
    verification = VerificationContract(
        issue_validation=VerificationStageContract(
            required=True,
            commands=("pytest",),
            pass_condition=PassConditionContract(type="exit_code", expected=0),
        )
    )
    return IssueContract(
        issue_id=issue_id,
        title=f"Title for {issue_id}",
        kind=kind,
        priority=priority,
        goal="Ship the thing",
        allowed_paths=("src",),
        forbidden_paths=("secrets",),
        verification=verification,
        test_edit_policy=TestEditPolicyContract(
            can_add_tests=True,
            can_modify_existing_tests=True,
            can_weaken_assertions=False,
            requires_test_change_reason=True,
        ),
        attempt_limits=AttemptLimitsContract(),
        timeouts=TimeoutsContract(),
    )


def make_record(
    issue_id: str,
    *,
    issue_state: IssueState = IssueState.ready,
    attempt_state: AttemptState = AttemptState.pending,
    queue_priority: str = "high",
    **extra: object,
) -> IssueRecord:
    payload = {
        "issue_id": issue_id,
        "issue_state": issue_state,
        "attempt_state": attempt_state,
        "delivery_state": DeliveryState.none,
        "queue_priority": queue_priority,
        "created_at": "2026-03-28T00:00:00Z",
        "updated_at": "2026-03-28T00:00:00Z",
        **extra,
    }
    return IssueRecord.model_validate(payload)


def seed_issue(repo: Path, issue_id: str, *, issue_state: IssueState = IssueState.ready, attempt_state: AttemptState = AttemptState.pending, queue_priority: str = "high", kind: IssueKind = IssueKind.execution, **extra: object) -> IssueRegistry:
    registry = IssueRegistry(repo)
    registry.save_contract(make_contract(issue_id, kind=kind, priority=queue_priority))
    registry.save_record(
        make_record(
            issue_id,
            issue_state=issue_state,
            attempt_state=attempt_state,
            queue_priority=queue_priority,
            **extra,
        )
    )
    return registry


def test_admit_to_queue_is_idempotent_for_ready_pending_issue(tmp_path: Path) -> None:
    registry = seed_issue(tmp_path, "GH-1")

    result = admit_to_queue(registry, ["GH-1"])

    assert result.summary.requested == 1
    assert result.summary.admitted == 0
    assert result.summary.already_admitted == 1
    assert result.statuses[0].status == "already_admitted"


def test_admit_to_queue_updates_queue_priority_only_on_record(tmp_path: Path) -> None:
    registry = seed_issue(tmp_path, "GH-1", queue_priority="high")

    result = admit_to_queue(registry, ["GH-1"], priority="urgent")

    assert result.summary.admitted == 1
    assert registry.get_record("GH-1").queue_priority == "urgent"
    assert registry.get_contract("GH-1").priority == "high"


def test_admit_to_queue_normalizes_draft_issue_to_ready(tmp_path: Path) -> None:
    registry = seed_issue(tmp_path, "GH-1", issue_state=IssueState.draft, queue_priority="high")

    result = admit_to_queue(registry, ["GH-1"])

    assert result.summary.admitted == 1
    assert registry.get_record("GH-1").issue_state == IssueState.ready
    assert registry.get_record("GH-1").attempt_state == AttemptState.pending


def test_admit_to_queue_preserves_first_seen_order_and_removes_duplicates(tmp_path: Path) -> None:
    registry = seed_issue(tmp_path, "GH-1")
    seed_issue(tmp_path, "GH-2")

    result = admit_to_queue(registry, ["GH-2", "GH-1", "GH-2"])

    assert [status.issue_id for status in result.statuses] == ["GH-2", "GH-1"]


def test_admit_to_queue_fails_closed_for_missing_contract(tmp_path: Path) -> None:
    registry = IssueRegistry(tmp_path)
    registry.save_record(make_record("GH-1"))

    with pytest.raises(SelectionError, match="missing contract for issue GH-1"):
        admit_to_queue(registry, ["GH-1"])


def test_admit_to_queue_fails_closed_for_missing_record(tmp_path: Path) -> None:
    registry = IssueRegistry(tmp_path)
    registry.save_contract(make_contract("GH-1"))

    with pytest.raises(SelectionError, match="missing record for issue GH-1"):
        admit_to_queue(registry, ["GH-1"])


def test_admit_to_queue_rejects_non_execution_issue(tmp_path: Path) -> None:
    registry = seed_issue(tmp_path, "GH-1", kind=IssueKind.planning)

    with pytest.raises(SelectionError, match="issue GH-1 is not execution-capable"):
        admit_to_queue(registry, ["GH-1"])


@pytest.mark.parametrize(
    ("issue_state", "attempt_state", "extra", "message"),
    [
        (IssueState.running, AttemptState.executing, {}, "issue GH-1 is currently running"),
        (
            IssueState.done,
            AttemptState.accepted,
            {"accepted_attempt_id": "ATT-1"},
            "issue GH-1 is already done",
        ),
        (IssueState.blocked, AttemptState.pending, {"blocker_type": "waiting"}, "issue GH-1 is currently blocked"),
        (
            IssueState.deferred,
            AttemptState.pending,
            {"deferred_reason": "later"},
            "issue GH-1 is currently deferred",
        ),
    ],
)
def test_admit_to_queue_rejects_invalid_live_states(
    tmp_path: Path,
    issue_state: IssueState,
    attempt_state: AttemptState,
    extra: dict[str, object],
    message: str,
) -> None:
    registry = seed_issue(tmp_path, "GH-1", issue_state=issue_state, attempt_state=attempt_state, **extra)

    with pytest.raises(SelectionError, match=message):
        admit_to_queue(registry, ["GH-1"])


def test_admit_to_queue_does_not_partially_mutate_on_mixed_validity_input(tmp_path: Path) -> None:
    registry = seed_issue(tmp_path, "GH-1", queue_priority="high")
    seed_issue(tmp_path, "GH-2", issue_state=IssueState.blocked, blocker_type="waiting")

    with pytest.raises(SelectionError, match="issue GH-2 is currently blocked"):
        admit_to_queue(registry, ["GH-1", "GH-2"], priority="urgent")

    assert registry.get_record("GH-1").queue_priority == "high"
