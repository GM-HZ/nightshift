from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from nightshift.cli.app import app
from nightshift.domain import AttemptState, DeliveryState, IssueState
from nightshift.domain.records import IssueRecord
from nightshift.registry.issue_registry import IssueRegistry


def make_record(issue_id: str) -> IssueRecord:
    return IssueRecord.model_validate(
        {
            "issue_id": issue_id,
            "issue_state": IssueState.draft,
            "attempt_state": AttemptState.pending,
            "delivery_state": DeliveryState.none,
            "queue_priority": "medium",
            "created_at": "2026-03-29T00:00:00Z",
            "updated_at": "2026-03-29T00:00:00Z",
        }
    )


def write_config(repo_root: Path) -> Path:
    config_path = repo_root / "nightshift.yaml"
    config_path.write_text(
        f"""
project:
  repo_path: {repo_root}
  main_branch: main
runner:
  default_engine: codex
  fallback_engine: claude
  issue_timeout_seconds: 7200
  overnight_timeout_seconds: 28800
validation:
  enabled: true
issue_defaults:
  default_priority: high
  default_forbidden_paths:
    - secrets
  default_test_edit_policy:
    can_add_tests: true
    can_modify_existing_tests: false
    can_weaken_assertions: false
    requires_test_change_reason: true
  default_attempt_limits:
    max_files_changed: 5
    max_lines_added: 500
    max_lines_deleted: 200
  default_timeouts:
    command_seconds: 900
    issue_budget_seconds: 7200
retry:
  max_retries: 1
  retry_policy: never
  failure_circuit_breaker: false
workspace:
  worktree_root: .nightshift/worktrees
  artifact_root: nightshift-data/runs
alerts:
  enabled_channels: []
  severity_thresholds:
    info: info
    warning: warning
    critical: critical
report:
  output_directory: nightshift-data/reports
  summary_verbosity: concise
"""
    )
    return config_path


def write_work_order(
    repo_root: Path,
    *,
    include_goal: bool = True,
    include_verification_commands: bool = True,
    include_verification: bool = False,
) -> Path:
    goal_block = "  goal: Add a Chinese README and link it from the main README.\n" if include_goal else ""
    verification_commands_block = (
        "  verification_commands:\n"
        "    - test -s README.zh-CN.md\n"
        "    - rg -n \"README\\\\.zh-CN\\\\.md\" README.md\n"
        if include_verification_commands
        else ""
    )
    verification_block = (
        "  verification:\n"
        "    issue_validation:\n"
        "      - test -s README.zh-CN.md\n"
        "    regression_validation:\n"
        "      - rg -n \"README\\\\.zh-CN\\\\.md\" README.md\n"
        "    promotion_validation: []\n"
        if include_verification
        else ""
    )
    markdown = f"""---
work_order_id: WO-20260329-001
status: approved
source_issue:
  repo: GM-HZ/nightshift
  number: 7
  url: https://github.com/GM-HZ/nightshift/issues/7
execution:
  title: Add Chinese README
{goal_block}  allowed_paths:
    - README.md
    - README.zh-CN.md
  non_goals:
    - Change packaging
  acceptance_criteria:
    - README.zh-CN.md exists and is non-empty
    - README.md links to README.zh-CN.md
  context_files:
    - README.md
{verification_commands_block}{verification_block}rationale:
  summary: Add a Chinese entry point without expanding scope.
---
# Execution Work Order

Human-readable notes are not materialized.
"""
    path = repo_root / ".nightshift" / "work-orders" / "WO-20260329-001.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown)
    return path


def test_queue_add_reports_frozen_contract_and_admission(tmp_path: Path) -> None:
    repo_root = tmp_path
    config_path = write_config(repo_root)
    write_work_order(repo_root)
    registry = IssueRegistry(repo_root)
    registry.save_record(make_record("WO-20260329-001"))

    result = CliRunner().invoke(
        app,
        [
            "queue",
            "add",
            "WO-20260329-001",
            "--repo",
            str(repo_root),
            "--config",
            str(config_path),
        ],
    )

    assert result.exit_code == 0
    assert "queue add" in result.stdout.lower()
    assert "frozen" in result.stdout.lower()
    assert "admitted" in result.stdout.lower()
    assert "WO-20260329-001" in result.stdout

    contract = registry.get_contract("WO-20260329-001")
    record = registry.get_record("WO-20260329-001")
    assert contract.work_order_revision is not None
    assert record.issue_state == IssueState.ready


def test_queue_add_surfaces_materialization_errors_without_traceback(tmp_path: Path) -> None:
    repo_root = tmp_path
    config_path = write_config(repo_root)
    write_work_order(repo_root, include_goal=False)
    registry = IssueRegistry(repo_root)
    registry.save_record(make_record("WO-20260329-001"))

    result = CliRunner().invoke(
        app,
        [
            "queue",
            "add",
            "WO-20260329-001",
            "--repo",
            str(repo_root),
            "--config",
            str(config_path),
        ],
    )

    assert result.exit_code == 1
    assert "queue add failed" in result.stderr.lower()
    assert "execution.goal is required" in result.stderr
    assert "Traceback" not in result.stderr


def test_queue_add_surfaces_ambiguous_verification_errors_without_traceback(tmp_path: Path) -> None:
    repo_root = tmp_path
    config_path = write_config(repo_root)
    write_work_order(repo_root, include_verification_commands=True, include_verification=True)
    registry = IssueRegistry(repo_root)
    registry.save_record(make_record("WO-20260329-001"))

    result = CliRunner().invoke(
        app,
        [
            "queue",
            "add",
            "WO-20260329-001",
            "--repo",
            str(repo_root),
            "--config",
            str(config_path),
        ],
    )

    assert result.exit_code == 1
    assert "queue add failed" in result.stderr.lower()
    assert "execution cannot declare both verification and verification_commands" in result.stderr
    assert "Traceback" not in result.stderr
