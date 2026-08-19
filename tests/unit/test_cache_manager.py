import os
import logging
import time
from pathlib import Path
from tempfile import TemporaryDirectory

from tooluniverse.cache.result_cache_manager import ResultCacheManager
from tooluniverse.cache import result_cache_manager


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


def test_default_persistence_failure_falls_back_without_warning(monkeypatch, caplog):
    monkeypatch.setattr(
        result_cache_manager,
        "PersistentCache",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("read only")),
    )
    caplog.set_level(logging.WARNING)

    manager = ResultCacheManager(
        persistent_path="/default/cache.sqlite",
        warn_on_persistence_error=False,
    )
    try:
        assert manager.persistent is None
        assert "Failed to initialize persistent cache" not in caplog.text
    finally:
        manager.close()


def test_explicit_persistence_failure_remains_actionable(monkeypatch, caplog):
    monkeypatch.setattr(
        result_cache_manager,
        "PersistentCache",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("read only")),
    )
    caplog.set_level(logging.WARNING)

    manager = ResultCacheManager(
        persistent_path="/configured/cache.sqlite",
        warn_on_persistence_error=True,
    )
    try:
        assert manager.persistent is None
        assert "using memory only" in caplog.text
    finally:
        manager.close()
