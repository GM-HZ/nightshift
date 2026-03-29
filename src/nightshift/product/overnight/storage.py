from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from nightshift.config.models import ResolvedRuntimeStorage
from nightshift.store.filesystem import read_json, read_model_json, safe_path_component, write_json, write_model_json

from .loop_metadata import DaemonLoopMetadata


class OvernightLoopMetadataStore:
    def __init__(self, runtime_storage: ResolvedRuntimeStorage) -> None:
        self.runtime_storage = runtime_storage

    def save(self, metadata: DaemonLoopMetadata) -> None:
        write_model_json(self._metadata_path(metadata.run_id), metadata)

    def load(self, run_id: str) -> DaemonLoopMetadata:
        return read_model_json(self._metadata_path(run_id), DaemonLoopMetadata)

    def request_stop(self, run_id: str) -> DaemonLoopMetadata:
        metadata = self.load(run_id)
        payload = metadata.model_dump(mode="json")
        payload.update(
            {
                "stop_requested": True,
                "stopped_reason": "user_stop",
                "updated_at": datetime.now(timezone.utc),
            }
        )
        updated = DaemonLoopMetadata.model_validate(payload)
        self.save(updated)
        return updated

    def set_active_run(self, run_id_or_none: str | None) -> None:
        write_json(self._active_marker_path(), {"run_id": run_id_or_none})

    def get_active_run(self) -> str | None:
        if not self._active_marker_path().exists():
            return None
        payload = read_json(self._active_marker_path())
        if payload is None:
            return None
        return payload.get("run_id")

    def _metadata_path(self, run_id: str) -> Path:
        safe_run_id = safe_path_component(run_id, field_name="run_id")
        return self.runtime_storage.runs_root / safe_run_id / "daemon-loop.json"

    def _active_marker_path(self) -> Path:
        return self.runtime_storage.records_root.parent / "active-daemon.json"
