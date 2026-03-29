from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, NonNegativeInt, StringConstraints

NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class ExecutionSelectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    issue_ids: tuple[NonEmptyStr, ...] = Field(default_factory=tuple)


class ExecutionSelectionItemResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    issue_id: NonEmptyStr
    accepted: bool
    run_id: NonEmptyStr | None = None
    attempt_id: NonEmptyStr | None = None
    summary: NonEmptyStr | None = None


class ExecutionSelectionSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    requested: NonNegativeInt
    completed: NonNegativeInt
    stopped_early: bool
    last_issue_id: NonEmptyStr | None = None
    last_run_id: NonEmptyStr | None = None


class ExecutionSelectionResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    items: tuple[ExecutionSelectionItemResult, ...] = Field(default_factory=tuple)
    summary: ExecutionSelectionSummary
