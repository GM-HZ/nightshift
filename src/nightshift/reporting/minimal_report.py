from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from nightshift.domain import RunLifecycleState


def _enum_value(value: object) -> str:
    return str(getattr(value, "value", value))


class RetryDistribution(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_retries: int
    issues_with_retries: int
    max_retries_on_single_issue: int
    retry_histogram: dict[str, int]


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
    attempts_by_state: dict[str, int]
    engine_usage: dict[str, int]
    retry_distribution: RetryDistribution
    alert_count: int
    alerts_by_severity: dict[str, int]
    delivery_refs: tuple[str, ...]
    delivery_ids: tuple[str, ...]
    artifact_dirs: tuple[str, ...]
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
    return runs[-1].run_id


def build_minimal_report(state_store: Any, run_id: str | None = None) -> MinimalReport:
    resolved_run_id = resolve_report_run_id(state_store, run_id)
    run_state = state_store.load_run_state(resolved_run_id)
    issue_snapshots = state_store.list_run_issue_snapshots(resolved_run_id)
    attempts = state_store.list_attempt_records(resolved_run_id)
    events = state_store.read_events(resolved_run_id)
    alerts = state_store.read_alerts(run_id=resolved_run_id)

    attempts_by_state = Counter(_enum_value(attempt.attempt_state) for attempt in attempts)
    engine_usage = Counter(attempt.engine_name for attempt in attempts)

    attempt_count_by_issue = Counter(attempt.issue_id for attempt in attempts)
    retries_by_issue = {issue_id: max(0, count - 1) for issue_id, count in attempt_count_by_issue.items()}
    total_retries = sum(retries_by_issue.values())
    issues_with_retries = sum(1 for retry_count in retries_by_issue.values() if retry_count > 0)
    max_retries_on_single_issue = max(retries_by_issue.values(), default=0)
    retry_histogram = {
        "0": sum(1 for retry_count in retries_by_issue.values() if retry_count == 0),
        "1": sum(1 for retry_count in retries_by_issue.values() if retry_count == 1),
        "2+": sum(1 for retry_count in retries_by_issue.values() if retry_count >= 2),
    }

    alerts_by_severity = Counter(_enum_value(alert.severity) for alert in alerts)
    delivery_refs = tuple(
        sorted({record.delivery_ref for record in issue_snapshots if getattr(record, "delivery_ref", None)})
    )
    delivery_ids = tuple(
        sorted({record.delivery_id for record in issue_snapshots if getattr(record, "delivery_id", None)})
    )
    artifact_dirs = tuple(sorted({attempt.artifact_dir for attempt in attempts if attempt.artifact_dir}))

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
        attempts_by_state=dict(attempts_by_state),
        engine_usage=dict(engine_usage),
        retry_distribution=RetryDistribution(
            total_retries=total_retries,
            issues_with_retries=issues_with_retries,
            max_retries_on_single_issue=max_retries_on_single_issue,
            retry_histogram=retry_histogram,
        ),
        alert_count=len(alerts),
        alerts_by_severity=dict(alerts_by_severity),
        delivery_refs=delivery_refs,
        delivery_ids=delivery_ids,
        artifact_dirs=artifact_dirs,
        recent_event_types=tuple(event.event_type for event in events[-4:]),
    )
