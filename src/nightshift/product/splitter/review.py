from __future__ import annotations

from pydantic import ValidationError

from nightshift.product.execution_selection.models import SelectionError

from .models import ProposalReviewStatus, SplitterProposal


def approve_proposal(proposal: SplitterProposal) -> SplitterProposal:
    return _with_review_status(proposal, ProposalReviewStatus.approved)


def reject_proposal(proposal: SplitterProposal) -> SplitterProposal:
    return _with_review_status(proposal, ProposalReviewStatus.rejected)


def ensure_publish_ready(proposal: SplitterProposal) -> SplitterProposal:
    if proposal.review_status != ProposalReviewStatus.approved:
        raise SelectionError(f"proposal {proposal.proposal_id} is not approved for publish")
    if not proposal.title.strip():
        raise SelectionError(f"proposal {proposal.proposal_id} is missing a concrete title")
    if not proposal.allowed_paths:
        raise SelectionError(f"proposal {proposal.proposal_id} is missing allowed paths")
    if not proposal.acceptance_criteria:
        raise SelectionError(f"proposal {proposal.proposal_id} is missing acceptance criteria")
    if not proposal.verification_commands:
        raise SelectionError(f"proposal {proposal.proposal_id} is missing verification commands")
    if proposal.missing_context:
        raise SelectionError(f"proposal {proposal.proposal_id} still has unresolved missing context")
    return proposal


def _with_review_status(proposal: SplitterProposal, review_status: ProposalReviewStatus) -> SplitterProposal:
    payload = proposal.model_dump(mode="json")
    payload["review_status"] = review_status
    try:
        return SplitterProposal.model_validate(payload)
    except ValidationError as error:
        raise SelectionError(str(error)) from error
