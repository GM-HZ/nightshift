from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class EnginePreferencesContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    primary: list[str] = Field(default_factory=list)
    fallback: list[str] = Field(default_factory=list)


class VerificationStageContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    required: bool
    commands: list[str] = Field(default_factory=list)
    pass_condition: str


class VerificationContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    issue_validation: VerificationStageContract | None = None
    static_validation: VerificationStageContract | None = None
    regression_validation: VerificationStageContract | None = None
    promotion_validation: VerificationStageContract | None = None


class TestEditPolicyContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    can_add_tests: bool
    can_modify_existing_tests: bool
    can_weaken_assertions: bool
    requires_test_change_reason: bool


TestEditPolicyContract.__test__ = False


class AttemptLimitsContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_files_changed: int | None = None
    max_lines_added: int | None = None
    max_lines_deleted: int | None = None


class TimeoutsContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    command_seconds: int | None = None
    issue_budget_seconds: int | None = None


class IssueContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    issue_id: str
    title: str
    kind: str
    goal: str
    allowed_paths: list[str]
    forbidden_paths: list[str]
    verification: VerificationContract
    test_edit_policy: TestEditPolicyContract
    attempt_limits: AttemptLimitsContract
    timeouts: TimeoutsContract
    priority: str
    engine_preferences: EnginePreferencesContract = Field(default_factory=EnginePreferencesContract)
    description: str | None = None
    acceptance: list[str] = Field(default_factory=list)
    notes: str | None = None
    risk: str | None = None
