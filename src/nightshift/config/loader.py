from __future__ import annotations

from pathlib import Path

import yaml

from .models import LayoutMode, MigrationMarkerConfig, NightShiftConfig, ResolvedConfigSource

_COMPATIBILITY_CONFIG_PATH = Path("nightshift.yaml")
_MIGRATION_MARKER_PATH = Path(".nightshift/config/migration.yaml")
_LAYERED_PROJECT_CONFIG_PATH = Path(".nightshift/config/project.yaml")


def load_config(path: Path) -> NightShiftConfig:
    data = yaml.safe_load(path.read_text())
    if data is None:
        data = {}
    elif not isinstance(data, dict):
        raise ValueError("nightshift config root must be a mapping")

    return NightShiftConfig.model_validate(data)


def resolve_project_config_source(repo_root: Path) -> ResolvedConfigSource:
    marker_path = repo_root / _MIGRATION_MARKER_PATH
    if not marker_path.exists():
        return ResolvedConfigSource(
            mode=LayoutMode.COMPATIBILITY,
            path=repo_root / _COMPATIBILITY_CONFIG_PATH,
            migration_marker_path=marker_path,
        )

    marker = _load_migration_marker(marker_path)
    if marker.layout_version != 1:
        raise ValueError(f"unsupported migration layout_version: {marker.layout_version}")
    if marker.runtime_layout_source not in (None, "compatibility"):
        raise ValueError(
            "runtime_layout_source=layered is not supported during Phase 1 layered project config migration"
        )
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
