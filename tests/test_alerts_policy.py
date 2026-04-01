from __future__ import annotations

from datetime import datetime, timezone

from nightshift.domain.enums import AlertSeverity
from nightshift.product.alerts import AlertPolicy, AlertTrigger, AlertTriggerSource


def test_alert_policy_builds_critical_daemon_failure_event() -> None:
    policy = AlertPolicy()
    trigger = AlertTrigger(
        run_id="RUN-1",
        source=AlertTriggerSource.daemon_aborted,
        summary="daemon loop aborted",
        details={"reason": "engine crash"},
    )

    event = policy.create_event(
        trigger,
        alert_id="ALERT-1",
        created_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
    )

    assert event.alert_id == "ALERT-1"
    assert event.run_id == "RUN-1"
    assert event.severity == AlertSeverity.critical
    assert event.event_type == "daemon_aborted"
    assert event.summary == "daemon loop aborted"
    assert event.details == {"reason": "engine crash"}
    assert event.delivery_status == "pending"


def test_alert_policy_defaults_delivery_failure_to_warning() -> None:
    policy = AlertPolicy()
    trigger = AlertTrigger(
        run_id="RUN-2",
        source=AlertTriggerSource.delivery_failed,
        issue_id="GH-7",
    )

    event = policy.create_event(
        trigger,
        alert_id="ALERT-2",
        created_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
    )

    assert event.severity == AlertSeverity.warning
    assert event.issue_id == "GH-7"
    assert "delivery failed" in event.summary.lower()
