from pathlib import Path

from typer.testing import CliRunner

from nightshift.cli.app import app
from nightshift.product.issue_ingestion.models import GitHubIssue


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
  issue_ingestion:
    enabled: true
    allowed_authors:
      - nightshift-bot
    required_label: nightshift
"""
    )


def test_issue_ingest_github_materializes_issue(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "nightshift.yaml"
    _write_config(config_path, tmp_path)

    def fake_fetch(repo_full_name: str, issue_number: int) -> GitHubIssue:
        assert repo_full_name == "GM-HZ/nightshift"
        assert issue_number == 1
        return GitHubIssue(
            repo_full_name=repo_full_name,
            issue_number=issue_number,
            title="Add zh-CN README",
            author_login="nightshift-bot",
            labels=("nightshift", "docs"),
            body="""
NightShift-Issue: true
NightShift-Version: product-mvp

## Background
The project needs a Chinese README.

## Goal
Add a Chinese-language README entry point.

## Allowed Paths
- README.md
- README.zh-CN.md

## Acceptance Criteria
- Chinese README exists

## Verification Commands
- python3 -m pytest tests/test_cli_smoke.py -q
""",
        )

    monkeypatch.setattr("nightshift.cli.app.fetch_github_issue", fake_fetch)

    result = CliRunner().invoke(
        app,
        [
            "issue",
            "ingest-github",
            "--repo-full-name",
            "GM-HZ/nightshift",
            "--issue",
            "1",
            "--config",
            str(config_path),
        ],
    )

    assert result.exit_code == 0
    assert "ingested GH-1 from GM-HZ/nightshift#1" in result.stdout
    assert (tmp_path / "nightshift" / "issues" / "GH-1.yaml").is_file()
    assert (tmp_path / "nightshift-data" / "issue-records" / "GH-1.json").is_file()


def test_issue_ingest_github_reports_provenance_rejection(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "nightshift.yaml"
    _write_config(config_path, tmp_path)

    monkeypatch.setattr(
        "nightshift.cli.app.fetch_github_issue",
        lambda repo_full_name, issue_number: GitHubIssue(
            repo_full_name=repo_full_name,
            issue_number=issue_number,
            title="Untrusted issue",
            author_login="external-user",
            labels=("docs",),
            body="## Goal\nShip docs.\n",
        ),
    )

    result = CliRunner().invoke(
        app,
        [
            "issue",
            "ingest-github",
            "--repo-full-name",
            "GM-HZ/nightshift",
            "--issue",
            "2",
            "--config",
            str(config_path),
        ],
    )

    assert result.exit_code == 1
    assert "provenance rejected: author external-user is not allowlisted" in result.stderr
    assert not (tmp_path / "nightshift" / "issues" / "GH-2.yaml").exists()


def test_issue_ingest_github_materialize_only_creates_non_admitted_record(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "nightshift.yaml"
    _write_config(config_path, tmp_path)

    monkeypatch.setattr(
        "nightshift.cli.app.fetch_github_issue",
        lambda repo_full_name, issue_number: GitHubIssue(
            repo_full_name=repo_full_name,
            issue_number=issue_number,
            title="Add zh-CN README",
            author_login="nightshift-bot",
            labels=("nightshift", "docs"),
            body="""
NightShift-Issue: true
NightShift-Version: product-mvp

## Goal
Add a Chinese-language README entry point.

## Allowed Paths
- README.md

## Acceptance Criteria
- Chinese README exists

## Verification Commands
- python3 -m pytest tests/test_cli_smoke.py -q
""",
        ),
    )

    result = CliRunner().invoke(
        app,
        [
            "issue",
            "ingest-github",
            "--repo-full-name",
            "GM-HZ/nightshift",
            "--issue",
            "3",
            "--materialize-only",
            "--config",
            str(config_path),
        ],
    )

    record_path = tmp_path / "nightshift-data" / "issue-records" / "GH-3.json"

    assert result.exit_code == 0
    assert "issue_state=draft attempt_state=pending" in result.stdout
    assert '"issue_state": "draft"' in record_path.read_text()
