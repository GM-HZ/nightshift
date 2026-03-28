from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
DeliveryStateValue = Literal["none", "submitted", "failed"]


class DeliveryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    issue_ids: tuple[NonEmptyStr, ...]

    @model_validator(mode="after")
    def _validate_issue_ids(self) -> "DeliveryRequest":
        if not self.issue_ids:
            raise ValueError("delivery request requires at least one issue id")
        return self


class DeliveryResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    issue_id: NonEmptyStr
    delivery_state: DeliveryStateValue
    delivery_ref: NonEmptyStr | None = None
    delivery_id: str | None = None
    reason: str | None = None


class DeliveryBatchResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    results: tuple[DeliveryResult, ...] = Field(default_factory=tuple)

    @property
    def delivered_issue_ids(self) -> tuple[str, ...]:
        return tuple(result.issue_id for result in self.results if result.delivery_state == "submitted")

    @property
    def failed_issue_ids(self) -> tuple[str, ...]:
        return tuple(result.issue_id for result in self.results if result.delivery_state == "failed")
