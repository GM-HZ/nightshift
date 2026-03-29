from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
import re

import yaml

from nightshift.config.models import NightShiftConfig
from nightshift.product.issue_ingestion_bridge.models import (
    GitHubIssueBridgeDraft,
    GitHubIssuePayload,
)
from nightshift.product.work_orders.models import (
    WorkOrderExecution,
    WorkOrderFrontmatter,
    WorkOrderRationale,
    WorkOrderSourceIssue,
)


class IssueIngestionBridgeError(ValueError):
    """Raised when a GitHub issue cannot be bridged into a work order."""


@dataclass(frozen=True, slots=True)
class _ParsedIssueSections:
    goal: str
    allowed_paths: tuple[str, ...]
    non_goals: tuple[str, ...]
    acceptance_criteria: tuple[str, ...]
    verification_commands: tuple[str, ...]
    context_files: tuple[str, ...]
    background: str | None = None


def bridge_github_issue_to_work_order(
    payload: GitHubIssuePayload,
    *,
    config: NightShiftConfig,
    author_allowlist: Iterable[str],
    required_label: str = "nightshift",
) -> GitHubIssueBridgeDraft:
    del config
    _validate_provenance(payload, author_allowlist=author_allowlist, required_label=required_label)
    sections = _parse_issue_sections(payload)

    work_order_id = f"WO-GH-{payload.issue_number}"
    issue_id = f"GH-{payload.issue_number}"
    work_order_path = f".nightshift/work-orders/{work_order_id}.md"

    frontmatter = WorkOrderFrontmatter(
        work_order_id=work_order_id,
        status="approved",
        source_issue=WorkOrderSourceIssue(
            repo=payload.repo_full_name,
            number=payload.issue_number,
            url=payload.html_url,
        ),
        execution=WorkOrderExecution(
            title=payload.title,
            goal=sections.goal,
            allowed_paths=sections.allowed_paths,
            non_goals=sections.non_goals,
            acceptance_criteria=sections.acceptance_criteria,
            context_files=sections.context_files,
            issue_id=issue_id,
            verification_commands=sections.verification_commands,
        ),
        rationale=WorkOrderRationale(
            summary=f"Ingested from GitHub issue #{payload.issue_number}.",
            notes=((sections.background,) if sections.background else ()),
        ),
    )

    return GitHubIssueBridgeDraft(
        work_order_id=work_order_id,
        issue_id=issue_id,
        work_order_path=work_order_path,
        markdown=_render_work_order_markdown(frontmatter, background=sections.background),
    )


def _validate_provenance(
    payload: GitHubIssuePayload,
    *,
    author_allowlist: Iterable[str],
    required_label: str,
) -> None:
    allowed = {item.strip() for item in author_allowlist if item.strip()}
    if payload.author_login not in allowed:
        raise IssueIngestionBridgeError(f"author {payload.author_login} is not allowed")

    normalized_labels = {label.strip().lower() for label in payload.labels}
    if required_label.strip().lower() not in normalized_labels:
        raise IssueIngestionBridgeError(f"missing required label: {required_label}")

    body = payload.body or ""
    if "NightShift-Issue: true" not in body:
        raise IssueIngestionBridgeError("issue does not match the NightShift issue template")


def _parse_issue_sections(payload: GitHubIssuePayload) -> _ParsedIssueSections:
    body = payload.body or ""
    sections = _extract_sections(body)

    return _ParsedIssueSections(
        goal=_require_text_section(sections, "Goal"),
        allowed_paths=_require_bullets(sections, "Allowed Paths"),
        non_goals=_require_bullets(sections, "Non-Goals"),
        acceptance_criteria=_require_bullets(sections, "Acceptance Criteria"),
        verification_commands=_require_bullets(sections, "Verification Commands"),
        context_files=_require_bullets(sections, "Context Files"),
        background=_optional_text_section(sections, "Background"),
    )


def _extract_sections(body: str) -> dict[str, str]:
    matches = list(re.finditer(r"^##\s+(.+?)\s*$", body, flags=re.MULTILINE))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        name = match.group(1).strip()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        sections[name] = body[start:end].strip()
    return sections


def _require_text_section(sections: dict[str, str], name: str) -> str:
    value = _optional_text_section(sections, name)
    if value is None:
        raise IssueIngestionBridgeError(f"missing required section: {name.lower()}")
    return value


def _optional_text_section(sections: dict[str, str], name: str) -> str | None:
    value = sections.get(name)
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _require_bullets(sections: dict[str, str], name: str) -> tuple[str, ...]:
    value = sections.get(name)
    if value is None:
        raise IssueIngestionBridgeError(f"missing required section: {name.lower()}")

    items = tuple(
        line[2:].strip()
        for line in value.splitlines()
        if line.strip().startswith("- ")
    )
    if not items:
        raise IssueIngestionBridgeError(f"{name.lower()} must contain at least one bullet")
    return items


def _render_work_order_markdown(frontmatter: WorkOrderFrontmatter, *, background: str | None) -> str:
    frontmatter_text = yaml.safe_dump(
        frontmatter.model_dump(mode="python", exclude_none=True),
        sort_keys=False,
        allow_unicode=False,
    ).strip()

    body_lines = ["# Execution Work Order", ""]
    if background:
        body_lines.extend(["## Background", "", background, ""])
    body_lines.extend(
        [
            "## Source Issue",
            "",
            f"- {frontmatter.source_issue.repo}#{frontmatter.source_issue.number}",
        ]
    )
    if frontmatter.source_issue.url:
        body_lines.append(f"- {frontmatter.source_issue.url}")
    body_lines.append("")
    return f"---\n{frontmatter_text}\n---\n\n" + "\n".join(body_lines).rstrip() + "\n"
