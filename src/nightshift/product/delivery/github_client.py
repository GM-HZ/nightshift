from __future__ import annotations

import json
import os
from urllib import error, request

from nightshift.config.loader import load_github_auth_config
from nightshift.domain import DeliveryState
from nightshift.product.delivery.models import DeliveryWriteResult


class GitHubPullRequestClientError(ValueError):
    """Raised when GitHub PR creation cannot complete cleanly."""


def resolve_delivery_github_token() -> str:
    for variable in ("NIGHTSHIFT_GITHUB_TOKEN", "GITHUB_TOKEN"):
        value = os.environ.get(variable, "").strip()
        if value:
            return value
    auth = load_github_auth_config()
    if auth is not None:
        if auth.token_env_var:
            value = os.environ.get(auth.token_env_var, "").strip()
            if value:
                return value
        if auth.token:
            return auth.token
    raise GitHubPullRequestClientError(
        "missing GitHub token; set NIGHTSHIFT_GITHUB_TOKEN or GITHUB_TOKEN"
    )


class GitHubPullRequestClient:
    def __init__(self, *, token: str) -> None:
        self._token = token

    def create_pull_request(
        self,
        *,
        repo_full_name: str,
        title: str,
        body: str,
        head: str,
        base: str,
        issue_id: str,
    ) -> DeliveryWriteResult:
        url = f"https://api.github.com/repos/{repo_full_name}/pulls"
        payload = {
            "title": title,
            "body": body,
            "head": head,
            "base": base,
            "draft": True,
        }
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "nightshift-delivery",
            "Content-Type": "application/json",
        }
        http_request = request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        try:
            with request.urlopen(http_request) as response:
                raw_payload = json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            raise GitHubPullRequestClientError(
                f"failed to create pull request for {repo_full_name}: HTTP {exc.code}"
            ) from exc
        except (OSError, json.JSONDecodeError) as exc:
            raise GitHubPullRequestClientError(
                f"failed to create pull request for {repo_full_name}"
            ) from exc

        delivery_id = raw_payload.get("number")
        delivery_ref = raw_payload.get("html_url")
        if delivery_id is None or not delivery_ref:
            raise GitHubPullRequestClientError(
                f"failed to create pull request for {repo_full_name}: missing response fields"
            )

        return DeliveryWriteResult(
            issue_id=issue_id,
            delivery_state=DeliveryState.pr_opened,
            delivery_id=str(delivery_id),
            delivery_ref=str(delivery_ref),
        )
