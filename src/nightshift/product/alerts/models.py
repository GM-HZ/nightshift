from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from nightshift.domain.enums import AlertSeverity

NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class AlertTriggerSource(StrEnum):
    daemon_aborted = "daemon_aborted"
    daemon_stop_requested = "daemon_stop_requested"
    daemon_drained = "daemon_drained"
    delivery_failed = "delivery_failed"
    recovery_failed = "recovery_failed"
    state_store_corruption = "state_store_corruption"
    total_overnight_timeout = "total_overnight_timeout"
    repeated_engine_crash = "repeated_engine_crash"


class AlertTrigger(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: NonEmptyStr
    source: AlertTriggerSource
    issue_id: NonEmptyStr | None = None
    summary: NonEmptyStr | None = None
    details: NonEmptyStr | dict[str, Any] | None = None


class DispatchDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    channel: NonEmptyStr
    delivered: bool = False
    skipped: bool = False
    error: NonEmptyStr | None = None
    summary: NonEmptyStr | None = None


class AlertDispatchResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    alert: Any
    alert_id: NonEmptyStr
    run_id: NonEmptyStr
    severity: AlertSeverity
    results: tuple[DispatchDecision, ...] = Field(default_factory=tuple)
