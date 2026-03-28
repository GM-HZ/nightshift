from __future__ import annotations

import json
import os
from typing import Annotated
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import BaseModel, ConfigDict, StringConstraints

from nightshift.domain.contracts import VerificationContract
from nightshift.product.execution_selection.models import SelectionError

NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class PullRequestPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    title: NonEmptyStr
    body: NonEmptyStr
    head_branch: NonEmptyStr
    base_branch: NonEmptyStr


class PullRequestRef(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    pr_number: int
    html_url: NonEmptyStr | None = None


def render_pr_title(*, issue_id: str, issue_title: str) -> str:
    return f"{issue_id}: {issue_title}".strip()


def render_pr_payload(
    *,
    repo_full_name: str,
    issue_id: str,
    source_issue_number: int | None,
    title: str,
    acceptance: tuple[str, ...],
    verification: VerificationContract,
    head_branch: str = "nightshift-placeholder",
    base_branch: str = "master",
) -> PullRequestPayload:
    verification_commands = _collect_verification_commands(verification)
    issue_ref = f"#{source_issue_number}" if source_issue_number is not None else issue_id
    body_lines = [
        "## Summary",
        f"- Delivered by NightShift for {issue_ref}",
        "",
        "## Acceptance",
        *_as_bullets(acceptance or ("See issue contract.",)),
        "",
        "## Verification",
        *_as_bullets(verification_commands or ("No verification commands recorded.",)),
        "",
        f"Source repository: {repo_full_name}",
    ]
    return PullRequestPayload(
        title=render_pr_title(issue_id=issue_id, issue_title=title),
        body="\n".join(body_lines).strip(),
        head_branch=head_branch,
        base_branch=base_branch,
    )


def create_github_pull_request(repo_full_name: str, payload: PullRequestPayload) -> PullRequestRef:
    token = os.environ.get("NIGHTSHIFT_GITHUB_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SelectionError("GitHub pull request creation requires NIGHTSHIFT_GITHUB_TOKEN or GITHUB_TOKEN")

    request = Request(
        f"https://api.github.com/repos/{repo_full_name}/pulls",
        data=json.dumps(
            {
                "title": payload.title,
                "body": payload.body,
                "head": payload.head_branch,
                "base": payload.base_branch,
            }
        ).encode("utf-8"),
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "nightshift-product-mvp",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request) as response:
            raw_payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        raise SelectionError(f"failed to create GitHub pull request in {repo_full_name}: HTTP {error.code}") from error
    except URLError as error:
        raise SelectionError(f"failed to create GitHub pull request in {repo_full_name}: {error.reason}") from error

    pr_number = raw_payload.get("number")
    if not isinstance(pr_number, int):
        raise SelectionError(f"GitHub pull request creation in {repo_full_name} returned no pull request number")

    html_url = raw_payload.get("html_url")
    return PullRequestRef(pr_number=pr_number, html_url=html_url if isinstance(html_url, str) and html_url.strip() else None)


def _collect_verification_commands(verification: VerificationContract) -> tuple[str, ...]:
    commands: list[str] = []
    for stage in (
        verification.issue_validation,
        verification.static_validation,
        verification.regression_validation,
        verification.promotion_validation,
    ):
        if stage is None:
            continue
        for command in stage.commands:
            if command not in commands:
                commands.append(command)
    return tuple(commands)


def _as_bullets(items: tuple[str, ...]) -> list[str]:
    return [f"- {item}" for item in items]
