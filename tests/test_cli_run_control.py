from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from typer.testing import CliRunner

from nightshift.cli.app import app
from nightshift.domain import AlertSeverity, AttemptState, DeliveryState, IssueState, RunLifecycleState
from nightshift.domain.records import AlertEvent, AttemptRecord, AttemptValidationResult, EventRecord, IssueRecord, RunState
from nightshift.orchestrator.run_orchestrator import RunOneResult
from nightshift.store.state_store import StateStore


def _write_config(path: Path, repo_path: Path) -> None:
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
        "retry:\n  max_retries: 1\n  retry_policy: never\n  failure_circuit_breaker: false\n"
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
