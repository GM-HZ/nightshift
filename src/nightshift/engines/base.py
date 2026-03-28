from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class EngineCapabilities:
    supports_streaming_output: bool = False
    supports_structured_result: bool = False
    supports_patch_artifact: bool = False
    supports_resume: bool = False
    supports_noninteractive_mode: bool = False
    supports_worktree_execution: bool = False
    supports_file_scope_constraints: bool = False
    supports_timeout_enforcement: bool = False
    supports_json_output_hint: bool = False


@dataclass(frozen=True, slots=True)
class PreparedInvocation:
    engine_name: str
    invocation_id: str
    command: tuple[str, ...]
    cwd: Path
    artifact_dir: Path
    prompt: str
    stdout_path: Path
    stderr_path: Path
    outcome_path: Path
    context_path: Path | None = None
    env: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class EngineOutcome:
    engine_name: str
    engine_invocation_id: str
    outcome_type: str
    exit_code: int | None = None
    recoverable: bool = False
    engine_error_type: str | None = None
    summary: str = ""
    stdout_path: str | None = None
    stderr_path: str | None = None
    artifact_paths: tuple[str, ...] = ()
    started_at: datetime | None = None
    ended_at: datetime | None = None
    duration_ms: int | None = None


@runtime_checkable
class EngineAdapter(Protocol):
    def name(self) -> str: ...

    def capabilities(self) -> EngineCapabilities: ...

    def prepare(self, issue_contract: object, workspace: object, context_bundle: object) -> PreparedInvocation: ...

    def execute(self, prepared_invocation: PreparedInvocation) -> EngineOutcome: ...

    def normalize_output(self, raw_result: object) -> EngineOutcome: ...

