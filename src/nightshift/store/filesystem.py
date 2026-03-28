from __future__ import annotations

import json
from tempfile import NamedTemporaryFile
from pathlib import Path
from typing import Any, TypeVar

import yaml
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text())


def write_json(path: Path, payload: Any) -> None:
    ensure_parent(path)
    _atomic_write_text(path, json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n")


def read_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text())


def write_yaml(path: Path, payload: Any) -> None:
    ensure_parent(path)
    _atomic_write_text(path, yaml.safe_dump(payload, sort_keys=False))


def append_ndjson(path: Path, payload: Any) -> None:
    ensure_parent(path)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True, ensure_ascii=False) + "\n")


def read_ndjson(path: Path) -> list[Any]:
    if not path.exists():
        return []

    payloads: list[Any] = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            payloads.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return payloads


def write_model_json(path: Path, model: BaseModel) -> None:
    write_json(path, model.model_dump(mode="json"))


def read_model_json(path: Path, model_type: type[T]) -> T:
    return model_type.model_validate(read_json(path))


def write_model_yaml(path: Path, model: BaseModel) -> None:
    write_yaml(path, model.model_dump(mode="json"))


def read_model_yaml(path: Path, model_type: type[T]) -> T:
    return model_type.model_validate(read_yaml(path))


def _atomic_write_text(path: Path, contents: str) -> None:
    ensure_parent(path)
    temp_path: Path | None = None
    with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(contents)
        handle.flush()
        temp_path = Path(handle.name)

    try:
        temp_path.replace(path)
    except Exception:
        if temp_path.exists():
            temp_path.unlink()
        raise
