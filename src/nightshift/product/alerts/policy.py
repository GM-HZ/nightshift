from __future__ import annotations

from datetime import datetime
from typing import Any, Callable

from nightshift.domain import AlertEvent
from nightshift.domain.enums import AlertSeverity

from .models import AlertTrigger, AlertTriggerSource


class AlertPolicy:
    def create_event(
        self,
        trigger: AlertTrigger,
        *,
        alert_id: str,
        created_at: datetime,
    ) -> AlertEvent:
        severity = _default_severity(trigger.source)
        summary = trigger.summary or _default_summary(trigger.source, trigger.issue_id)
        details = trigger.details
        return AlertEvent(
            alert_id=alert_id,
            run_id=trigger.run_id,
            issue_id=trigger.issue_id,
            severity=severity,
            event_type=trigger.source.value,
            summary=summary,
            details=details,
            created_at=created_at,
            delivery_status="pending",
        )

    def create_event_with_factory(
        self,
        trigger: AlertTrigger,
        *,
        alert_id_factory: Callable[[], str],
        now_factory: Callable[[], datetime],
    ) -> AlertEvent:
        return self.create_event(
            trigger,
            alert_id=alert_id_factory(),
            created_at=now_factory(),
        )


def _default_severity(source: AlertTriggerSource) -> AlertSeverity:
    if source in {
        AlertTriggerSource.daemon_aborted,
        AlertTriggerSource.recovery_failed,
        AlertTriggerSource.state_store_corruption,
        AlertTriggerSource.total_overnight_timeout,
    }:
        return AlertSeverity.critical
    if source in {
        AlertTriggerSource.delivery_failed,
        AlertTriggerSource.repeated_engine_crash,
    }:
        return AlertSeverity.warning
    return AlertSeverity.info


def _default_summary(source: AlertTriggerSource, issue_id: str | None) -> str:
    if source == AlertTriggerSource.delivery_failed and issue_id is not None:
        return f"delivery failed for {issue_id}"
    if source == AlertTriggerSource.daemon_stop_requested:
        return "daemon stop requested"
    if source == AlertTriggerSource.daemon_drained:
        return "daemon run drained"
    if source == AlertTriggerSource.recovery_failed:
        return "recovery failed"
    if source == AlertTriggerSource.state_store_corruption:
        return "state store corruption detected"
    if source == AlertTriggerSource.total_overnight_timeout:
        return "overnight timeout reached"
    if source == AlertTriggerSource.repeated_engine_crash:
        return "repeated engine crash detected"
    if source == AlertTriggerSource.daemon_aborted:
        return "daemon loop aborted"
    return source.value.replace("_", " ")
