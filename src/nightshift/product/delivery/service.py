from __future__ import annotations

from pathlib import Path
from typing import Callable

from nightshift.config.models import NightShiftConfig
from nightshift.domain import DeliveryState
from nightshift.product.delivery.admission import evaluate_deliverability
from nightshift.product.delivery.github_pr import PullRequestRef, render_pr_payload
from nightshift.product.delivery.git_ops import (
    git_add_paths,
    git_changed_paths,
    git_commit,
    git_push,
    render_commit_message,
)
from nightshift.product.delivery.models import DeliveryBatchResult, DeliveryRequest, DeliveryResult
from nightshift.product.execution_selection.models import SelectionError
from nightshift.registry.issue_registry import IssueRegistry


class DeliveryService:
    def __init__(
        self,
        *,
        repo_root: str | Path,
        config: NightShiftConfig,
        registry: IssueRegistry | None = None,
        git_add: Callable[[str | Path, tuple[str, ...]], None] = git_add_paths,
        git_changed_paths: Callable[[str | Path], tuple[str, ...]] = git_changed_paths,
        git_commit: Callable[[str | Path, str], None] = git_commit,
        git_push: Callable[[str | Path, str, str], None] = git_push,
        create_pull_request: Callable[[str, object], PullRequestRef],
    ) -> None:
        self.repo_root = Path(repo_root)
        self.config = config
        self.registry = registry or IssueRegistry(self.repo_root)
        self.git_add = git_add
        self.git_changed_paths = git_changed_paths
        self.git_commit = git_commit
        self.git_push = git_push
        self.create_pull_request = create_pull_request

    def deliver(self, request: DeliveryRequest) -> DeliveryBatchResult:
        results: list[DeliveryResult] = []
        for issue_id in request.issue_ids:
            results.append(self._deliver_one(issue_id))
        return DeliveryBatchResult(results=tuple(results))

    def _deliver_one(self, issue_id: str) -> DeliveryResult:
        contract = self.registry.get_contract(issue_id)
        record = self.registry.get_record(issue_id)
        worktree_path = Path(record.worktree_path or "")
        changed_paths = self.git_changed_paths(worktree_path)
        admission = evaluate_deliverability(contract, record, changed_paths=changed_paths)
        if not admission.allowed:
            return DeliveryResult(issue_id=issue_id, delivery_state="failed", reason=admission.reason)
        try:
            self.git_add(worktree_path, changed_paths)
            self.git_commit(worktree_path, render_commit_message(issue_id=issue_id, title=contract.title, kind=contract.kind))
            self.registry.attach_delivery(issue_id, DeliveryState.branch_ready)
            self.git_push(self.repo_root, self.config.product.delivery.remote_name, record.branch_name or "")
            pr_payload = render_pr_payload(
                repo_full_name=self._repo_full_name(),
                issue_id=issue_id,
                source_issue_ref=_source_issue_ref(contract.notes),
                title=contract.title,
                acceptance=contract.acceptance,
                verification=contract.verification,
                head_branch=record.branch_name or "",
                base_branch=self.config.product.delivery.base_branch,
            )
            pr_ref = self.create_pull_request(self._repo_full_name(), pr_payload)
            self.registry.attach_delivery(
                issue_id,
                DeliveryState.pr_opened,
                delivery_id=str(pr_ref.pr_number),
                delivery_ref=pr_ref.html_url,
            )
            return DeliveryResult(
                issue_id=issue_id,
                delivery_state="submitted",
                delivery_id=str(pr_ref.pr_number),
                delivery_ref=pr_ref.html_url,
            )
        except Exception as exc:  # noqa: BLE001
            self.registry.attach_delivery(issue_id, DeliveryState.none)
            return DeliveryResult(issue_id=issue_id, delivery_state="failed", reason=str(exc))

    def _repo_full_name(self) -> str:
        repo_full_name = self.config.product.delivery.repo_full_name
        if not repo_full_name:
            raise SelectionError("delivery requires product.delivery.repo_full_name")
        return repo_full_name


def _source_issue_ref(notes: str | None) -> str | None:
    if not notes:
        return None
    prefix = "Source GitHub issue:"
    for line in notes.splitlines():
        stripped = line.strip()
        if stripped.startswith(prefix):
            value = stripped[len(prefix) :].strip()
            return value or None
    return None
