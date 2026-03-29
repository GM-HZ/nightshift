from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, PositiveInt, StringConstraints

NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class IssueIngestionBridgeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    repo_full_name: NonEmptyStr
    issue_number: PositiveInt
    local_repo_path: NonEmptyStr
    update_existing: bool = False


class GitHubIssuePayload(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    repo_full_name: NonEmptyStr
    issue_number: PositiveInt
    title: NonEmptyStr
    body: NonEmptyStr | None = None
    labels: tuple[NonEmptyStr, ...] = Field(default_factory=tuple)
    author_login: NonEmptyStr
    html_url: NonEmptyStr | None = None


class GitHubIssueBridgeSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    repo_full_name: NonEmptyStr
    issue_number: PositiveInt
    work_order_id: NonEmptyStr
    updated_existing: bool


class GitHubIssueBridgeResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    payload: GitHubIssuePayload
    summary: GitHubIssueBridgeSummary
