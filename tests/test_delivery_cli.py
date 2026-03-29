from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from typer.testing import CliRunner

from nightshift.cli.app import app
from nightshift.domain import DeliveryState
from nightshift.product.delivery.models import DeliveryWriteResult


def write_config(repo_root: Path) -> Path:
    config_path = repo_root / "nightshift.yaml"
    config_path.write_text(
        f"""
project:
  repo_path: {repo_root}
  main_branch: master
runner:
  default_engine: codex
  fallback_engine: claude
  issue_timeout_seconds: 7200
  overnight_timeout_seconds: 28800
validation:
  enabled: true
issue_defaults:
  default_priority: high
  default_forbidden_paths:
    - secrets
  default_test_edit_policy:
    can_add_tests: true
    can_modify_existing_tests: false
    can_weaken_assertions: false
    requires_test_change_reason: true
  default_attempt_limits:
    max_files_changed: 5
    max_lines_added: 500
    max_lines_deleted: 200
  default_timeouts:
    command_seconds: 900
    issue_budget_seconds: 7200
retry:
  max_retries: 1
  retry_policy: never
  failure_circuit_breaker: false
workspace:
  worktree_root: .nightshift/worktrees
  artifact_root: nightshift-data/runs
  cleanup_whitelist: []
alerts:
  enabled_channels: []
  severity_thresholds:
    info: info
    warning: warning
    critical: critical
report:
  output_directory: nightshift-data/reports
  summary_verbosity: concise
"""
    )
    return config_path


def test_deliver_cli_runs_delivery_and_reports_summary(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path
    config_path = write_config(repo_root)
    observed: dict[str, object] = {}

    monkeypatch.setattr("nightshift.cli.app.resolve_delivery_github_token", lambda: "token")

    class FakeClient:
        def __init__(self, *, token: str) -> None:
            observed["token"] = token

        def create_pull_request(self, **kwargs):
            observed["pr_kwargs"] = kwargs
            return DeliveryWriteResult(
                issue_id=kwargs["issue_id"],
                delivery_state=DeliveryState.pr_opened,
                delivery_id="8",
                delivery_ref="https://github.com/GM-HZ/nightshift/pull/8",
            )

    monkeypatch.setattr("nightshift.cli.app.GitHubPullRequestClient", FakeClient)

    def fake_deliver_issue(issue_id, **kwargs):
        observed["issue_id"] = issue_id
        kwargs["push_delivery"](snapshot={"branch_name": "nightshift-issue-gh-7-readme"})
        return kwargs["create_pr"](
            issue_record=type("IssueRecordStub", (), {"issue_id": issue_id})(),
            snapshot={
                "source_issue": {"repo": "GM-HZ/nightshift", "number": 7},
                "branch_name": "nightshift-issue-gh-7-readme",
                "work_order_id": "WO-GH-7",
                "run_id": "RUN-1",
                "attempt_id": "ATTEMPT-1",
            },
        )

    monkeypatch.setattr("nightshift.cli.app.deliver_issue", fake_deliver_issue)
    monkeypatch.setattr("nightshift.cli.app.build_issue_registry", lambda repo_root: object())
    monkeypatch.setattr(
        "nightshift.cli.app.StateStore",
        lambda repo_root: SimpleNamespace(runtime_storage=SimpleNamespace(artifacts_root=repo_root / ".nightshift" / "artifacts")),
    )
    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: None)

    result = CliRunner().invoke(
        app,
        [
            "deliver",
            "--issues",
            "GH-7",
            "--repo",
            str(repo_root),
            "--config",
            str(config_path),
        ],
    )

    assert result.exit_code == 0
    assert observed["token"] == "token"
    assert observed["issue_id"] == "GH-7"
    assert observed["pr_kwargs"]["head"] == "nightshift-issue-gh-7-readme"
    assert "pr_opened" in result.stdout
    assert "GH-7" in result.stdout


def test_deliver_cli_surfaces_delivery_errors_without_traceback(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path
    config_path = write_config(repo_root)

    monkeypatch.setattr("nightshift.cli.app.resolve_delivery_github_token", lambda: "token")
    monkeypatch.setattr("nightshift.cli.app.GitHubPullRequestClient", lambda token: object())
    monkeypatch.setattr("nightshift.cli.app.build_issue_registry", lambda repo_root: object())
    monkeypatch.setattr(
        "nightshift.cli.app.StateStore",
        lambda repo_root: SimpleNamespace(runtime_storage=SimpleNamespace(artifacts_root=repo_root / ".nightshift" / "artifacts")),
    )

    def fail_deliver(issue_id, **kwargs):
        raise ValueError("issue GH-7 is not deliverable")

    monkeypatch.setattr("nightshift.cli.app.deliver_issue", fail_deliver)

    result = CliRunner().invoke(
        app,
        [
            "deliver",
            "--issues",
            "GH-7",
            "--repo",
            str(repo_root),
            "--config",
            str(config_path),
        ],
    )

    assert result.exit_code == 1
    assert "not deliverable" in result.stderr.lower()
    assert "traceback" not in result.stderr.lower()
