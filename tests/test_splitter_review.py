from __future__ import annotations

import pytest

from nightshift.product.execution_selection.models import SelectionError
from nightshift.product.splitter.models import ProposalBatch, ProposalReviewStatus, SplitterProposal
from nightshift.product.splitter.review import (
    approve_proposal,
    approve_proposals,
    ensure_publish_ready,
    reject_proposal,
    reject_proposals,
    update_proposals,
)
from nightshift.product.splitter.storage import ProposalStore


def make_proposal(**overrides: object) -> SplitterProposal:
    payload = {
        "proposal_id": "PROP-1",
        "title": "Add zh-CN README",
        "summary": "Create a Chinese README and link it from the main README.",
        "suggested_kind": "execution",
        "allowed_paths": ("README.md", "README.zh-CN.md"),
        "acceptance_criteria": ("Chinese README exists",),
        "verification_commands": ("python3 -m pytest tests/test_cli_smoke.py -q",),
        "review_notes": (),
        "missing_context": (),
    }
    payload.update(overrides)
    return SplitterProposal.model_validate(payload)


def test_approve_proposal_marks_it_approved() -> None:
    proposal = make_proposal()

    approved = approve_proposal(proposal)

    assert approved.review_status == ProposalReviewStatus.approved


def test_reject_proposal_marks_it_rejected() -> None:
    proposal = make_proposal()

    rejected = reject_proposal(proposal)

    assert rejected.review_status == ProposalReviewStatus.rejected


def test_publish_ready_requires_explicit_approval() -> None:
    with pytest.raises(SelectionError, match="proposal PROP-1 is not approved for publish"):
        ensure_publish_ready(make_proposal())


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("allowed_paths", (), "proposal PROP-1 is missing allowed paths"),
        ("acceptance_criteria", (), "proposal PROP-1 is missing acceptance criteria"),
        ("verification_commands", (), "proposal PROP-1 is missing verification commands"),
        ("missing_context", ("repo context missing",), "proposal PROP-1 still has unresolved missing context"),
    ],
)
def test_publish_ready_fails_closed_for_unresolved_execution_fields(
    field: str,
    value: object,
    message: str,
) -> None:
    proposal = approve_proposal(make_proposal(**{field: value}))

    with pytest.raises(SelectionError, match=message):
        ensure_publish_ready(proposal)


def test_publish_ready_accepts_edited_and_approved_proposal() -> None:
    proposal = approve_proposal(
        make_proposal(
            title="Add Chinese README and docs entrypoint",
            allowed_paths=("README.md", "README.zh-CN.md", "docs/"),
            acceptance_criteria=("Chinese README exists", "README links to it"),
        )
    )

    ready = ensure_publish_ready(proposal)

    assert ready.review_status == ProposalReviewStatus.approved


def test_approve_proposals_updates_batch_review_state(tmp_path) -> None:
    store = ProposalStore(tmp_path)
    store.save_batch(
        ProposalBatch(
            batch_id="BATCH-1",
            source_requirement_path="requirements/feature-x.md",
            proposals=(make_proposal(),),
        )
    )

    updated = approve_proposals(store, "BATCH-1", ["PROP-1"])

    assert updated.proposals[0].review_status == ProposalReviewStatus.approved
    assert store.load_batch("BATCH-1").proposals[0].review_status == ProposalReviewStatus.approved


def test_reject_proposals_updates_batch_review_state(tmp_path) -> None:
    store = ProposalStore(tmp_path)
    store.save_batch(
        ProposalBatch(
            batch_id="BATCH-1",
            source_requirement_path="requirements/feature-x.md",
            proposals=(make_proposal(),),
        )
    )

    updated = reject_proposals(store, "BATCH-1", ["PROP-1"])

    assert updated.proposals[0].review_status == ProposalReviewStatus.rejected


def test_update_proposals_replaces_execution_fields_and_clears_missing_context(tmp_path) -> None:
    store = ProposalStore(tmp_path)
    store.save_batch(
        ProposalBatch(
            batch_id="BATCH-1",
            source_requirement_path="requirements/feature-x.md",
            proposals=(
                make_proposal(
                    allowed_paths=(),
                    acceptance_criteria=(),
                    verification_commands=(),
                    missing_context=(
                        "allowed paths not yet specified",
                        "acceptance criteria not yet specified",
                        "verification commands not yet specified",
                    ),
                ),
            ),
        )
    )

    updated = update_proposals(
        store,
        "BATCH-1",
        ["PROP-1"],
        allowed_paths=["README.md", "README.zh-CN.md"],
        acceptance_criteria=["Chinese README exists", "README links to it"],
        verification_commands=["python -m pytest -q"],
        clear_missing_context=True,
    )

    proposal = updated.proposals[0]
    assert proposal.allowed_paths == ("README.md", "README.zh-CN.md")
    assert proposal.acceptance_criteria == ("Chinese README exists", "README links to it")
    assert proposal.verification_commands == ("python -m pytest -q",)
    assert proposal.missing_context == ()


def test_update_proposals_requires_at_least_one_mutation(tmp_path) -> None:
    store = ProposalStore(tmp_path)
    store.save_batch(
        ProposalBatch(
            batch_id="BATCH-1",
            source_requirement_path="requirements/feature-x.md",
            proposals=(make_proposal(),),
        )
    )

    with pytest.raises(SelectionError, match="at least one proposal field update is required"):
        update_proposals(store, "BATCH-1", ["PROP-1"])
