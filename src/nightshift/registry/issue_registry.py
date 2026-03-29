from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from nightshift.domain import AttemptState, DeliveryState, IssueKind, IssueState
from nightshift.domain.contracts import IssueContract
from nightshift.domain.records import IssueRecord
from nightshift.store.filesystem import (
    read_model_json,
    read_model_yaml,
    safe_path_component,
    write_model_json,
    write_model_yaml,
)


class IssueRegistry:
    _QUEUE_PRIORITY_ORDER = {
        "urgent": 0,
        "high": 1,
        "medium": 2,
        "normal": 2,
        "low": 3,
    }

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def save_contract(self, issue_contract: IssueContract) -> None:
        path = self._contract_path(issue_contract.issue_id)
        if path.exists():
            existing = read_model_yaml(path, IssueContract)
            if existing == issue_contract:
                return
            if not existing.work_order_revision or not issue_contract.work_order_revision:
                raise ValueError(f"contract already exists for issue_id={issue_contract.issue_id}")
            if existing.work_order_revision == issue_contract.work_order_revision:
                raise ValueError(
                    f"contract revision already exists for issue_id={issue_contract.issue_id} "
                    f"revision={issue_contract.work_order_revision}"
                )

        self._write_contract_revision(issue_contract)
        write_model_yaml(path, issue_contract)

    def get_contract(self, issue_id: str) -> IssueContract:
        return read_model_yaml(self._contract_path(issue_id), IssueContract)

    def list_contracts(self, kind: IssueKind | str | None = None) -> list[IssueContract]:
        contracts: list[IssueContract] = []
        for path in sorted(self._contracts_dir().glob("*.yaml")):
            contract = read_model_yaml(path, IssueContract)
            if kind is None or contract.kind == IssueKind(kind):
                contracts.append(contract)
        return contracts

    def list_contract_revisions(self, issue_id: str) -> list[IssueContract]:
        revisions_dir = self._contract_revisions_dir(issue_id)
        if not revisions_dir.exists():
            return []
        return [read_model_yaml(path, IssueContract) for path in sorted(revisions_dir.glob("*.yaml"))]

    def save_record(self, issue_record: IssueRecord) -> None:
        write_model_json(self._record_path(issue_record.issue_id), issue_record)

    def get_record(self, issue_id: str) -> IssueRecord:
        return read_model_json(self._record_path(issue_id), IssueRecord)

    def list_schedulable_records(self) -> list[IssueRecord]:
        records = [record for record in self._all_records() if record.issue_state == IssueState.ready]
        return sorted(
            records,
            key=lambda record: (
                self._QUEUE_PRIORITY_ORDER.get(record.queue_priority, len(self._QUEUE_PRIORITY_ORDER)),
                record.queue_priority,
                record.issue_id,
            ),
        )

    def set_queue_priority(self, issue_id: str, queue_priority: str) -> IssueRecord:
        updated = self._validated_update(issue_id, {"queue_priority": queue_priority, "updated_at": self._now()})
        self.save_record(updated)
        return updated

    def attach_attempt(self, issue_id: str, attempt_id: str, attempt_state: AttemptState, run_id: str) -> IssueRecord:
        updated = self._validated_update(
            issue_id,
            {
                "latest_attempt_id": attempt_id,
                "current_run_id": run_id,
                "attempt_state": attempt_state,
                "issue_state": IssueState.running,
                "updated_at": self._now(),
            },
        )
        self.save_record(updated)
        return updated

    def attach_delivery(
        self,
        issue_id: str,
        delivery_state: DeliveryState,
        delivery_id: str | None = None,
        delivery_ref: str | None = None,
    ) -> IssueRecord:
        updated = self._validated_update(
            issue_id,
            {
                "delivery_state": delivery_state,
                "delivery_id": delivery_id,
                "delivery_ref": delivery_ref,
                "updated_at": self._now(),
            },
        )
        self.save_record(updated)
        return updated

    def _all_records(self) -> list[IssueRecord]:
        if not self._records_dir().exists():
            return []
        return [read_model_json(path, IssueRecord) for path in sorted(self._records_dir().glob("*.json"))]

    def _contracts_dir(self) -> Path:
        return self.root / "nightshift" / "issues"

    def _records_dir(self) -> Path:
        return self.root / "nightshift-data" / "issue-records"

    def _contract_revisions_root(self) -> Path:
        return self.root / "nightshift" / "contracts"

    def _contract_path(self, issue_id: str) -> Path:
        safe_issue_id = safe_path_component(issue_id, field_name="issue_id")
        return self._contracts_dir() / f"{safe_issue_id}.yaml"

    def _record_path(self, issue_id: str) -> Path:
        safe_issue_id = safe_path_component(issue_id, field_name="issue_id")
        return self._records_dir() / f"{safe_issue_id}.json"

    def _contract_revisions_dir(self, issue_id: str) -> Path:
        safe_issue_id = safe_path_component(issue_id, field_name="issue_id")
        return self._contract_revisions_root() / safe_issue_id

    def _write_contract_revision(self, issue_contract: IssueContract) -> None:
        revision = issue_contract.work_order_revision
        if not revision:
            return

        revisions_dir = self._contract_revisions_dir(issue_contract.issue_id)
        existing_paths = sorted(revisions_dir.glob("*.yaml")) if revisions_dir.exists() else []
        for path in existing_paths:
            existing = read_model_yaml(path, IssueContract)
            if existing == issue_contract:
                return
            if existing.work_order_revision == revision:
                raise ValueError(
                    f"contract revision already exists for issue_id={issue_contract.issue_id} revision={revision}"
                )

        sequence = len(existing_paths) + 1
        safe_revision = safe_path_component(revision, field_name="work_order_revision")
        write_model_yaml(revisions_dir / f"{sequence:04d}-{safe_revision}.yaml", issue_contract)

    def _validated_update(self, issue_id: str, update: dict[str, object]) -> IssueRecord:
        record = self.get_record(issue_id)
        payload = record.model_dump(mode="json")
        payload.update(update)
        return IssueRecord.model_validate(payload)

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)
