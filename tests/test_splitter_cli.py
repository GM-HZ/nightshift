from pathlib import Path

from typer.testing import CliRunner

from nightshift.cli.app import app
from nightshift.product.splitter.models import ProposalBatch, ProposalReviewStatus, PublishedIssueRef, SplitterProposal
from nightshift.product.splitter.storage import ProposalStore


def test_split_command_creates_a_proposal_batch(tmp_path: Path) -> None:
    requirement_path = tmp_path / "requirements" / "feature-x.md"
    requirement_path.parent.mkdir(parents=True, exist_ok=True)
    requirement_path.write_text("# Feature X\n\nNeed a Chinese README.\n")

    result = CliRunner().invoke(app, ["split", "--file", str(requirement_path), "--repo", str(tmp_path)])

    assert result.exit_code == 0
    assert "created proposal batch" in result.stdout
    batches = ProposalStore(tmp_path).list_batches()
    assert len(batches) == 1
    assert batches[0].source_requirement_path == str(requirement_path)


def test_proposals_show_lists_saved_batches_and_statuses(tmp_path: Path) -> None:
    store = ProposalStore(tmp_path)
    store.save_batch(
        ProposalBatch(
            batch_id="BATCH-1",
            source_requirement_path="requirements/feature-x.md",
            proposals=(
                SplitterProposal(
                    proposal_id="PROP-1",
                    title="Add zh-CN README",
                    summary="Need a Chinese README.",
                    suggested_kind="execution",
                    allowed_paths=("README.md",),
                    acceptance_criteria=("Chinese README exists",),
                    verification_commands=("python3 -m pytest tests/test_cli_smoke.py -q",),
                    review_notes=(),
                    missing_context=(),
                    review_status=ProposalReviewStatus.approved,
                ),
            ),
        )
    )

    result = CliRunner().invoke(app, ["proposals", "show", "--repo", str(tmp_path)])

    assert result.exit_code == 0
    assert "batch_id=BATCH-1" in result.stdout
    assert "proposal_id=PROP-1" in result.stdout
    assert "review_status=approved" in result.stdout


def test_proposals_publish_publishes_only_explicitly_approved_proposals(monkeypatch, tmp_path: Path) -> None:
    store = ProposalStore(tmp_path)
    store.save_batch(
        ProposalBatch(
            batch_id="BATCH-1",
            source_requirement_path="requirements/feature-x.md",
            proposals=(
                SplitterProposal(
                    proposal_id="PROP-1",
                    title="Add zh-CN README",
                    summary="Need a Chinese README.",
                    suggested_kind="execution",
                    allowed_paths=("README.md",),
                    acceptance_criteria=("Chinese README exists",),
                    verification_commands=("python3 -m pytest tests/test_cli_smoke.py -q",),
                    review_notes=(),
                    missing_context=(),
                    review_status=ProposalReviewStatus.approved,
                ),
            ),
        )
    )

    monkeypatch.setattr(
        "nightshift.cli.app.create_github_issue",
        lambda repo_full_name, title, body, labels: PublishedIssueRef(
            repo_full_name=repo_full_name,
            issue_number=42,
            html_url="https://example.com/issues/42",
        ),
    )

    result = CliRunner().invoke(
        app,
        ["proposals", "publish", "PROP-1", "--batch", "BATCH-1", "--repo", str(tmp_path), "--repo-full-name", "GM-HZ/nightshift"],
    )

    assert result.exit_code == 0
    assert "published proposal PROP-1 as GM-HZ/nightshift#42" in result.stdout


def test_proposals_publish_reports_unapproved_proposal(monkeypatch, tmp_path: Path) -> None:
    store = ProposalStore(tmp_path)
    store.save_batch(
        ProposalBatch(
            batch_id="BATCH-1",
            source_requirement_path="requirements/feature-x.md",
            proposals=(
                SplitterProposal(
                    proposal_id="PROP-1",
                    title="Add zh-CN README",
                    summary="Need a Chinese README.",
                    suggested_kind="execution",
                    allowed_paths=("README.md",),
                    acceptance_criteria=("Chinese README exists",),
                    verification_commands=("python3 -m pytest tests/test_cli_smoke.py -q",),
                    review_notes=(),
                    missing_context=(),
                    review_status=ProposalReviewStatus.pending_review,
                ),
            ),
        )
    )

    monkeypatch.setattr(
        "nightshift.cli.app.create_github_issue",
        lambda repo_full_name, title, body, labels: PublishedIssueRef(repo_full_name=repo_full_name, issue_number=42),
    )

    result = CliRunner().invoke(
        app,
        ["proposals", "publish", "PROP-1", "--batch", "BATCH-1", "--repo", str(tmp_path), "--repo-full-name", "GM-HZ/nightshift"],
    )

    assert result.exit_code == 1
    assert "proposal PROP-1 is not approved for publish" in result.stderr


