from pathlib import Path

from nightshift.config.loader import load_config


def test_load_config_reads_issue_defaults(tmp_path: Path) -> None:
    config_path = tmp_path / "nightshift.yaml"
    config_path.write_text(
        """
project:
  name: NightShift
runner:
  engine_policy: default
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
  enabled: true
workspace:
  root: .
alerts:
  enabled: true
report:
  format: text
"""
    )

    config = load_config(config_path)

    assert config.issue_defaults.default_priority == "high"
    assert config.issue_defaults.default_forbidden_paths == ["secrets"]
