from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, NonNegativeInt, StringConstraints

NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class SelectionError(ValueError):
    """Raised when a batch selection request cannot be resolved safely."""


class SelectionItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    issue_id: NonEmptyStr
    queue_priority: NonEmptyStr


class SelectionResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    items: tuple[SelectionItem, ...] = Field(default_factory=tuple)

    @property
    def issue_ids(self) -> tuple[str, ...]:
        return tuple(item.issue_id for item in self.items)


class BatchRunSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    batch_size: NonNegativeInt
    issues_attempted: NonNegativeInt
    issues_accepted: NonNegativeInt
    stopped_early: bool
    first_failure_issue_id: NonEmptyStr | None = None
