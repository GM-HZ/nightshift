from __future__ import annotations

import subprocess
from pathlib import Path

from nightshift.domain import IssueKind
from nightshift.domain.contracts import (
    AttemptLimitsContract,
    IssueContract,
    PassConditionContract,
    TestEditPolicyContract,
    TimeoutsContract,
    VerificationContract,
    VerificationStageContract,
)
from nightshift.workspace.manager import WorkspaceManager


def make_contract(issue_id: str, title: str = "Add Workspace Manager") -> IssueContract:
    return IssueContract(
        issue_id=issue_id,
        title=title,
        kind=IssueKind.execution,
        priority="high",
        goal="Manage isolated workspaces",
        allowed_paths=("src",),
        forbidden_paths=("secrets",),
        verification=VerificationContract(
            issue_validation=VerificationStageContract(
                required=True,
                commands=("pytest",),
                pass_condition=PassConditionContract(type="exit_code", expected=0),
            )
        ),
        test_edit_policy=TestEditPolicyContract(
            can_add_tests=True,
            can_modify_existing_tests=True,
            can_weaken_assertions=False,
            requires_test_change_reason=True,
        ),
        attempt_limits=AttemptLimitsContract(),
        timeouts=TimeoutsContract(),
    )


def run_git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    run_git(repo, "init", "-b", "main")
    run_git(repo, "config", "user.name", "NightShift")
    run_git(repo, "config", "user.email", "nightshift@example.com")
    (repo / ".gitignore").write_text("*.cache\n")
    (repo / "tracked.txt").write_text("original\n")
    run_git(repo, "add", ".gitignore", "tracked.txt")
    run_git(repo, "commit", "-m", "initial commit")
    return repo


def test_workspace_manager_prepares_expected_branch_and_worktree_path(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    manager = WorkspaceManager(repo)

    workspace = manager.prepare_workspace(make_contract("ISSUE-123", "Add Workspace Manager"))

    assert workspace.branch_name == "nightshift/issue-issue-123-add-workspace-manager"
    assert workspace.worktree_path == repo / ".nightshift" / "worktrees" / "issue-ISSUE-123"
    assert run_git(workspace.worktree_path, "branch", "--show-current") == workspace.branch_name


def test_workspace_manager_sanitizes_issue_id_for_branch_name(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    manager = WorkspaceManager(repo)

    workspace = manager.prepare_workspace(make_contract("ISSUE 123", "Add Workspace Manager"))

    assert workspace.branch_name == "nightshift/issue-issue-123-add-workspace-manager"
    assert run_git(workspace.worktree_path, "branch", "--show-current") == workspace.branch_name


def test_workspace_manager_snapshot_captures_pre_edit_commit_sha(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    manager = WorkspaceManager(repo)
    workspace = manager.prepare_workspace(make_contract("ISSUE-123"))

    snapshot = manager.snapshot(workspace)

    assert snapshot.pre_edit_commit_sha == run_git(workspace.worktree_path, "rev-parse", "HEAD")


def test_workspace_manager_rolls_back_tracked_changes(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    manager = WorkspaceManager(repo)
    workspace = manager.prepare_workspace(make_contract("ISSUE-123"))
    snapshot = manager.snapshot(workspace)

    tracked_file = workspace.worktree_path / "tracked.txt"
    tracked_file.write_text("changed\n")
    assert run_git(workspace.worktree_path, "status", "--short") == "M tracked.txt"

    manager.rollback(workspace, snapshot)

    assert tracked_file.read_text() == "original\n"
    assert run_git(workspace.worktree_path, "status", "--short") == ""


def test_workspace_manager_cleanup_preserves_whitelisted_untracked_files(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    manager = WorkspaceManager(repo, cleanup_whitelist=(".git", "keep.txt"))
    workspace = manager.prepare_workspace(make_contract("ISSUE-123"))

    keep_file = workspace.worktree_path / "keep.txt"
    drop_file = workspace.worktree_path / "drop.txt"
    keep_file.write_text("keep\n")
    drop_file.write_text("drop\n")

    manager.cleanup(workspace)

    assert keep_file.exists()
    assert not drop_file.exists()


def test_workspace_manager_cleanup_removes_ignored_files(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    manager = WorkspaceManager(repo)
    workspace = manager.prepare_workspace(make_contract("ISSUE-123"))

    ignored_file = workspace.worktree_path / "build.cache"
    ignored_file.write_text("generated\n")

    manager.cleanup(workspace)

    assert not ignored_file.exists()
