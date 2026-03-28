from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
import json
import subprocess
from typing import Sequence

from nightshift.context.bundle import ContextBundle
from nightshift.domain.contracts import IssueContract

from .base import EngineAdapter, EngineCapabilities, EngineOutcome, PreparedInvocation


@dataclass(frozen=True, slots=True)
class _ExecutionResult:
    prepared: PreparedInvocation
    completed: subprocess.CompletedProcess[str] | None
    started_at: datetime
    ended_at: datetime
    engine_error_type: str | None = None
    timeout: bool = False
    environment_error: str | None = None


class ClaudeCodeAdapter(EngineAdapter):
    def __init__(self, command: Sequence[str] = ("claude",)) -> None:
        self._command = tuple(command)

    def name(self) -> str:
        return "claude"

    def capabilities(self) -> EngineCapabilities:
        return EngineCapabilities(
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

    def prepare(self, issue_contract: IssueContract, workspace: object, context_bundle: ContextBundle) -> PreparedInvocation:
        cwd = _workspace_path(workspace)
        artifact_dir = Path(context_bundle.artifact_dir)
        artifact_dir.mkdir(parents=True, exist_ok=True)
        invocation_id = uuid4().hex
        stdout_path = artifact_dir / "stdout.txt"
        stderr_path = artifact_dir / "stderr.txt"
        outcome_path = artifact_dir / "engine-outcome.json"
        context_path = artifact_dir / "context.txt"
        structured_output_path = artifact_dir / "structured-output.json"
        context_path.write_text(context_bundle.prompt)
        return PreparedInvocation(
            engine_name=self.name(),
            invocation_id=invocation_id,
            command=self._command,
            cwd=cwd,
            artifact_dir=artifact_dir,
            prompt=context_bundle.prompt,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            outcome_path=outcome_path,
            context_path=context_path,
            structured_output_path=structured_output_path,
            timeout_seconds=issue_contract.timeouts.command_seconds,
        )

    def execute(self, prepared_invocation: PreparedInvocation) -> EngineOutcome:
        started_at = datetime.now(timezone.utc)
        try:
            completed = subprocess.run(
                prepared_invocation.command,
                cwd=prepared_invocation.cwd,
                capture_output=True,
                text=True,
                check=False,
                input=prepared_invocation.prompt,
                timeout=prepared_invocation.timeout_seconds,
            )
        except OSError as error:
            return self._finalize(
                _ExecutionResult(
                    prepared=prepared_invocation,
                    completed=None,
                    started_at=started_at,
                    ended_at=datetime.now(timezone.utc),
                    engine_error_type="environment_error",
                    environment_error=str(error),
                )
            )
        except subprocess.TimeoutExpired as error:
            prepared_invocation.stdout_path.write_text(_text_or_empty(error.stdout))
            prepared_invocation.stderr_path.write_text(_text_or_empty(error.stderr))
            return self._finalize(
                _ExecutionResult(
                    prepared=prepared_invocation,
                    completed=None,
                    started_at=started_at,
                    ended_at=datetime.now(timezone.utc),
                    engine_error_type="engine_timeout",
                    timeout=True,
                )
            )

        prepared_invocation.stdout_path.write_text(completed.stdout or "")
        prepared_invocation.stderr_path.write_text(completed.stderr or "")
        _write_structured_output(prepared_invocation, completed.stdout)
        return self._finalize(
            _ExecutionResult(
                prepared=prepared_invocation,
                completed=completed,
                started_at=started_at,
                ended_at=datetime.now(timezone.utc),
            )
        )

    def normalize_output(self, raw_result: object) -> EngineOutcome:
        if isinstance(raw_result, EngineOutcome):
            return raw_result

        if isinstance(raw_result, _ExecutionResult):
            return self._normalize_execution_result(raw_result)

        raise TypeError("unsupported raw_result for ClaudeCodeAdapter normalization")

    def _finalize(self, execution_result: _ExecutionResult) -> EngineOutcome:
        outcome = self.normalize_output(execution_result)
        execution_result.prepared.outcome_path.write_text(json.dumps(asdict(outcome), default=str, indent=2))
        return outcome

    def _normalize_execution_result(self, execution_result: _ExecutionResult) -> EngineOutcome:
        prepared = execution_result.prepared
        completed = execution_result.completed

        if execution_result.environment_error is not None:
            return EngineOutcome(
                engine_name=prepared.engine_name,
                engine_invocation_id=prepared.invocation_id,
                outcome_type="environment_error",
                exit_code=None,
                recoverable=True,
                engine_error_type="environment_error",
                summary=execution_result.environment_error,
                stdout_path=str(prepared.stdout_path),
                stderr_path=str(prepared.stderr_path),
                artifact_paths=_artifact_paths(prepared),
                started_at=execution_result.started_at,
                ended_at=execution_result.ended_at,
                duration_ms=_duration_ms(execution_result.started_at, execution_result.ended_at),
            )

        if execution_result.timeout:
            return EngineOutcome(
                engine_name=prepared.engine_name,
                engine_invocation_id=prepared.invocation_id,
                outcome_type="engine_timeout",
                exit_code=None,
                recoverable=True,
                engine_error_type="engine_timeout",
                summary="command timed out",
                stdout_path=str(prepared.stdout_path),
                stderr_path=str(prepared.stderr_path),
                artifact_paths=_artifact_paths(prepared),
                started_at=execution_result.started_at,
                ended_at=execution_result.ended_at,
                duration_ms=_duration_ms(execution_result.started_at, execution_result.ended_at),
            )

        if completed is None:
            raise TypeError("completed process is required when no error was recorded")

        if completed.returncode == 0:
            outcome_type = "success"
            recoverable = False
            summary = "command completed successfully"
        else:
            outcome_type = "engine_crash"
            recoverable = True
            summary = f"command exited with code {completed.returncode}"

        return EngineOutcome(
            engine_name=prepared.engine_name,
            engine_invocation_id=prepared.invocation_id,
            outcome_type=outcome_type,
            exit_code=completed.returncode,
            recoverable=recoverable,
            summary=summary,
            stdout_path=str(prepared.stdout_path),
            stderr_path=str(prepared.stderr_path),
            artifact_paths=_artifact_paths(prepared),
            started_at=execution_result.started_at,
            ended_at=execution_result.ended_at,
            duration_ms=_duration_ms(execution_result.started_at, execution_result.ended_at),
        )


def _artifact_paths(prepared: PreparedInvocation) -> tuple[str, ...]:
    artifact_paths: list[str] = []
    if prepared.context_path is not None:
        artifact_paths.append(str(prepared.context_path))
    artifact_paths.append(str(prepared.stdout_path))
    artifact_paths.append(str(prepared.stderr_path))
    if prepared.structured_output_path is not None and prepared.structured_output_path.exists():
        artifact_paths.append(str(prepared.structured_output_path))
    artifact_paths.append(str(prepared.outcome_path))
    return tuple(artifact_paths)


def _write_structured_output(prepared: PreparedInvocation, stdout: str | None) -> None:
    if prepared.structured_output_path is None or not stdout:
        return

    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        return

    prepared.structured_output_path.write_text(json.dumps(payload, indent=2))


def _text_or_empty(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode()
    return value


def _duration_ms(started_at: datetime, ended_at: datetime) -> int:
    return int((ended_at - started_at).total_seconds() * 1000)


def _workspace_path(workspace: object) -> Path:
    if isinstance(workspace, Path):
        return workspace

    if isinstance(workspace, str):
        return Path(workspace)

    candidate = getattr(workspace, "worktree_path", None)
    if candidate is not None:
        return Path(candidate)

    candidate = getattr(workspace, "path", None)
    if candidate is not None:
        return Path(candidate)

    raise TypeError("workspace must be a path or expose worktree_path")
