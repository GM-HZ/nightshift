from __future__ import annotations

from nightshift.product.issue_ingestion_bridge.models import (
    GitHubIssueBridgeResult,
    GitHubIssueBridgeSummary,
    GitHubIssuePayload,
    IssueIngestionBridgeRequest,
)


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