def test_proposals_approve_updates_review_status(tmp_path: Path) -> None:
    store = ProposalStore(tmp_path)
    store.save_batch(
        ProposalBatch(
            batch_id="BATCH-1",
            source_requirement_path="requirements/feature-x.md",
            proposals=(
                SplitterProposal(
                    proposal_id="PROP-1",
                    title="Add zh-CN README",
                    summary="Need a Chinese README.",
                    suggested_kind="execution",
                    allowed_paths=("README.md",),
                    acceptance_criteria=("Chinese README exists",),
                    verification_commands=("python3 -m pytest tests/test_cli_smoke.py -q",),
                    review_notes=(),
                    missing_context=(),
                    review_status=ProposalReviewStatus.pending_review,
                ),
            ),
        )
    )

    result = CliRunner().invoke(app, ["proposals", "approve", "PROP-1", "--batch", "BATCH-1", "--repo", str(tmp_path)])

    assert result.exit_code == 0
    assert "approved proposal PROP-1" in result.stdout
    assert ProposalStore(tmp_path).load_batch("BATCH-1").proposals[0].review_status == ProposalReviewStatus.approved


def test_proposals_reject_updates_review_status(tmp_path: Path) -> None:
    store = ProposalStore(tmp_path)
    store.save_batch(
        ProposalBatch(
            batch_id="BATCH-1",
            source_requirement_path="requirements/feature-x.md",
            proposals=(
                SplitterProposal(
                    proposal_id="PROP-1",
                    title="Add zh-CN README",
                    summary="Need a Chinese README.",
                    suggested_kind="execution",
                    allowed_paths=("README.md",),
                    acceptance_criteria=("Chinese README exists",),
                    verification_commands=("python3 -m pytest tests/test_cli_smoke.py -q",),
                    review_notes=(),
                    missing_context=(),
                    review_status=ProposalReviewStatus.pending_review,
                ),
            ),
        )
    )

    result = CliRunner().invoke(app, ["proposals", "reject", "PROP-1", "--batch", "BATCH-1", "--repo", str(tmp_path)])

    assert result.exit_code == 0
    assert "rejected proposal PROP-1" in result.stdout
    assert ProposalStore(tmp_path).load_batch("BATCH-1").proposals[0].review_status == ProposalReviewStatus.rejected


def test_proposals_update_replaces_execution_fields(tmp_path: Path) -> None:
    store = ProposalStore(tmp_path)
    store.save_batch(
        ProposalBatch(
            batch_id="BATCH-1",
            source_requirement_path="requirements/feature-x.md",
            proposals=(
                SplitterProposal(
                    proposal_id="PROP-1",
                    title="Add zh-CN README",
                    summary="Need a Chinese README.",
                    suggested_kind="execution",
                    allowed_paths=(),
                    acceptance_criteria=(),
                    verification_commands=(),
                    review_notes=(),
                    missing_context=(
                        "allowed paths not yet specified",
                        "acceptance criteria not yet specified",
                        "verification commands not yet specified",
                    ),
                    review_status=ProposalReviewStatus.pending_review,
                ),
            ),
        )
    )

    result = CliRunner().invoke(
        app,
        [
            "proposals",
            "update",
            "PROP-1",
            "--batch",
            "BATCH-1",
            "--repo",
            str(tmp_path),
            "--allowed-path",
            "README.md",
            "--allowed-path",
            "README.zh-CN.md",
            "--acceptance",
            "Chinese README exists",
            "--acceptance",
            "README links to it",
            "--verify",
            "python -m pytest -q",
            "--clear-missing-context",
        ],
    )

    assert result.exit_code == 0
    assert "updated proposal PROP-1" in result.stdout
    proposal = ProposalStore(tmp_path).load_batch("BATCH-1").proposals[0]
    assert proposal.allowed_paths == ("README.md", "README.zh-CN.md")
    assert proposal.acceptance_criteria == ("Chinese README exists", "README links to it")
    assert proposal.verification_commands == ("python -m pytest -q",)
    assert proposal.missing_context == ()


def test_proposals_update_requires_at_least_one_field_mutation(tmp_path: Path) -> None:
    store = ProposalStore(tmp_path)
    store.save_batch(
        ProposalBatch(
            batch_id="BATCH-1",
            source_requirement_path="requirements/feature-x.md",
            proposals=(
                SplitterProposal(
                    proposal_id="PROP-1",
                    title="Add zh-CN README",
                    summary="Need a Chinese README.",
                    suggested_kind="execution",
                    allowed_paths=(),
                    acceptance_criteria=(),
                    verification_commands=(),
                    review_notes=(),
                    missing_context=(),
                    review_status=ProposalReviewStatus.pending_review,
                ),
            ),
        )
    )

    result = CliRunner().invoke(
        app,
        ["proposals", "update", "PROP-1", "--batch", "BATCH-1", "--repo", str(tmp_path)],
    )

    assert result.exit_code == 1
    assert "at least one proposal field update is required" in result.stderr
