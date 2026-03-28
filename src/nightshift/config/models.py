from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, NonNegativeInt, PositiveInt


class ProjectConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    repo_path: str
    main_branch: str


class RunnerConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    default_engine: str
    fallback_engine: str | None = None
    issue_timeout_seconds: PositiveInt
    overnight_timeout_seconds: PositiveInt


class ValidationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    static_validation_commands: list[str] = Field(default_factory=list)
    core_regression_commands: list[str] = Field(default_factory=list)
    promotion_commands: list[str] = Field(default_factory=list)


class TestEditPolicyConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    can_add_tests: bool
    can_modify_existing_tests: bool
    can_weaken_assertions: bool
    requires_test_change_reason: bool


TestEditPolicyConfig.__test__ = False


class AttemptLimitsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_files_changed: NonNegativeInt | None = None
    max_lines_added: NonNegativeInt | None = None
    max_lines_deleted: NonNegativeInt | None = None


class TimeoutsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    command_seconds: PositiveInt | None = None
    issue_budget_seconds: PositiveInt | None = None


class IssueDefaultsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    default_priority: str
    default_forbidden_paths: list[str]
    default_test_edit_policy: TestEditPolicyConfig
    default_attempt_limits: AttemptLimitsConfig
    default_timeouts: TimeoutsConfig


class RetryConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_retries: NonNegativeInt
    retry_policy: str
    failure_circuit_breaker: bool


class WorkspaceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    worktree_root: str
    artifact_root: str
    cleanup_whitelist: list[str] = Field(default_factory=list)


class SeverityThresholdsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    info: str
    warning: str
    critical: str


class AlertsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled_channels: list[str] = Field(default_factory=list)
    severity_thresholds: SeverityThresholdsConfig


class ReportConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    output_directory: str
    summary_verbosity: str


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
