from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from nightshift.cli.app import app
from nightshift.product.issue_ingestion_bridge.models import (
    GitHubIssueBridgeDraft,
    GitHubIssueBridgeResult,
    GitHubIssueBridgeSummary,
    GitHubIssuePayload,
)


def write_config(repo_root: Path) -> Path:
    config_path = repo_root / "nightshift.yaml"
    config_path.write_text(
        f"""
project:
  repo_path: {repo_root}
  main_branch: main
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


def make_payload() -> GitHubIssuePayload:
    return GitHubIssuePayload.model_validate(
        {
            "repo_full_name": "GM-HZ/nightshift",
            "issue_number": 7,
            "title": "Add Chinese README",
            "body": "NightShift-Issue: true",
            "labels": ["nightshift", "docs"],
            "author_login": "GM-HZ",
            "html_url": "https://github.com/GM-HZ/nightshift/issues/7",
        }
    )


def make_draft() -> GitHubIssueBridgeDraft:
    return GitHubIssueBridgeDraft.model_validate(
        {
            "work_order_id": "WO-GH-7",
            "issue_id": "GH-7",
            "work_order_path": ".nightshift/work-orders/WO-GH-7.md",
            "markdown": "---\nwork_order_id: WO-GH-7\nstatus: approved\nsource_issue:\n  repo: GM-HZ/nightshift\n  number: 7\nexecution:\n  title: Add Chinese README\n  goal: Add a Chinese README.\n  allowed_paths:\n    - README.md\n  non_goals:\n    - Change packaging\n  acceptance_criteria:\n    - README.zh-CN.md exists\n  context_files:\n    - README.md\n  verification_commands:\n    - test -s README.zh-CN.md\nrationale:\n  summary: Imported from GitHub issue #7.\n---\n",
        }
    )


def make_result(updated_existing: bool = False) -> GitHubIssueBridgeResult:
    return GitHubIssueBridgeResult(
        payload=make_payload(),
        summary=GitHubIssueBridgeSummary(
            repo_full_name="GM-HZ/nightshift",
            issue_number=7,
            work_order_id="WO-GH-7",
            updated_existing=updated_existing,
        ),
    )


def test_issue_ingest_github_runs_bridge_and_reports_summary(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path
    config_path = write_config(repo_root)
    observed: dict[str, object] = {}

    monkeypatch.setattr("nightshift.cli.app.resolve_github_token", lambda: "token")

    class FakeClient:
        def __init__(self, *, token: str) -> None:
            observed["token"] = token

        def fetch_issue(self, repo_full_name: str, issue_number: int) -> GitHubIssuePayload:
            observed["repo_full_name"] = repo_full_name
            observed["issue_number"] = issue_number
            return make_payload()

    monkeypatch.setattr("nightshift.cli.app.GitHubIssueClient", FakeClient)
    monkeypatch.setattr(
        "nightshift.cli.app.bridge_github_issue_to_work_order",
        lambda payload, *, config, author_allowlist, required_label="nightshift": make_draft(),
    )
    monkeypatch.setattr(
        "nightshift.cli.app.write_bridge_draft_to_work_order",
        lambda *, repo_root, payload, draft, update_existing: make_result(),
    )

    result = CliRunner().invoke(
        app,
        [
            "issue",
            "ingest-github",
            "--repo-full-name",
            "GM-HZ/nightshift",
            "--issue",
            "7",
            "--repo",
            str(repo_root),
            "--config",
            str(config_path),
        ],
    )

    assert result.exit_code == 0
    assert observed["token"] == "token"
    assert observed["repo_full_name"] == "GM-HZ/nightshift"
    assert observed["issue_number"] == 7
    assert "WO-GH-7" in result.stdout
    assert "created" in result.stdout.lower()


def test_issue_ingest_github_surfaces_bridge_errors_without_traceback(
    tmp_path: Path, monkeypatch
) -> None:
    repo_root = tmp_path
    config_path = write_config(repo_root)

    monkeypatch.setattr("nightshift.cli.app.resolve_github_token", lambda: "token")

    class FakeClient:
        def __init__(self, *, token: str) -> None:
            pass

        def fetch_issue(self, repo_full_name: str, issue_number: int) -> GitHubIssuePayload:
            return make_payload()

    monkeypatch.setattr("nightshift.cli.app.GitHubIssueClient", FakeClient)

    def fail_bridge(payload, *, config, author_allowlist, required_label="nightshift"):
        raise ValueError("missing required label: nightshift")

    monkeypatch.setattr("nightshift.cli.app.bridge_github_issue_to_work_order", fail_bridge)

    result = CliRunner().invoke(
        app,
        [
            "issue",
            "ingest-github",
            "--repo-full-name",
            "GM-HZ/nightshift",
            "--issue",
            "7",
            "--repo",
            str(repo_root),
            "--config",
            str(config_path),
        ],
    )

    assert result.exit_code == 1
    assert "missing required label" in result.stderr.lower()
    assert "traceback" not in result.stderr.lower()
