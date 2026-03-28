from __future__ import annotations

import pytest

from nightshift.product.execution_selection.models import SelectionError
from nightshift.product.splitter.models import ProposalReviewStatus, SplitterProposal
from nightshift.product.splitter.review import approve_proposal, ensure_publish_ready, reject_proposal


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
