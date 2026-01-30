"""Tests for ProviderRegistry."""

from __future__ import annotations

import sys


class MockLogger:
    def bind(self, **kwargs):
        return self

    def debug(self, *args, **kwargs):
        pass

    def info(self, *args, **kwargs):
        pass

    def warning(self, *args, **kwargs):
        pass

    def error(self, *args, **kwargs):
        pass


class MockStructlog:
    BoundLogger = MockLogger

    @staticmethod
    def get_logger():
        return MockLogger()


# Must set BEFORE inserting path
sys.modules["structlog"] = MockStructlog()
sys.path.insert(0, "src")

# Import directly from the module file to avoid __init__.py cascade
import importlib.util
spec = importlib.util.spec_from_file_location(
    "provider_registry",
    "src/flight_finder/infrastructure/providers/provider_registry.py"
)
provider_registry_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(provider_registry_module)
ProviderRegistry = provider_registry_module.ProviderRegistry
ProviderMetadata = provider_registry_module.ProviderMetadata


class MockProvider:
    def __init__(self, name: str):
        self._name = name

    @property
    def provider_name(self) -> str:
        return self._name


def test_register_provider():
    registry = ProviderRegistry()
    provider = MockProvider("test_provider")

    registry.register(provider, priority=50)

    assert registry.get("test_provider") is provider
    assert len(registry.get_all()) == 1


def test_register_duplicate_skipped():
    registry = ProviderRegistry()
    provider1 = MockProvider("test_provider")
    provider2 = MockProvider("test_provider")

    registry.register(provider1, priority=50)
    registry.register(provider2, priority=60)

    # Should still have only one provider (first one)
    assert registry.get("test_provider") is provider1
    assert len(registry.get_all()) == 1


def test_get_nonexistent_returns_none():
    registry = ProviderRegistry()

    assert registry.get("nonexistent") is None


def test_get_all_providers():
    registry = ProviderRegistry()
    provider1 = MockProvider("provider1")
    provider2 = MockProvider("provider2")

    registry.register(provider1)
    registry.register(provider2)

    all_providers = registry.get_all()
    assert len(all_providers) == 2
    assert provider1 in all_providers
    assert provider2 in all_providers


def test_get_enabled_providers():
    registry = ProviderRegistry()
    provider1 = MockProvider("provider1")
    provider2 = MockProvider("provider2")

    registry.register(provider1, enabled=True)
    registry.register(provider2, enabled=False)

    enabled = registry.get_enabled()
    assert len(enabled) == 1
    assert provider1 in enabled


def test_get_by_priority():
    registry = ProviderRegistry()
    low = MockProvider("low_priority")
    high = MockProvider("high_priority")
    medium = MockProvider("medium_priority")

    registry.register(low, priority=10)
    registry.register(high, priority=90)
    registry.register(medium, priority=50)

    sorted_providers = registry.get_by_priority()

    assert len(sorted_providers) == 3
    assert sorted_providers[0].provider_name == "high_priority"
    assert sorted_providers[1].provider_name == "medium_priority"
    assert sorted_providers[2].provider_name == "low_priority"


def test_get_by_priority_with_limit():
    registry = ProviderRegistry()
    low = MockProvider("low_priority")
    high = MockProvider("high_priority")
    medium = MockProvider("medium_priority")

    registry.register(low, priority=10)
    registry.register(high, priority=90)
    registry.register(medium, priority=50)

    sorted_providers = registry.get_by_priority(limit=2)

    assert len(sorted_providers) == 2
    assert sorted_providers[0].provider_name == "high_priority"
    assert sorted_providers[1].provider_name == "medium_priority"


def test_enable_disable_provider():
    registry = ProviderRegistry()
    provider = MockProvider("test_provider")

    registry.register(provider, enabled=True)
    assert registry.is_enabled("test_provider") is True

    registry.disable("test_provider")
    assert registry.is_enabled("test_provider") is False

    registry.enable("test_provider")
    assert registry.is_enabled("test_provider") is True


def test_count_enabled():
    registry = ProviderRegistry()
    provider1 = MockProvider("provider1")
    provider2 = MockProvider("provider2")
    provider3 = MockProvider("provider3")

    registry.register(provider1, enabled=True)
    registry.register(provider2, enabled=True)
    registry.register(provider3, enabled=False)

    assert registry.count_enabled() == 2


def test_get_status():
    registry = ProviderRegistry()
    provider = MockProvider("test_provider")

    registry.register(provider, priority=75, enabled=True, weight=0.8)

    status = registry.get_status()

    assert "test_provider" in status
    assert status["test_provider"]["enabled"] is True
    assert status["test_provider"]["priority"] == 75
    assert status["test_provider"]["weight"] == 0.8


def test_disabled_provider_excluded_from_priority_list():
    registry = ProviderRegistry()
    provider1 = MockProvider("enabled_provider")
    provider2 = MockProvider("disabled_provider")

    registry.register(provider1, priority=50, enabled=True)
    registry.register(provider2, priority=90, enabled=False)

    sorted_providers = registry.get_by_priority()

    assert len(sorted_providers) == 1
    assert sorted_providers[0].provider_name == "enabled_provider"


def run_tests():
    print("Testing ProviderRegistry...")

    test_register_provider()
    print("  ✓ test_register_provider")

    test_register_duplicate_skipped()
    print("  ✓ test_register_duplicate_skipped")

    test_get_nonexistent_returns_none()
    print("  ✓ test_get_nonexistent_returns_none")

    test_get_all_providers()
    print("  ✓ test_get_all_providers")

    test_get_enabled_providers()
    print("  ✓ test_get_enabled_providers")

    test_get_by_priority()
    print("  ✓ test_get_by_priority")

    test_get_by_priority_with_limit()
    print("  ✓ test_get_by_priority_with_limit")

    test_enable_disable_provider()
    print("  ✓ test_enable_disable_provider")

    test_count_enabled()
    print("  ✓ test_count_enabled")

    test_get_status()
    print("  ✓ test_get_status")

    test_disabled_provider_excluded_from_priority_list()
    print("  ✓ test_disabled_provider_excluded_from_priority_list")

    print("\nAll ProviderRegistry tests passed!")


if __name__ == "__main__":
    run_tests()
