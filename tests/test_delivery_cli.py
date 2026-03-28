from pathlib import Path

from typer.testing import CliRunner

from nightshift.cli.app import app
from nightshift.product.delivery.models import DeliveryBatchResult, DeliveryResult


def _write_config(path: Path, repo_path: Path) -> None:
    path.write_text(
        f"""
project:
  repo_path: {repo_path}
  main_branch: main
runner:
  default_engine: codex
  issue_timeout_seconds: 900
  overnight_timeout_seconds: 7200
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
  retry_policy: never
  failure_circuit_breaker: false
workspace:
  worktree_root: .worktrees
  artifact_root: nightshift-data/runs
alerts:
  enabled_channels: []
  severity_thresholds:
    info: info
    warning: warning
    critical: critical
report:
  output_directory: nightshift-data/reports
  summary_verbosity: concise
product:
  delivery:
    repo_full_name: GM-HZ/nightshift
"""
    )


def test_deliver_command_runs_delivery_for_selected_issues(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "nightshift.yaml"
    _write_config(config_path, tmp_path)

    class FakeService:
        def deliver(self, request):
            assert request.issue_ids == ("GH-7",)
            return DeliveryBatchResult(
                results=(DeliveryResult(issue_id="GH-7", delivery_state="submitted", delivery_ref="https://example.com/pr/7"),)
            )

    monkeypatch.setattr("nightshift.cli.app.build_delivery_service", lambda repo_root, config: FakeService())

    result = CliRunner().invoke(app, ["deliver", "--issues", "GH-7", "--config", str(config_path)])

    assert result.exit_code == 0
    assert "delivered=1" in result.stdout
    assert "failed=0" in result.stdout


def test_deliver_command_reports_failed_delivery(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "nightshift.yaml"
    _write_config(config_path, tmp_path)

    class FakeService:
        def deliver(self, request):
            return DeliveryBatchResult(results=(DeliveryResult(issue_id="GH-7", delivery_state="failed", reason="push failed"),))

    monkeypatch.setattr("nightshift.cli.app.build_delivery_service", lambda repo_root, config: FakeService())

    result = CliRunner().invoke(app, ["deliver", "--issues", "GH-7", "--config", str(config_path)])

    assert result.exit_code == 1
    assert "delivered=0" in result.stdout
    assert "failed=1" in result.stdout
