from __future__ import annotations

from pathlib import Path

import pytest

from nightshift.product.splitter.models import ProposalBatch, ProposalReviewStatus, SplitterProposal
from nightshift.product.splitter.storage import ProposalStore


def make_proposal(proposal_id: str) -> SplitterProposal:
    return SplitterProposal(
        proposal_id=proposal_id,
        title=f"Proposal {proposal_id}",
        summary="Implement the requested change",
        suggested_kind="execution",
        allowed_paths=("README.md",),
        acceptance_criteria=("README exists",),
        verification_commands=("python3 -m pytest tests/test_cli_smoke.py -q",),
        review_notes=("Needs human review",),
        missing_context=(),
    )


def make_batch(batch_id: str = "BATCH-1") -> ProposalBatch:
    return ProposalBatch(
        batch_id=batch_id,
        source_requirement_path="requirements/feature-x.md",
        proposals=(make_proposal("PROP-1"), make_proposal("PROP-2")),
    )


def test_proposal_batch_defaults_review_state_to_pending_review() -> None:
    batch = make_batch()

    assert all(proposal.review_status == ProposalReviewStatus.pending_review for proposal in batch.proposals)


def test_proposal_store_saves_and_loads_batch(tmp_path: Path) -> None:
    store = ProposalStore(tmp_path)
    batch = make_batch()

    store.save_batch(batch)

    loaded = store.load_batch("BATCH-1")

    assert loaded == batch
    assert (tmp_path / "nightshift-data" / "proposals" / "BATCH-1" / "batch.json").is_file()


def test_proposal_store_lists_batches_in_sorted_order(tmp_path: Path) -> None:
    store = ProposalStore(tmp_path)
    store.save_batch(make_batch("BATCH-2"))
    store.save_batch(make_batch("BATCH-1"))

    batches = store.list_batches()

    assert [batch.batch_id for batch in batches] == ["BATCH-1", "BATCH-2"]


def test_proposal_store_rejects_conflicting_overwrite(tmp_path: Path) -> None:
    store = ProposalStore(tmp_path)
    original = make_batch("BATCH-1")
    updated = ProposalBatch(
        batch_id="BATCH-1",
        source_requirement_path="requirements/feature-y.md",
        proposals=(make_proposal("PROP-9"),),
    )

    store.save_batch(original)
    store.save_batch(original)

    with pytest.raises(ValueError, match="proposal batch already exists for batch_id=BATCH-1"):
        store.save_batch(updated)

    assert store.load_batch("BATCH-1") == original
