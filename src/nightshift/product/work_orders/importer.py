from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from nightshift.config.models import NightShiftConfig
from nightshift.domain import AttemptState, DeliveryState, IssueState
from nightshift.domain.records import IssueRecord
from nightshift.product.work_orders.materialize import (
    WorkOrderMaterializationError,
    WorkOrderMaterializationProvenance,
    materialize_work_order,
)
from nightshift.product.work_orders.parser import WorkOrderParseError, parse_work_order_markdown


class WorkOrderImportError(ValueError):
    """Raised when a work order cannot be imported into issue storage."""


@dataclass(frozen=True, slots=True)
class WorkOrderImportResult:
    issue_id: str
    work_order_id: str
    record_created: bool


def import_work_order(
    issue_registry: object,
    *,
    config: NightShiftConfig,
    work_order_path: Path,
    repo_root: Path,
) -> WorkOrderImportResult:
    markdown = work_order_path.read_text()
    revision = hashlib.sha256(markdown.encode("utf-8")).hexdigest()

    try:
        parsed = parse_work_order_markdown(markdown)
    except WorkOrderParseError as exc:
        raise WorkOrderImportError(f"failed to parse work order: {exc}") from exc

    if parsed.frontmatter.status != "approved":
        raise WorkOrderImportError("only approved work orders can be imported")

    try:
        relative_path = work_order_path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError as exc:
        raise WorkOrderImportError("work order path must be inside repo root") from exc

    try:
        contract = materialize_work_order(
            parsed,
            config,
            WorkOrderMaterializationProvenance(
                work_order_path=relative_path,
                work_order_revision=revision,
            ),
        )
    except (WorkOrderMaterializationError, ValueError) as exc:
        raise WorkOrderImportError(f"failed to materialize work order: {exc}") from exc

    issue_registry.save_contract(contract)

    try:
        issue_registry.get_record(contract.issue_id)
        record_created = False
    except FileNotFoundError:
        now = datetime.now(timezone.utc)
        issue_registry.save_record(
            IssueRecord.from_contract(
                contract,
                issue_state=IssueState.draft,
                attempt_state=AttemptState.pending,
                delivery_state=DeliveryState.none,
                created_at=now,
                updated_at=now,
            )
        )
        record_created = True

    return WorkOrderImportResult(
        issue_id=contract.issue_id,
        work_order_id=parsed.frontmatter.work_order_id,
        record_created=record_created,
    )
