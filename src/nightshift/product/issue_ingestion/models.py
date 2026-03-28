from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, NonNegativeInt, StringConstraints

NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class GitHubIssue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    repo_full_name: NonEmptyStr
    issue_number: NonNegativeInt
    title: NonEmptyStr
    body: str | None = None
    author_login: NonEmptyStr
    labels: tuple[NonEmptyStr, ...] = Field(default_factory=tuple)


class ParsedIssueTemplate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    repo_full_name: NonEmptyStr
    issue_number: NonNegativeInt
    title: NonEmptyStr
    author_login: NonEmptyStr
    labels: tuple[NonEmptyStr, ...]
    nightshift_issue: bool
    nightshift_version: NonEmptyStr | None = None
    background: str | None = None
    goal: str | None = None
    allowed_paths: tuple[NonEmptyStr, ...] = Field(default_factory=tuple)
    non_goals: tuple[NonEmptyStr, ...] = Field(default_factory=tuple)
    acceptance_criteria: tuple[NonEmptyStr, ...] = Field(default_factory=tuple)
    verification_commands: tuple[NonEmptyStr, ...] = Field(default_factory=tuple)
    notes: str | None = None


class ProvenanceCheckResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    accepted: bool
    reasons: tuple[NonEmptyStr, ...] = Field(default_factory=tuple)


class AdmittedIssueDraft(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    issue_id: NonEmptyStr
    repo_full_name: NonEmptyStr
    source_issue_number: NonNegativeInt
    title: NonEmptyStr
    description: str | None = None
    goal: NonEmptyStr
    allowed_paths: tuple[NonEmptyStr, ...]
    forbidden_paths: tuple[NonEmptyStr, ...]
    acceptance_criteria: tuple[NonEmptyStr, ...]
    verification_commands: tuple[NonEmptyStr, ...]
    priority: NonEmptyStr
    notes: str | None = None


class AdmissionCheckResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    accepted: bool
    reasons: tuple[NonEmptyStr, ...] = Field(default_factory=tuple)
    draft: AdmittedIssueDraft | None = None
