from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from .models import ProposalBatch, SplitterProposal


def split_requirement_file(requirement_path: str | Path) -> ProposalBatch:
    path = Path(requirement_path)
    body = path.read_text().strip()
    title = _extract_title(path, body)
    summary = _extract_summary(body)
    batch_id = f"BATCH-{uuid4().hex[:8]}"
    proposal_id = f"PROP-{uuid4().hex[:8]}"
    return ProposalBatch(
        batch_id=batch_id,
        source_requirement_path=str(path),
        proposals=(
            SplitterProposal(
                proposal_id=proposal_id,
                title=title,
                summary=summary,
                suggested_kind="execution",
                allowed_paths=(),
                acceptance_criteria=(),
                verification_commands=(),
                review_notes=("Generated from requirement file.",),
                missing_context=(
                    "allowed paths not yet specified",
                    "acceptance criteria not yet specified",
                    "verification commands not yet specified",
                ),
            ),
        ),
    )


def _extract_title(path: Path, body: str) -> str:
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return path.stem.replace("-", " ").replace("_", " ").title()


def _extract_summary(body: str) -> str:
    for line in body.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            return stripped
    return "Requirement imported for proposal review."
