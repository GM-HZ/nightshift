from __future__ import annotations

from pathlib import Path

import pytest

from nightshift.product.delivery.service import DeliveryPRError, open_pull_request


class _Result:
    def __init__(self, returncode: int, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_open_pull_request_pushes_and_creates_pr(monkeypatch, tmp_path: Path) -> None:
    calls: list[tuple[str, ...]] = []

    def fake_run(args, check=False, text=True, capture_output=True):  # type: ignore[no-untyped-def]
        command = tuple(args)
        calls.append(command)
        if command[:6] == ("git", "-C", str(tmp_path), "remote", "get-url", "origin"):
            return _Result(0, stdout="https://github.com/GM-HZ/nightshift.git\n")
        if command[:6] == ("git", "-C", str(tmp_path), "push", "origin", "nightshift/issue-1"):
            return _Result(0, stdout="pushed\n")
        if command[:4] == ("gh", "-R", "GM-HZ/nightshift", "pr"):
            return _Result(0, stdout="https://github.com/GM-HZ/nightshift/pull/77\n")
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr("subprocess.run", fake_run)

    result = open_pull_request(
        repo_root=tmp_path,
        branch_name="nightshift/issue-1",
        base_branch="main",
        title="Ship change",
        body="Body",
    )

    assert result.pr_ref == "https://github.com/GM-HZ/nightshift/pull/77"
    assert result.pr_id == "77"
    assert len(calls) == 3


def test_open_pull_request_raises_with_command_context(monkeypatch, tmp_path: Path) -> None:
    def fake_run(args, check=False, text=True, capture_output=True):  # type: ignore[no-untyped-def]
        command = tuple(args)
        if command[:6] == ("git", "-C", str(tmp_path), "remote", "get-url", "origin"):
            return _Result(0, stdout="https://github.com/GM-HZ/nightshift.git\n")
        return _Result(1, stderr="boom")

    monkeypatch.setattr("subprocess.run", fake_run)

    with pytest.raises(DeliveryPRError, match="git -C"):
        open_pull_request(
            repo_root=tmp_path,
            branch_name="nightshift/issue-1",
            base_branch="main",
            title="Ship change",
            body="Body",
        )
