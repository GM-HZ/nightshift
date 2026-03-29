from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, NonNegativeInt, StringConstraints

NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class ExecutionSelectionBatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    issue_ids: tuple[NonEmptyStr, ...] = Field(default_factory=tuple)
    run_all: bool = False


class ExecutionSelectionOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    issue_id: NonEmptyStr
    run_id: NonEmptyStr
    accepted: bool
    attempt_id: NonEmptyStr


class ExecutionSelectionBatchSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    requested: NonNegativeInt
    completed: NonNegativeInt
    stopped_early: bool
    last_issue_id: NonEmptyStr | None = None
    last_run_id: NonEmptyStr | None = None
    failed_issue_id: NonEmptyStr | None = None


class ExecutionSelectionBatchResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    outcomes: tuple[ExecutionSelectionOutcome, ...] = Field(default_factory=tuple)
    summary: ExecutionSelectionBatchSummary
