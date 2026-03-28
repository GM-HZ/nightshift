from __future__ import annotations

from pathlib import Path

import yaml

from .models import NightShiftConfig


def load_config(path: Path) -> NightShiftConfig:
    data = yaml.safe_load(path.read_text()) or {}
    return NightShiftConfig.model_validate(data)
