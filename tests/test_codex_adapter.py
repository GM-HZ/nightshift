from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import subprocess
from typing import Any

import pytest

from nightshift.context.bundle import ContextBundle
from nightshift.domain.contracts import (
    AttemptLimitsContract,
    EnginePreferencesContract,
    IssueContract,
    PassConditionContract,
    TestEditPolicyContract,
    TimeoutsContract,
    VerificationContract,
    VerificationStageContract,
)
from nightshift.domain.enums import IssueKind
from nightshift.engines.base import EngineCapabilities, EngineOutcome
from nightshift.engines.codex_adapter import CodexAdapter
from nightshift.engines.registry import EngineRegistry


def _make_issue_contract(*, primary: str | None = "codex", fallback: str | None = "claude") -> IssueContract:
    return IssueContract(
        issue_id="ISSUE-1",
        title="Implement feature",
        kind=IssueKind.execution,
        priority="high",
        goal="Ship the feature",
        allowed_paths=["src"],
        forbidden_paths=["secrets"],
        verification=VerificationContract(
            issue_validation=VerificationStageContract(
                required=True,
                commands=("python -c \"print('ok')\"",),
                pass_condition=PassConditionContract(type="exit_code", expected=0),
            )
        ),
        engine_preferences=EnginePreferencesContract(primary=primary, fallback=fallback),
        test_edit_policy=TestEditPolicyContract(
            can_add_tests=True,
            can_modify_existing_tests=True,
            can_weaken_assertions=False,
            requires_test_change_reason=True,
        ),
        attempt_limits=AttemptLimitsContract(max_files_changed=3, max_lines_added=200, max_lines_deleted=50),
        timeouts=TimeoutsContract(command_seconds=60, issue_budget_seconds=120),
    )


def test_codex_adapter_declares_expected_capabilities() -> None:
    adapter = CodexAdapter(command=("python", "-c", "print('codex')"))

    capabilities = adapter.capabilities()

    assert capabilities == EngineCapabilities(
        supports_streaming_output=False,
        supports_structured_result=True,
        supports_patch_artifact=False,
        supports_resume=False,
        supports_noninteractive_mode=True,
        supports_worktree_execution=True,
        supports_file_scope_constraints=True,
        supports_timeout_enforcement=True,
        supports_json_output_hint=True,
    )


def test_registry_prefers_primary_then_fallback_then_deterministic_default() -> None:
    @dataclass
    class DummyAdapter:
        adapter_name: str

        def name(self) -> str:
            return self.adapter_name

        def capabilities(self) -> EngineCapabilities:
            return EngineCapabilities()

        def prepare(self, issue_contract: IssueContract, workspace: object, context_bundle: ContextBundle) -> object:
            del issue_contract, workspace, context_bundle
            return object()

        def execute(self, prepared_invocation: object) -> EngineOutcome:
            del prepared_invocation
            return EngineOutcome(
                engine_name=self.adapter_name,
                engine_invocation_id="invocation",
                outcome_type="success",
                exit_code=0,
                recoverable=False,
                summary="ok",
            )

        def normalize_output(self, raw_result: object) -> EngineOutcome:
            del raw_result
            return self.execute(object())

    registry = EngineRegistry()
    registry.register(DummyAdapter("codex"))
    registry.register(DummyAdapter("claude"))

    primary_contract = _make_issue_contract(primary="claude", fallback="codex")
    resolved_primary = registry.resolve(primary_contract)
    assert resolved_primary.name() == "claude"

    fallback_contract = _make_issue_contract(primary="unknown", fallback="codex")
    resolved_fallback = registry.resolve(fallback_contract)
    assert resolved_fallback.name() == "codex"

    default_contract = _make_issue_contract(primary=None, fallback=None)
    resolved_default = registry.resolve(default_contract)
    assert resolved_default.name() == "claude"


def test_codex_prepare_builds_artifact_backed_invocation(tmp_path: Path) -> None:
    issue_contract = _make_issue_contract()
    artifact_dir = tmp_path / "artifacts"
    context_bundle = ContextBundle(
        issue_id=issue_contract.issue_id,
        prompt="Fix the failing issue",
        artifact_dir=artifact_dir,
        worktree_path=tmp_path / "worktree",
    )
    adapter = CodexAdapter(command=("python", "-c", "print('codex')"))

    prepared = adapter.prepare(issue_contract, tmp_path / "workspace", context_bundle)

    assert prepared.cwd == tmp_path / "workspace"
    assert prepared.artifact_dir == artifact_dir
    assert prepared.stdout_path == artifact_dir / "stdout.txt"
    assert prepared.stderr_path == artifact_dir / "stderr.txt"
    assert prepared.outcome_path == artifact_dir / "engine-outcome.json"
    assert prepared.command == ("python", "-c", "print('codex')")
    assert prepared.prompt == "Fix the failing issue"


def test_codex_execute_writes_artifacts_and_normalizes_outcome(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    issue_contract = _make_issue_contract()
    artifact_dir = tmp_path / "artifacts"
    context_bundle = ContextBundle(
        issue_id=issue_contract.issue_id,
        prompt="Fix the failing issue",
        artifact_dir=artifact_dir,
        worktree_path=tmp_path / "worktree",
    )
    adapter = CodexAdapter(command=("python", "-c", "print('codex')"))
    prepared = adapter.prepare(issue_contract, tmp_path / "workspace", context_bundle)

    def fake_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        del args, kwargs
        return subprocess.CompletedProcess(
            args=("python", "-c", "print('codex')"),
            returncode=0,
            stdout="hello from codex\n",
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    outcome = adapter.execute(prepared)

    assert isinstance(outcome, EngineOutcome)
    assert outcome.engine_name == "codex"
    assert outcome.engine_invocation_id == prepared.invocation_id
    assert outcome.outcome_type == "success"
    assert outcome.exit_code == 0
    assert outcome.recoverable is False
    assert outcome.stdout_path == str(prepared.stdout_path)
    assert outcome.stderr_path == str(prepared.stderr_path)
    assert outcome.artifact_paths == (
        str(prepared.stdout_path),
        str(prepared.stderr_path),
        str(prepared.outcome_path),
    )
    assert prepared.stdout_path.read_text() == "hello from codex\n"
    assert prepared.stderr_path.read_text() == ""

    outcome_payload = json.loads(prepared.outcome_path.read_text())
    assert outcome_payload["engine_name"] == "codex"
    assert outcome_payload["outcome_type"] == "success"
    assert outcome_payload["summary"] == "command completed successfully"
