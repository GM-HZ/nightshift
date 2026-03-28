import pytest
from pydantic import ValidationError

from nightshift.product.delivery.models import DeliveryBatchResult, DeliveryRequest, DeliveryResult


def test_delivery_request_requires_non_empty_issue_ids() -> None:
    with pytest.raises(ValidationError):
        DeliveryRequest(issue_ids=())


def test_delivery_request_trims_issue_ids() -> None:
    request = DeliveryRequest(issue_ids=(" GH-7 ",))

    assert request.issue_ids == ("GH-7",)


def test_delivery_result_requires_known_state() -> None:
    result = DeliveryResult(issue_id="GH-7", delivery_state="submitted", delivery_ref="https://example.com/pr/1")

    assert result.issue_id == "GH-7"
    assert result.delivery_state == "submitted"


def test_delivery_batch_result_counts_delivered_and_failed() -> None:
    batch = DeliveryBatchResult(
        results=(
            DeliveryResult(issue_id="GH-7", delivery_state="submitted", delivery_ref="https://example.com/pr/1"),
            DeliveryResult(issue_id="GH-8", delivery_state="failed", reason="push failed"),
        )
    )

    assert batch.delivered_issue_ids == ("GH-7",)
    assert batch.failed_issue_ids == ("GH-8",)
