from nightshift.config.models import NightShiftConfig
from nightshift.product.issue_ingestion import GitHubIssue, check_issue_provenance, parse_github_issue_template


def _config() -> NightShiftConfig:
    return NightShiftConfig.model_validate(
        {
            "project": {"repo_path": "/workspace/nightshift", "main_branch": "main"},
            "runner": {"default_engine": "codex", "issue_timeout_seconds": 900, "overnight_timeout_seconds": 7200},
            "validation": {"enabled": True},
            "issue_defaults": {
                "default_priority": "high",
                "default_forbidden_paths": ["secrets"],
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
            "product": {
                "issue_ingestion": {
                    "enabled": True,
                    "allowed_authors": ["nightshift-bot", "gongmeng"],
                    "required_label": "nightshift",
                }
            },
        }
    )


def test_check_issue_provenance_accepts_allowlisted_labeled_template_issue() -> None:
    parsed = parse_github_issue_template(
        GitHubIssue(
            repo_full_name="GM-HZ/nightshift",
            issue_number=1,
            title="Add README.zh-CN.md",
            author_login="nightshift-bot",
            labels=("nightshift", "docs"),
            body="NightShift-Issue: true\nNightShift-Version: product-mvp\n\n## Goal\nShip docs.\n",
        )
    )

    result = check_issue_provenance(parsed, _config())

    assert result.accepted is True
    assert result.reasons == ()


def test_check_issue_provenance_reports_all_rejection_reasons() -> None:
    parsed = parse_github_issue_template(
        GitHubIssue(
            repo_full_name="GM-HZ/nightshift",
            issue_number=2,
            title="Untrusted issue",
            author_login="external-user",
            labels=("docs",),
            body="## Goal\nShip docs.\n",
        )
    )

    result = check_issue_provenance(parsed, _config())

    assert result.accepted is False
    assert result.reasons == (
        "author external-user is not allowlisted",
        "required label nightshift is missing",
        "NightShift-Issue marker must be true",
        "NightShift-Version marker is missing",
    )
