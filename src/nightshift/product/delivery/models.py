from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints, model_validator

NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class DeliveryBatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    issue_ids: tuple[NonEmptyStr, ...]

    @model_validator(mode="after")
    def validate_issue_ids(self) -> "DeliveryBatchRequest":
        if not self.issue_ids:
            raise ValueError("at least one issue id is required")
        return self


class DeliveryWriteResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    issue_id: NonEmptyStr
    delivery_state: NonEmptyStr
    delivery_id: NonEmptyStr | None = None
    delivery_ref: NonEmptyStr | None = None
