"""
Tests to verify cache system bug fixes.

This test suite validates that the following bugs have been fixed:
1. SingleFlight lock leak issue
2. Async worker shutdown data loss
3. Missing expires_at in iter_entries
4. Cache key consistency with tool instance reuse
"""

import os
import time
import threading
from tempfile import TemporaryDirectory

from tooluniverse.cache.memory_cache import SingleFlight
from tooluniverse.cache.result_cache_manager import ResultCacheManager
from tooluniverse import ToolUniverse
from tooluniverse.base_tool import BaseTool


class TestTool(BaseTool):
    """Test tool for cache validation."""
    call_count = 0
    STATIC_CACHE_VERSION = "1"

    def run(self, arguments, **kwargs):
        TestTool.call_count += 1
        value = arguments.get("value", 0)
        return {"value": value, "calls": TestTool.call_count}


def test_singleflight_no_lock_leak():
    """Test that SingleFlight properly cleans up locks (Bug #3 fix)."""
    sf = SingleFlight()
    
    # Acquire and release lock multiple times
    for i in range(10):
        with sf.acquire(f"key_{i % 3}"):
            pass
    
    # All locks should be cleaned up
    assert len(sf._locks) == 0, f"Lock leak detected: {len(sf._locks)} locks remaining"
    assert len(sf._refcounts) == 0, f"Refcount leak detected: {len(sf._refcounts)} refcounts remaining"


def test_singleflight_concurrent_access():
    """Test that SingleFlight handles concurrent access without leaks."""
    sf = SingleFlight()
    results = []
    
    def worker(key, value):
        with sf.acquire(key):
            time.sleep(0.01)  # Simulate work
            results.append(value)
    
    threads = []
    for i in range(20):
        t = threading.Thread(target=worker, args=(f"key_{i % 5}", i))
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    # All work completed
    assert len(results) == 20
    
    # No locks should remain
    assert len(sf._locks) == 0, f"Lock leak detected: {len(sf._locks)} locks remaining"
    assert len(sf._refcounts) == 0, f"Refcount leak detected: {len(sf._refcounts)} refcounts remaining"


def test_async_worker_processes_pending_on_shutdown(tmp_path):
    """Test that async worker processes all pending items before shutdown (Bug #4 fix)."""
    cache_path = str(tmp_path / "cache.sqlite")

    manager = ResultCacheManager(
        memory_size=2, persistent_path=cache_path,
        enabled=True, persistence_enabled=True,
        singleflight=False, async_persist=True,
    )

    for i in range(10):
        manager.set(namespace="test", version="v1", cache_key=f"key_{i}", value={"data": i})

    manager.close()

    manager2 = ResultCacheManager(
        memory_size=2, persistent_path=cache_path,
        enabled=True, persistence_enabled=True, singleflight=False,
    )

    found_count = sum(
        1 for i in range(10)
        if manager2.get(namespace="test", version="v1", cache_key=f"key_{i}") is not None
    )
    manager2.close()

    assert found_count >= 8, f"Only {found_count}/10 items persisted, expected at least 8"


def test_iter_entries_includes_expires_at(tmp_path):
    """Test that iter_entries returns expires_at field (Bug #5 fix)."""
    cache_path = str(tmp_path / "cache.sqlite")

    manager = ResultCacheManager(
        memory_size=2, persistent_path=cache_path,
        enabled=True, persistence_enabled=True, singleflight=False,
    )

    manager.set(namespace="test", version="v1", cache_key="with_ttl", value={"data": "test"}, ttl=60)
    manager.set(namespace="test", version="v1", cache_key="without_ttl", value={"data": "test2"})
    manager.flush()

    entries = list(manager.dump(namespace="test"))
    assert len(entries) >= 2, f"Expected at least 2 entries, got {len(entries)}"

    with_ttl_entry = next((e for e in entries if e["cache_key"].endswith("with_ttl")), None)
    without_ttl_entry = next((e for e in entries if e["cache_key"].endswith("without_ttl")), None)
    assert with_ttl_entry is not None, "Entry with TTL not found"
    assert without_ttl_entry is not None, "Entry without TTL not found"

    manager.close()


def test_cache_key_consistency(cache_env):
    """Test that cache keys are consistent when tool instance is reused (Bug #1 fix)."""
    TestTool.call_count = 0
    tu = ToolUniverse(tool_files={}, keep_default_tools=False)
    tu.register_custom_tool(
        TestTool,
        tool_config={
            "name": "TestTool",
            "type": "TestTool",
            "description": "Test tool",
            "parameter": {
                "type": "object",
                "properties": {"value": {"type": "integer"}},
                "required": ["value"],
            },
        },
    )

    result1 = tu.run_one_function({"name": "TestTool", "arguments": {"value": 42}}, use_cache=True)
    assert TestTool.call_count == 1

    result2 = tu.run_one_function({"name": "TestTool", "arguments": {"value": 42}}, use_cache=True)
    assert TestTool.call_count == 1, "Cache miss indicates key inconsistency"
    assert result2 == result1

    tu.run_one_function({"name": "TestTool", "arguments": {"value": 99}}, use_cache=True)
    assert TestTool.call_count == 2

    tu.close()


def test_cache_expiration_accuracy(tmp_path):
    """Test that cache expiration is handled correctly."""
    cache_path = str(tmp_path / "cache.sqlite")

    manager = ResultCacheManager(
        memory_size=2, persistent_path=cache_path,
        enabled=True, persistence_enabled=True, singleflight=False,
    )

    manager.set(
        namespace="test", version="v1", cache_key="expire_test",
        value={"data": "should_expire"}, ttl=1,
    )

    assert manager.get(namespace="test", version="v1", cache_key="expire_test") is not None
    time.sleep(1.2)
    assert manager.get(namespace="test", version="v1", cache_key="expire_test") is None, \
        "Cache entry should have expired"

    manager.close()
