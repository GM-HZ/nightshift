from __future__ import annotations

import subprocess
from pathlib import Path

from nightshift.domain import IssueKind


def render_commit_message(*, issue_id: str, title: str, kind: IssueKind) -> str:
    prefix = "docs" if kind == IssueKind.execution else "chore"
    return f"{prefix}(issue): {issue_id} {title}".strip()


def git_add_all(worktree_path: str | Path) -> None:
    _run_git(worktree_path, "add", "-A")


def git_add_paths(worktree_path: str | Path, changed_paths: tuple[str, ...]) -> None:
    if not changed_paths:
        raise ValueError("changed_paths must not be empty")
    _run_git(worktree_path, "add", "--", *changed_paths)


def git_commit(worktree_path: str | Path, message: str) -> None:
    _run_git(worktree_path, "commit", "-m", message)


def git_push(repo_root: str | Path, remote_name: str, branch_name: str) -> None:
    _run_git(repo_root, "push", remote_name, branch_name)


def git_changed_paths(worktree_path: str | Path) -> tuple[str, ...]:
    output = _run_git(worktree_path, "status", "--short").stdout.strip()
    if not output:
        return ()

    paths: list[str] = []
    for line in output.splitlines():
        raw = line[3:] if len(line) > 3 else ""
        path = raw.split(" -> ", 1)[-1].strip()
        if path and path not in paths:
            paths.append(path)
    return tuple(paths)


def _run_git(repo_root: str | Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(Path(repo_root)), *args],
        check=True,
        capture_output=True,
        text=True,
    )
