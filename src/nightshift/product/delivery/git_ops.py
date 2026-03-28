from __future__ import annotations

import subprocess
from pathlib import Path

from nightshift.domain import IssueKind


def render_commit_message(*, issue_id: str, title: str, kind: IssueKind) -> str:
    prefix = "docs" if kind == IssueKind.execution else "chore"
    return f"{prefix}(issue): {issue_id} {title}".strip()


def git_add_all(worktree_path: str | Path) -> None:
    _run_git(worktree_path, "add", "-A")


def git_commit(worktree_path: str | Path, message: str) -> None:
    _run_git(worktree_path, "commit", "-m", message)


def git_push(repo_root: str | Path, remote_name: str, branch_name: str) -> None:
    _run_git(repo_root, "push", remote_name, branch_name)


def _run_git(repo_root: str | Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(Path(repo_root)), *args],
        check=True,
        capture_output=True,
        text=True,
    )
