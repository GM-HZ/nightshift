from __future__ import annotations

from pathlib import Path

from nightshift.domain import AlertEvent, AttemptRecord, EventRecord, RunState
from nightshift.domain.enums import AlertSeverity
from nightshift.domain.records import IssueRecord
from nightshift.product.overnight.loop_metadata import DaemonLoopMetadata
from nightshift.config.loader import resolve_runtime_storage
from nightshift.store.filesystem import (
    append_ndjson,
    read_json,
    read_model_json,
    read_ndjson,
    safe_path_component,
    write_json,
    write_model_json,
)


class StateStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.runtime_storage = resolve_runtime_storage(self.root)

    def save_run_state(self, run_state: RunState) -> None:
        write_model_json(self._run_state_path(run_state.run_id), run_state)

    def load_run_state(self, run_id: str) -> RunState:
        return read_model_json(self._run_state_path(run_id), RunState)

    def list_runs(self, limit: int | None = None) -> list[RunState]:
        runs: list[RunState] = []
        if not self._runs_dir().exists():
            return runs

        for run_dir in sorted(path for path in self._runs_dir().iterdir() if path.is_dir()):
            run_state_path = run_dir / "run-state.json"
            if run_state_path.exists():
                runs.append(read_model_json(run_state_path, RunState))

        if limit is not None:
            return runs[:limit]
        return runs

    def set_active_run(self, run_id_or_none: str | None) -> None:
        write_json(self._active_run_path(), {"run_id": run_id_or_none})

    def get_active_run(self) -> str | None:
        if not self._active_run_path().exists():
            return None

        payload = read_json(self._active_run_path())
        if payload is None:
            return None
        return payload.get("run_id")

    def save_daemon_loop_metadata(self, metadata: DaemonLoopMetadata) -> None:
        write_model_json(self._daemon_loop_metadata_path(metadata.run_id), metadata)

    def load_daemon_loop_metadata(self, run_id: str) -> DaemonLoopMetadata:
        return read_model_json(self._daemon_loop_metadata_path(run_id), DaemonLoopMetadata)

    def set_active_daemon_run(self, run_id_or_none: str | None) -> None:
        write_json(self._active_daemon_run_path(), {"run_id": run_id_or_none})

    def get_active_daemon_run(self) -> str | None:
        if not self._active_daemon_run_path().exists():
            return None

        payload = read_json(self._active_daemon_run_path())
        if payload is None:
            return None
        return payload.get("run_id")

    def save_run_issue_snapshot(self, run_id: str, issue_record: IssueRecord) -> None:
        write_model_json(self._issue_snapshot_path(run_id, issue_record.issue_id), issue_record)

    def list_run_issue_snapshots(self, run_id: str) -> list[IssueRecord]:
        issues_dir = self._issues_dir(run_id)
        if not issues_dir.exists():
            return []
        return [read_model_json(path, IssueRecord) for path in sorted(issues_dir.glob("*.json"))]

    def save_attempt_record(self, attempt_record: AttemptRecord) -> None:
        write_model_json(self._attempt_path(attempt_record.run_id, attempt_record.attempt_id), attempt_record)

    def load_attempt_record(self, attempt_id: str) -> AttemptRecord:
        for path in self._attempt_paths():
            if path.name == f"{attempt_id}.json":
                return read_model_json(path, AttemptRecord)
        raise FileNotFoundError(attempt_id)

    def list_attempt_records(self, run_id: str, issue_id: str | None = None) -> list[AttemptRecord]:
        attempts_dir = self._attempts_dir(run_id)
        if not attempts_dir.exists():
            return []

        attempts = [read_model_json(path, AttemptRecord) for path in sorted(attempts_dir.glob("*.json"))]
        if issue_id is not None:
            attempts = [attempt for attempt in attempts if attempt.issue_id == issue_id]
        return attempts

    def append_event(self, event_record: EventRecord) -> None:
        append_ndjson(self._events_path(event_record.run_id), event_record.model_dump(mode="json"))

    def read_events(self, run_id: str, issue_id: str | None = None, since_seq: int | None = None) -> list[EventRecord]:
        events = [EventRecord.model_validate(payload) for payload in read_ndjson(self._events_path(run_id))]
        if issue_id is not None:
            events = [event for event in events if event.issue_id == issue_id]
        if since_seq is not None:
            events = [event for event in events if event.seq >= since_seq]
        return events

    def append_alert(self, alert_event: AlertEvent) -> None:
        append_ndjson(self._alerts_path(), alert_event.model_dump(mode="json"))

    def read_alerts(
        self,
        run_id: str | None = None,
        issue_id: str | None = None,
        severity: AlertSeverity | str | None = None,
    ) -> list[AlertEvent]:
        alerts = [AlertEvent.model_validate(payload) for payload in read_ndjson(self._alerts_path())]
        if run_id is not None:
            alerts = [alert for alert in alerts if alert.run_id == run_id]
        if issue_id is not None:
            alerts = [alert for alert in alerts if alert.issue_id == issue_id]
        if severity is not None:
            severity_value = AlertSeverity(severity)
            alerts = [alert for alert in alerts if alert.severity == severity_value]
        return alerts

    def _runs_dir(self) -> Path:
        return self.runtime_storage.runs_root

    def _run_state_path(self, run_id: str) -> Path:
        safe_run_id = safe_path_component(run_id, field_name="run_id")
        return self._runs_dir() / safe_run_id / "run-state.json"

    def _issues_dir(self, run_id: str) -> Path:
        safe_run_id = safe_path_component(run_id, field_name="run_id")
        return self._runs_dir() / safe_run_id / "issues"

    def _issue_snapshot_path(self, run_id: str, issue_id: str) -> Path:
        safe_issue_id = safe_path_component(issue_id, field_name="issue_id")
        return self._issues_dir(run_id) / f"{safe_issue_id}.json"

    def _attempts_dir(self, run_id: str) -> Path:
        safe_run_id = safe_path_component(run_id, field_name="run_id")
        return self._runs_dir() / safe_run_id / "attempts"

    def _attempt_path(self, run_id: str, attempt_id: str) -> Path:
        safe_attempt_id = safe_path_component(attempt_id, field_name="attempt_id")
        return self._attempts_dir(run_id) / f"{safe_attempt_id}.json"

    def _attempt_paths(self) -> list[Path]:
        if not self._runs_dir().exists():
            return []

        paths: list[Path] = []
        for run_dir in sorted(path for path in self._runs_dir().iterdir() if path.is_dir()):
            attempts_dir = run_dir / "attempts"
            if attempts_dir.exists():
                paths.extend(sorted(attempts_dir.glob("*.json")))
        return paths

    def _events_path(self, run_id: str) -> Path:
        safe_run_id = safe_path_component(run_id, field_name="run_id")
        return self._runs_dir() / safe_run_id / "events.ndjson"

    def _alerts_path(self) -> Path:
        return self.runtime_storage.alerts_path

    def _active_run_path(self) -> Path:
        return self.runtime_storage.active_run_path

    def _active_daemon_run_path(self) -> Path:
        return self.runtime_storage.records_root.parent / "active-daemon-run.json"

    def _daemon_loop_metadata_path(self, run_id: str) -> Path:
        safe_run_id = safe_path_component(run_id, field_name="run_id")
        return self._runs_dir() / safe_run_id / "daemon-loop.json"
