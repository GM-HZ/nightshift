from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from nightshift.cli.app import app
from nightshift.domain import AttemptState, IssueState
from nightshift.registry.issue_registry import IssueRegistry


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


def write_work_order(repo_root: Path) -> Path:
    markdown = """---
work_order_id: WO-20260409-CLI
status: approved
source_issue:
  repo: GM-HZ/nightshift
  number: 9
  url: https://github.com/GM-HZ/nightshift/issues/9
execution:
  title: Add issue import command
  goal: Import approved work orders via CLI.
  allowed_paths:
    - src/nightshift/cli/app.py
  non_goals:
    - Rewrite queue orchestrator
  acceptance_criteria:
    - issue import command exists
  context_files:
    - README.zh-CN.md
  verification_commands:
    - rg -n "issue import" src/nightshift/cli/app.py
rationale:
  summary: Remove manual bootstrapping.
---
# Execution Work Order
"""
    path = repo_root / ".nightshift" / "work-orders" / "WO-20260409-CLI.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown)
    return path


def test_issue_import_cli_creates_contract_and_record(tmp_path: Path) -> None:
    config_path = write_config(tmp_path)
    work_order_path = write_work_order(tmp_path)
    registry = IssueRegistry(tmp_path)

    result = CliRunner().invoke(
        app,
        [
            "issue",
            "import",
            str(work_order_path),
            "--repo",
            str(tmp_path),
            "--config",
            str(config_path),
        ],
    )

    assert result.exit_code == 0
    assert "issue import" in result.stdout
    record = registry.get_record("WO-20260409-CLI")
    assert record.issue_state == IssueState.draft
    assert record.attempt_state == AttemptState.pending


def test_issue_import_cli_with_admit_moves_issue_to_ready(tmp_path: Path) -> None:
    config_path = write_config(tmp_path)
    work_order_path = write_work_order(tmp_path)
    registry = IssueRegistry(tmp_path)

    result = CliRunner().invoke(
        app,
        [
            "issue",
            "import",
            str(work_order_path),
            "--repo",
            str(tmp_path),
            "--config",
            str(config_path),
            "--admit",
        ],
    )

    assert result.exit_code == 0
    assert "admitted" in result.stdout
    record = registry.get_record("WO-20260409-CLI")
    assert record.issue_state == IssueState.ready


def test_issue_import_cli_surfaces_non_approved_error(tmp_path: Path) -> None:
    config_path = write_config(tmp_path)
    work_order_path = write_work_order(tmp_path)
    work_order_path.write_text(work_order_path.read_text().replace("status: approved", "status: draft"))

    result = CliRunner().invoke(
        app,
        [
            "issue",
            "import",
            str(work_order_path),
            "--repo",
            str(tmp_path),
            "--config",
            str(config_path),
        ],
    )

    assert result.exit_code == 1
    assert "issue import failed" in result.stderr
    assert "approved" in result.stderr
