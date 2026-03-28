from __future__ import annotations

from collections.abc import Callable

from nightshift.product.execution_selection.models import SelectionError

from .models import ProposalBatch, ProposalReviewStatus, PublishedIssueRef, SplitterProposal
from .review import ensure_publish_ready
from .storage import ProposalStore


def render_github_issue_body(proposal: SplitterProposal) -> str:
    ready = ensure_publish_ready(proposal)

    sections = [
        "NightShift-Issue: true",
        "NightShift-Version: product-mvp",
        "",
        "## Background",
        ready.summary,
        "",
        "## Goal",
        ready.title,
        "",
        "## Allowed Paths",
        *_as_bullets(ready.allowed_paths),
        "",
        "## Non-Goals",
        "- None specified.",
        "",
        "## Acceptance Criteria",
        *_as_bullets(ready.acceptance_criteria),
        "",
        "## Verification Commands",
        *_as_bullets(ready.verification_commands),
        "",
        "## Notes",
        *_as_bullets(ready.review_notes or ("Generated from reviewed NightShift proposal.",)),
    ]
    return "\n".join(sections).strip() + "\n"


def publish_proposals(
    store: ProposalStore,
    batch_id: str,
    proposal_ids: list[str],
    *,
    repo_full_name: str,
    publisher: Callable[[str, str, str, tuple[str, ...]], PublishedIssueRef],
) -> tuple[ProposalBatch, tuple[PublishedIssueRef, ...]]:
    batch = store.load_batch(batch_id)
    selected_ids = _dedupe(proposal_ids)
    if not selected_ids:
        raise SelectionError("at least one proposal id is required")

    proposals_by_id = {proposal.proposal_id: proposal for proposal in batch.proposals}
    published_refs: list[PublishedIssueRef] = []
    updated_proposals: list[SplitterProposal] = []
    to_publish: set[str] = set(selected_ids)

    for proposal_id in selected_ids:
        if proposal_id not in proposals_by_id:
            raise SelectionError(f"unknown proposal_id: {proposal_id}")

    for proposal in batch.proposals:
        if proposal.proposal_id not in to_publish:
            updated_proposals.append(proposal)
            continue

        if proposal.review_status == ProposalReviewStatus.published:
            raise SelectionError(f"proposal {proposal.proposal_id} has already been published")

        issue_body = render_github_issue_body(proposal)
        published_ref = publisher(
            repo_full_name,
            proposal.title,
            issue_body,
            ("nightshift",),
        )
        published_refs.append(published_ref)
        updated_proposals.append(_with_review_status(proposal, ProposalReviewStatus.published))

    updated_batch = ProposalBatch.model_validate(
        {
            **batch.model_dump(mode="json"),
            "proposals": [proposal.model_dump(mode="json") for proposal in updated_proposals],
        }
    )
    store.replace_batch(updated_batch)
    return updated_batch, tuple(published_refs)


def _as_bullets(items: tuple[str, ...]) -> list[str]:
    return [f"- {item}" for item in items]


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


def _with_review_status(proposal: SplitterProposal, review_status: ProposalReviewStatus) -> SplitterProposal:
    payload = proposal.model_dump(mode="json")
    payload["review_status"] = review_status
    return SplitterProposal.model_validate(payload)
