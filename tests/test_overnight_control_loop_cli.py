from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from nightshift.cli.app import app
from nightshift.domain import RunLifecycleState
from nightshift.product.overnight import OvernightControlLoopResult, OvernightControlLoopSummary
from nightshift.product.overnight.loop_metadata import DaemonLoopMetadata


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


def _result(run_state: RunLifecycleState = RunLifecycleState.completed) -> OvernightControlLoopResult:
    metadata = DaemonLoopMetadata(
        run_id="DAEMON-1",
        created_at="2026-03-29T00:00:00Z",
        updated_at="2026-03-29T00:00:00Z",
        stopped_reason="drained" if run_state == RunLifecycleState.completed else "failure",
        issues_attempted=1,
        issues_completed=1 if run_state == RunLifecycleState.completed else 0,
        last_issue_id="WO-1",
        last_run_id="RUN-1",
        failed_issue_id=None if run_state == RunLifecycleState.completed else "WO-1",
    )
    return OvernightControlLoopResult(
        daemon_run_id="DAEMON-1",
        run_state=run_state,
        started_at="2026-03-29T00:00:00Z",
        ended_at="2026-03-29T01:00:00Z",
        outcomes=(),
        summary=OvernightControlLoopSummary(
            requested=1,
            completed=1 if run_state == RunLifecycleState.completed else 0,
            stopped_early=run_state != RunLifecycleState.completed,
            stopped_reason="drained" if run_state == RunLifecycleState.completed else "failure",
            last_issue_id="WO-1",
            last_run_id="RUN-1",
            failed_issue_id=None if run_state == RunLifecycleState.completed else "WO-1",
        ),
        metadata=metadata,
    )


def test_run_daemon_requires_all(tmp_path: Path) -> None:
    repo_root = tmp_path
    config_path = _write_config(repo_root)

    result = CliRunner().invoke(app, ["run", "--daemon", "--repo", str(repo_root), "--config", str(config_path)])

    assert result.exit_code == 1
    assert "--daemon currently requires --all" in result.stderr


def test_run_daemon_rejects_issues_flag(tmp_path: Path) -> None:
    repo_root = tmp_path
    config_path = _write_config(repo_root)

    result = CliRunner().invoke(
        app,
        ["run", "--daemon", "--all", "--issues", "WO-1", "--repo", str(repo_root), "--config", str(config_path)],
    )

    assert result.exit_code == 1
    assert "--daemon cannot be combined with --issues" in result.stderr


def test_run_daemon_prints_summary_and_succeeds(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path
    config_path = _write_config(repo_root)

    class FakeService:
        def __init__(self, *, state_store):
            self.state_store = state_store

        def run(self, *, orchestrator, issue_registry, request, stop_check=None):
            return _result()

    monkeypatch.setattr("nightshift.cli.app.OvernightControlLoopService", FakeService)

    result = CliRunner().invoke(
        app,
        ["run", "--daemon", "--all", "--repo", str(repo_root), "--config", str(config_path)],
    )

    assert result.exit_code == 0
    assert "daemon run DAEMON-1" in result.stdout
    assert "run_state=completed" in result.stdout
    assert "stopped_reason=drained" in result.stdout


def test_run_daemon_exits_nonzero_on_aborted_result(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path
    config_path = _write_config(repo_root)

    class FakeService:
        def __init__(self, *, state_store):
            self.state_store = state_store

        def run(self, *, orchestrator, issue_registry, request, stop_check=None):
            return _result(RunLifecycleState.aborted)

    monkeypatch.setattr("nightshift.cli.app.OvernightControlLoopService", FakeService)

    result = CliRunner().invoke(
        app,
        ["run", "--daemon", "--all", "--repo", str(repo_root), "--config", str(config_path)],
    )

    assert result.exit_code == 1
    assert "run_state=aborted" in result.stdout


def test_stop_requests_active_daemon_run(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path
    config_path = _write_config(repo_root)
    observed: dict[str, object] = {}

    class FakeStateStore:
        def __init__(self, root):
            self.root = root

        def get_active_daemon_run(self):
            return "DAEMON-9"

    class FakeService:
        def __init__(self, *, state_store):
            self.state_store = state_store

        def request_stop(self, run_id):
            observed["run_id"] = run_id
            return DaemonLoopMetadata(
                run_id=run_id,
                created_at="2026-03-29T00:00:00Z",
                updated_at="2026-03-29T00:00:01Z",
                stop_requested=True,
                stopped_reason="user_stop",
            )

    monkeypatch.setattr("nightshift.cli.app.StateStore", FakeStateStore)
    monkeypatch.setattr("nightshift.cli.app.OvernightControlLoopService", FakeService)

    result = CliRunner().invoke(app, ["stop", "--repo", str(repo_root), "--config", str(config_path)])

    assert result.exit_code == 0
    assert observed["run_id"] == "DAEMON-9"
    assert "stop requested for DAEMON-9" in result.stdout


def test_stop_fails_when_no_active_daemon_run(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path
    config_path = _write_config(repo_root)

    class FakeStateStore:
        def __init__(self, root):
            self.root = root

        def get_active_daemon_run(self):
            return None

    monkeypatch.setattr("nightshift.cli.app.StateStore", FakeStateStore)

    result = CliRunner().invoke(app, ["stop", "--repo", str(repo_root), "--config", str(config_path)])

    assert result.exit_code == 1
    assert "no active daemon run" in result.stderr.lower()
