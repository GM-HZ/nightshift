from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class ProposalReviewStatus(StrEnum):
    pending_review = "pending_review"
    approved = "approved"
    rejected = "rejected"
    published = "published"


class SplitterProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposal_id: NonEmptyStr
    title: NonEmptyStr
    summary: NonEmptyStr
    suggested_kind: NonEmptyStr
    allowed_paths: tuple[NonEmptyStr, ...] = Field(default_factory=tuple)
    acceptance_criteria: tuple[NonEmptyStr, ...] = Field(default_factory=tuple)
    verification_commands: tuple[NonEmptyStr, ...] = Field(default_factory=tuple)
    review_notes: tuple[NonEmptyStr, ...] = Field(default_factory=tuple)
    missing_context: tuple[NonEmptyStr, ...] = Field(default_factory=tuple)
    review_status: ProposalReviewStatus = ProposalReviewStatus.pending_review


class ProposalBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    batch_id: NonEmptyStr
    source_requirement_path: NonEmptyStr
    proposals: tuple[SplitterProposal, ...]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PublishedIssueRef(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    repo_full_name: NonEmptyStr
    issue_number: int
    html_url: NonEmptyStr | None = None
