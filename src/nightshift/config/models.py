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


class AttemptLimitsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_attempts: int | None = None
    max_retries: int | None = None
    max_parallel_attempts: int | None = None


class TimeoutsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preflight_seconds: int | None = None
    execution_seconds: int | None = None
    validation_seconds: int | None = None
    promotion_seconds: int | None = None


class IssueDefaultsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    priority: str
    forbidden_paths: list[str] = Field(default_factory=list)
    test_edit_policy: str
    attempt_limits: AttemptLimitsConfig
    timeouts: TimeoutsConfig


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
