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
  priority: high
  forbidden_paths:
    - secrets
  test_edit_policy: allow
  attempt_limits:
    max_attempts: 3
  timeouts:
    preflight_seconds: 30
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

    assert config.issue_defaults.priority == "high"
    assert config.issue_defaults.forbidden_paths == ["secrets"]
