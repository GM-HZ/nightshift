from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, NonNegativeInt, StringConstraints

from .loop_metadata import DaemonLoopMetadata
from nightshift.domain import RunLifecycleState

NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class OvernightControlLoopRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    daemon_run_id: NonEmptyStr | None = None
    run_all: bool = True
    fail_fast: bool = True


class OvernightControlLoopSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    requested: NonNegativeInt
    completed: NonNegativeInt
    stopped_early: bool
    stopped_reason: Literal["drained", "failure", "user_stop", "none"]
    last_issue_id: NonEmptyStr | None = None
    last_run_id: NonEmptyStr | None = None
    failed_issue_id: NonEmptyStr | None = None


class OvernightControlLoopResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    daemon_run_id: NonEmptyStr
    run_state: RunLifecycleState
    started_at: datetime
    ended_at: datetime
    outcomes: tuple[dict[str, object], ...] = Field(default_factory=tuple)
    summary: OvernightControlLoopSummary
    metadata: DaemonLoopMetadata
