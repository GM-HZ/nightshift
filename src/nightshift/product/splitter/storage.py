from __future__ import annotations

from pathlib import Path

from nightshift.store.filesystem import read_model_json, safe_path_component, write_model_json

from .models import ProposalBatch


class ProposalStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def save_batch(self, batch: ProposalBatch) -> None:
        path = self._batch_path(batch.batch_id)
        if path.exists():
            existing = read_model_json(path, ProposalBatch)
            if existing == batch:
                return
            raise ValueError(f"proposal batch already exists for batch_id={batch.batch_id}")
        write_model_json(path, batch)

    def load_batch(self, batch_id: str) -> ProposalBatch:
        return read_model_json(self._batch_path(batch_id), ProposalBatch)

    def replace_batch(self, batch: ProposalBatch) -> None:
        write_model_json(self._batch_path(batch.batch_id), batch)

    def list_batches(self) -> list[ProposalBatch]:
        batches: list[ProposalBatch] = []
        if not self._batches_dir().exists():
            return batches
        for path in sorted(self._batches_dir().glob("*/batch.json")):
            batches.append(read_model_json(path, ProposalBatch))
        return batches

    def _batches_dir(self) -> Path:
        return self.root / "nightshift-data" / "proposals"

    def _batch_path(self, batch_id: str) -> Path:
        safe_batch_id = safe_path_component(batch_id, field_name="batch_id")
        return self._batches_dir() / safe_batch_id / "batch.json"
