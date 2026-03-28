from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, NonNegativeInt, PositiveInt, StringConstraints

NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class ProjectConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    repo_path: NonEmptyStr
    main_branch: NonEmptyStr


class RunnerConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    default_engine: NonEmptyStr
    fallback_engine: NonEmptyStr | None = None
    issue_timeout_seconds: PositiveInt
    overnight_timeout_seconds: PositiveInt


class ValidationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    static_validation_commands: list[NonEmptyStr] = Field(default_factory=list)
    core_regression_commands: list[NonEmptyStr] = Field(default_factory=list)
    promotion_commands: list[NonEmptyStr] = Field(default_factory=list)


class TestEditPolicyConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    can_add_tests: bool
    can_modify_existing_tests: bool
    can_weaken_assertions: bool
    requires_test_change_reason: bool


TestEditPolicyConfig.__test__ = False


class AttemptLimitsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_files_changed: NonNegativeInt
    max_lines_added: NonNegativeInt
    max_lines_deleted: NonNegativeInt


class TimeoutsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    command_seconds: PositiveInt
    issue_budget_seconds: PositiveInt


class IssueDefaultsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    default_priority: NonEmptyStr
    default_forbidden_paths: list[NonEmptyStr]
    default_test_edit_policy: TestEditPolicyConfig
    default_attempt_limits: AttemptLimitsConfig
    default_timeouts: TimeoutsConfig


class RetryConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_retries: NonNegativeInt
    retry_policy: NonEmptyStr
    failure_circuit_breaker: bool


class WorkspaceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    worktree_root: NonEmptyStr
    artifact_root: NonEmptyStr
    cleanup_whitelist: list[NonEmptyStr] = Field(default_factory=list)


class SeverityThresholdsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    info: NonEmptyStr
    warning: NonEmptyStr
    critical: NonEmptyStr


class AlertsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled_channels: list[NonEmptyStr] = Field(default_factory=list)
    severity_thresholds: SeverityThresholdsConfig


class ReportConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    output_directory: NonEmptyStr
    summary_verbosity: NonEmptyStr


class IssueIngestionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    allowed_authors: list[NonEmptyStr] = Field(default_factory=list)
    required_label: NonEmptyStr = "nightshift"


class DeliveryConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    repo_full_name: NonEmptyStr | None = None
    remote_name: NonEmptyStr = "origin"
    base_branch: NonEmptyStr = "master"


class ProductConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    issue_ingestion: IssueIngestionConfig = Field(default_factory=IssueIngestionConfig)
    delivery: DeliveryConfig = Field(default_factory=DeliveryConfig)


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
    product: ProductConfig = Field(default_factory=ProductConfig)
