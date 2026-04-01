from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Callable, Mapping, Protocol
from urllib.request import Request, urlopen

from nightshift.domain import AlertEvent
from nightshift.domain.enums import AlertSeverity

from .models import AlertDispatchResult, DispatchDecision


class AlertDispatchError(RuntimeError):
    pass


class AlertChannel(Protocol):
    def name(self) -> str:
        ...

    def send(self, alert: AlertEvent) -> DispatchDecision:
        ...


@dataclass(frozen=True, slots=True)
class ConsoleAlertChannel:
    stream: Any

    def name(self) -> str:
        return "console"

    def send(self, alert: AlertEvent) -> DispatchDecision:
        message = (
            f"[{alert.severity}] {alert.event_type} "
            f"run={alert.run_id} issue={alert.issue_id or '-'} alert={alert.alert_id} "
            f"{alert.summary}"
        )
        self.stream.write(message + "\n")
        return DispatchDecision(channel=self.name(), delivered=True, summary=message)


@dataclass(frozen=True, slots=True)
class WebhookAlertChannel:
    url: str
    opener: Callable[[Request], Any] | None = None

    def name(self) -> str:
        return "webhook"

    def send(self, alert: AlertEvent) -> DispatchDecision:
        payload = alert.model_dump(mode="json")
        request = Request(
            self.url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        opener = self.opener or urlopen
        try:
            response = opener(request)
            status = getattr(response, "status", 200)
            if status >= 400:
                return DispatchDecision(channel=self.name(), delivered=False, error=f"webhook returned status {status}")
        except Exception as exc:
            return DispatchDecision(channel=self.name(), delivered=False, error=str(exc))
        return DispatchDecision(channel=self.name(), delivered=True, summary=f"sent to {self.url}")


class AlertDispatcher:
    def __init__(
        self,
        *,
        channels: Mapping[str, AlertChannel],
        enabled_channels: tuple[str, ...],
        severity_thresholds: Mapping[str, AlertSeverity | str] | None = None,
    ) -> None:
        self.channels = dict(channels)
        self.enabled_channels = enabled_channels
        self.severity_thresholds = {
            name: AlertSeverity(value) if not isinstance(value, AlertSeverity) else value
            for name, value in (severity_thresholds or {}).items()
        }

    def dispatch(self, alert: AlertEvent) -> AlertDispatchResult:
        results: list[DispatchDecision] = []
        for channel_name in self.enabled_channels:
            channel = self.channels.get(channel_name)
            if channel is None:
                results.append(DispatchDecision(channel=channel_name, delivered=False, skipped=True, error="channel not configured"))
                continue

            threshold = self.severity_thresholds.get(channel_name)
            if threshold is not None and _severity_rank(alert.severity) < _severity_rank(threshold):
                results.append(DispatchDecision(channel=channel_name, delivered=False, skipped=True, summary="below severity threshold"))
                continue

            try:
                results.append(channel.send(alert))
            except Exception as exc:
                results.append(DispatchDecision(channel=channel_name, delivered=False, error=str(exc)))

        return AlertDispatchResult(
            alert=alert,
            alert_id=alert.alert_id,
            run_id=alert.run_id,
            severity=alert.severity,
            results=tuple(results),
        )


def _severity_rank(severity: AlertSeverity) -> int:
    if severity == AlertSeverity.info:
        return 0
    if severity == AlertSeverity.warning:
        return 1
    return 2
