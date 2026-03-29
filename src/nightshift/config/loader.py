from __future__ import annotations

from pathlib import Path
import os

import yaml

from .models import (
    ContractStorageMode,
    GitHubAuthConfig,
    LayoutMode,
    MigrationMarkerConfig,
    NightShiftConfig,
    ResolvedConfigSource,
    ResolvedContractStorage,
    ResolvedRuntimeStorage,
    RuntimeStorageMode,
    UserConfig,
)

_COMPATIBILITY_CONFIG_PATH = Path("nightshift.yaml")
_MIGRATION_MARKER_PATH = Path(".nightshift/config/migration.yaml")
_LAYERED_PROJECT_CONFIG_PATH = Path(".nightshift/config/project.yaml")
_USER_CONFIG_PATH = Path("config/user.yaml")
_GITHUB_AUTH_PATH = Path("auth/github.yaml")


def load_config(path: Path) -> NightShiftConfig:
    data = yaml.safe_load(path.read_text())
    if data is None:
        data = {}
    elif not isinstance(data, dict):
        raise ValueError("nightshift config root must be a mapping")

    return NightShiftConfig.model_validate(data)


def resolve_user_space_root() -> Path:
    configured = os.environ.get("NIGHTSHIFT_HOME", "").strip()
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".nightshift"


def load_user_config() -> UserConfig | None:
    path = resolve_user_space_root() / _USER_CONFIG_PATH
    if not path.exists():
        return None
    data = yaml.safe_load(path.read_text())
    if data is None:
        data = {}
    elif not isinstance(data, dict):
        raise ValueError("user config root must be a mapping")
    return UserConfig.model_validate(data)


def load_github_auth_config() -> GitHubAuthConfig | None:
    path = resolve_user_space_root() / _GITHUB_AUTH_PATH
    if not path.exists():
        return None
    data = yaml.safe_load(path.read_text())
    if data is None:
        data = {}
    elif not isinstance(data, dict):
        raise ValueError("github auth config root must be a mapping")
    return GitHubAuthConfig.model_validate(data)


def resolve_project_config_source(repo_root: Path) -> ResolvedConfigSource:
    marker_path = repo_root / _MIGRATION_MARKER_PATH
    if not marker_path.exists():
        return ResolvedConfigSource(
            mode=LayoutMode.COMPATIBILITY,
            path=repo_root / _COMPATIBILITY_CONFIG_PATH,
            migration_marker_path=marker_path,
        )

    marker = _load_migration_marker(marker_path)
    _validate_migration_marker(marker)
    if marker.project_config_source == "layered":
        return ResolvedConfigSource(
            mode=LayoutMode.LAYERED_PROJECT_CONFIG,
            path=repo_root / _LAYERED_PROJECT_CONFIG_PATH,
            migration_marker_path=marker_path,
        )
    if marker.project_config_source == "compatibility":
        return ResolvedConfigSource(
            mode=LayoutMode.COMPATIBILITY,
            path=repo_root / _COMPATIBILITY_CONFIG_PATH,
            migration_marker_path=marker_path,
        )

    raise ValueError(
        "migration marker must set project_config_source to 'compatibility' or 'layered'"
    )


def resolve_contract_storage(repo_root: Path) -> ResolvedContractStorage:
    marker_path = repo_root / _MIGRATION_MARKER_PATH
    if not marker_path.exists():
        return ResolvedContractStorage(
            mode=ContractStorageMode.COMPATIBILITY,
            current_path=repo_root / "nightshift/issues",
            history_path=repo_root / "nightshift/contracts",
            migration_marker_path=marker_path,
        )

    marker = _load_migration_marker(marker_path)
    _validate_migration_marker(marker)
    if marker.contract_storage_source == "layered":
        return ResolvedContractStorage(
            mode=ContractStorageMode.LAYERED,
            current_path=repo_root / ".nightshift/contracts/current",
            history_path=repo_root / ".nightshift/contracts/history",
            migration_marker_path=marker_path,
        )

    return ResolvedContractStorage(
        mode=ContractStorageMode.COMPATIBILITY,
        current_path=repo_root / "nightshift/issues",
        history_path=repo_root / "nightshift/contracts",
        migration_marker_path=marker_path,
    )


def resolve_runtime_storage(repo_root: Path) -> ResolvedRuntimeStorage:
    marker_path = repo_root / _MIGRATION_MARKER_PATH
    if not marker_path.exists():
        return ResolvedRuntimeStorage(
            mode=RuntimeStorageMode.COMPATIBILITY,
            records_root=repo_root / "nightshift-data" / "issue-records",
            active_run_path=repo_root / "nightshift-data" / "active-run.json",
            runs_root=repo_root / "nightshift-data" / "runs",
            alerts_path=repo_root / "nightshift-data" / "alerts.ndjson",
            artifacts_root=repo_root / "nightshift-data" / "runs",
            reports_root=repo_root / "nightshift-data" / "reports",
            migration_marker_path=marker_path,
        )

    marker = _load_migration_marker(marker_path)
    _validate_migration_marker(marker)
    if marker.runtime_layout_source == "layered":
        return ResolvedRuntimeStorage(
            mode=RuntimeStorageMode.LAYERED,
            records_root=repo_root / ".nightshift" / "records" / "current",
            active_run_path=repo_root / ".nightshift" / "records" / "active-run.json",
            runs_root=repo_root / ".nightshift" / "runs",
            alerts_path=repo_root / ".nightshift" / "records" / "alerts.ndjson",
            artifacts_root=repo_root / ".nightshift" / "artifacts",
            reports_root=repo_root / ".nightshift" / "reports",
            migration_marker_path=marker_path,
        )

    return ResolvedRuntimeStorage(
        mode=RuntimeStorageMode.COMPATIBILITY,
        records_root=repo_root / "nightshift-data" / "issue-records",
        active_run_path=repo_root / "nightshift-data" / "active-run.json",
        runs_root=repo_root / "nightshift-data" / "runs",
        alerts_path=repo_root / "nightshift-data" / "alerts.ndjson",
        artifacts_root=repo_root / "nightshift-data" / "runs",
        reports_root=repo_root / "nightshift-data" / "reports",
        migration_marker_path=marker_path,
    )


def load_project_config(repo_root: Path) -> NightShiftConfig:
    resolved_source = resolve_project_config_source(repo_root)
    if resolved_source.mode == LayoutMode.LAYERED_PROJECT_CONFIG and not resolved_source.path.exists():
        raise FileNotFoundError(f"layered project config not found: {resolved_source.path}")
    return load_config(resolved_source.path)


def _load_migration_marker(path: Path) -> MigrationMarkerConfig:
    data = yaml.safe_load(path.read_text())
    if data is None:
        data = {}
    elif not isinstance(data, dict):
        raise ValueError("migration marker root must be a mapping")
    return MigrationMarkerConfig.model_validate(data)


def _validate_migration_marker(marker: MigrationMarkerConfig) -> None:
    if marker.layout_version != 1:
        raise ValueError(f"unsupported migration layout_version: {marker.layout_version}")
    if marker.runtime_layout_source == "layered" and marker.project_config_source != "layered":
        raise ValueError("runtime_layout_source=layered requires project_config_source=layered")
    if marker.contract_storage_source == "layered" and marker.project_config_source != "layered":
        raise ValueError("contract_storage_source=layered requires project_config_source=layered")
