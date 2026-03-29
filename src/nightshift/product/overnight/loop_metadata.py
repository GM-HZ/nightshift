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
    created_at: datetime
    updated_at: datetime
