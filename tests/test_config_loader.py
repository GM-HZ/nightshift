from pathlib import Path

import pytest
from pydantic import ValidationError

from nightshift.config.loader import (
    load_config,
    load_github_auth_config,
    load_user_config,
    load_project_config,
    resolve_user_space_root,
    resolve_contract_storage,
    resolve_project_config_source,
    resolve_runtime_storage,
)
from nightshift.config.models import ContractStorageMode, LayoutMode, RuntimeStorageMode


def _write_complete_config(path: Path, *, repo_path: str, default_engine: str) -> None:
    path.write_text(
        f"""
project:
  repo_path: {repo_path}
  main_branch: main
runner:
  default_engine: {default_engine}
  fallback_engine: gpt-4.1
  issue_timeout_seconds: 900
  overnight_timeout_seconds: 28800
validation:
  static_validation_commands:
    - pytest
  core_regression_commands:
    - pytest -m core
  promotion_commands:
    - pytest -m promotion
issue_defaults:
  default_priority: high
  default_forbidden_paths:
    - secrets
  default_test_edit_policy:
    can_add_tests: true
    can_modify_existing_tests: true
    can_weaken_assertions: false
    requires_test_change_reason: true
  default_attempt_limits:
    max_files_changed: 3
    max_lines_added: 200
    max_lines_deleted: 50
  default_timeouts:
    command_seconds: 900
    issue_budget_seconds: 7200
retry:
  max_retries: 3
  retry_policy: exponential_backoff
  failure_circuit_breaker: true
workspace:
  worktree_root: {repo_path}/.worktrees
  artifact_root: {repo_path}/.artifacts
  cleanup_whitelist:
    - .git
alerts:
  enabled_channels:
    - console
  severity_thresholds:
    info: info
    warning: warning
    critical: critical
report:
  output_directory: {repo_path}/.reports
  summary_verbosity: concise
"""
    )


def test_load_config_reads_issue_defaults(tmp_path: Path) -> None:
    config_path = tmp_path / "nightshift.yaml"
    _write_complete_config(config_path, repo_path="/workspace/nightshift", default_engine="gpt-5")

    config = load_config(config_path)

    assert config.project.repo_path == "/workspace/nightshift"
    assert config.runner.default_engine == "gpt-5"
    assert config.validation.static_validation_commands == ["pytest"]
    assert config.issue_defaults.default_priority == "high"
    assert config.issue_defaults.default_forbidden_paths == ["secrets"]
    assert config.workspace.worktree_root == "/workspace/nightshift/.worktrees"
    assert config.alerts.enabled_channels == ["console"]
    assert config.report.summary_verbosity == "concise"


def test_load_config_requires_explicit_default_forbidden_paths(tmp_path: Path) -> None:
    config_path = tmp_path / "nightshift.yaml"
    config_path.write_text(
        """
project:
  repo_path: /workspace/nightshift
  main_branch: main
runner:
  default_engine: gpt-5
  fallback_engine: gpt-4.1
  issue_timeout_seconds: 900
  overnight_timeout_seconds: 28800
validation:
  static_validation_commands:
    - pytest
  core_regression_commands:
    - pytest -m core
  promotion_commands:
    - pytest -m promotion
issue_defaults:
  default_priority: high
  default_test_edit_policy:
    can_add_tests: true
    can_modify_existing_tests: true
    can_weaken_assertions: false
    requires_test_change_reason: true
  default_attempt_limits:
    max_files_changed: 3
    max_lines_added: 200
    max_lines_deleted: 50
  default_timeouts:
    command_seconds: 900
    issue_budget_seconds: 7200
retry:
  max_retries: 3
  retry_policy: exponential_backoff
  failure_circuit_breaker: true
workspace:
  worktree_root: /workspace/nightshift/.worktrees
  artifact_root: /workspace/nightshift/.artifacts
  cleanup_whitelist:
    - .git
alerts:
  enabled_channels:
    - console
  severity_thresholds:
    info: info
    warning: warning
    critical: critical
report:
  output_directory: /workspace/nightshift/.reports
  summary_verbosity: concise
"""
    )

    with pytest.raises(ValidationError):
        load_config(config_path)


