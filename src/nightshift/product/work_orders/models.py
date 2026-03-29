from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, NonNegativeInt, PositiveInt, StringConstraints, model_validator

NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class WorkOrderSourceIssue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    repo: NonEmptyStr
    number: PositiveInt
    url: NonEmptyStr | None = None


class WorkOrderVerification(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    issue_validation: tuple[NonEmptyStr, ...] = Field(default_factory=tuple)
    regression_validation: tuple[NonEmptyStr, ...] = Field(default_factory=tuple)
    promotion_validation: tuple[NonEmptyStr, ...] = Field(default_factory=tuple)

    def has_commands(self) -> bool:
        return any((self.issue_validation, self.regression_validation, self.promotion_validation))


class WorkOrderTestEditPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    can_add_tests: bool
    can_modify_existing_tests: bool
    can_weaken_assertions: bool
    requires_test_change_reason: bool


class WorkOrderAttemptLimits(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    max_files_changed: NonNegativeInt
    max_lines_added: NonNegativeInt
    max_lines_deleted: NonNegativeInt


class WorkOrderTimeouts(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    command_seconds: PositiveInt
    issue_budget_seconds: PositiveInt


class WorkOrderEngineHints(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    primary: NonEmptyStr | None = None
    fallback: NonEmptyStr | None = None


class WorkOrderRationale(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    summary: NonEmptyStr
    risks: tuple[NonEmptyStr, ...] = Field(default_factory=tuple)
    notes: tuple[NonEmptyStr, ...] = Field(default_factory=tuple)


class WorkOrderExecution(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    title: NonEmptyStr
    goal: NonEmptyStr
    allowed_paths: tuple[NonEmptyStr, ...]
    non_goals: tuple[NonEmptyStr, ...]
    acceptance_criteria: tuple[NonEmptyStr, ...]
    context_files: tuple[NonEmptyStr, ...]
    issue_id: NonEmptyStr | None = None
    verification: WorkOrderVerification | None = None
    verification_commands: tuple[NonEmptyStr, ...] | None = None
    priority: NonEmptyStr | None = None
    forbidden_paths: tuple[NonEmptyStr, ...] | None = None
    test_edit_policy: WorkOrderTestEditPolicy | None = None
    attempt_limits: WorkOrderAttemptLimits | None = None
    timeouts: WorkOrderTimeouts | None = None
    constraints: tuple[NonEmptyStr, ...] | None = None
    engine_hints: WorkOrderEngineHints | None = None

    @model_validator(mode="after")
    def validate_required_execution_shape(self) -> "WorkOrderExecution":
        if not self.allowed_paths:
            raise ValueError("execution.allowed_paths must not be empty")

        if not self.non_goals:
            raise ValueError("execution.non_goals must not be empty")

        if not self.acceptance_criteria:
            raise ValueError("execution.acceptance_criteria must not be empty")

        if not self.context_files:
            raise ValueError("execution.context_files must not be empty")

        if not self.has_verification_input():
            raise ValueError("execution requires verification or verification_commands")

        return self

    def has_verification_input(self) -> bool:
        if self.verification_commands:
            return True

        return self.verification is not None and self.verification.has_commands()


class WorkOrderFrontmatter(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    work_order_id: NonEmptyStr
    status: NonEmptyStr
    source_issue: WorkOrderSourceIssue
    execution: WorkOrderExecution
    rationale: WorkOrderRationale
