from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from typer.testing import CliRunner

from nightshift.cli.app import app
from nightshift.domain import AlertSeverity, AttemptState, DeliveryState, IssueState, RunLifecycleState
from nightshift.domain.records import AlertEvent, AttemptRecord, AttemptValidationResult, EventRecord, IssueRecord, RunState
from nightshift.orchestrator.run_orchestrator import RunOneResult
from nightshift.registry.issue_registry import IssueRegistry
from nightshift.store.state_store import StateStore


def _write_config(
    path: Path,
    repo_path: Path,
    *,
    max_retries: int = 1,
    retry_policy: str = "never",
    failure_circuit_breaker: bool = False,
) -> None:
    path.write_text(
        f"project:\n  repo_path: {repo_path}\n  main_branch: main\n"
        "runner:\n  default_engine: codex\n  issue_timeout_seconds: 1\n  overnight_timeout_seconds: 60\n"
        "validation:\n  enabled: true\n"
        "issue_defaults:\n"
        "  default_priority: high\n"
        "  default_forbidden_paths: [secrets]\n"
        "  default_test_edit_policy:\n"
        "    can_add_tests: true\n"
        "    can_modify_existing_tests: true\n"
        "    can_weaken_assertions: false\n"
        "    requires_test_change_reason: true\n"
        "  default_attempt_limits:\n"
        "    max_files_changed: 1\n"
        "    max_lines_added: 1\n"
        "    max_lines_deleted: 1\n"
        "  default_timeouts:\n"
        "    command_seconds: 1\n"
        "    issue_budget_seconds: 1\n"
        f"retry:\n  max_retries: {max_retries}\n  retry_policy: {retry_policy}\n  failure_circuit_breaker: {'true' if failure_circuit_breaker else 'false'}\n"
        "workspace:\n  worktree_root: .nightshift/worktrees\n  artifact_root: nightshift-data/runs\n"
        "alerts:\n  enabled_channels: []\n  severity_thresholds:\n    info: info\n    warning: warning\n    critical: critical\n"
        "report:\n  output_directory: nightshift-data/reports\n  summary_verbosity: concise\n"
    )


def _make_ready_record(issue_id: str) -> IssueRecord:
    now = datetime(2026, 4, 9, tzinfo=timezone.utc)
    return IssueRecord(
        issue_id=issue_id,
        issue_state=IssueState.ready,
        attempt_state=AttemptState.pending,
        delivery_state=DeliveryState.none,
        queue_priority="high",
        created_at=now,
        updated_at=now,
    )


