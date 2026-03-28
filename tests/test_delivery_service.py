from __future__ import annotations

from pathlib import Path

import pytest

from nightshift.config.models import NightShiftConfig
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
from nightshift.product.delivery.models import DeliveryRequest
from nightshift.product.delivery.service import DeliveryService
from nightshift.registry.issue_registry import IssueRegistry


def _config(repo_root: Path) -> NightShiftConfig:
    return NightShiftConfig.model_validate(
        {
            "project": {"repo_path": str(repo_root), "main_branch": "master"},
            "runner": {"default_engine": "codex", "issue_timeout_seconds": 900, "overnight_timeout_seconds": 7200},
            "validation": {"enabled": True},
            "issue_defaults": {
                "default_priority": "high",
                "default_forbidden_paths": ["secrets"],
                "default_test_edit_policy": {
                    "can_add_tests": True,
                    "can_modify_existing_tests": True,
                    "can_weaken_assertions": False,
                    "requires_test_change_reason": True,
                },
                "default_attempt_limits": {
                    "max_files_changed": 3,
                    "max_lines_added": 200,
                    "max_lines_deleted": 50,
                },
                "default_timeouts": {"command_seconds": 900, "issue_budget_seconds": 7200},
            },
            "retry": {"max_retries": 3, "retry_policy": "never", "failure_circuit_breaker": False},
            "workspace": {"worktree_root": str(repo_root / ".worktrees"), "artifact_root": str(repo_root / "nightshift-data" / "runs")},
            "alerts": {"enabled_channels": [], "severity_thresholds": {"info": "info", "warning": "warning", "critical": "critical"}},
            "report": {"output_directory": str(repo_root / "nightshift-data" / "reports"), "summary_verbosity": "concise"},
            "product": {"delivery": {"repo_full_name": "GM-HZ/nightshift", "remote_name": "origin", "base_branch": "master"}},
        }
    )


def _make_contract(issue_id: str) -> IssueContract:
    return IssueContract(
        issue_id=issue_id,
        title="增加中文 README 说明",
        kind=IssueKind.execution,
        priority="high",
        goal="增加中文 README 说明",
        allowed_paths=("README.md", "README.zh-CN.md"),
        forbidden_paths=("secrets",),
        verification=VerificationContract(
            issue_validation=VerificationStageContract(
                required=True,
                commands=("test -s README.zh-CN.md",),
                pass_condition=PassConditionContract(type="all_exit_codes_zero"),
            ),
            regression_validation=VerificationStageContract(
                required=True,
                commands=("test -s README.zh-CN.md",),
                pass_condition=PassConditionContract(type="all_exit_codes_zero"),
            ),
        ),
        test_edit_policy=TestEditPolicyContract(
            can_add_tests=True,
            can_modify_existing_tests=True,
            can_weaken_assertions=False,
            requires_test_change_reason=True,
        ),
        attempt_limits=AttemptLimitsContract(),
        timeouts=TimeoutsContract(),
        acceptance=("仓库根目录存在 README.zh-CN.md",),
    )


def _make_record(issue_id: str, worktree: Path) -> IssueRecord:
    return IssueRecord.model_validate(
        {
            "issue_id": issue_id,
            "issue_state": IssueState.done,
            "attempt_state": AttemptState.accepted,
            "delivery_state": DeliveryState.none,
            "accepted_attempt_id": "ATT-1",
            "branch_name": "nightshift-issue-gh-7-readme",
            "worktree_path": str(worktree),
            "queue_priority": "high",
            "created_at": "2026-03-29T00:00:00Z",
            "updated_at": "2026-03-29T00:00:00Z",
        }
    )


def _seed_issue(repo_root: Path, issue_id: str = "GH-7") -> IssueRegistry:
    registry = IssueRegistry(repo_root)
    worktree = repo_root / ".worktrees" / f"issue-{issue_id}"
    worktree.mkdir(parents=True)
    (worktree / "README.md").write_text("hello\n")
    registry.save_contract(_make_contract(issue_id))
    registry.save_record(_make_record(issue_id, worktree))
    return registry


def test_service_delivers_single_accepted_issue_and_updates_registry(tmp_path: Path) -> None:
    registry = _seed_issue(tmp_path)
    calls: list[tuple[str, ...]] = []

    service = DeliveryService(
        repo_root=tmp_path,
        config=_config(tmp_path),
        registry=registry,
        git_add=lambda worktree_path: calls.append(("add", str(worktree_path))),
        git_commit=lambda worktree_path, message: calls.append(("commit", str(worktree_path), message)),
        git_push=lambda repo_root, remote_name, branch_name: calls.append(("push", str(repo_root), remote_name, branch_name)),
        create_pull_request=lambda repo_full_name, payload: type(
            "PRRef",
            (),
            {"pr_number": 123, "html_url": "https://github.com/GM-HZ/nightshift/pull/123"},
        )(),
    )

    result = service.deliver(DeliveryRequest(issue_ids=("GH-7",)))

    assert result.delivered_issue_ids == ("GH-7",)
    updated = registry.get_record("GH-7")
    assert updated.delivery_state == DeliveryState.pr_opened
    assert updated.delivery_id == "123"
    assert updated.delivery_ref == "https://github.com/GM-HZ/nightshift/pull/123"
    assert [call[0] for call in calls] == ["add", "commit", "push"]


def test_service_marks_failed_when_push_fails(tmp_path: Path) -> None:
    registry = _seed_issue(tmp_path)

    def fail_push(repo_root: Path, remote_name: str, branch_name: str) -> None:
        raise RuntimeError("push failed")

    service = DeliveryService(
        repo_root=tmp_path,
        config=_config(tmp_path),
        registry=registry,
        git_add=lambda worktree_path: None,
        git_commit=lambda worktree_path, message: None,
        git_push=fail_push,
        create_pull_request=lambda repo_full_name, payload: pytest.fail("PR should not be attempted"),
    )

    result = service.deliver(DeliveryRequest(issue_ids=("GH-7",)))

    assert result.failed_issue_ids == ("GH-7",)
    updated = registry.get_record("GH-7")
    assert updated.delivery_state == DeliveryState.branch_ready
    assert updated.delivery_ref is None
    assert updated.delivery_id is None
