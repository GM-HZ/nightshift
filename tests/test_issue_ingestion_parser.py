from nightshift.product.issue_ingestion import GitHubIssue, parse_github_issue_template


def test_parse_github_issue_template_extracts_markers_and_sections() -> None:
    issue = GitHubIssue(
        repo_full_name="GM-HZ/nightshift",
        issue_number=12,
        title="Add zh-CN README",
        author_login="nightshift-bot",
        labels=("nightshift", "docs"),
        body="""
NightShift-Issue: true
NightShift-Version: product-mvp

## Background
The project needs a Chinese README.

## Goal
Add a Chinese-language README entry point.

## Allowed Paths
- README.md
- README.zh-CN.md

## Non-Goals
- Change kernel behavior

## Acceptance Criteria
- Chinese README exists
- README links to it

## Verification Commands
- python3 -m pytest tests/test_cli_smoke.py -q

## Notes
Docs-only change.
""",
    )

    parsed = parse_github_issue_template(issue)

    assert parsed.nightshift_issue is True
    assert parsed.nightshift_version == "product-mvp"
    assert parsed.goal == "Add a Chinese-language README entry point."
    assert parsed.allowed_paths == ("README.md", "README.zh-CN.md")
    assert parsed.non_goals == ("Change kernel behavior",)
    assert parsed.acceptance_criteria == ("Chinese README exists", "README links to it")
    assert parsed.verification_commands == ("python3 -m pytest tests/test_cli_smoke.py -q",)
    assert parsed.notes == "Docs-only change."


def test_parse_github_issue_template_tolerates_missing_sections() -> None:
    issue = GitHubIssue(
        repo_full_name="GM-HZ/nightshift",
        issue_number=13,
        title="Minimal issue",
        author_login="gongmeng",
        labels=("nightshift",),
        body="""
NightShift-Issue: false

## Goal
Ship one small doc update.

## Allowed Paths
- README.md
""",
    )

    parsed = parse_github_issue_template(issue)

    assert parsed.nightshift_issue is False
    assert parsed.nightshift_version is None
    assert parsed.goal == "Ship one small doc update."
    assert parsed.allowed_paths == ("README.md",)
    assert parsed.acceptance_criteria == ()
    assert parsed.verification_commands == ()
    assert parsed.notes is None
