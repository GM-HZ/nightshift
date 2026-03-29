from __future__ import annotations

from pathlib import Path

import pytest

from nightshift.config.loader import load_config
from nightshift.product.issue_ingestion_bridge.models import (
    GitHubIssueBridgeDraft,
    GitHubIssueBridgeResult,
    GitHubIssueBridgeSummary,
    GitHubIssuePayload,
    IssueIngestionBridgeRequest,
)
from nightshift.product.issue_ingestion_bridge.service import (
    IssueIngestionBridgeError,
    bridge_github_issue_to_work_order,
    write_bridge_draft_to_work_order,
)
from nightshift.product.work_orders.parser import parse_work_order_markdown


def test_issue_ingestion_bridge_request_normalizes_issue_ids() -> None:
    request = IssueIngestionBridgeRequest.model_validate(
        {
            "repo_full_name": "GM-HZ/nightshift",
            "issue_number": 7,
            "local_repo_path": "/tmp/nightshift",
        }
    )

    assert request.repo_full_name == "GM-HZ/nightshift"
    assert request.issue_number == 7
    assert request.local_repo_path == "/tmp/nightshift"
    assert request.update_existing is False


def test_github_issue_payload_accepts_structured_issue_content() -> None:
    payload = GitHubIssuePayload.model_validate(
        {
            "repo_full_name": "GM-HZ/nightshift",
            "issue_number": 7,
            "title": "Add Chinese README",
            "body": "Please add a Chinese README.",
            "labels": ["nightshift", "docs"],
            "author_login": "GM-HZ",
            "html_url": "https://github.com/GM-HZ/nightshift/issues/7",
        }
    )

    assert payload.repo_full_name == "GM-HZ/nightshift"
    assert payload.issue_number == 7
    assert payload.title == "Add Chinese README"
    assert payload.labels == ("nightshift", "docs")
    assert payload.author_login == "GM-HZ"


def test_issue_ingestion_bridge_summary_tracks_write_result() -> None:
    summary = GitHubIssueBridgeSummary.model_validate(
        {
            "repo_full_name": "GM-HZ/nightshift",
            "issue_number": 7,
            "work_order_id": "WO-20260329-001",
            "updated_existing": True,
        }
    )

    assert summary.repo_full_name == "GM-HZ/nightshift"
    assert summary.issue_number == 7
    assert summary.work_order_id == "WO-20260329-001"
    assert summary.updated_existing is True


def test_issue_ingestion_bridge_result_groups_payload_and_summary() -> None:
    result = GitHubIssueBridgeResult.model_validate(
        {
            "payload": {
                "repo_full_name": "GM-HZ/nightshift",
                "issue_number": 7,
                "title": "Add Chinese README",
                "body": "Please add a Chinese README.",
                "labels": ["nightshift"],
                "author_login": "GM-HZ",
                "html_url": "https://github.com/GM-HZ/nightshift/issues/7",
            },
            "summary": {
                "repo_full_name": "GM-HZ/nightshift",
                "issue_number": 7,
                "work_order_id": "WO-20260329-001",
                "updated_existing": False,
            },
        }
    )

    assert result.payload.issue_number == 7
    assert result.summary.work_order_id == "WO-20260329-001"


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


def make_payload(
    *,
    author_login: str = "GM-HZ",
    labels: tuple[str, ...] = ("nightshift", "docs"),
    body_override: str | None = None,
) -> GitHubIssuePayload:
    body = body_override or """NightShift-Issue: true

## Goal
Add a Chinese README and link it from the main README.

## Allowed Paths
- README.md
- README.zh-CN.md

## Non-Goals
- Change packaging

## Acceptance Criteria
- README.zh-CN.md exists and is non-empty
- README.md links to README.zh-CN.md

## Verification Commands
- test -s README.zh-CN.md
- rg -n "README\\.zh-CN\\.md" README.md

## Context Files
- README.md
- docs/usage/workflow.md

## Background
This should stay narrowly scoped to documentation updates.
"""
    return GitHubIssuePayload.model_validate(
        {
            "repo_full_name": "GM-HZ/nightshift",
            "issue_number": 7,
            "title": "Add Chinese README",
            "body": body,
            "labels": list(labels),
            "author_login": author_login,
            "html_url": "https://github.com/GM-HZ/nightshift/issues/7",
        }
    )


