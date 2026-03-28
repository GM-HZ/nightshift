from pathlib import Path

import pytest

from nightshift.domain import DeliveryState, IssueKind, IssueState, AttemptState
from nightshift.domain.contracts import (
    AttemptLimitsContract,
    PassConditionContract,
    IssueContract,
    TestEditPolicyContract,
    TimeoutsContract,
    VerificationContract,
    VerificationStageContract,
)
from nightshift.domain.records import IssueRecord
from nightshift.registry.issue_registry import IssueRegistry


def make_contract(issue_id: str, kind: IssueKind = IssueKind.planning, priority: str = "high") -> IssueContract:
    verification = VerificationContract()
    if kind == IssueKind.execution:
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
    delivery_state: DeliveryState = DeliveryState.none,
    queue_priority: str = "high",
    created_at: str = "2026-03-28T00:00:00Z",
    updated_at: str = "2026-03-28T00:00:00Z",
    **data: object,
) -> IssueRecord:
    return IssueRecord.model_validate(
        {
            "issue_id": issue_id,
            "issue_state": issue_state,
            "attempt_state": attempt_state,
            "delivery_state": delivery_state,
            "queue_priority": queue_priority,
            "created_at": created_at,
            "updated_at": updated_at,
            **data,
        }
    )


def test_issue_registry_saves_and_loads_contract(tmp_path: Path) -> None:
    registry = IssueRegistry(tmp_path)
    contract = make_contract("ISSUE-1")

    registry.save_contract(contract)

    assert registry.get_contract("ISSUE-1") == contract
    assert (tmp_path / "nightshift" / "issues" / "ISSUE-1.yaml").is_file()


def test_issue_registry_lists_contracts_by_kind(tmp_path: Path) -> None:
    registry = IssueRegistry(tmp_path)
    planning = make_contract("ISSUE-1", kind=IssueKind.planning)
    execution = make_contract("ISSUE-2", kind=IssueKind.execution)

    registry.save_contract(planning)
    registry.save_contract(execution)

    contracts = registry.list_contracts(kind=IssueKind.execution)

    assert [contract.issue_id for contract in contracts] == ["ISSUE-2"]


def test_issue_registry_saves_and_loads_record(tmp_path: Path) -> None:
    registry = IssueRegistry(tmp_path)
    record = make_record("ISSUE-1")

    registry.save_record(record)

    assert registry.get_record("ISSUE-1") == record
    assert (tmp_path / "nightshift-data" / "issue-records" / "ISSUE-1.json").is_file()


def test_issue_registry_lists_schedulable_records(tmp_path: Path) -> None:
    registry = IssueRegistry(tmp_path)
    registry.save_record(make_record("ISSUE-1", issue_state=IssueState.ready))
    registry.save_record(make_record("ISSUE-2", issue_state=IssueState.blocked, blocker_type="waiting"))
    registry.save_record(make_record("ISSUE-3", issue_state=IssueState.deferred, deferred_reason="later"))

    records = registry.list_schedulable_records()

    assert [record.issue_id for record in records] == ["ISSUE-1"]


def test_issue_registry_updates_queue_priority_without_changing_contract_priority(tmp_path: Path) -> None:
    registry = IssueRegistry(tmp_path)
    contract = make_contract("ISSUE-1", priority="medium")
    registry.save_contract(contract)
    registry.save_record(make_record("ISSUE-1", queue_priority=contract.priority))

    updated = registry.set_queue_priority("ISSUE-1", "urgent")

    assert updated.queue_priority == "urgent"
    assert registry.get_record("ISSUE-1").queue_priority == "urgent"
    assert registry.get_contract("ISSUE-1").priority == "medium"


def test_issue_registry_attaches_attempt(tmp_path: Path) -> None:
    registry = IssueRegistry(tmp_path)
    registry.save_record(make_record("ISSUE-1"))

    updated = registry.attach_attempt("ISSUE-1", "ATT-1", AttemptState.executing, "RUN-1")

    assert updated.latest_attempt_id == "ATT-1"
    assert updated.current_run_id == "RUN-1"
    assert updated.attempt_state == AttemptState.executing
    assert updated.issue_state == IssueState.running


def test_issue_registry_attaches_delivery(tmp_path: Path) -> None:
    registry = IssueRegistry(tmp_path)
    registry.save_record(
        make_record(
            "ISSUE-1",
            issue_state=IssueState.done,
            attempt_state=AttemptState.accepted,
            delivery_state=DeliveryState.none,
            accepted_attempt_id="ATT-1",
            branch_name="feature/issue-1",
        )
    )

    updated = registry.attach_delivery(
        "ISSUE-1",
        DeliveryState.branch_ready,
        delivery_id="PR-1",
        delivery_ref="refs/pull/1",
    )

    assert updated.delivery_state == DeliveryState.branch_ready
    assert updated.delivery_id == "PR-1"
    assert updated.delivery_ref == "refs/pull/1"
    assert registry.get_record("ISSUE-1").delivery_state == DeliveryState.branch_ready
