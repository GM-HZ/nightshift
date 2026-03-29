from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class ExecutionSelectionBatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    issue_ids: tuple[NonEmptyStr, ...] = Field(default_factory=tuple)
    run_all: bool = False

    @model_validator(mode="after")
    def validate_selection(self) -> "ExecutionSelectionBatchRequest":
        if not self.run_all and not self.issue_ids:
            raise ValueError("batch selection requires issue_ids or run_all")

        if self.run_all and self.issue_ids:
            raise ValueError("run_all cannot be combined with explicit issue_ids")

        return self


class ExecutionSelectionOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    issue_id: NonEmptyStr
    run_id: NonEmptyStr
    accepted: bool
    attempt_id: NonEmptyStr | None = None


class ExecutionSelectionBatchSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    requested: int
    completed: int
    stopped_early: bool
    last_issue_id: NonEmptyStr | None = None
    last_run_id: NonEmptyStr | None = None
    failed_issue_id: NonEmptyStr | None = None


class ExecutionSelectionBatchResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    outcomes: tuple[ExecutionSelectionOutcome, ...] = Field(default_factory=tuple)
    summary: ExecutionSelectionBatchSummary