def test_bridge_service_maps_compliant_issue_into_work_order_markdown(tmp_path: Path) -> None:
    config = load_config(write_config(tmp_path))

    draft = bridge_github_issue_to_work_order(
        make_payload(),
        config=config,
        author_allowlist=("GM-HZ",),
    )

    assert isinstance(draft, GitHubIssueBridgeDraft)
    assert draft.work_order_id == "WO-GH-7"
    assert draft.issue_id == "GH-7"
    assert draft.work_order_path == ".nightshift/work-orders/WO-GH-7.md"

    parsed = parse_work_order_markdown(draft.markdown)
    assert parsed.frontmatter.work_order_id == "WO-GH-7"
    assert parsed.frontmatter.status == "approved"
    assert parsed.frontmatter.source_issue.repo == "GM-HZ/nightshift"
    assert parsed.frontmatter.source_issue.number == 7
    assert parsed.frontmatter.execution.issue_id == "GH-7"
    assert parsed.frontmatter.execution.allowed_paths == ("README.md", "README.zh-CN.md")
    assert parsed.frontmatter.execution.non_goals == ("Change packaging",)
    assert parsed.frontmatter.execution.context_files == ("README.md", "docs/usage/workflow.md")
    assert parsed.frontmatter.execution.verification_commands == (
        "test -s README.zh-CN.md",
        'rg -n "README\\.zh-CN\\.md" README.md',
    )


def test_bridge_service_rejects_non_allowlisted_author(tmp_path: Path) -> None:
    config = load_config(write_config(tmp_path))

    with pytest.raises(IssueIngestionBridgeError, match="author .* is not allowed"):
        bridge_github_issue_to_work_order(
            make_payload(author_login="someone-else"),
            config=config,
            author_allowlist=("GM-HZ",),
        )


def test_bridge_service_rejects_missing_required_label(tmp_path: Path) -> None:
    config = load_config(write_config(tmp_path))

    with pytest.raises(IssueIngestionBridgeError, match="missing required label"):
        bridge_github_issue_to_work_order(
            make_payload(labels=("docs",)),
            config=config,
            author_allowlist=("GM-HZ",),
        )


def test_bridge_service_rejects_missing_required_execution_field(tmp_path: Path) -> None:
    config = load_config(write_config(tmp_path))
    payload = make_payload(
        body_override="""NightShift-Issue: true

## Goal
Add a Chinese README.

## Non-Goals
- Change packaging

## Acceptance Criteria
- README.zh-CN.md exists

## Verification Commands
- test -s README.zh-CN.md

## Context Files
- README.md
"""
    )

    with pytest.raises(IssueIngestionBridgeError, match="allowed paths"):
        bridge_github_issue_to_work_order(
            payload,
            config=config,
            author_allowlist=("GM-HZ",),
        )


def test_bridge_service_writes_new_work_order_into_repo_layout(tmp_path: Path) -> None:
    config = load_config(write_config(tmp_path))
    draft = bridge_github_issue_to_work_order(
        make_payload(),
        config=config,
        author_allowlist=("GM-HZ",),
    )

    result = write_bridge_draft_to_work_order(
        repo_root=tmp_path,
        payload=make_payload(),
        draft=draft,
        update_existing=False,
    )

    work_order_path = tmp_path / ".nightshift" / "work-orders" / "WO-GH-7.md"
    assert work_order_path.exists()
    assert result.summary.updated_existing is False
    assert result.summary.work_order_id == "WO-GH-7"
    assert result.summary.issue_number == 7

    parsed = parse_work_order_markdown(work_order_path.read_text())
    assert parsed.frontmatter.work_order_id == "WO-GH-7"
    assert parsed.frontmatter.execution.issue_id == "GH-7"


def test_bridge_service_rejects_overwrite_by_default(tmp_path: Path) -> None:
    config = load_config(write_config(tmp_path))
    draft = bridge_github_issue_to_work_order(
        make_payload(),
        config=config,
        author_allowlist=("GM-HZ",),
    )

    existing_path = tmp_path / ".nightshift" / "work-orders" / "WO-GH-7.md"
    existing_path.parent.mkdir(parents=True, exist_ok=True)
    existing_path.write_text("stale contents")

    with pytest.raises(IssueIngestionBridgeError, match="already exists"):
        write_bridge_draft_to_work_order(
            repo_root=tmp_path,
            payload=make_payload(),
            draft=draft,
            update_existing=False,
        )

    assert existing_path.read_text() == "stale contents"


def test_bridge_service_allows_explicit_update_existing(tmp_path: Path) -> None:
    config = load_config(write_config(tmp_path))
    draft = bridge_github_issue_to_work_order(
        make_payload(),
        config=config,
        author_allowlist=("GM-HZ",),
    )

    existing_path = tmp_path / ".nightshift" / "work-orders" / "WO-GH-7.md"
    existing_path.parent.mkdir(parents=True, exist_ok=True)
    existing_path.write_text("stale contents")

    result = write_bridge_draft_to_work_order(
        repo_root=tmp_path,
        payload=make_payload(),
        draft=draft,
        update_existing=True,
    )

    assert result.summary.updated_existing is True
    assert parse_work_order_markdown(existing_path.read_text()).frontmatter.work_order_id == "WO-GH-7"
