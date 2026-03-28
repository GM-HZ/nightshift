from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ProjectConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str


class RunnerConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    engine_policy: str


class ValidationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True


class TestEditPolicyConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    can_add_tests: bool
    can_modify_existing_tests: bool
    can_weaken_assertions: bool
    requires_test_change_reason: bool


TestEditPolicyConfig.__test__ = False


class AttemptLimitsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_files_changed: int | None = None
    max_lines_added: int | None = None
    max_lines_deleted: int | None = None


class TimeoutsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    command_seconds: int | None = None
    issue_budget_seconds: int | None = None


class IssueDefaultsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    default_priority: str
    default_forbidden_paths: list[str] = Field(default_factory=list)
    default_test_edit_policy: TestEditPolicyConfig
    default_attempt_limits: AttemptLimitsConfig
    default_timeouts: TimeoutsConfig


class RetryConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True


class WorkspaceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    root: str


class AlertsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True


class ReportConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    format: str


class NightShiftConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project: ProjectConfig
    runner: RunnerConfig
    validation: ValidationConfig
    issue_defaults: IssueDefaultsConfig
    retry: RetryConfig
    workspace: WorkspaceConfig
    alerts: AlertsConfig
    report: ReportConfig
