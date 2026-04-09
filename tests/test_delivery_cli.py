from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from typer.testing import CliRunner

from nightshift.cli.app import app
from nightshift.domain import AttemptState, DeliveryState, IssueState
from nightshift.product.delivery import DeliveryPRResult
from nightshift.domain.records import IssueRecord
from nightshift.domain.contracts import (
    AttemptLimitsContract,
    EnginePreferencesContract,
    IssueContract,
    PassConditionContract,
    TestEditPolicyContract,
    TimeoutsContract,
    VerificationContract,
    VerificationStageContract,
)
from nightshift.registry.issue_registry import IssueRegistry


def _done_accepted_record(issue_id: str) -> IssueRecord:
    now = datetime(2026, 4, 9, tzinfo=timezone.utc)
    return IssueRecord(
        issue_id=issue_id,
        issue_state=IssueState.done,
        attempt_state=AttemptState.accepted,
        delivery_state=DeliveryState.none,
        queue_priority="high",
        accepted_attempt_id="ATTEMPT-1",
        branch_name="nightshift/issue-1",
        created_at=now,
        updated_at=now,
    )


def _execution_contract(issue_id: str) -> IssueContract:
    return IssueContract(
        issue_id=issue_id,
        title=f"Title for {issue_id}",
        kind="execution",
        goal="Ship accepted change",
        allowed_paths=("src",),
        forbidden_paths=("secrets",),
        non_goals=(),
        context_files=("README.md",),
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


def test_deliver_branch_ready_updates_delivery_state(tmp_path: Path) -> None:
    registry = IssueRegistry(tmp_path)
    registry.save_record(_done_accepted_record("ISSUE-1"))

    result = CliRunner().invoke(
        app,
        ["deliver", "branch-ready", "ISSUE-1", "--repo", str(tmp_path)],
    )

    assert result.exit_code == 0
    assert "delivery_state=branch_ready" in result.stdout
    updated = registry.get_record("ISSUE-1")
    assert updated.delivery_state == DeliveryState.branch_ready


def test_deliver_pr_open_promotes_to_pr_opened(tmp_path: Path) -> None:
    registry = IssueRegistry(tmp_path)
    registry.save_record(_done_accepted_record("ISSUE-2"))

    result = CliRunner().invoke(
        app,
        [
            "deliver",
            "pr-open",
            "ISSUE-2",
            "--pr-id",
            "42",
            "--pr-ref",
            "https://github.com/GM-HZ/nightshift/pull/42",
            "--repo",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "delivery_state=pr_opened" in result.stdout
    updated = registry.get_record("ISSUE-2")
    assert updated.delivery_state == DeliveryState.pr_opened
    assert updated.delivery_id == "42"


def test_deliver_pr_open_auto_uses_delivery_service(tmp_path: Path, monkeypatch) -> None:
    registry = IssueRegistry(tmp_path)
    registry.save_record(_done_accepted_record("ISSUE-4"))
    registry.save_contract(_execution_contract("ISSUE-4"))

    captured: dict[str, str] = {}

    def fake_open_pull_request(*, repo_root: Path, branch_name: str, base_branch: str, title: str, body: str) -> DeliveryPRResult:
        captured["repo_root"] = str(repo_root)
        captured["branch_name"] = branch_name
        captured["base_branch"] = base_branch
        captured["title"] = title
        captured["body"] = body
        return DeliveryPRResult(pr_ref="https://github.com/GM-HZ/nightshift/pull/88", pr_id="88")

    monkeypatch.setattr("nightshift.cli.app.open_pull_request", fake_open_pull_request)

    result = CliRunner().invoke(
        app,
        [
            "deliver",
            "pr-open",
            "ISSUE-4",
            "--auto",
            "--repo",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "delivery_state=pr_opened" in result.stdout
    updated = registry.get_record("ISSUE-4")
    assert updated.delivery_state == DeliveryState.pr_opened
    assert updated.delivery_ref == "https://github.com/GM-HZ/nightshift/pull/88"
    assert updated.delivery_id == "88"
    assert captured["base_branch"] == "main"


def test_deliver_pr_open_requires_pr_ref_without_auto(tmp_path: Path) -> None:
    registry = IssueRegistry(tmp_path)
    registry.save_record(_done_accepted_record("ISSUE-5"))

    result = CliRunner().invoke(
        app,
        [
            "deliver",
            "pr-open",
            "ISSUE-5",
            "--repo",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 1
    assert "--pr-ref is required" in result.stderr


def test_deliver_pr_open_requires_done_accepted_issue(tmp_path: Path) -> None:
    now = datetime(2026, 4, 9, tzinfo=timezone.utc)
    registry = IssueRegistry(tmp_path)
    registry.save_record(
        IssueRecord(
            issue_id="ISSUE-3",
            issue_state=IssueState.ready,
            attempt_state=AttemptState.pending,
            delivery_state=DeliveryState.none,
            queue_priority="high",
            created_at=now,
            updated_at=now,
        )
    )

    result = CliRunner().invoke(
        app,
        [
            "deliver",
            "pr-open",
            "ISSUE-3",
            "--pr-ref",
            "https://github.com/GM-HZ/nightshift/pull/43",
            "--repo",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 1
    assert "done+accepted" in result.stderr
