import os
import time
from pathlib import Path
from tempfile import TemporaryDirectory

from tooluniverse.cache.result_cache_manager import ResultCacheManager


def test_memory_cache_roundtrip(memory_cache_manager):
    """Memory cache stores and retrieves values correctly."""
    memory_cache_manager.set(
        namespace="tool", version="v1", cache_key="key", value={"data": 123},
    )
    result = memory_cache_manager.get(namespace="tool", version="v1", cache_key="key")
    assert result == {"data": 123}


def test_cache_ttl_expiration(memory_cache_manager):
    """Cache entries expire after their TTL elapses."""
    memory_cache_manager.set(
        namespace="tool", version="v1", cache_key="expire", value=42, ttl=1,
    )
    assert memory_cache_manager.get(namespace="tool", version="v1", cache_key="expire") == 42
    time.sleep(1.1)
    assert memory_cache_manager.get(namespace="tool", version="v1", cache_key="expire") is None


def test_persistent_cache_survives_restart(tmp_path):
    """Data persisted to SQLite is available after a manager restart."""
    cache_path = str(tmp_path / "cache.sqlite")

    manager1 = ResultCacheManager(
        memory_size=2, persistent_path=cache_path,
        enabled=True, persistence_enabled=True, singleflight=False,
    )
    manager1.set(namespace="tool", version="v1", cache_key="persist", value={"foo": "bar"})
    manager1.close()

    manager2 = ResultCacheManager(
        memory_size=1, persistent_path=cache_path,
        enabled=True, persistence_enabled=True, singleflight=False,
    )
    persisted = manager2.get(namespace="tool", version="v1", cache_key="persist")
    assert persisted == {"foo": "bar"}
    manager2.close()
