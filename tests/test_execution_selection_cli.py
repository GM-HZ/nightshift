from pathlib import Path

from typer.testing import CliRunner

from nightshift.cli.app import app
from nightshift.product.execution_selection.models import BatchRunSummary, SelectionItem, SelectionResult


def _write_config(path: Path, repo_path: Path) -> None:
    path.write_text(
        f"""
project:
  repo_path: {repo_path}
  main_branch: main
runner:
  default_engine: codex
  issue_timeout_seconds: 900
  overnight_timeout_seconds: 7200
validation:
  enabled: true
issue_defaults:
  default_priority: high
  default_forbidden_paths:
    - secrets
  default_test_edit_policy:
    can_add_tests: true
    can_modify_existing_tests: true
    can_weaken_assertions: false
    requires_test_change_reason: true
  default_attempt_limits:
    max_files_changed: 3
    max_lines_added: 200
    max_lines_deleted: 50
  default_timeouts:
    command_seconds: 900
    issue_budget_seconds: 7200
retry:
  max_retries: 3
  retry_policy: never
  failure_circuit_breaker: false
workspace:
  worktree_root: .worktrees
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


def test_run_command_executes_selected_issue_list(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "nightshift.yaml"
    _write_config(config_path, tmp_path)

    monkeypatch.setattr(
        "nightshift.cli.app.resolve_selected_issues",
        lambda registry, issue_ids: SelectionResult(
            items=(SelectionItem(issue_id="GH-2", queue_priority="high"), SelectionItem(issue_id="GH-1", queue_priority="low"))
        ),
    )
    monkeypatch.setattr(
        "nightshift.cli.app.run_batch",
        lambda selection, run_one: BatchRunSummary(
            batch_size=2,
            issues_attempted=2,
            issues_accepted=2,
            stopped_early=False,
        ),
    )

    result = CliRunner().invoke(
        app,
        ["run", "--issues", "GH-2,GH-1", "--config", str(config_path)],
    )

    assert result.exit_code == 0
    assert "selected issues: GH-2, GH-1" in result.stdout
    assert '"issues_attempted":2' in result.stdout.replace(" ", "").replace("\n", "")


def test_run_command_executes_all_schedulable_issue_list(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "nightshift.yaml"
    _write_config(config_path, tmp_path)

    monkeypatch.setattr(
        "nightshift.cli.app.resolve_all_schedulable_issues",
        lambda registry: SelectionResult(items=(SelectionItem(issue_id="GH-1", queue_priority="urgent"),)),
    )
    monkeypatch.setattr(
        "nightshift.cli.app.run_batch",
        lambda selection, run_one: BatchRunSummary(
            batch_size=1,
            issues_attempted=1,
            issues_accepted=1,
            stopped_early=False,
        ),
    )

    result = CliRunner().invoke(app, ["run", "--all", "--config", str(config_path)])

    assert result.exit_code == 0
    assert "selected issues: GH-1" in result.stdout


def test_run_command_rejects_invalid_selection_before_batch_execution(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "nightshift.yaml"
    _write_config(config_path, tmp_path)

    def fail_selection(registry, issue_ids):
        raise ValueError("issue GH-9 is not schedulable")

    monkeypatch.setattr("nightshift.cli.app.resolve_selected_issues", fail_selection)

    result = CliRunner().invoke(app, ["run", "--issues", "GH-9", "--config", str(config_path)])

    assert result.exit_code == 1
    assert "issue GH-9 is not schedulable" in result.stderr


def test_run_command_handles_empty_all_selection_cleanly(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "nightshift.yaml"
    _write_config(config_path, tmp_path)

    monkeypatch.setattr("nightshift.cli.app.resolve_all_schedulable_issues", lambda registry: SelectionResult())

    result = CliRunner().invoke(app, ["run", "--all", "--config", str(config_path)])

    assert result.exit_code == 0
    assert "no schedulable issues selected" in result.stdout


def test_run_command_surfaces_operator_friendly_failure_summary(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "nightshift.yaml"
    _write_config(config_path, tmp_path)

    monkeypatch.setattr(
        "nightshift.cli.app.resolve_selected_issues",
        lambda registry, issue_ids: SelectionResult(items=(SelectionItem(issue_id="GH-6", queue_priority="high"),)),
    )

    def fail_batch(selection, run_one):
        raise RuntimeError("engine outcome engine_crash cannot be accepted")

    monkeypatch.setattr("nightshift.cli.app.run_batch", fail_batch)

    result = CliRunner().invoke(app, ["run", "--issues", "GH-6", "--config", str(config_path)])

    assert result.exit_code == 1
    assert "run failed for selected issues" in result.stderr
    assert "engine outcome engine_crash cannot be accepted" in result.stderr
    assert "Traceback" not in result.stderr
