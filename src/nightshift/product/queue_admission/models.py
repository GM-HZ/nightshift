from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, NonNegativeInt, StringConstraints

NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class QueueAdmissionStatus(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    issue_id: NonEmptyStr
    status: Literal["admitted", "already_admitted"]
    queue_priority: NonEmptyStr


class QueueAdmissionSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    requested: NonNegativeInt
    admitted: NonNegativeInt
    already_admitted: NonNegativeInt


class QueueAdmissionResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    statuses: tuple[QueueAdmissionStatus, ...] = Field(default_factory=tuple)
    summary: QueueAdmissionSummary
