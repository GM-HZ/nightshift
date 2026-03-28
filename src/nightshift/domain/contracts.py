from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ValidationContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    commands: list[str] = Field(default_factory=list)
    timeout_seconds: int | None = None


class VerificationContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    issue_validation: ValidationContract | None = None
    static_validation: ValidationContract | None = None
    regression_validation: ValidationContract | None = None
    promotion_validation: ValidationContract | None = None


class AttemptLimitsContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_attempts: int | None = None
    max_retries: int | None = None
    max_parallel_attempts: int | None = None


class TimeoutsContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preflight_seconds: int | None = None
    execution_seconds: int | None = None
    validation_seconds: int | None = None
    promotion_seconds: int | None = None


class IssueContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    issue_id: str
    title: str
    kind: str
    goal: str
    allowed_paths: list[str]
    forbidden_paths: list[str]
    verification: VerificationContract
    test_edit_policy: str
    attempt_limits: AttemptLimitsContract
    timeouts: TimeoutsContract
    description: str | None = None
    acceptance: list[str] = Field(default_factory=list)
    notes: str | None = None
    risk: str | None = None
    priority: str
    engine_preferences: list[str] = Field(default_factory=list)
