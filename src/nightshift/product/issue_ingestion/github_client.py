from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .models import GitHubIssue


def fetch_github_issue(repo_full_name: str, issue_number: int) -> GitHubIssue:
    url = f"https://api.github.com/repos/{repo_full_name}/issues/{issue_number}"
    request = Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "nightshift-product-mvp",
        },
    )
    try:
        with urlopen(request) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        raise ValueError(f"failed to fetch issue {repo_full_name}#{issue_number}: HTTP {error.code}") from error
    except URLError as error:
        raise ValueError(f"failed to fetch issue {repo_full_name}#{issue_number}: {error.reason}") from error

    if "pull_request" in payload:
        raise ValueError(f"{repo_full_name}#{issue_number} is a pull request, not an issue")

    labels = tuple(
        label["name"]
        for label in payload.get("labels", [])
        if isinstance(label, dict) and isinstance(label.get("name"), str) and label["name"].strip()
    )
    author = payload.get("user", {}).get("login")
    if not isinstance(author, str) or not author.strip():
        raise ValueError(f"issue {repo_full_name}#{issue_number} is missing an author login")

    title = payload.get("title")
    if not isinstance(title, str) or not title.strip():
        raise ValueError(f"issue {repo_full_name}#{issue_number} is missing a title")

    body = payload.get("body")
    if body is not None and not isinstance(body, str):
        body = str(body)

    return GitHubIssue(
        repo_full_name=repo_full_name,
        issue_number=issue_number,
        title=title,
        body=body,
        author_login=author,
        labels=labels,
    )
