from pathlib import Path

from nightshift.config.models import NightShiftConfig
from nightshift.domain import AttemptState, DeliveryState, IssueKind, IssueState
from nightshift.product.issue_ingestion import AdmittedIssueDraft, materialize_issue
from nightshift.registry.issue_registry import IssueRegistry


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
        }
    )


def test_materialize_issue_writes_contract_and_record(tmp_path: Path) -> None:
    draft = AdmittedIssueDraft(
        issue_id="GH-1",
        repo_full_name="GM-HZ/nightshift",
        source_issue_number=1,
        title="Add zh-CN README",
        description="Add a Chinese README entry point.",
        goal="Ship a Chinese README.",
        allowed_paths=("README.md", "README.zh-CN.md"),
        forbidden_paths=("secrets",),
        acceptance_criteria=("Chinese README exists",),
        verification_commands=("python3 -m pytest tests/test_cli_smoke.py -q",),
        priority="high",
        notes="Docs-only change.",
    )

    contract, record = materialize_issue(tmp_path, draft, _config())
    registry = IssueRegistry(tmp_path)

    assert contract.kind == IssueKind.execution
    assert contract.acceptance == ("Chinese README exists",)
    assert contract.verification.issue_validation is not None
    assert contract.verification.issue_validation.commands == ("python3 -m pytest tests/test_cli_smoke.py -q",)
    assert record.issue_state == IssueState.ready
    assert record.attempt_state == AttemptState.pending
    assert record.delivery_state == DeliveryState.none
    assert registry.get_contract("GH-1") == contract
    assert registry.get_record("GH-1") == record
