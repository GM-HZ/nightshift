from pathlib import Path

import pytest
from pydantic import ValidationError

from nightshift.config.loader import load_config


def test_load_config_reads_issue_defaults(tmp_path: Path) -> None:
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

    config = load_config(config_path)

    assert config.project.repo_path == "/workspace/nightshift"
    assert config.runner.default_engine == "gpt-5"
    assert config.validation.static_validation_commands == ["pytest"]
    assert config.issue_defaults.default_priority == "high"
    assert config.issue_defaults.default_forbidden_paths == ["secrets"]
    assert config.workspace.worktree_root == "/workspace/nightshift/.worktrees"
    assert config.alerts.enabled_channels == ["console"]
    assert config.report.summary_verbosity == "concise"
    assert config.product.issue_ingestion.enabled is False
    assert config.product.issue_ingestion.required_label == "nightshift"


def test_load_config_reads_product_issue_ingestion_settings(tmp_path: Path) -> None:
    config_path = tmp_path / "nightshift.yaml"
    config_path.write_text(
        """
project:
  repo_path: /workspace/nightshift
  main_branch: main
runner:
  default_engine: gpt-5
  issue_timeout_seconds: 900
  overnight_timeout_seconds: 28800
validation:
  enabled: true
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
alerts:
  enabled_channels: []
  severity_thresholds:
    info: info
    warning: warning
    critical: critical
report:
  output_directory: /workspace/nightshift/.reports
  summary_verbosity: concise
product:
  issue_ingestion:
    enabled: true
    allowed_authors:
      - nightshift-bot
      - gongmeng
    required_label: nightshift
"""
    )

    config = load_config(config_path)

    assert config.product.issue_ingestion.enabled is True
    assert config.product.issue_ingestion.allowed_authors == ["nightshift-bot", "gongmeng"]
    assert config.product.issue_ingestion.required_label == "nightshift"
    assert config.product.delivery.remote_name == "origin"
    assert config.product.delivery.base_branch == "master"


def test_load_config_reads_product_delivery_settings(tmp_path: Path) -> None:
    config_path = tmp_path / "nightshift.yaml"
    config_path.write_text(
        """
project:
  repo_path: /workspace/nightshift
  main_branch: main
runner:
  default_engine: gpt-5
  issue_timeout_seconds: 900
  overnight_timeout_seconds: 28800
validation:
  enabled: true
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
alerts:
  enabled_channels: []
  severity_thresholds:
    info: info
    warning: warning
    critical: critical
report:
  output_directory: /workspace/nightshift/.reports
  summary_verbosity: concise
product:
  delivery:
    repo_full_name: GM-HZ/nightshift
    remote_name: upstream
    base_branch: stable
"""
    )

    config = load_config(config_path)

    assert config.product.delivery.repo_full_name == "GM-HZ/nightshift"
    assert config.product.delivery.remote_name == "upstream"
    assert config.product.delivery.base_branch == "stable"


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
