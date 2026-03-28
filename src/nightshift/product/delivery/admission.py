from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from nightshift.domain.contracts import IssueContract
from nightshift.domain.records import IssueRecord


class DeliverabilityResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    allowed: bool
    reason: str | None = None


def evaluate_deliverability(contract: IssueContract, record: IssueRecord) -> DeliverabilityResult:
    if contract.issue_id != record.issue_id:
        return DeliverabilityResult(allowed=False, reason="contract and record issue ids do not match")

    if record.issue_state != "done" or record.attempt_state != "accepted":
        return DeliverabilityResult(allowed=False, reason=f"issue {record.issue_id} is not in an accepted state")

    if record.delivery_ref:
        return DeliverabilityResult(allowed=False, reason=f"issue {record.issue_id} already has delivery recorded")

    if not record.branch_name:
        return DeliverabilityResult(allowed=False, reason=f"issue {record.issue_id} is missing a delivery branch")

    if not record.worktree_path:
        return DeliverabilityResult(allowed=False, reason=f"issue {record.issue_id} is missing a worktree path")

    if not Path(record.worktree_path).exists():
        return DeliverabilityResult(allowed=False, reason=f"issue {record.issue_id} worktree does not exist")

    return DeliverabilityResult(allowed=True)
