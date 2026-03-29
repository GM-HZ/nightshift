import json
from pathlib import Path

import pytest

from nightshift.domain import AlertEvent, AttemptRecord, EventRecord, IssueState
from nightshift.domain.enums import RunState as RunLifecycleState
from nightshift.domain.records import IssueRecord, RunState as RunStateRecord
from nightshift.config.models import RuntimeStorageMode
from nightshift.product.overnight.loop_metadata import DaemonLoopMetadata
from nightshift.store.state_store import StateStore
from nightshift.store.filesystem import write_json


def make_issue_record(issue_id: str, *, issue_state: IssueState = IssueState.ready) -> IssueRecord:
    return IssueRecord.model_validate(
        {
            "issue_id": issue_id,
            "issue_state": issue_state,
            "attempt_state": "pending",
            "delivery_state": "none",
            "queue_priority": "high",
            "created_at": "2026-03-28T00:00:00Z",
            "updated_at": "2026-03-28T00:00:00Z",
        }
    )


def make_run_state(run_id: str, *, run_state: RunLifecycleState = RunLifecycleState.running) -> RunStateRecord:
    return RunStateRecord.model_validate(
        {
            "run_id": run_id,
            "run_state": run_state,
            "base_branch": "main",
            "started_at": "2026-03-28T00:00:00Z",
            "issues_attempted": 1,
            "issues_completed": 0,
            "issues_blocked": 0,
            "issues_deferred": 0,
            "active_issue_id": "ISSUE-1",
            "active_attempt_id": "ATT-1",
            "active_worktrees": ["/tmp/worktree"],
            "alert_counts": {"critical": 1},
        }
    )


def make_attempt_record(attempt_id: str, issue_id: str, run_id: str) -> AttemptRecord:
    return AttemptRecord.model_validate(
        {
            "attempt_id": attempt_id,
            "issue_id": issue_id,
            "run_id": run_id,
            "engine_name": "gpt-5",
            "engine_invocation_id": f"INV-{attempt_id}",
            "attempt_state": "pending",
        }
    )


def make_event(seq: int, run_id: str, *, issue_id: str | None = None, attempt_id: str | None = None) -> EventRecord:
    return EventRecord.model_validate(
        {
            "seq": seq,
            "run_id": run_id,
            "issue_id": issue_id,
            "attempt_id": attempt_id,
            "event_type": "run.started",
            "payload": {"seq": seq},
            "created_at": "2026-03-28T00:00:00Z",
        }
    )


def make_alert(alert_id: str, run_id: str, *, issue_id: str | None = None, severity: str = "warning") -> AlertEvent:
    return AlertEvent.model_validate(
        {
            "alert_id": alert_id,
            "run_id": run_id,
            "issue_id": issue_id,
            "severity": severity,
            "event_type": "run.degraded",
            "summary": "Something needs attention",
            "created_at": "2026-03-28T00:00:00Z",
            "delivery_status": "pending",
        }
    )


def make_daemon_loop_metadata(run_id: str) -> DaemonLoopMetadata:
    return DaemonLoopMetadata.model_validate(
        {
            "run_id": run_id,
            "loop_mode": "daemon",
            "fail_fast": True,
            "stop_requested": False,
            "stopped_reason": None,
            "created_at": "2026-03-28T00:00:00Z",
            "updated_at": "2026-03-28T00:00:00Z",
        }
    )


def _write_layered_runtime_marker(repo_root: Path) -> None:
    migration_marker = repo_root / ".nightshift/config/migration.yaml"
    migration_marker.parent.mkdir(parents=True, exist_ok=True)
    migration_marker.write_text(
        """
layout_version: 1
project_config_source: layered
runtime_layout_source: layered
contract_storage_source: layered
"""
    )


def test_state_store_saves_and_loads_run_state(tmp_path: Path) -> None:
    store = StateStore(tmp_path)
    run_state = make_run_state("run-1")

    store.save_run_state(run_state)

    loaded = store.load_run_state("run-1")

    assert loaded.run_id == "run-1"
    assert loaded.run_state == RunLifecycleState.running
    assert (tmp_path / "nightshift-data" / "runs" / "run-1" / "run-state.json").is_file()