def test_resolve_user_space_root_defaults_to_home_dot_nightshift(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NIGHTSHIFT_HOME", raising=False)
    monkeypatch.setenv("HOME", "/tmp/nightshift-home")

    resolved = resolve_user_space_root()

    assert resolved == Path("/tmp/nightshift-home/.nightshift")


def test_resolve_user_space_root_prefers_nightshift_home(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIGHTSHIFT_HOME", "/tmp/custom-nightshift")

    resolved = resolve_user_space_root()

    assert resolved == Path("/tmp/custom-nightshift")


def test_load_user_config_reads_user_defaults(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    user_root = tmp_path / ".nightshift"
    monkeypatch.setenv("NIGHTSHIFT_HOME", str(user_root))
    config_path = user_root / "config" / "user.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        """
runner:
  default_engine: codex
  fallback_engine: claude
github:
  default_repo_full_name: GM-HZ/nightshift
"""
    )

    config = load_user_config()

    assert config is not None
    assert config.runner.default_engine == "codex"
    assert config.github.default_repo_full_name == "GM-HZ/nightshift"


def test_load_github_auth_config_reads_private_auth_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    user_root = tmp_path / ".nightshift"
    monkeypatch.setenv("NIGHTSHIFT_HOME", str(user_root))
    auth_path = user_root / "auth" / "github.yaml"
    auth_path.parent.mkdir(parents=True, exist_ok=True)
    auth_path.write_text(
        """
token_env_var: NIGHTSHIFT_GITHUB_TOKEN
api_base_url: https://api.github.com
"""
    )

    auth = load_github_auth_config()

    assert auth is not None
    assert auth.token_env_var == "NIGHTSHIFT_GITHUB_TOKEN"
    assert auth.api_base_url == "https://api.github.com"


def test_resolve_project_config_source_defaults_to_compatibility_without_marker(tmp_path: Path) -> None:
    repo_root = tmp_path
    resolved = resolve_project_config_source(repo_root)

    assert resolved.mode is LayoutMode.COMPATIBILITY
    assert resolved.path == repo_root / "nightshift.yaml"
    assert resolved.migration_marker_path == repo_root / ".nightshift/config/migration.yaml"


def test_resolve_runtime_storage_defaults_to_compatibility_without_marker(tmp_path: Path) -> None:
    repo_root = tmp_path
    resolved = resolve_runtime_storage(repo_root)

    assert resolved.mode is RuntimeStorageMode.COMPATIBILITY
    assert resolved.records_root == repo_root / "nightshift-data" / "issue-records"
    assert resolved.active_run_path == repo_root / "nightshift-data" / "active-run.json"
    assert resolved.runs_root == repo_root / "nightshift-data" / "runs"
    assert resolved.alerts_path == repo_root / "nightshift-data" / "alerts.ndjson"
    assert resolved.artifacts_root == repo_root / "nightshift-data" / "runs"
    assert resolved.reports_root == repo_root / "nightshift-data" / "reports"
    assert resolved.migration_marker_path == repo_root / ".nightshift/config/migration.yaml"


def test_resolve_contract_storage_defaults_to_compatibility_without_explicit_marker(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path
    migration_marker = repo_root / ".nightshift/config/migration.yaml"
    migration_marker.parent.mkdir(parents=True, exist_ok=True)
    migration_marker.write_text(
        """
layout_version: 1
project_config_source: layered
runtime_layout_source: compatibility
"""
    )

    resolved = resolve_contract_storage(repo_root)

    assert resolved.mode is ContractStorageMode.COMPATIBILITY
    assert resolved.current_path == repo_root / "nightshift/issues"
    assert resolved.history_path == repo_root / "nightshift/contracts"
    assert resolved.migration_marker_path == migration_marker


def test_resolve_contract_storage_uses_layered_paths_when_marker_declares_layered(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path
    migration_marker = repo_root / ".nightshift/config/migration.yaml"
    migration_marker.parent.mkdir(parents=True, exist_ok=True)
    migration_marker.write_text(
        """
layout_version: 1
project_config_source: layered
runtime_layout_source: compatibility
contract_storage_source: layered
"""
    )

    resolved = resolve_contract_storage(repo_root)

    assert resolved.mode is ContractStorageMode.LAYERED
    assert resolved.current_path == repo_root / ".nightshift/contracts/current"
    assert resolved.history_path == repo_root / ".nightshift/contracts/history"
    assert resolved.migration_marker_path == migration_marker


def test_resolve_contract_storage_rejects_layered_contract_storage_without_layered_project_config(
    tmp_path: Path,
) -> None:
    migration_marker = tmp_path / ".nightshift/config/migration.yaml"
    migration_marker.parent.mkdir(parents=True, exist_ok=True)
    migration_marker.write_text(
        """
layout_version: 1
project_config_source: compatibility
runtime_layout_source: compatibility
contract_storage_source: layered
"""
    )

    with pytest.raises(ValueError, match="contract_storage_source=layered"):
        resolve_contract_storage(tmp_path)


def test_load_project_config_uses_root_config_when_marker_is_absent(tmp_path: Path) -> None:
    repo_root = tmp_path
    root_config = repo_root / "nightshift.yaml"
    layered_config = repo_root / ".nightshift/config/project.yaml"

    root_config.parent.mkdir(parents=True, exist_ok=True)
    layered_config.parent.mkdir(parents=True, exist_ok=True)
    _write_complete_config(root_config, repo_path="/workspace/root", default_engine="gpt-root")
    _write_complete_config(layered_config, repo_path="/workspace/layered", default_engine="gpt-layered")

    config = load_project_config(repo_root)

    assert config.project.repo_path == "/workspace/root"
    assert config.runner.default_engine == "gpt-root"


def test_load_project_config_uses_layered_project_yaml_when_marker_declares_layered(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path
    root_config = repo_root / "nightshift.yaml"
    layered_config = repo_root / ".nightshift/config/project.yaml"
    migration_marker = repo_root / ".nightshift/config/migration.yaml"

    root_config.parent.mkdir(parents=True, exist_ok=True)
    layered_config.parent.mkdir(parents=True, exist_ok=True)
    migration_marker.parent.mkdir(parents=True, exist_ok=True)
    _write_complete_config(root_config, repo_path="/workspace/root", default_engine="gpt-root")
    _write_complete_config(layered_config, repo_path="/workspace/layered", default_engine="gpt-layered")
    migration_marker.write_text(
        """
layout_version: 1
project_config_source: layered
runtime_layout_source: compatibility
"""
    )

    config = load_project_config(repo_root)

    assert config.project.repo_path == "/workspace/layered"
    assert config.runner.default_engine == "gpt-layered"


def test_load_project_config_fails_when_layered_project_yaml_is_missing(tmp_path: Path) -> None:
    repo_root = tmp_path
    migration_marker = repo_root / ".nightshift/config/migration.yaml"
    migration_marker.parent.mkdir(parents=True, exist_ok=True)
    migration_marker.write_text(
        """
layout_version: 1
project_config_source: layered
runtime_layout_source: compatibility
"""
    )

    with pytest.raises(FileNotFoundError, match="project.yaml"):
        load_project_config(repo_root)


def test_load_config_reads_explicit_layered_project_file_directly(tmp_path: Path) -> None:
    project_config = tmp_path / ".nightshift/config/project.yaml"
    project_config.parent.mkdir(parents=True, exist_ok=True)
    _write_complete_config(project_config, repo_path="/workspace/layered", default_engine="gpt-layered")

    config = load_config(project_config)

    assert config.project.repo_path == "/workspace/layered"
    assert config.runner.default_engine == "gpt-layered"


def test_resolve_project_config_source_rejects_unsupported_layout_version(tmp_path: Path) -> None:
    migration_marker = tmp_path / ".nightshift/config/migration.yaml"
    migration_marker.parent.mkdir(parents=True, exist_ok=True)
    migration_marker.write_text(
        """
layout_version: 2
project_config_source: layered
runtime_layout_source: compatibility
"""
    )

    with pytest.raises(ValueError, match="unsupported migration layout_version"):
        resolve_project_config_source(tmp_path)


def test_resolve_runtime_storage_uses_layered_paths_when_marker_declares_layered(tmp_path: Path) -> None:
    migration_marker = tmp_path / ".nightshift/config/migration.yaml"
    migration_marker.parent.mkdir(parents=True, exist_ok=True)
    migration_marker.write_text(
        """
layout_version: 1
project_config_source: layered
runtime_layout_source: layered
"""
    )

    resolved = resolve_runtime_storage(tmp_path)

    assert resolved.mode is RuntimeStorageMode.LAYERED
    assert resolved.records_root == tmp_path / ".nightshift" / "records" / "current"
    assert resolved.active_run_path == tmp_path / ".nightshift" / "records" / "active-run.json"
    assert resolved.runs_root == tmp_path / ".nightshift" / "runs"
    assert resolved.alerts_path == tmp_path / ".nightshift" / "records" / "alerts.ndjson"
    assert resolved.artifacts_root == tmp_path / ".nightshift" / "artifacts"
    assert resolved.reports_root == tmp_path / ".nightshift" / "reports"
    assert resolved.migration_marker_path == migration_marker


def test_resolve_runtime_storage_rejects_layered_without_layered_project_config(
    tmp_path: Path,
) -> None:
    migration_marker = tmp_path / ".nightshift/config/migration.yaml"
    migration_marker.parent.mkdir(parents=True, exist_ok=True)
    migration_marker.write_text(
        """
layout_version: 1
project_config_source: compatibility
runtime_layout_source: layered
"""
    )

    with pytest.raises(ValueError, match="runtime_layout_source=layered"):
        resolve_runtime_storage(tmp_path)


def test_load_config_requires_complete_default_attempt_limits(tmp_path: Path) -> None:
    config_path = tmp_path / "nightshift.yaml"
    config_path.write_text(
        """
project:
  repo_path: /workspace/nightshift
  main_branch: main
runner:
  default_engine: gpt-5
  fallback_engine: gpt-4.1
  issue_timeout_seconds: 900
  overnight_timeout_seconds: 28800
validation:
  static_validation_commands:
    - pytest
  core_regression_commands:
    - pytest -m core
  promotion_commands:
    - pytest -m promotion
issue_defaults:
  default_priority: high
  default_forbidden_paths:
    - secrets
  default_test_edit_policy:
    can_add_tests: true
    can_modify_existing_tests: true
    can_weaken_assertions: false
    requires_test_change_reason: true
  default_attempt_limits:
    max_files_changed: 3
    max_lines_added: 200
  default_timeouts:
    command_seconds: 900
    issue_budget_seconds: 7200
retry:
  max_retries: 3
  retry_policy: exponential_backoff
  failure_circuit_breaker: true
workspace:
  worktree_root: /workspace/nightshift/.worktrees
  artifact_root: /workspace/nightshift/.artifacts
  cleanup_whitelist:
    - .git
alerts:
  enabled_channels:
    - console
  severity_thresholds:
    info: info
    warning: warning
    critical: critical
report:
  output_directory: /workspace/nightshift/.reports
  summary_verbosity: concise
"""
    )

    with pytest.raises(ValidationError):
        load_config(config_path)


def test_load_config_requires_complete_default_timeouts(tmp_path: Path) -> None:
    config_path = tmp_path / "nightshift.yaml"
    config_path.write_text(
        """
project:
  repo_path: /workspace/nightshift
  main_branch: main
runner:
  default_engine: gpt-5
  fallback_engine: gpt-4.1
  issue_timeout_seconds: 900
  overnight_timeout_seconds: 28800
validation:
  static_validation_commands:
    - pytest
  core_regression_commands:
    - pytest -m core
  promotion_commands:
    - pytest -m promotion
issue_defaults:
  default_priority: high
  default_forbidden_paths:
    - secrets
  default_test_edit_policy:
    can_add_tests: true
    can_modify_existing_tests: true
    can_weaken_assertions: false
    requires_test_change_reason: true
  default_attempt_limits:
    max_files_changed: 3
    max_lines_added: 200
    max_lines_deleted: 50
  default_timeouts:
    command_seconds: 900
retry:
  max_retries: 3
  retry_policy: exponential_backoff
  failure_circuit_breaker: true
workspace:
  worktree_root: /workspace/nightshift/.worktrees
  artifact_root: /workspace/nightshift/.artifacts
  cleanup_whitelist:
    - .git
alerts:
  enabled_channels:
    - console
  severity_thresholds:
    info: info
    warning: warning
    critical: critical
report:
  output_directory: /workspace/nightshift/.reports
  summary_verbosity: concise
"""
    )

    with pytest.raises(ValidationError):
        load_config(config_path)


def test_load_config_rejects_non_mapping_root(tmp_path: Path) -> None:
    config_path = tmp_path / "nightshift.yaml"
    config_path.write_text("false\n")

    with pytest.raises(ValueError, match="root must be a mapping"):
        load_config(config_path)


def test_load_config_rejects_negative_timeouts(tmp_path: Path) -> None:
    config_path = tmp_path / "nightshift.yaml"
    config_path.write_text(
        """
project:
  repo_path: /workspace/nightshift
  main_branch: main
runner:
  default_engine: gpt-5
  fallback_engine: gpt-4.1
  issue_timeout_seconds: -1
  overnight_timeout_seconds: 28800
validation:
  static_validation_commands:
    - pytest
  core_regression_commands:
    - pytest -m core
  promotion_commands:
    - pytest -m promotion
issue_defaults:
  default_priority: high
  default_forbidden_paths:
    - secrets
  default_test_edit_policy:
    can_add_tests: true
    can_modify_existing_tests: true
    can_weaken_assertions: false
    requires_test_change_reason: true
  default_attempt_limits:
    max_files_changed: 3
    max_lines_added: 200
    max_lines_deleted: 50
  default_timeouts:
    command_seconds: 900
    issue_budget_seconds: 7200
retry:
  max_retries: 3
  retry_policy: exponential_backoff
  failure_circuit_breaker: true
workspace:
  worktree_root: /workspace/nightshift/.worktrees
  artifact_root: /workspace/nightshift/.artifacts
  cleanup_whitelist:
    - .git
alerts:
  enabled_channels:
    - console
  severity_thresholds:
    info: info
    warning: warning
    critical: critical
report:
  output_directory: /workspace/nightshift/.reports
  summary_verbosity: concise
"""
    )

    with pytest.raises(ValidationError):
        load_config(config_path)


def test_load_config_rejects_blank_paths_and_channels(tmp_path: Path) -> None:
    config_path = tmp_path / "nightshift.yaml"
    config_path.write_text(
        """
project:
  repo_path: "   "
  main_branch: main
runner:
  default_engine: gpt-5
  fallback_engine: gpt-4.1
  issue_timeout_seconds: 900
  overnight_timeout_seconds: 28800
validation:
  static_validation_commands:
    - pytest
  core_regression_commands:
    - pytest -m core
  promotion_commands:
    - pytest -m promotion
issue_defaults:
  default_priority: high
  default_forbidden_paths:
    - "   "
  default_test_edit_policy:
    can_add_tests: true
    can_modify_existing_tests: true
    can_weaken_assertions: false
    requires_test_change_reason: true
  default_attempt_limits:
    max_files_changed: 3
    max_lines_added: 200
    max_lines_deleted: 50
  default_timeouts:
    command_seconds: 900
    issue_budget_seconds: 7200
retry:
  max_retries: 3
  retry_policy: exponential_backoff
  failure_circuit_breaker: true
workspace:
  worktree_root: /workspace/nightshift/.worktrees
  artifact_root: /workspace/nightshift/.artifacts
  cleanup_whitelist:
    - .git
alerts:
  enabled_channels:
    - "   "
  severity_thresholds:
    info: info
    warning: warning
    critical: critical
report:
  output_directory: /workspace/nightshift/.reports
  summary_verbosity: concise
"""
    )

    with pytest.raises(ValidationError):
        load_config(config_path)
