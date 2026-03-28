from __future__ import annotations

from pydantic import ValidationError

from nightshift.product.execution_selection.models import SelectionError

from .models import ProposalBatch, ProposalReviewStatus, SplitterProposal
from .storage import ProposalStore


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


def approve_proposals(store: ProposalStore, batch_id: str, proposal_ids: list[str]) -> ProposalBatch:
    return _update_batch_review_status(store, batch_id, proposal_ids, ProposalReviewStatus.approved)


def reject_proposals(store: ProposalStore, batch_id: str, proposal_ids: list[str]) -> ProposalBatch:
    return _update_batch_review_status(store, batch_id, proposal_ids, ProposalReviewStatus.rejected)


def update_proposals(
    store: ProposalStore,
    batch_id: str,
    proposal_ids: list[str],
    *,
    allowed_paths: list[str] | None = None,
    acceptance_criteria: list[str] | None = None,
    verification_commands: list[str] | None = None,
    clear_missing_context: bool = False,
) -> ProposalBatch:
    selected_ids = _dedupe(proposal_ids)
    if not selected_ids:
        raise SelectionError("at least one proposal id is required")

    if (
        allowed_paths is None
        and acceptance_criteria is None
        and verification_commands is None
        and not clear_missing_context
    ):
        raise SelectionError("at least one proposal field update is required")

    batch = store.load_batch(batch_id)
    proposals_by_id = {proposal.proposal_id: proposal for proposal in batch.proposals}
    for proposal_id in selected_ids:
        if proposal_id not in proposals_by_id:
            raise SelectionError(f"unknown proposal_id: {proposal_id}")

    selected = set(selected_ids)
    updated_proposals: list[SplitterProposal] = []
    for proposal in batch.proposals:
        if proposal.proposal_id in selected:
            updated_proposals.append(
                _update_proposal_fields(
                    proposal,
                    allowed_paths=allowed_paths,
                    acceptance_criteria=acceptance_criteria,
                    verification_commands=verification_commands,
                    clear_missing_context=clear_missing_context,
                )
            )
        else:
            updated_proposals.append(proposal)

    updated_batch = ProposalBatch.model_validate(
        {
            **batch.model_dump(mode="json"),
            "proposals": [proposal.model_dump(mode="json") for proposal in updated_proposals],
        }
    )
    store.replace_batch(updated_batch)
    return updated_batch


def _with_review_status(proposal: SplitterProposal, review_status: ProposalReviewStatus) -> SplitterProposal:
    payload = proposal.model_dump(mode="json")
    payload["review_status"] = review_status
    try:
        return SplitterProposal.model_validate(payload)
    except ValidationError as error:
        raise SelectionError(str(error)) from error


def _update_batch_review_status(
    store: ProposalStore,
    batch_id: str,
    proposal_ids: list[str],
    review_status: ProposalReviewStatus,
) -> ProposalBatch:
    selected_ids = _dedupe(proposal_ids)
    if not selected_ids:
        raise SelectionError("at least one proposal id is required")

    batch = store.load_batch(batch_id)
    proposals_by_id = {proposal.proposal_id: proposal for proposal in batch.proposals}
    for proposal_id in selected_ids:
        if proposal_id not in proposals_by_id:
            raise SelectionError(f"unknown proposal_id: {proposal_id}")

    updated_proposals: list[SplitterProposal] = []
    selected = set(selected_ids)
    for proposal in batch.proposals:
        if proposal.proposal_id in selected:
            updated_proposals.append(_with_review_status(proposal, review_status))
        else:
            updated_proposals.append(proposal)

    updated_batch = ProposalBatch.model_validate(
        {
            **batch.model_dump(mode="json"),
            "proposals": [proposal.model_dump(mode="json") for proposal in updated_proposals],
        }
    )
    store.replace_batch(updated_batch)
    return updated_batch


def _update_proposal_fields(
    proposal: SplitterProposal,
    *,
    allowed_paths: list[str] | None,
    acceptance_criteria: list[str] | None,
    verification_commands: list[str] | None,
    clear_missing_context: bool,
) -> SplitterProposal:
    payload = proposal.model_dump(mode="json")
    if allowed_paths is not None:
        payload["allowed_paths"] = allowed_paths
    if acceptance_criteria is not None:
        payload["acceptance_criteria"] = acceptance_criteria
    if verification_commands is not None:
        payload["verification_commands"] = verification_commands
    if clear_missing_context:
        payload["missing_context"] = []
    try:
        return SplitterProposal.model_validate(payload)
    except ValidationError as error:
        raise SelectionError(str(error)) from error


def _dedupe(proposal_ids: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for proposal_id in proposal_ids:
        normalized = proposal_id.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered
