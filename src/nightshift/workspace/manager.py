from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from nightshift.domain.contracts import IssueContract
from nightshift.store.filesystem import safe_path_component

from .git_tools import (
    git_clean_untracked,
    git_head_sha,
    git_reset_hard,
    git_worktree_add,
)


@dataclass(frozen=True, slots=True)
class WorkspaceHandle:
    issue_id: str
    branch_name: str
    worktree_path: Path


@dataclass(frozen=True, slots=True)
class SnapshotHandle:
    pre_edit_commit_sha: str


class WorkspaceManager:
    def __init__(
        self,
        repo_root: str | Path,
        *,
        worktree_root: str | Path | None = None,
        main_branch: str = "main",
        cleanup_whitelist: tuple[str, ...] = (),
    ) -> None:
        self.repo_root = Path(repo_root)
        self.worktree_root = Path(worktree_root) if worktree_root is not None else self.repo_root / ".nightshift" / "worktrees"
        self.main_branch = main_branch
        self.cleanup_whitelist = cleanup_whitelist

    def prepare_workspace(self, issue_contract: IssueContract) -> WorkspaceHandle:
        issue_id = safe_path_component(issue_contract.issue_id, field_name="issue_id")
        branch_name = self._branch_name(issue_id, issue_contract.title)
        worktree_path = self._worktree_path(issue_id)

        worktree_path.parent.mkdir(parents=True, exist_ok=True)
        git_worktree_add(self.repo_root, worktree_path, branch_name, self.main_branch)

        return WorkspaceHandle(issue_id=issue_id, branch_name=branch_name, worktree_path=worktree_path)

    def snapshot(self, workspace: WorkspaceHandle) -> SnapshotHandle:
        return SnapshotHandle(pre_edit_commit_sha=git_head_sha(workspace.worktree_path))

    def rollback(self, workspace: WorkspaceHandle, snapshot: SnapshotHandle) -> None:
        git_reset_hard(workspace.worktree_path, snapshot.pre_edit_commit_sha)
        git_clean_untracked(workspace.worktree_path, self.cleanup_whitelist)

    def cleanup(self, workspace: WorkspaceHandle) -> None:
        git_clean_untracked(workspace.worktree_path, self.cleanup_whitelist)

    def _branch_name(self, issue_id: str, title: str) -> str:
        slug = self._slugify(title) or issue_id.lower()
        return f"nightshift/issue-{issue_id}-{slug}"

    def _worktree_path(self, issue_id: str) -> Path:
        return self.worktree_root / f"issue-{issue_id}"

    def _slugify(self, value: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
        return slug
