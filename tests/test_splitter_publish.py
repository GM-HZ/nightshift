from __future__ import annotations

import pytest

from nightshift.product.execution_selection.models import SelectionError
from nightshift.product.issue_ingestion import GitHubIssue, parse_github_issue_template
from nightshift.product.splitter.github_publish import publish_proposals, render_github_issue_body
from nightshift.product.splitter.models import ProposalBatch, ProposalReviewStatus, PublishedIssueRef, SplitterProposal
from nightshift.product.splitter.storage import ProposalStore


def make_proposal(proposal_id: str, *, review_status: ProposalReviewStatus = ProposalReviewStatus.approved) -> SplitterProposal:
    return SplitterProposal(
        proposal_id=proposal_id,
        title="Add zh-CN README",
        summary="The project needs a Chinese README and a main README link.",
        suggested_kind="execution",
        allowed_paths=("README.md", "README.zh-CN.md"),
        acceptance_criteria=("Chinese README exists", "README links to it"),
        verification_commands=("python3 -m pytest tests/test_cli_smoke.py -q",),
        review_notes=("Docs-only change",),
        missing_context=(),
        review_status=review_status,
    )


def test_render_github_issue_body_matches_ingestion_template_shape() -> None:
    body = render_github_issue_body(make_proposal("PROP-1"))

    parsed = parse_github_issue_template(
        GitHubIssue(
            repo_full_name="GM-HZ/nightshift",
            issue_number=1,
            title="Add zh-CN README",
            author_login="nightshift-bot",
            labels=("nightshift",),
            body=body,
        )
    )

    assert parsed.nightshift_issue is True
    assert parsed.nightshift_version == "product-mvp"
    assert parsed.goal == "Add zh-CN README"
    assert parsed.allowed_paths == ("README.md", "README.zh-CN.md")
    assert parsed.acceptance_criteria == ("Chinese README exists", "README links to it")
    assert parsed.verification_commands == ("python3 -m pytest tests/test_cli_smoke.py -q",)


def test_publish_proposals_marks_approved_proposal_as_published(tmp_path) -> None:
    store = ProposalStore(tmp_path)
    batch = ProposalBatch(
        batch_id="BATCH-1",
        source_requirement_path="requirements/feature-x.md",
        proposals=(make_proposal("PROP-1"),),
    )
    store.save_batch(batch)

    calls: list[tuple[str, str, str, tuple[str, ...]]] = []

    def fake_publisher(repo_full_name: str, title: str, body: str, labels: tuple[str, ...]) -> PublishedIssueRef:
        calls.append((repo_full_name, title, body, labels))
        return PublishedIssueRef(repo_full_name=repo_full_name, issue_number=12, html_url="https://example.com/issues/12")

    updated_batch, refs = publish_proposals(
        store,
        "BATCH-1",
        ["PROP-1"],
        repo_full_name="GM-HZ/nightshift",
        publisher=fake_publisher,
    )

    assert len(calls) == 1
    assert calls[0][0] == "GM-HZ/nightshift"
    assert calls[0][1] == "Add zh-CN README"
    assert calls[0][3] == ("nightshift",)
    assert refs[0].issue_number == 12
    assert updated_batch.proposals[0].review_status == ProposalReviewStatus.published
    assert store.load_batch("BATCH-1").proposals[0].review_status == ProposalReviewStatus.published


def test_publish_proposals_rejects_duplicate_publish_attempt(tmp_path) -> None:
    store = ProposalStore(tmp_path)
    store.save_batch(
        ProposalBatch(
            batch_id="BATCH-1",
            source_requirement_path="requirements/feature-x.md",
            proposals=(make_proposal("PROP-1", review_status=ProposalReviewStatus.published),),
        )
    )

    with pytest.raises(SelectionError, match="proposal PROP-1 has already been published"):
        publish_proposals(
            store,
            "BATCH-1",
            ["PROP-1"],
            repo_full_name="GM-HZ/nightshift",
            publisher=lambda *args: PublishedIssueRef(repo_full_name="GM-HZ/nightshift", issue_number=1),
        )


def test_publish_proposals_rejects_unapproved_proposal(tmp_path) -> None:
    store = ProposalStore(tmp_path)
    store.save_batch(
        ProposalBatch(
            batch_id="BATCH-1",
            source_requirement_path="requirements/feature-x.md",
            proposals=(make_proposal("PROP-1", review_status=ProposalReviewStatus.pending_review),),
        )
    )

    with pytest.raises(SelectionError, match="proposal PROP-1 is not approved for publish"):
        publish_proposals(
            store,
            "BATCH-1",
            ["PROP-1"],
            repo_full_name="GM-HZ/nightshift",
            publisher=lambda *args: PublishedIssueRef(repo_full_name="GM-HZ/nightshift", issue_number=1),
        )
