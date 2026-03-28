from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ContextBundle:
    issue_id: str
    prompt: str
    artifact_dir: Path
    worktree_path: Path
    run_id: str | None = None
    attempt_id: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)

