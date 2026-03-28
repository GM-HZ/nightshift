from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from nightshift.domain import AttemptState, DeliveryState, IssueKind, IssueState
from nightshift.domain.contracts import IssueContract
from nightshift.domain.records import IssueRecord
from nightshift.store.filesystem import read_model_yaml, write_model_yaml, read_model_json, write_model_json


class IssueRegistry:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def save_contract(self, issue_contract: IssueContract) -> None:
        write_model_yaml(self._contract_path(issue_contract.issue_id), issue_contract)

    def get_contract(self, issue_id: str) -> IssueContract:
        return read_model_yaml(self._contract_path(issue_id), IssueContract)

    def list_contracts(self, kind: IssueKind | str | None = None) -> list[IssueContract]:
        contracts: list[IssueContract] = []
        for path in sorted(self._contracts_dir().glob("*.yaml")):
            contract = read_model_yaml(path, IssueContract)
            if kind is None or contract.kind == IssueKind(kind):
                contracts.append(contract)
        return contracts

    def save_record(self, issue_record: IssueRecord) -> None:
        write_model_json(self._record_path(issue_record.issue_id), issue_record)

    def get_record(self, issue_id: str) -> IssueRecord:
        return read_model_json(self._record_path(issue_id), IssueRecord)

    def list_schedulable_records(self) -> list[IssueRecord]:
        records = [record for record in self._all_records() if record.issue_state == IssueState.ready]
        return sorted(records, key=lambda record: (record.queue_priority, record.issue_id))

    def set_queue_priority(self, issue_id: str, queue_priority: str) -> IssueRecord:
        record = self.get_record(issue_id)
        updated = record.model_copy(update={"queue_priority": queue_priority, "updated_at": self._now()})
        self.save_record(updated)
        return updated

    def attach_attempt(self, issue_id: str, attempt_id: str, attempt_state: AttemptState, run_id: str) -> IssueRecord:
        record = self.get_record(issue_id)
        updated = record.model_copy(
            update={
                "latest_attempt_id": attempt_id,
                "current_run_id": run_id,
                "attempt_state": attempt_state,
                "issue_state": IssueState.running,
                "updated_at": self._now(),
            }
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
        record = self.get_record(issue_id)
        updated = record.model_copy(
            update={
                "delivery_state": delivery_state,
                "delivery_id": delivery_id,
                "delivery_ref": delivery_ref,
                "updated_at": self._now(),
            }
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

    def _contract_path(self, issue_id: str) -> Path:
        return self._contracts_dir() / f"{issue_id}.yaml"

    def _record_path(self, issue_id: str) -> Path:
        return self._records_dir() / f"{issue_id}.json"

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

