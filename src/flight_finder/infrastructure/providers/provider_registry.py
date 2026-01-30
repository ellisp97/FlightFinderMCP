from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from flight_finder.domain.protocols.flight_provider import IFlightProvider

logger = structlog.get_logger()


@dataclass
class ProviderMetadata:
    provider: IFlightProvider
    priority: int = 0
    enabled: bool = True
    weight: float = 1.0


class ProviderRegistry:
    """Registry for managing multiple flight providers.

    Providers are registered with priority and can be enabled/disabled.
    """

    def __init__(self) -> None:
        self._providers: dict[str, ProviderMetadata] = {}
        self._logger = logger.bind(component="provider_registry")

    def register(
        self,
        provider: IFlightProvider,
        priority: int = 0,
        enabled: bool = True,
        weight: float = 1.0,
    ) -> None:
        name = provider.provider_name

        if name in self._providers:
            self._logger.warning("provider_already_registered", name=name)
            return

        self._providers[name] = ProviderMetadata(
            provider=provider,
            priority=priority,
            enabled=enabled,
            weight=weight,
        )

        self._logger.info(
            "provider_registered",
            name=name,
            priority=priority,
            enabled=enabled,
        )

    def get(self, name: str) -> IFlightProvider | None:
        metadata = self._providers.get(name)
        return metadata.provider if metadata else None

    def get_all(self) -> list[IFlightProvider]:
        return [m.provider for m in self._providers.values()]

    def get_enabled(self) -> list[IFlightProvider]:
        return [m.provider for m in self._providers.values() if m.enabled]

    def get_by_priority(self, limit: int | None = None) -> list[IFlightProvider]:
        sorted_metadata = sorted(
            [m for m in self._providers.values() if m.enabled],
            key=lambda m: m.priority,
            reverse=True,
        )

        providers = [m.provider for m in sorted_metadata]

        if limit:
            return providers[:limit]

        return providers

    def enable(self, name: str) -> None:
        if name in self._providers:
            self._providers[name].enabled = True
            self._logger.info("provider_enabled", name=name)

    def disable(self, name: str) -> None:
        if name in self._providers:
            self._providers[name].enabled = False
            self._logger.info("provider_disabled", name=name)

    def is_enabled(self, name: str) -> bool:
        metadata = self._providers.get(name)
        return metadata.enabled if metadata else False

    def count_enabled(self) -> int:
        return sum(1 for m in self._providers.values() if m.enabled)

    def get_status(self) -> dict[str, dict]:
        return {
            name: {
                "enabled": m.enabled,
                "priority": m.priority,
                "weight": m.weight,
            }
            for name, m in self._providers.items()
        }
