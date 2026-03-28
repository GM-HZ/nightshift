from __future__ import annotations

import subprocess
from pathlib import Path


def _run_git(repo_root: str | Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(Path(repo_root)), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def git_output(repo_root: str | Path, *args: str) -> str:
    return _run_git(repo_root, *args).stdout.strip()


def git_worktree_add(repo_root: str | Path, worktree_path: str | Path, branch_name: str, base_branch: str) -> None:
    args = ["worktree", "add"]
    if git_branch_exists(repo_root, branch_name):
        args.extend([str(Path(worktree_path)), branch_name])
    else:
        args.extend(["-b", branch_name, str(Path(worktree_path)), base_branch])
    _run_git(repo_root, *args)


def git_branch_exists(repo_root: str | Path, branch_name: str) -> bool:
    result = subprocess.run(
        ["git", "-C", str(Path(repo_root)), "show-ref", "--verify", "--quiet", f"refs/heads/{branch_name}"],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def git_head_sha(worktree_path: str | Path) -> str:
    return git_output(worktree_path, "rev-parse", "HEAD")


def git_current_branch(worktree_path: str | Path) -> str:
    return git_output(worktree_path, "branch", "--show-current")


def git_status_porcelain(worktree_path: str | Path) -> str:
    return git_output(worktree_path, "status", "--short")


def git_reset_hard(worktree_path: str | Path, commit_sha: str) -> None:
    _run_git(worktree_path, "reset", "--hard", commit_sha)


def git_clean_untracked(worktree_path: str | Path, whitelist: tuple[str, ...] = ()) -> None:
    args = ["clean", "-fdx"]
    for entry in whitelist:
        args.extend(["-e", entry])
    _run_git(worktree_path, *args)