def test_write_json_is_atomicish(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "payload.json"
    target.write_text('{"original": true}\n')
    original = target.read_text()
    calls: list[tuple[str, str]] = []

    def fake_replace(self: Path, destination: Path) -> Path:
        calls.append((str(self), str(destination)))
        raise RuntimeError("boom")

    monkeypatch.setattr(Path, "replace", fake_replace, raising=False)

    with pytest.raises(RuntimeError, match="boom"):
        write_json(target, {"new": "value"})

    assert target.read_text() == original
    assert calls


def test_state_store_lists_runs(tmp_path: Path) -> None:
    store = StateStore(tmp_path)
    store.save_run_state(make_run_state("run-2"))
    store.save_run_state(make_run_state("run-1"))

    assert [run.run_id for run in store.list_runs()] == ["run-1", "run-2"]


def test_state_store_tracks_active_run(tmp_path: Path) -> None:
    store = StateStore(tmp_path)

    store.set_active_run("run-1")

    assert store.get_active_run() == "run-1"
    store.set_active_run(None)
    assert store.get_active_run() is None
    assert (tmp_path / "nightshift-data" / "active-run.json").is_file()


def test_state_store_tracks_active_daemon_run(tmp_path: Path) -> None:
    store = StateStore(tmp_path)

    store.set_active_daemon_run("run-1")

    assert store.get_active_daemon_run() == "run-1"
    store.set_active_daemon_run(None)
    assert store.get_active_daemon_run() is None
    assert (tmp_path / "nightshift-data" / "active-daemon-run.json").is_file()


def test_state_store_uses_layered_runtime_paths_when_marker_declares_layered(tmp_path: Path) -> None:
    _write_layered_runtime_marker(tmp_path)
    store = StateStore(tmp_path)

    assert store.runtime_storage.mode is RuntimeStorageMode.LAYERED
    assert store.runtime_storage.records_root == tmp_path / ".nightshift" / "records" / "current"
    assert store.runtime_storage.active_run_path == tmp_path / ".nightshift" / "records" / "active-run.json"
    assert store.runtime_storage.runs_root == tmp_path / ".nightshift" / "runs"
    assert store.runtime_storage.alerts_path == tmp_path / ".nightshift" / "records" / "alerts.ndjson"

    run_state = make_run_state("run-layered")
    store.save_run_state(run_state)
    store.set_active_run("run-layered")
    store.append_alert(make_alert("ALERT-LAYERED", "run-layered"))
    store.append_event(make_event(1, "run-layered"))

    assert store.load_run_state("run-layered") == run_state
    assert store.get_active_run() == "run-layered"
    assert (tmp_path / ".nightshift" / "runs" / "run-layered" / "run-state.json").is_file()
    assert (tmp_path / ".nightshift" / "records" / "active-run.json").is_file()
    assert (tmp_path / ".nightshift" / "records" / "alerts.ndjson").is_file()
    assert (tmp_path / ".nightshift" / "runs" / "run-layered" / "events.ndjson").is_file()


def test_state_store_tracks_active_daemon_run_in_layered_runtime_layout(tmp_path: Path) -> None:
    _write_layered_runtime_marker(tmp_path)
    store = StateStore(tmp_path)

    store.set_active_daemon_run("run-layered")

    assert store.get_active_daemon_run() == "run-layered"
    assert (tmp_path / ".nightshift" / "records" / "active-daemon-run.json").is_file()


def test_state_store_saves_and_loads_daemon_loop_metadata(tmp_path: Path) -> None:
    store = StateStore(tmp_path)
    metadata = make_daemon_loop_metadata("run-1")

    store.save_daemon_loop_metadata(metadata)

    loaded = store.load_daemon_loop_metadata("run-1")

    assert loaded == metadata
    assert (tmp_path / "nightshift-data" / "runs" / "run-1" / "daemon-loop.json").is_file()


def test_state_store_uses_layered_runtime_paths_for_daemon_loop_metadata(tmp_path: Path) -> None:
    _write_layered_runtime_marker(tmp_path)
    store = StateStore(tmp_path)
    metadata = make_daemon_loop_metadata("run-layered")

    store.save_daemon_loop_metadata(metadata)

    loaded = store.load_daemon_loop_metadata("run-layered")

    assert loaded == metadata
    assert (tmp_path / ".nightshift" / "runs" / "run-layered" / "daemon-loop.json").is_file()


def test_state_store_saves_and_lists_run_issue_snapshots(tmp_path: Path) -> None:
    store = StateStore(tmp_path)
    store.save_run_issue_snapshot("run-1", make_issue_record("ISSUE-1"))
    store.save_run_issue_snapshot("run-1", make_issue_record("ISSUE-2"))

    assert [record.issue_id for record in store.list_run_issue_snapshots("run-1")] == ["ISSUE-1", "ISSUE-2"]


def test_state_store_saves_loads_and_lists_attempt_records(tmp_path: Path) -> None:
    store = StateStore(tmp_path)
    attempt_one = make_attempt_record("ATT-1", "ISSUE-1", "run-1")
    attempt_two = make_attempt_record("ATT-2", "ISSUE-1", "run-1")

    store.save_attempt_record(attempt_one)
    store.save_attempt_record(attempt_two)

    assert store.load_attempt_record("ATT-1") == attempt_one
    assert [attempt.attempt_id for attempt in store.list_attempt_records("run-1")] == ["ATT-1", "ATT-2"]
    assert [attempt.attempt_id for attempt in store.list_attempt_records("run-1", issue_id="ISSUE-1")] == [
        "ATT-1",
        "ATT-2",
    ]


def test_state_store_appends_and_reads_events(tmp_path: Path) -> None:
    store = StateStore(tmp_path)
    store.append_event(make_event(1, "run-1", issue_id="ISSUE-1"))
    store.append_event(make_event(2, "run-1", issue_id="ISSUE-1", attempt_id="ATT-1"))

    assert [event.seq for event in store.read_events("run-1")] == [1, 2]
    assert [event.seq for event in store.read_events("run-1", since_seq=2)] == [2]


def test_state_store_ignores_truncated_event_lines(tmp_path: Path) -> None:
    store = StateStore(tmp_path)
    events_path = tmp_path / "nightshift-data" / "runs" / "run-1" / "events.ndjson"
    events_path.parent.mkdir(parents=True, exist_ok=True)
    events_path.write_text(
        "\n".join(
            [
                json.dumps(make_event(1, "run-1").model_dump(mode="json")),
                '{"seq": 2, "run_id": "run-1"',
            ]
        )
        + "\n"
    )

    assert [event.seq for event in store.read_events("run-1")] == [1]


def test_state_store_appends_and_reads_alerts(tmp_path: Path) -> None:
    store = StateStore(tmp_path)
    store.append_alert(make_alert("ALERT-1", "run-1", issue_id="ISSUE-1", severity="warning"))
    store.append_alert(make_alert("ALERT-2", "run-2", issue_id="ISSUE-1", severity="critical"))

    assert [alert.alert_id for alert in store.read_alerts(run_id="run-1")] == ["ALERT-1"]
    assert [alert.alert_id for alert in store.read_alerts(issue_id="ISSUE-1")] == ["ALERT-1", "ALERT-2"]
    assert [alert.alert_id for alert in store.read_alerts(severity="critical")] == ["ALERT-2"]


def test_state_store_ignores_truncated_alert_lines(tmp_path: Path) -> None:
    store = StateStore(tmp_path)
    alerts_path = tmp_path / "nightshift-data" / "alerts.ndjson"
    alerts_path.parent.mkdir(parents=True, exist_ok=True)
    alerts_path.write_text(
        "\n".join(
            [
                json.dumps(make_alert("ALERT-1", "run-1").model_dump(mode="json")),
                '{"alert_id": "ALERT-2", "run_id": "run-1"',
            ]
        )
        + "\n"
    )

    assert [alert.alert_id for alert in store.read_alerts()] == ["ALERT-1"]


def test_state_store_rejects_path_traversal_identifiers(tmp_path: Path) -> None:
    store = StateStore(tmp_path)

    with pytest.raises(ValueError):
        store.save_run_state(make_run_state("../run-1"))

    with pytest.raises(ValueError):
        store.save_run_issue_snapshot("../run-1", make_issue_record("ISSUE-1"))

    with pytest.raises(ValueError):
        store.list_attempt_records("../run-1")

    with pytest.raises(ValueError):
        store.save_attempt_record(make_attempt_record("../ATT-1", "ISSUE-1", "run-1"))
