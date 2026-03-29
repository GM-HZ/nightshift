from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Annotated, Literal

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


class LayoutMode(str, Enum):
    COMPATIBILITY = "compatibility"
    LAYERED_PROJECT_CONFIG = "layered_project_config"


class ContractStorageMode(str, Enum):
    COMPATIBILITY = "compatibility"
    LAYERED = "layered"


class MigrationMarkerConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    layout_version: PositiveInt = 1
    project_config_source: Literal["compatibility", "layered"]
    runtime_layout_source: Literal["compatibility", "layered"] | None = None
    contract_storage_source: Literal["compatibility", "layered"] | None = None


@dataclass(frozen=True, slots=True)
class ResolvedConfigSource:
    mode: LayoutMode
    path: Path
    migration_marker_path: Path | None = None


@dataclass(frozen=True, slots=True)
class ResolvedContractStorage:
    mode: ContractStorageMode
    current_path: Path
    history_path: Path
    migration_marker_path: Path | None = None


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
