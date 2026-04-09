from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import subprocess


class DeliveryPRError(RuntimeError):
    """Raised when opening a PR from a delivery branch fails."""


@dataclass(frozen=True, slots=True)
class DeliveryPRResult:
    pr_ref: str
    pr_id: str | None = None


def open_pull_request(
    *,
    repo_root: Path,
    branch_name: str,
    base_branch: str,
    title: str,
    body: str,
) -> DeliveryPRResult:
    _run_checked("git", "-C", str(repo_root), "push", "origin", branch_name)

    result = _run_checked(
        "gh",
        "-R",
        _origin_slug(repo_root),
        "pr",
        "create",
        "--base",
        base_branch,
        "--head",
        branch_name,
        "--title",
        title,
        "--body",
        body,
    )

    pr_ref = result.stdout.strip().splitlines()[-1].strip()
    if not pr_ref:
        raise DeliveryPRError("gh pr create returned empty output")

    match = re.search(r"/pull/(\d+)(?:$|[/?#])", pr_ref)
    pr_id = match.group(1) if match else None
    return DeliveryPRResult(pr_ref=pr_ref, pr_id=pr_id)


def _origin_slug(repo_root: Path) -> str:
    result = _run_checked("git", "-C", str(repo_root), "remote", "get-url", "origin")
    url = result.stdout.strip()
    if not url:
        raise DeliveryPRError("git remote origin URL is empty")

    ssh = re.match(r"git@github\.com:(?P<slug>[^/]+/[^/.]+?)(?:\.git)?$", url)
    if ssh:
        return ssh.group("slug")

    https = re.match(r"https://github\.com/(?P<slug>[^/]+/[^/.]+?)(?:\.git)?$", url)
    if https:
        return https.group("slug")

    raise DeliveryPRError(f"unsupported origin URL for GitHub PR creation: {url}")


def _run_checked(*args: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(args, check=False, text=True, capture_output=True)
    if result.returncode != 0:
        stderr = result.stderr.strip()
        stdout = result.stdout.strip()
        detail = stderr or stdout or "command failed without output"
        command = " ".join(args)
        raise DeliveryPRError(f"{command}: {detail}")
    return result
