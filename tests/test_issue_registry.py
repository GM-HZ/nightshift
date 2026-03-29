from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError
from typer.testing import CliRunner

from nightshift.cli.app import app
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
from nightshift.store.filesystem import write_yaml


def make_contract(
    issue_id: str,
    kind: IssueKind = IssueKind.planning,
    priority: str = "high",
    *,
    work_order_revision: str | None = None,
    non_goals: tuple[str, ...] = ("Do not change API shape",),
    context_files: tuple[str, ...] = ("docs/spec.md",),
) -> IssueContract:
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
        non_goals=non_goals,
        context_files=context_files,
        verification=verification,
        test_edit_policy=TestEditPolicyContract(
            can_add_tests=True,
            can_modify_existing_tests=True,
            can_weaken_assertions=False,
            requires_test_change_reason=True,
        ),
        attempt_limits=AttemptLimitsContract(),
        timeouts=TimeoutsContract(),
        work_order_revision=work_order_revision,
    )


def _write_layered_migration_marker(repo_root: Path) -> None:
    migration_marker = repo_root / ".nightshift/config/migration.yaml"
    migration_marker.parent.mkdir(parents=True, exist_ok=True)
    migration_marker.write_text(
        """
layout_version: 1
project_config_source: layered
runtime_layout_source: compatibility
contract_storage_source: layered
"""
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


def test_issue_registry_uses_compatibility_contract_storage_paths(tmp_path: Path) -> None:
    registry = IssueRegistry(tmp_path)
    contract = make_contract("ISSUE-1", work_order_revision="wo-1")

    registry.save_contract(contract)

    assert registry.get_contract("ISSUE-1") == contract
    assert registry.list_contracts() == [contract]
    assert registry.list_contract_revisions("ISSUE-1") == [contract]
    assert (tmp_path / "nightshift" / "issues" / "ISSUE-1.yaml").is_file()
    assert (tmp_path / "nightshift" / "contracts" / "ISSUE-1" / "0001-wo-1.yaml").is_file()


def test_issue_registry_uses_layered_contract_storage_paths(tmp_path: Path) -> None:
    _write_layered_migration_marker(tmp_path)
    registry = IssueRegistry(tmp_path)
    contract = make_contract("ISSUE-1", work_order_revision="wo-1")

    registry.save_contract(contract)

    assert registry.get_contract("ISSUE-1") == contract
    assert registry.list_contracts() == [contract]
    assert registry.list_contract_revisions("ISSUE-1") == [contract]
    assert (tmp_path / ".nightshift" / "contracts" / "current" / "ISSUE-1.yaml").is_file()
    assert (tmp_path / ".nightshift" / "contracts" / "history" / "ISSUE-1" / "0001-wo-1.yaml").is_file()


def test_write_yaml_is_atomicish(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "nightshift" / "issues" / "ISSUE-1.yaml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("title: original\n")
    original = target.read_text()
    calls: list[tuple[str, str]] = []

    def fake_replace(self: Path, destination: Path) -> Path:
        calls.append((str(self), str(destination)))
        raise RuntimeError("boom")

    monkeypatch.setattr(Path, "replace", fake_replace, raising=False)

    with pytest.raises(RuntimeError, match="boom"):
        write_yaml(target, {"title": "updated"})

    assert target.read_text() == original
    assert calls


def test_issue_registry_rejects_contract_overwrite_with_different_content(tmp_path: Path) -> None:
    registry = IssueRegistry(tmp_path)
    original = make_contract("ISSUE-1", priority="high")
    updated = make_contract("ISSUE-1", priority="urgent")

    registry.save_contract(original)
    registry.save_contract(original)

    with pytest.raises((ValueError, FileExistsError)):
        registry.save_contract(updated)

    assert registry.get_contract("ISSUE-1") == original


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


def test_issue_registry_orders_schedulable_records_by_canonical_priority(tmp_path: Path) -> None:
    registry = IssueRegistry(tmp_path)
    registry.save_record(make_record("ISSUE-LOW", queue_priority="low"))
    registry.save_record(make_record("ISSUE-URGENT", queue_priority="urgent"))
    registry.save_record(make_record("ISSUE-MEDIUM", queue_priority="medium"))
    registry.save_record(make_record("ISSUE-HIGH", queue_priority="high"))

    records = registry.list_schedulable_records()

    assert [record.issue_id for record in records] == [
        "ISSUE-URGENT",
        "ISSUE-HIGH",
        "ISSUE-MEDIUM",
        "ISSUE-LOW",
    ]


def test_issue_registry_updates_queue_priority_without_changing_contract_priority(tmp_path: Path) -> None:
    registry = IssueRegistry(tmp_path)
    contract = make_contract("ISSUE-1", priority="medium")
    registry.save_contract(contract)
    registry.save_record(make_record("ISSUE-1", queue_priority=contract.priority))

    updated = registry.set_queue_priority("ISSUE-1", "urgent")

    assert updated.queue_priority == "urgent"
    assert registry.get_record("ISSUE-1").queue_priority == "urgent"
    assert registry.get_contract("ISSUE-1").priority == "medium"


def test_issue_registry_rejects_invalid_queue_priority_update(tmp_path: Path) -> None:
    registry = IssueRegistry(tmp_path)
    record = make_record("ISSUE-1")
    registry.save_record(record)

    with pytest.raises(ValidationError):
        registry.set_queue_priority("ISSUE-1", "   ")

    assert registry.get_record("ISSUE-1") == record


def test_issue_registry_attaches_attempt(tmp_path: Path) -> None:
    registry = IssueRegistry(tmp_path)
    registry.save_record(make_record("ISSUE-1"))

    updated = registry.attach_attempt("ISSUE-1", "ATT-1", AttemptState.executing, "RUN-1")

    assert updated.latest_attempt_id == "ATT-1"
    assert updated.current_run_id == "RUN-1"
    assert updated.attempt_state == AttemptState.executing
    assert updated.issue_state == IssueState.running


def test_issue_registry_rejects_invalid_attach_attempt(tmp_path: Path) -> None:
    registry = IssueRegistry(tmp_path)
    record = make_record(
        "ISSUE-1",
        issue_state=IssueState.done,
        attempt_state=AttemptState.accepted,
        delivery_state=DeliveryState.branch_ready,
        accepted_attempt_id="ATT-0",
        branch_name="feature/issue-1",
        delivery_id="PR-1",
    )
    registry.save_record(record)

    with pytest.raises(ValidationError):
        registry.attach_attempt("ISSUE-1", "ATT-1", AttemptState.executing, "RUN-1")

    assert registry.get_record("ISSUE-1") == record


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


def test_issue_registry_rejects_invalid_attach_delivery(tmp_path: Path) -> None:
    registry = IssueRegistry(tmp_path)
    record = make_record(
        "ISSUE-1",
        issue_state=IssueState.done,
        attempt_state=AttemptState.accepted,
        delivery_state=DeliveryState.none,
        accepted_attempt_id="ATT-1",
    )
    registry.save_record(record)

    with pytest.raises(ValidationError):
        registry.attach_delivery("ISSUE-1", DeliveryState.branch_ready, delivery_id="PR-1")

    assert registry.get_record("ISSUE-1") == record


def test_issue_registry_rejects_path_traversal_issue_ids(tmp_path: Path) -> None:
    registry = IssueRegistry(tmp_path)

    with pytest.raises(ValueError):
        registry.save_contract(make_contract("../ISSUE-1"))

    with pytest.raises(ValueError):
        registry.save_record(make_record("../ISSUE-1"))


def test_queue_status_lists_current_records(tmp_path: Path) -> None:
    registry = IssueRegistry(tmp_path)
    registry.save_record(make_record("ISSUE-2", queue_priority="low"))
    registry.save_record(make_record("ISSUE-1", queue_priority="high"))

    result = CliRunner().invoke(app, ["queue", "status", "--repo", str(tmp_path)])

    assert result.exit_code == 0
    assert "queue status" not in result.stdout.lower()
    assert "ISSUE-1" in result.stdout
    assert "ISSUE-2" in result.stdout
    assert result.stdout.index("ISSUE-1") < result.stdout.index("ISSUE-2")
    assert "queue_priority=high" in result.stdout
    assert "queue_priority=low" in result.stdout


def test_queue_show_displays_contract_and_record_state(tmp_path: Path) -> None:
    registry = IssueRegistry(tmp_path)
    registry.save_contract(
        make_contract(
            "ISSUE-1",
            priority="medium",
            non_goals=("Do not change API shape", "Do not add new endpoints"),
            context_files=("docs/spec.md", "src/module.py"),
        )
    )
    registry.save_record(
        make_record(
            "ISSUE-1",
            queue_priority="urgent",
            issue_state=IssueState.running,
            attempt_state=AttemptState.executing,
            delivery_state=DeliveryState.none,
        )
    )

    result = CliRunner().invoke(app, ["queue", "show", "ISSUE-1", "--repo", str(tmp_path)])

    assert result.exit_code == 0
    assert "issue_id=ISSUE-1" in result.stdout
    assert "priority=medium" in result.stdout
    assert "queue_priority=urgent" in result.stdout
    assert "issue_state=running" in result.stdout
    assert "attempt_state=executing" in result.stdout
    assert "delivery_state=none" in result.stdout
    assert "non_goals_count=2" in result.stdout
    assert "context_files=docs/spec.md,src/module.py" in result.stdout


def test_queue_reprioritize_updates_only_current_issue_record(tmp_path: Path) -> None:
    registry = IssueRegistry(tmp_path)
    registry.save_contract(make_contract("ISSUE-1", priority="medium"))
    registry.save_record(make_record("ISSUE-1", queue_priority="medium"))

    result = CliRunner().invoke(app, ["queue", "reprioritize", "ISSUE-1", "urgent", "--repo", str(tmp_path)])

    assert result.exit_code == 0
    assert "queue_priority=urgent" in result.stdout
    assert registry.get_record("ISSUE-1").queue_priority == "urgent"
    assert registry.get_contract("ISSUE-1").priority == "medium"
