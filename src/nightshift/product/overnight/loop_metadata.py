from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DaemonLoopMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    loop_mode: str = "daemon"
    fail_fast: bool = True
    stop_requested: bool = False
    stopped_reason: str | None = None
    issues_attempted: int = 0
    issues_completed: int = 0
    last_issue_id: str | None = None
    last_run_id: str | None = None
    failed_issue_id: str | None = None
    created_at: datetime
    updated_at: datetime
