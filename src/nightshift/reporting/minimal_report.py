from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from nightshift.domain import RunLifecycleState


class MinimalReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    run_state: RunLifecycleState
    started_at: datetime | None = None
    ended_at: datetime | None = None
    issues_attempted: int
    issues_completed: int
    issues_blocked: int
    issues_deferred: int
    issue_snapshot_count: int
    attempt_count: int
    recent_event_types: tuple[str, ...]


def resolve_report_run_id(state_store: Any, run_id: str | None) -> str:
    if run_id is not None:
        return run_id

    active_run_id = state_store.get_active_run()
    if active_run_id is not None:
        return active_run_id

    runs = state_store.list_runs()
    if not runs:
        raise ValueError("no runs available for reporting")
    latest_run = max(runs, key=lambda run: (run.started_at is not None, run.started_at, run.run_id))
    return latest_run.run_id


def build_minimal_report(state_store: Any, run_id: str | None = None) -> MinimalReport:
    resolved_run_id = resolve_report_run_id(state_store, run_id)
    run_state = state_store.load_run_state(resolved_run_id)
    issue_snapshots = state_store.list_run_issue_snapshots(resolved_run_id)
    attempts = state_store.list_attempt_records(resolved_run_id)
    events = state_store.read_events(resolved_run_id)

    return MinimalReport(
        run_id=run_state.run_id,
        run_state=run_state.run_state,
        started_at=run_state.started_at,
        ended_at=run_state.ended_at,
        issues_attempted=run_state.issues_attempted,
        issues_completed=run_state.issues_completed,
        issues_blocked=run_state.issues_blocked,
        issues_deferred=run_state.issues_deferred,
        issue_snapshot_count=len(issue_snapshots),
        attempt_count=len(attempts),
        recent_event_types=tuple(event.event_type for event in events[-4:]),
    )
