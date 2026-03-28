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
from nightshift.engines.claude_code_adapter import ClaudeCodeAdapter
from nightshift.engines.registry import EngineRegistry


def _make_issue_contract(*, primary: str | None = "claude", fallback: str | None = "codex") -> IssueContract:
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


def test_claude_adapter_declares_expected_capabilities() -> None:
    adapter = ClaudeCodeAdapter(command=("python", "-c", "print('claude')"))

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


def test_registry_fallback_helper_requires_distinct_available_adapter() -> None:
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
    codex = DummyAdapter("codex")
    claude = DummyAdapter("claude")
    registry.register(codex)
    registry.register(claude)

    contract = _make_issue_contract(primary="codex", fallback="claude")

    assert registry.is_fallback_eligible(contract, codex) is True
    assert registry.is_fallback_eligible(contract, claude) is False
    assert registry.is_fallback_eligible(_make_issue_contract(primary="codex", fallback="missing"), codex) is False
    assert registry.is_fallback_eligible(_make_issue_contract(primary="claude", fallback="claude"), claude) is False


def test_registry_prefers_configured_default_before_alphabetic_fallback() -> None:
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

    registry = EngineRegistry(default_adapter_name="codex")
    registry.register(DummyAdapter("codex"))
    registry.register(DummyAdapter("claude"))

    resolved = registry.resolve(_make_issue_contract(primary=None, fallback=None))

    assert resolved.name() == "codex"


def test_registry_rejects_explicit_unavailable_preferences_instead_of_silent_default() -> None:
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

    registry = EngineRegistry(default_adapter_name="codex")
    registry.register(DummyAdapter("codex"))
    registry.register(DummyAdapter("claude"))

    with pytest.raises(LookupError):
        registry.resolve(_make_issue_contract(primary="missing", fallback=None))

    with pytest.raises(LookupError):
        registry.resolve(_make_issue_contract(primary="missing", fallback="also-missing"))


def test_claude_prepare_builds_artifact_backed_invocation(tmp_path: Path) -> None:
    issue_contract = _make_issue_contract()
    artifact_dir = tmp_path / "artifacts"
    context_bundle = ContextBundle(
        issue_id=issue_contract.issue_id,
        prompt="Fix the failing issue",
        artifact_dir=artifact_dir,
        worktree_path=tmp_path / "worktree",
    )
    adapter = ClaudeCodeAdapter(command=("python", "-c", "print('claude')"))

    prepared = adapter.prepare(issue_contract, tmp_path / "workspace", context_bundle)

    assert prepared.cwd == tmp_path / "workspace"
    assert prepared.artifact_dir == artifact_dir
    assert prepared.stdout_path == artifact_dir / "stdout.txt"
    assert prepared.stderr_path == artifact_dir / "stderr.txt"
    assert prepared.outcome_path == artifact_dir / "engine-outcome.json"
    assert prepared.context_path == artifact_dir / "context.txt"
    assert prepared.structured_output_path == artifact_dir / "structured-output.json"
    assert prepared.timeout_seconds == 60
    assert prepared.command == ("python", "-c", "print('claude')")
    assert prepared.prompt == "Fix the failing issue"
    assert prepared.context_path.read_text() == "Fix the failing issue"


def test_claude_execute_writes_artifacts_and_normalizes_outcome(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    issue_contract = _make_issue_contract()
    artifact_dir = tmp_path / "artifacts"
    context_bundle = ContextBundle(
        issue_id=issue_contract.issue_id,
        prompt="Fix the failing issue",
        artifact_dir=artifact_dir,
        worktree_path=tmp_path / "worktree",
    )
    adapter = ClaudeCodeAdapter(command=("python", "-c", "print('claude')"))
    prepared = adapter.prepare(issue_contract, tmp_path / "workspace", context_bundle)

    run_kwargs: dict[str, Any] = {}

    def fake_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        del args
        run_kwargs.update(kwargs)
        return subprocess.CompletedProcess(
            args=("python", "-c", "print('claude')"),
            returncode=0,
            stdout='{"summary":"hello from claude"}\n',
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    outcome = adapter.execute(prepared)

    assert isinstance(outcome, EngineOutcome)
    assert outcome.engine_name == "claude"
    assert outcome.engine_invocation_id == prepared.invocation_id
    assert outcome.outcome_type == "success"
    assert outcome.exit_code == 0
    assert outcome.recoverable is False
    assert outcome.stdout_path == str(prepared.stdout_path)
    assert outcome.stderr_path == str(prepared.stderr_path)
    assert run_kwargs["input"] == "Fix the failing issue"
    assert run_kwargs["timeout"] == 60
    assert outcome.artifact_paths == (
        str(prepared.context_path),
        str(prepared.stdout_path),
        str(prepared.stderr_path),
        str(prepared.structured_output_path),
        str(prepared.outcome_path),
    )
    assert prepared.stdout_path.read_text() == '{"summary":"hello from claude"}\n'
    assert prepared.stderr_path.read_text() == ""
    assert json.loads(prepared.structured_output_path.read_text()) == {"summary": "hello from claude"}

    outcome_payload = json.loads(prepared.outcome_path.read_text())
    assert outcome_payload["engine_name"] == "claude"
    assert outcome_payload["outcome_type"] == "success"
    assert outcome_payload["summary"] == "command completed successfully"


def test_claude_execute_normalizes_timeout_as_engine_timeout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    issue_contract = _make_issue_contract()
    artifact_dir = tmp_path / "artifacts"
    context_bundle = ContextBundle(
        issue_id=issue_contract.issue_id,
        prompt="Fix the failing issue",
        artifact_dir=artifact_dir,
        worktree_path=tmp_path / "worktree",
    )
    adapter = ClaudeCodeAdapter(command=("python", "-c", "print('claude')"))
    prepared = adapter.prepare(issue_contract, tmp_path / "workspace", context_bundle)

    def fake_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        del args
        raise subprocess.TimeoutExpired(
            cmd=kwargs["args"] if "args" in kwargs else prepared.command,
            timeout=kwargs["timeout"],
            output="partial stdout\n",
            stderr="partial stderr\n",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    outcome = adapter.execute(prepared)

    assert outcome.outcome_type == "engine_timeout"
    assert outcome.engine_error_type == "engine_timeout"
    assert outcome.recoverable is True
    assert prepared.stdout_path.read_text() == "partial stdout\n"
    assert prepared.stderr_path.read_text() == "partial stderr\n"
