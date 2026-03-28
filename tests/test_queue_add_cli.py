from pathlib import Path

from typer.testing import CliRunner

from nightshift.cli.app import app


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


def test_queue_add_command_reports_admitted_and_priority(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "nightshift.yaml"
    _write_config(config_path, tmp_path)

    class Status:
        def __init__(self, issue_id: str, status: str, queue_priority: str) -> None:
            self.issue_id = issue_id
            self.status = status
            self.queue_priority = queue_priority

    class Summary:
        def __init__(self) -> None:
            self.requested = 1
            self.admitted = 1
            self.already_admitted = 0

    class Result:
        statuses = (Status("GH-1", "admitted", "urgent"),)
        summary = Summary()

    monkeypatch.setattr("nightshift.cli.app.admit_to_queue", lambda registry, issue_ids, priority=None: Result())

    result = CliRunner().invoke(
        app,
        ["queue", "add", "GH-1", "--priority", "urgent", "--config", str(config_path)],
    )

    assert result.exit_code == 0
    assert "GH-1 status=admitted queue_priority=urgent" in result.stdout
    assert "requested=1 admitted=1 already_admitted=0" in result.stdout


def test_queue_add_command_reports_rejection(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "nightshift.yaml"
    _write_config(config_path, tmp_path)

    def fail(registry, issue_ids, priority=None):
        raise ValueError("issue GH-2 is currently blocked")

    monkeypatch.setattr("nightshift.cli.app.admit_to_queue", fail)

    result = CliRunner().invoke(app, ["queue", "add", "GH-2", "--config", str(config_path)])

    assert result.exit_code == 1
    assert "issue GH-2 is currently blocked" in result.stderr
