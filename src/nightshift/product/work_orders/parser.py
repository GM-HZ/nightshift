from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import yaml

from nightshift.product.work_orders.models import WorkOrderFrontmatter


class WorkOrderParseError(ValueError):
    """Raised when a markdown work order cannot be parsed."""


@dataclass(frozen=True, slots=True)
class ParsedWorkOrder:
    frontmatter: WorkOrderFrontmatter
    body: str


def parse_work_order_markdown(markdown: str) -> ParsedWorkOrder:
    frontmatter_text, body = _split_frontmatter(markdown)

    try:
        raw_frontmatter = yaml.safe_load(frontmatter_text)
    except yaml.YAMLError as exc:
        raise WorkOrderParseError("work order frontmatter contains malformed YAML") from exc

    if raw_frontmatter is None:
        raw_frontmatter = {}

    if not isinstance(raw_frontmatter, Mapping):
        raise WorkOrderParseError("work order frontmatter must be a mapping")

    return ParsedWorkOrder(frontmatter=WorkOrderFrontmatter.model_validate(raw_frontmatter), body=body)


def _split_frontmatter(markdown: str) -> tuple[str, str]:
    lines = markdown.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise WorkOrderParseError("work order markdown is missing frontmatter")

    closing_index = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            closing_index = index
            break

    if closing_index is None:
        raise WorkOrderParseError("work order frontmatter is missing a closing delimiter")

    frontmatter_text = "".join(lines[1:closing_index])
    body = "".join(lines[closing_index + 1 :])
    return frontmatter_text, body
