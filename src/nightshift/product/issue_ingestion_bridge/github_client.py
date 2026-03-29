from __future__ import annotations

import json
import os
from urllib import error, request

from nightshift.product.issue_ingestion_bridge.models import GitHubIssuePayload


class GitHubIssueClientError(ValueError):
    """Raised when GitHub issue fetch cannot complete cleanly."""


def resolve_github_token() -> str:
    for variable in ("NIGHTSHIFT_GITHUB_TOKEN", "GITHUB_TOKEN"):
        value = os.environ.get(variable, "").strip()
        if value:
            return value
    raise GitHubIssueClientError(
        "missing GitHub token; set NIGHTSHIFT_GITHUB_TOKEN or GITHUB_TOKEN"
    )


class GitHubIssueClient:
    def __init__(self, *, token: str) -> None:
        self._token = token

    def fetch_issue(self, repo_full_name: str, issue_number: int) -> GitHubIssuePayload:
        url = f"https://api.github.com/repos/{repo_full_name}/issues/{issue_number}"
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "nightshift-ingestion-bridge",
        }
        http_request = request.Request(url, headers=headers)

        try:
            with request.urlopen(http_request) as response:
                raw_payload = json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            raise GitHubIssueClientError(
                f"failed to fetch GitHub issue {repo_full_name}#{issue_number}: HTTP {exc.code}"
            ) from exc
        except (OSError, json.JSONDecodeError) as exc:
            raise GitHubIssueClientError(
                f"failed to fetch GitHub issue {repo_full_name}#{issue_number}"
            ) from exc

        return GitHubIssuePayload.model_validate(
            {
                "repo_full_name": repo_full_name,
                "issue_number": issue_number,
                "title": raw_payload.get("title"),
                "body": raw_payload.get("body"),
                "labels": [
                    label.get("name")
                    for label in raw_payload.get("labels", [])
                    if isinstance(label, dict) and label.get("name")
                ],
                "author_login": (raw_payload.get("user") or {}).get("login"),
                "html_url": raw_payload.get("html_url"),
            }
        )
