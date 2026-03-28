from __future__ import annotations

from .models import GitHubIssue, ParsedIssueTemplate

_SECTION_NAMES = (
    "Background",
    "Goal",
    "Allowed Paths",
    "Non-Goals",
    "Acceptance Criteria",
    "Verification Commands",
    "Notes",
)


def parse_github_issue_template(issue: GitHubIssue) -> ParsedIssueTemplate:
    body = (issue.body or "").replace("\r\n", "\n")
    lines = body.split("\n")
    markers: dict[str, str] = {}
    sections: dict[str, str] = {}
    current_section: str | None = None
    section_lines: list[str] = []

    def flush_section() -> None:
        nonlocal current_section, section_lines
        if current_section is None:
            return
        sections[current_section] = "\n".join(section_lines).strip()
        current_section = None
        section_lines = []

    for raw_line in lines:
        line = raw_line.strip()
        if current_section is None and ":" in line and not line.startswith("#"):
            key, value = line.split(":", 1)
            if key in {"NightShift-Issue", "NightShift-Version"}:
                markers[key] = value.strip()
                continue

        if line.startswith("## "):
            flush_section()
            heading = line[3:].strip()
            if heading in _SECTION_NAMES:
                current_section = heading
                section_lines = []
            else:
                current_section = None
                section_lines = []
            continue

        if current_section is not None:
            section_lines.append(raw_line)

    flush_section()

    return ParsedIssueTemplate(
        repo_full_name=issue.repo_full_name,
        issue_number=issue.issue_number,
        title=issue.title,
        author_login=issue.author_login,
        labels=issue.labels,
        nightshift_issue=markers.get("NightShift-Issue", "").lower() == "true",
        nightshift_version=markers.get("NightShift-Version") or None,
        background=_normalize_block(sections.get("Background")),
        goal=_normalize_block(sections.get("Goal")),
        allowed_paths=_parse_bulleted_list(sections.get("Allowed Paths")),
        non_goals=_parse_bulleted_list(sections.get("Non-Goals")),
        acceptance_criteria=_parse_bulleted_list(sections.get("Acceptance Criteria")),
        verification_commands=_parse_bulleted_list(sections.get("Verification Commands")),
        notes=_normalize_block(sections.get("Notes")),
    )


def _normalize_block(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _parse_bulleted_list(value: str | None) -> tuple[str, ...]:
    if value is None:
        return ()

    items: list[str] = []
    for raw_line in value.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("- "):
            candidate = line[2:].strip()
        else:
            candidate = line
        if candidate:
            items.append(candidate)
    return tuple(items)
