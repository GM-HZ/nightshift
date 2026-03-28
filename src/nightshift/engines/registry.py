from __future__ import annotations

from collections.abc import Iterable

from nightshift.domain.contracts import IssueContract

from .base import EngineAdapter


class EngineRegistry:
    def __init__(
        self,
        adapters: Iterable[EngineAdapter] | None = None,
        *,
        default_adapter_name: str | None = None,
        fallback_adapter_name: str | None = None,
    ) -> None:
        self._adapters: dict[str, EngineAdapter] = {}
        self._default_adapter_name = default_adapter_name
        self._fallback_adapter_name = fallback_adapter_name
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
        has_explicit_preference = any(preference is not None for preference in preferences)
        for preference in preferences:
            if preference is not None and preference in self._adapters:
                return self._adapters[preference]

        if has_explicit_preference:
            raise LookupError("no registered adapter satisfies the issue engine preferences")

        if self._default_adapter_name is not None and self._default_adapter_name in self._adapters:
            return self._adapters[self._default_adapter_name]

        if self._adapters:
            default_name = sorted(self._adapters)[0]
            return self._adapters[default_name]

        raise LookupError("no engine adapters have been registered")

    def is_fallback_eligible(self, issue_contract: IssueContract, current_adapter: EngineAdapter) -> bool:
        return self.fallback_for(issue_contract, current_adapter) is not None

    def fallback_for(self, issue_contract: IssueContract, current_adapter: EngineAdapter) -> EngineAdapter | None:
        configured_names: tuple[str | None, ...] = (
            issue_contract.engine_preferences.fallback,
            self._fallback_adapter_name,
        )
        for fallback_name in configured_names:
            if fallback_name is None or fallback_name == current_adapter.name():
                continue
            adapter = self._adapters.get(fallback_name)
            if adapter is not None:
                return adapter
        return None
