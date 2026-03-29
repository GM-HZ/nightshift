from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from nightshift.cli.app import app
from nightshift.product.execution_selection.models import (
    ExecutionSelectionBatchRequest,
    ExecutionSelectionBatchResult,
    ExecutionSelectionBatchSummary,
    ExecutionSelectionOutcome,
)


def _write_config(repo_root: Path) -> Path:
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


def test_run_issues_cli_runs_in_explicit_order(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path
    config_path = _write_config(repo_root)
    observed: dict[str, object] = {}

    def fake_execute_selection_batch(orchestrator, issue_registry, request):
        observed["orchestrator"] = orchestrator
        observed["issue_registry"] = issue_registry
        observed["request"] = request
        return ExecutionSelectionBatchResult(
            outcomes=(
                ExecutionSelectionOutcome(issue_id="NS-2", run_id="RUN-2", accepted=True, attempt_id="ATTEMPT-2"),
                ExecutionSelectionOutcome(issue_id="NS-1", run_id="RUN-1", accepted=True, attempt_id="ATTEMPT-1"),
            ),
            summary=ExecutionSelectionBatchSummary(
                requested=2,
                completed=2,
                stopped_early=False,
                last_issue_id="NS-1",
                last_run_id="RUN-1",
            ),
        )

    monkeypatch.setattr("nightshift.cli.app.execute_selection_batch", fake_execute_selection_batch)

    result = CliRunner().invoke(
        app,
        [
            "run",
            "--issues",
            "NS-2,NS-1",
            "--repo",
            str(repo_root),
            "--config",
            str(config_path),
        ],
    )

    assert result.exit_code == 0
    assert observed["request"] == ExecutionSelectionBatchRequest(issue_ids=("NS-2", "NS-1"))
    assert "NS-2 accepted in RUN-2 (ATTEMPT-2)" in result.stdout
    assert "NS-1 accepted in RUN-1 (ATTEMPT-1)" in result.stdout
    assert "run: requested=2" in result.stdout
    assert "completed=2" in result.stdout
    assert "stopped_early=False" in result.stdout


def test_run_all_cli_uses_schedulable_selection(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path
    config_path = _write_config(repo_root)
    observed: dict[str, object] = {}

    def fake_execute_selection_batch(orchestrator, issue_registry, request):
        observed["request"] = request
        return ExecutionSelectionBatchResult(
            outcomes=(
                ExecutionSelectionOutcome(issue_id="NS-1", run_id="RUN-1", accepted=True, attempt_id="ATTEMPT-1"),
            ),
            summary=ExecutionSelectionBatchSummary(
                requested=1,
                completed=1,
                stopped_early=False,
                last_issue_id="NS-1",
                last_run_id="RUN-1",
            ),
        )

    monkeypatch.setattr("nightshift.cli.app.execute_selection_batch", fake_execute_selection_batch)

    result = CliRunner().invoke(
        app,
        [
            "run",
            "--all",
            "--repo",
            str(repo_root),
            "--config",
            str(config_path),
        ],
    )

    assert result.exit_code == 0
    assert observed["request"] == ExecutionSelectionBatchRequest(run_all=True)
    assert "run: requested=1" in result.stdout
    assert "completed=1" in result.stdout


def test_run_cli_rejects_missing_selection_mode(tmp_path: Path) -> None:
    repo_root = tmp_path
    config_path = _write_config(repo_root)

    result = CliRunner().invoke(
        app,
        [
            "run",
            "--repo",
            str(repo_root),
            "--config",
            str(config_path),
        ],
    )

    assert result.exit_code != 0
    assert "either --issues or --all is required" in result.stderr.lower()
