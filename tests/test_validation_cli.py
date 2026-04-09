from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from typer.testing import CliRunner

from nightshift.cli.app import app
from nightshift.domain import (
    AttemptLimitsContract,
    AttemptState,
    DeliveryState,
    EnginePreferencesContract,
    IssueContract,
    IssueRecord,
    IssueState,
    PassConditionContract,
    TestEditPolicyContract,
    TimeoutsContract,
    VerificationContract,
    VerificationStageContract,
)
from nightshift.registry.issue_registry import IssueRegistry
from nightshift.validation.gate import CommandResult, ValidationResult, ValidationStageResult


def _contract(issue_id: str) -> IssueContract:
    return IssueContract(
        issue_id=issue_id,
        title=f"Validate {issue_id}",
        kind="execution",
        goal="Validate command wiring",
        allowed_paths=("src",),
        forbidden_paths=("secrets",),
        verification=VerificationContract(
            issue_validation=VerificationStageContract(
                required=True,
                commands=("python -m pytest -q",),
                pass_condition=PassConditionContract(type="all_exit_codes_zero"),
            )
        ),
        test_edit_policy=TestEditPolicyContract(
            can_add_tests=True,
            can_modify_existing_tests=True,
            can_weaken_assertions=False,
            requires_test_change_reason=True,
        ),
        attempt_limits=AttemptLimitsContract(),
        timeouts=TimeoutsContract(command_seconds=300, issue_budget_seconds=3600),
        priority="high",
        engine_preferences=EnginePreferencesContract(primary="codex"),
    )


def test_validation_issue_cli_prefers_record_worktree_path(tmp_path: Path, monkeypatch) -> None:
    registry = IssueRegistry(tmp_path)
    registry.save_contract(_contract("ISSUE-1"))
    worktree = tmp_path / ".nightshift" / "worktrees" / "ISSUE-1"
    worktree.mkdir(parents=True, exist_ok=True)
    now = datetime(2026, 4, 9, tzinfo=timezone.utc)
    registry.save_record(
        IssueRecord(
            issue_id="ISSUE-1",
            issue_state=IssueState.ready,
            attempt_state=AttemptState.pending,
            delivery_state=DeliveryState.none,
            queue_priority="high",
            worktree_path=str(worktree),
            created_at=now,
            updated_at=now,
        )
    )

    def fake_validate(issue_contract: IssueContract, workspace: object, attempt_record: object) -> ValidationResult:
        assert issue_contract.issue_id == "ISSUE-1"
        assert Path(str(workspace)) == worktree
        assert getattr(attempt_record, "attempt_state", None) == AttemptState.validating
        return ValidationResult(
            passed=True,
            failed_stage=None,
            summary="validation passed",
            stages=(
                ValidationStageResult(
                    stage_name="issue_validation",
                    required=True,
                    passed=True,
                    skipped=False,
                    pass_condition=PassConditionContract(type="all_exit_codes_zero"),
                    command_results=(CommandResult(command="python -m pytest -q", exit_code=0, passed=True),),
                ),
            ),
        )

    monkeypatch.setattr("nightshift.cli.app.validation_gate.validate", fake_validate)
    result = CliRunner().invoke(app, ["validation", "issue", "ISSUE-1", "--repo", str(tmp_path)])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["issue_id"] == "ISSUE-1"
    assert payload["workspace_path"] == str(worktree)
    assert payload["passed"] is True
    assert payload["stages"][0]["stage_name"] == "issue_validation"


def test_validation_issue_cli_strict_mode_exits_nonzero_on_failure(tmp_path: Path, monkeypatch) -> None:
    registry = IssueRegistry(tmp_path)
    registry.save_contract(_contract("ISSUE-2"))

    def fake_validate(issue_contract: IssueContract, workspace: object, attempt_record: object) -> ValidationResult:
        assert issue_contract.issue_id == "ISSUE-2"
        assert Path(str(workspace)) == tmp_path
        assert getattr(attempt_record, "attempt_state", None) == AttemptState.validating
        return ValidationResult(
            passed=False,
            failed_stage="issue_validation",
            summary="issue_validation failed",
            stages=(
                ValidationStageResult(
                    stage_name="issue_validation",
                    required=True,
                    passed=False,
                    skipped=False,
                    pass_condition=PassConditionContract(type="all_exit_codes_zero"),
                    command_results=(CommandResult(command="python -m pytest -q", exit_code=1, passed=False),),
                ),
            ),
        )

    monkeypatch.setattr("nightshift.cli.app.validation_gate.validate", fake_validate)
    result = CliRunner().invoke(app, ["validation", "issue", "ISSUE-2", "--repo", str(tmp_path)])

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["issue_id"] == "ISSUE-2"
    assert payload["workspace_path"] == str(tmp_path)
    assert payload["passed"] is False
    assert payload["failed_stage"] == "issue_validation"
