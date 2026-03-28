from __future__ import annotations

from pathlib import Path

import yaml

from .models import NightShiftConfig


def load_config(path: Path) -> NightShiftConfig:
    data = yaml.safe_load(path.read_text())
    if data is None:
        data = {}
    elif not isinstance(data, dict):
        raise ValueError("nightshift config root must be a mapping")

    return NightShiftConfig.model_validate(data)
