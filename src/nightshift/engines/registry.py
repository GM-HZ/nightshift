from __future__ import annotations

from collections.abc import Iterable

from nightshift.domain.contracts import IssueContract

from .base import EngineAdapter


class EngineRegistry:
    def __init__(self, adapters: Iterable[EngineAdapter] | None = None) -> None:
        self._adapters: dict[str, EngineAdapter] = {}
        if adapters is not None:
            for adapter in adapters:
                self.register(adapter)

    def register(self, adapter: EngineAdapter) -> None:
        self._adapters[adapter.name()] = adapter

    def resolve(self, issue_contract: IssueContract) -> EngineAdapter:
        preferences = (
            issue_contract.engine_preferences.primary,
            issue_contract.engine_preferences.fallback,
        )
        for preference in preferences:
            if preference is not None and preference in self._adapters:
                return self._adapters[preference]

        if self._adapters:
            default_name = sorted(self._adapters)[0]
            return self._adapters[default_name]

        raise LookupError("no engine adapters have been registered")

    def is_fallback_eligible(self, issue_contract: IssueContract, current_adapter: EngineAdapter) -> bool:
        fallback_name = issue_contract.engine_preferences.fallback
        if fallback_name is None:
            return False

        if fallback_name == current_adapter.name():
            return False

        return fallback_name in self._adapters