def test_run_cli_processes_schedulable_queue(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "nightshift.yaml"
    _write_config(config_path, tmp_path)

    class FakeOrchestrator:
        def run_one(self, issue_id: str) -> RunOneResult:
            if issue_id == "ISSUE-1":
                return RunOneResult(issue_id=issue_id, run_id="RUN-1", attempt_id="ATTEMPT-1", accepted=True)
            return RunOneResult(issue_id=issue_id, run_id="RUN-2", attempt_id="ATTEMPT-2", accepted=False)

    class FakeIssueRegistry:
        def list_schedulable_records(self) -> list[IssueRecord]:
            return [_make_ready_record("ISSUE-1"), _make_ready_record("ISSUE-2")]

    monkeypatch.setattr("nightshift.cli.app.build_run_orchestrator", lambda repo, config: FakeOrchestrator())
    monkeypatch.setattr("nightshift.cli.app.build_issue_registry", lambda repo: FakeIssueRegistry())

    result = CliRunner().invoke(app, ["run", "--repo", str(tmp_path), "--config", str(config_path)])

    assert result.exit_code == 0
    assert "ISSUE-1 accepted" in result.stdout
    assert "ISSUE-2 rejected" in result.stdout
    assert "run summary: rounds=1 accepted=1 rejected=1 failed=0" in result.stdout


def test_stop_cli_sets_stop_request_file(tmp_path: Path) -> None:
    result = CliRunner().invoke(app, ["stop", "--repo", str(tmp_path)])

    assert result.exit_code == 0
    assert "stop requested" in result.stdout
    payload = json.loads((tmp_path / "nightshift-data" / "stop-request.json").read_text())
    assert payload["requested"] is True


def test_logs_cli_returns_issue_scoped_history(tmp_path: Path) -> None:
    state_store = StateStore(tmp_path)
    state_store.save_run_state(
        RunState(
            run_id="RUN-1",
            run_state=RunLifecycleState.completed,
            started_at=datetime(2026, 4, 9, tzinfo=timezone.utc),
            ended_at=datetime(2026, 4, 9, tzinfo=timezone.utc),
            issues_attempted=1,
            issues_completed=1,
        )
    )
    state_store.save_attempt_record(
        AttemptRecord(
            attempt_id="ATTEMPT-1",
            issue_id="ISSUE-1",
            run_id="RUN-1",
            engine_name="codex",
            engine_invocation_id="invoke-1",
            attempt_state=AttemptState.accepted,
            summary="ok",
            validation_result=AttemptValidationResult(
                passed=True,
                summary="validation passed",
            ),
        )
    )
    state_store.append_event(
        EventRecord(
            seq=1,
            run_id="RUN-1",
            issue_id="ISSUE-1",
            attempt_id="ATTEMPT-1",
            event_type="attempt_finished",
            payload={"accepted": True},
            created_at=datetime(2026, 4, 9, tzinfo=timezone.utc),
        )
    )
    state_store.append_alert(
        AlertEvent(
            alert_id="ALERT-1",
            run_id="RUN-1",
            issue_id="ISSUE-1",
            severity=AlertSeverity.info,
            event_type="run_completed",
            summary="issue completed",
            delivery_status="not_sent",
            created_at=datetime(2026, 4, 9, tzinfo=timezone.utc),
        )
    )

    result = CliRunner().invoke(app, ["logs", "--issue", "ISSUE-1", "--repo", str(tmp_path)])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["issue_id"] == "ISSUE-1"
    assert len(payload["runs"]) == 1
    assert payload["runs"][0]["run_id"] == "RUN-1"
    assert payload["runs"][0]["attempts"][0]["attempt_id"] == "ATTEMPT-1"
    assert payload["alerts"][0]["alert_id"] == "ALERT-1"


def test_alerts_cli_supports_filters(tmp_path: Path) -> None:
    state_store = StateStore(tmp_path)
    state_store.append_alert(
        AlertEvent(
            alert_id="ALERT-1",
            run_id="RUN-1",
            issue_id="ISSUE-1",
            severity=AlertSeverity.warning,
            event_type="issue_blocked",
            summary="issue blocked",
            delivery_status="not_sent",
            created_at=datetime(2026, 4, 9, tzinfo=timezone.utc),
        )
    )
    state_store.append_alert(
        AlertEvent(
            alert_id="ALERT-2",
            run_id="RUN-2",
            issue_id="ISSUE-2",
            severity=AlertSeverity.critical,
            event_type="run_aborted",
            summary="run aborted",
            delivery_status="not_sent",
            created_at=datetime(2026, 4, 9, tzinfo=timezone.utc),
        )
    )

    result = CliRunner().invoke(
        app,
        ["alerts", "--repo", str(tmp_path), "--run", "RUN-1", "--severity", "warning"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["count"] == 1
    assert payload["filters"]["run_id"] == "RUN-1"
    assert payload["filters"]["severity"] == "warning"
    assert payload["alerts"][0]["alert_id"] == "ALERT-1"


def test_run_cli_marks_issue_retryable_when_retry_budget_allows(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "nightshift.yaml"
    _write_config(config_path, tmp_path, max_retries=1, retry_policy="exponential_backoff")
    registry = IssueRegistry(tmp_path)
    registry.save_record(_make_ready_record("ISSUE-RETRY"))

    class FakeOrchestrator:
        def run_one(self, issue_id: str) -> RunOneResult:
            assert issue_id == "ISSUE-RETRY"
            return RunOneResult(issue_id=issue_id, run_id="RUN-1", attempt_id="ATTEMPT-1", accepted=False)

    monkeypatch.setattr("nightshift.cli.app.build_run_orchestrator", lambda repo, config: FakeOrchestrator())

    result = CliRunner().invoke(app, ["run", "--repo", str(tmp_path), "--config", str(config_path)])

    assert result.exit_code == 0
    updated = registry.get_record("ISSUE-RETRY")
    assert updated.issue_state == IssueState.ready
    assert updated.attempt_state == AttemptState.retryable
    assert updated.retry_count == 1
    assert "retry scheduled for ISSUE-RETRY" in result.stdout


def test_run_cli_defers_issue_when_retry_budget_exhausted(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "nightshift.yaml"
    _write_config(config_path, tmp_path, max_retries=0, retry_policy="exponential_backoff")
    registry = IssueRegistry(tmp_path)
    registry.save_record(_make_ready_record("ISSUE-NORETRY"))

    class FakeOrchestrator:
        def run_one(self, issue_id: str) -> RunOneResult:
            assert issue_id == "ISSUE-NORETRY"
            return RunOneResult(issue_id=issue_id, run_id="RUN-1", attempt_id="ATTEMPT-1", accepted=False)

    monkeypatch.setattr("nightshift.cli.app.build_run_orchestrator", lambda repo, config: FakeOrchestrator())

    result = CliRunner().invoke(app, ["run", "--repo", str(tmp_path), "--config", str(config_path)])

    assert result.exit_code == 0
    updated = registry.get_record("ISSUE-NORETRY")
    assert updated.issue_state == IssueState.deferred
    assert updated.attempt_state == AttemptState.rejected
    assert updated.deferred_reason == "retry_budget_exhausted"
    assert "retry skipped for ISSUE-NORETRY" in result.stdout


def test_run_cli_triggers_failure_circuit_breaker_and_emits_critical_alert(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "nightshift.yaml"
    _write_config(
        config_path,
        tmp_path,
        max_retries=1,
        retry_policy="exponential_backoff",
        failure_circuit_breaker=True,
    )
    registry = IssueRegistry(tmp_path)
    registry.save_record(_make_ready_record("ISSUE-BREAKER"))
    state_store = StateStore(tmp_path)

    class FakeOrchestrator:
        def run_one(self, issue_id: str) -> RunOneResult:
            assert issue_id == "ISSUE-BREAKER"
            return RunOneResult(issue_id=issue_id, run_id="RUN-1", attempt_id="ATTEMPT-1", accepted=False)

    monkeypatch.setattr("nightshift.cli.app.build_run_orchestrator", lambda repo, config: FakeOrchestrator())

    result = CliRunner().invoke(app, ["run", "--repo", str(tmp_path), "--config", str(config_path)])

    assert result.exit_code == 0
    assert "failure circuit breaker triggered; exiting run loop" in result.stdout
    alerts = state_store.read_alerts(severity=AlertSeverity.critical)
    assert len(alerts) == 1
    assert alerts[0].event_type == "circuit_breaker_triggered"
    assert alerts[0].issue_id == "ISSUE-BREAKER"


def test_run_cli_does_not_trigger_circuit_breaker_when_disabled(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "nightshift.yaml"
    _write_config(
        config_path,
        tmp_path,
        max_retries=1,
        retry_policy="exponential_backoff",
        failure_circuit_breaker=False,
    )
    registry = IssueRegistry(tmp_path)
    registry.save_record(_make_ready_record("ISSUE-NOBREAKER"))
    state_store = StateStore(tmp_path)

    class FakeOrchestrator:
        def run_one(self, issue_id: str) -> RunOneResult:
            assert issue_id == "ISSUE-NOBREAKER"
            return RunOneResult(issue_id=issue_id, run_id="RUN-1", attempt_id="ATTEMPT-1", accepted=False)

    monkeypatch.setattr("nightshift.cli.app.build_run_orchestrator", lambda repo, config: FakeOrchestrator())

    result = CliRunner().invoke(app, ["run", "--repo", str(tmp_path), "--config", str(config_path)])

    assert result.exit_code == 0
    assert "failure circuit breaker triggered; exiting run loop" not in result.stdout
    alerts = state_store.read_alerts(severity=AlertSeverity.critical)
    assert alerts == []
