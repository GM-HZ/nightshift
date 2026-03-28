from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator

from .enums import IssueKind


class EnginePreferencesContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    primary: str | None = None
    fallback: str | None = None


class PassConditionContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    type: Literal["exit_code", "all_exit_codes_zero"]
    expected: StrictInt | None = None

    @model_validator(mode="after")
    def validate_expected(self) -> "PassConditionContract":
        if self.type == "exit_code" and self.expected is None:
            raise ValueError("exit_code pass conditions require an integer expected value")

        if self.type == "all_exit_codes_zero" and self.expected is not None:
            raise ValueError("all_exit_codes_zero pass conditions require expected to be omitted")

        return self


class VerificationStageContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    required: bool
    commands: tuple[str, ...] = Field(default_factory=tuple)
    pass_condition: PassConditionContract | None = None

    @model_validator(mode="after")
    def validate_stage_shape(self) -> "VerificationStageContract":
        if self.commands and self.pass_condition is None:
            raise ValueError("verification stages with commands require a pass_condition")

        if not self.commands and self.pass_condition is not None:
            raise ValueError("verification stages without commands must not declare a pass_condition")

        return self


class VerificationContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    issue_validation: VerificationStageContract | None = None
    static_validation: VerificationStageContract | None = None
    regression_validation: VerificationStageContract | None = None
    promotion_validation: VerificationStageContract | None = None


class TestEditPolicyContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    can_add_tests: bool
    can_modify_existing_tests: bool
    can_weaken_assertions: bool
    requires_test_change_reason: bool


TestEditPolicyContract.__test__ = False


class AttemptLimitsContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    max_files_changed: int | None = None
    max_lines_added: int | None = None
    max_lines_deleted: int | None = None


class TimeoutsContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    command_seconds: int | None = None
    issue_budget_seconds: int | None = None


class IssueContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    issue_id: str
    title: str
    kind: IssueKind
    goal: str
    allowed_paths: tuple[str, ...]
    forbidden_paths: tuple[str, ...]
    verification: VerificationContract
    test_edit_policy: TestEditPolicyContract
    attempt_limits: AttemptLimitsContract
    timeouts: TimeoutsContract
    priority: str
    engine_preferences: EnginePreferencesContract = Field(default_factory=EnginePreferencesContract)
    description: str | None = None
    acceptance: tuple[str, ...] = Field(default_factory=tuple)
    notes: str | None = None
    risk: str | None = None

    @model_validator(mode="after")
    def validate_execution_requirements(self) -> "IssueContract":
        if self.kind == IssueKind.execution:
            if not self.allowed_paths:
                raise ValueError("execution contracts require allowed_paths")

            if not self._has_executable_validation():
                raise ValueError("execution contracts require executable validation")

        return self

    def _has_executable_validation(self) -> bool:
        stages = (
            self.verification.issue_validation,
            self.verification.static_validation,
            self.verification.regression_validation,
            self.verification.promotion_validation,
        )
        return any(
            stage is not None and len(stage.commands) > 0 and stage.pass_condition is not None
            for stage in stages
        )
