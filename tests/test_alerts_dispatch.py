from __future__ import annotations

from datetime import datetime, timezone
from io import StringIO

from nightshift.domain import AlertEvent
from nightshift.domain.enums import AlertSeverity
from nightshift.product.alerts import (
    AlertDispatcher,
    ConsoleAlertChannel,
    DispatchDecision,
    WebhookAlertChannel,
)


def make_alert(severity: AlertSeverity = AlertSeverity.warning) -> AlertEvent:
    return AlertEvent.model_validate(
        {
            "alert_id": "ALERT-1",
            "run_id": "RUN-1",
            "issue_id": "GH-7",
            "severity": severity,
            "event_type": "delivery_failed",
            "summary": "delivery failed",
            "details": {"branch_name": "nightshift-gh-7"},
            "created_at": datetime(2026, 4, 1, tzinfo=timezone.utc),
            "delivery_status": "pending",
        }
    )


def test_console_alert_channel_writes_human_readable_output() -> None:
    stream = StringIO()
    channel = ConsoleAlertChannel(stream=stream)

    decision = channel.send(make_alert())

    assert decision.delivered is True
    output = stream.getvalue()
    assert "ALERT-1" in output
    assert "delivery failed" in output
    assert "RUN-1" in output


def test_webhook_alert_channel_posts_json_payload() -> None:
    captured: dict[str, object] = {}

    def fake_opener(request):
        captured["url"] = request.full_url
        captured["body"] = request.data.decode("utf-8")

        class Response:
            status = 200

            def read(self):
                return b"ok"

        return Response()

    channel = WebhookAlertChannel(url="https://alerts.example.test/hook", opener=fake_opener)

    decision = channel.send(make_alert())

    assert decision.delivered is True
    assert captured["url"] == "https://alerts.example.test/hook"
    assert '"alert_id": "ALERT-1"' in str(captured["body"])
    assert '"event_type": "delivery_failed"' in str(captured["body"])


def test_dispatcher_routes_by_enabled_channels_and_severity_threshold() -> None:
    stream = StringIO()
    captured: list[str] = []

    def fake_opener(request):
        captured.append(request.full_url)

        class Response:
            status = 200

            def read(self):
                return b"ok"

        return Response()

    dispatcher = AlertDispatcher(
        channels={
            "console": ConsoleAlertChannel(stream=stream),
            "webhook": WebhookAlertChannel(url="https://alerts.example.test/hook", opener=fake_opener),
        },
        enabled_channels=("console", "webhook"),
        severity_thresholds={
            "console": AlertSeverity.info,
            "webhook": AlertSeverity.critical,
        },
    )

    result = dispatcher.dispatch(make_alert(severity=AlertSeverity.warning))

    assert result.alert.alert_id == "ALERT-1"
    assert [item.channel for item in result.results] == ["console", "webhook"]
    assert result.results[0].delivered is True
    assert result.results[1].delivered is False
    assert result.results[1].skipped is True
    assert captured == []
    assert "ALERT-1" in stream.getvalue()
