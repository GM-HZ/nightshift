from nightshift.config.models import NightShiftConfig
from nightshift.product.issue_ingestion import GitHubIssue, check_issue_admission, parse_github_issue_template


def _config() -> NightShiftConfig:
    return NightShiftConfig.model_validate(
        {
            "project": {"repo_path": "/workspace/nightshift", "main_branch": "main"},
            "runner": {"default_engine": "codex", "issue_timeout_seconds": 900, "overnight_timeout_seconds": 7200},
            "validation": {"enabled": True},
            "issue_defaults": {
                "default_priority": "high",
                "default_forbidden_paths": ["secrets", ".env"],
                "default_test_edit_policy": {
                    "can_add_tests": True,
                    "can_modify_existing_tests": True,
                    "can_weaken_assertions": False,
                    "requires_test_change_reason": True,
                },
                "default_attempt_limits": {
                    "max_files_changed": 3,
                    "max_lines_added": 200,
                    "max_lines_deleted": 50,
                },
                "default_timeouts": {"command_seconds": 900, "issue_budget_seconds": 7200},
            },
            "retry": {"max_retries": 3, "retry_policy": "never", "failure_circuit_breaker": False},
            "workspace": {"worktree_root": ".worktrees", "artifact_root": "nightshift-data/runs"},
            "alerts": {"enabled_channels": [], "severity_thresholds": {"info": "info", "warning": "warning", "critical": "critical"}},
            "report": {"output_directory": "nightshift-data/reports", "summary_verbosity": "concise"},
        }
    )


def test_check_issue_admission_materializes_defaults_for_execution_ready_issue() -> None:
    parsed = parse_github_issue_template(
        GitHubIssue(
            repo_full_name="GM-HZ/nightshift",
            issue_number=7,
            title="Add zh-CN README",
            author_login="nightshift-bot",
            labels=("nightshift",),
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

## Acceptance Criteria
- Chinese README exists
- README links to it

## Verification Commands
- python3 -m pytest tests/test_cli_smoke.py -q

## Notes
Docs-only change.
""",
        )
    )

    result = check_issue_admission(parsed, _config())

    assert result.accepted is True
    assert result.reasons == ()
    assert result.draft is not None
    assert result.draft.issue_id == "GH-7"
    assert result.draft.priority == "high"
    assert result.draft.allowed_paths == ("README.md", "README.zh-CN.md")
    assert result.draft.forbidden_paths == ("secrets", ".env")
    assert result.draft.acceptance_criteria == ("Chinese README exists", "README links to it")


def test_check_issue_admission_reports_missing_execution_requirements() -> None:
    parsed = parse_github_issue_template(
        GitHubIssue(
            repo_full_name="GM-HZ/nightshift",
            issue_number=8,
            title="Too vague",
            author_login="nightshift-bot",
            labels=("nightshift",),
            body="""
NightShift-Issue: true
NightShift-Version: product-mvp

## Goal

## Allowed Paths

## Acceptance Criteria

## Verification Commands
""",
        )
    )

    result = check_issue_admission(parsed, _config())

    assert result.accepted is False
    assert result.draft is None
    assert result.reasons == (
        "Goal section is required",
        "Allowed Paths section must contain at least one path",
        "Acceptance Criteria section must contain at least one item",
        "Verification Commands section must contain at least one command",
    )
