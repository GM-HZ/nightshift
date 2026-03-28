from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json

from typer.testing import CliRunner

from nightshift.cli.app import app
from nightshift.domain import AttemptState, DeliveryState, IssueState, RunLifecycleState
from nightshift.domain.records import AttemptRecord, EventRecord, IssueRecord, RunState
from nightshift.reporting.minimal_report import MinimalReport, build_minimal_report, resolve_report_run_id
from nightshift.store.state_store import StateStore


def make_run_state(
    run_id: str,
    *,
    run_state: RunLifecycleState = RunLifecycleState.completed,
    active_issue_id: str | None = None,
    active_attempt_id: str | None = None,
) -> RunState:
    return RunState.model_validate(
        {
            "run_id": run_id,
            "run_state": run_state,
            "base_branch": "main",
            "started_at": "2026-03-28T00:00:00Z",
            "ended_at": "2026-03-28T00:05:00Z",
            "issues_attempted": 2,
            "issues_completed": 1,
            "issues_blocked": 1,
            "issues_deferred": 0,
            "active_issue_id": active_issue_id,
            "active_attempt_id": active_attempt_id,
            "active_worktrees": [],
            "alert_counts": {},
        }
    )


def make_issue_record(issue_id: str, *, issue_state: IssueState) -> IssueRecord:
    now = datetime(2026, 3, 28, tzinfo=timezone.utc)
    return IssueRecord(
        issue_id=issue_id,
        issue_state=issue_state,
        attempt_state=AttemptState.accepted if issue_state == IssueState.done else AttemptState.pending,
        delivery_state=DeliveryState.none,
        queue_priority="high",
        accepted_attempt_id="ATT-1" if issue_state == IssueState.done else None,
        created_at=now,
        updated_at=now,
    )


def make_attempt_record(attempt_id: str, issue_id: str, run_id: str, *, state: AttemptState) -> AttemptRecord:
    payload: dict[str, object] = {
        "attempt_id": attempt_id,
        "issue_id": issue_id,
        "run_id": run_id,
        "engine_name": "codex",
        "engine_invocation_id": f"INV-{attempt_id}",
        "attempt_state": state,
        "engine_outcome": "normalized output",
        "validation_result": None,
        "worktree_path": "/tmp/worktree",
        "artifact_dir": "/tmp/artifacts",
    }
    if state == AttemptState.accepted:
        payload["validation_result"] = {
            "passed": True,
            "summary": "validation passed",
            "details": {"checks": 1},
        }
    return AttemptRecord.model_validate(payload)


def make_event(seq: int, run_id: str, event_type: str) -> EventRecord:
    return EventRecord.model_validate(
        {
            "seq": seq,
            "run_id": run_id,
            "issue_id": "ISSUE-1",
            "attempt_id": "ATT-1",
            "event_type": event_type,
            "payload": {"seq": seq},
            "created_at": "2026-03-28T00:00:00Z",
        }
    )


def test_resolve_report_run_id_prefers_active_run_then_latest_run(tmp_path: Path) -> None:
    store = StateStore(tmp_path)
    store.save_run_state(make_run_state("run-20260328T000100Z-a"))
    store.save_run_state(make_run_state("run-20260328T000200Z-b"))
    store.set_active_run("run-20260328T000100Z-a")

    assert resolve_report_run_id(store, None) == "run-20260328T000100Z-a"

    store.set_active_run(None)

    assert resolve_report_run_id(store, None) == "run-20260328T000200Z-b"


def test_build_minimal_report_summarizes_persisted_history(tmp_path: Path) -> None:
    store = StateStore(tmp_path)
    store.save_run_state(make_run_state("run-1"))
    store.save_run_issue_snapshot("run-1", make_issue_record("ISSUE-1", issue_state=IssueState.done))
    store.save_run_issue_snapshot("run-1", make_issue_record("ISSUE-2", issue_state=IssueState.ready))
    store.save_attempt_record(make_attempt_record("ATT-1", "ISSUE-1", "run-1", state=AttemptState.accepted))
    store.save_attempt_record(make_attempt_record("ATT-2", "ISSUE-2", "run-1", state=AttemptState.rejected))
    store.append_event(make_event(1, "run-1", "run_started"))
    store.append_event(make_event(2, "run-1", "attempt_started"))
    store.append_event(make_event(3, "run-1", "attempt_finished"))
    store.append_event(make_event(4, "run-1", "run_completed"))

    report = build_minimal_report(store, "run-1")

    assert isinstance(report, MinimalReport)
    assert report.run_id == "run-1"
    assert report.run_state == RunLifecycleState.completed
    assert report.issues_attempted == 2
    assert report.issues_completed == 1
    assert report.issues_blocked == 1
    assert report.issues_deferred == 0
    assert report.issue_snapshot_count == 2
    assert report.attempt_count == 2
    assert report.recent_event_types == ("run_started", "attempt_started", "attempt_finished", "run_completed")


def test_report_command_defaults_to_active_run_and_emits_json(tmp_path: Path) -> None:
    store = StateStore(tmp_path)
    store.save_run_state(make_run_state("run-1"))
    store.set_active_run("run-1")
    store.save_run_issue_snapshot("run-1", make_issue_record("ISSUE-1", issue_state=IssueState.done))
    store.save_attempt_record(make_attempt_record("ATT-1", "ISSUE-1", "run-1", state=AttemptState.accepted))
    store.append_event(make_event(1, "run-1", "run_started"))

    result = CliRunner().invoke(app, ["report", "--repo", str(tmp_path)])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["run_id"] == "run-1"
    assert payload["issue_snapshot_count"] == 1


def test_report_command_can_use_repo_from_config_and_persist_output_file(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    reports_dir = tmp_path / "reports"
    config_path = tmp_path / "nightshift.yaml"
    config_path.write_text(f"project:\n  repo_path: {repo_root}\n  main_branch: main\nrunner:\n  default_engine: codex\n  issue_timeout_seconds: 1\n  overnight_timeout_seconds: 1\nvalidation:\n  enabled: true\nissue_defaults:\n  default_priority: high\n  default_forbidden_paths: [secrets]\n  default_test_edit_policy:\n    can_add_tests: true\n    can_modify_existing_tests: true\n    can_weaken_assertions: false\n    requires_test_change_reason: true\n  default_attempt_limits:\n    max_files_changed: 1\n    max_lines_added: 1\n    max_lines_deleted: 1\n  default_timeouts:\n    command_seconds: 1\n    issue_budget_seconds: 1\nretry:\n  max_retries: 1\n  retry_policy: never\n  failure_circuit_breaker: false\nworkspace:\n  worktree_root: .nightshift/worktrees\n  artifact_root: nightshift-data/runs\nalerts:\n  enabled_channels: []\n  severity_thresholds:\n    info: info\n    warning: warning\n    critical: critical\nreport:\n  output_directory: {reports_dir}\n  summary_verbosity: concise\n")
    store = StateStore(repo_root)
    store.save_run_state(make_run_state("run-1"))
    store.set_active_run("run-1")
    store.save_run_issue_snapshot("run-1", make_issue_record("ISSUE-1", issue_state=IssueState.done))
    store.save_attempt_record(make_attempt_record("ATT-1", "ISSUE-1", "run-1", state=AttemptState.accepted))
    store.append_event(make_event(1, "run-1", "run_started"))

    result = CliRunner().invoke(app, ["report", "--config", str(config_path)])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["run_id"] == "run-1"
    report_path = reports_dir / "run-1.json"
    assert report_path.is_file()
    assert json.loads(report_path.read_text())["run_id"] == "run-1"
