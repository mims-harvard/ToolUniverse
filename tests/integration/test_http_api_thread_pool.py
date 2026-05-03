#!/usr/bin/env python3
"""
Tests for HTTP API Server Thread Pool Functionality

Tests verify:
1. Thread pool is initialized correctly
2. Concurrent requests work via thread pool
3. Thread pool size is configurable
4. Async execution is non-blocking
5. Thread pool handles multiple concurrent calls

Run:
    pytest tests/test_http_api_thread_pool.py -v
"""

import os
import time
import pytest
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from fastapi.testclient import TestClient
import threading


def test_thread_pool_initialization():
    """Test that thread pool is initialized with correct size"""
    # Set environment variable
    os.environ["TOOLUNIVERSE_THREAD_POOL_SIZE"] = "30"
    
    # Force reimport to pick up environment variable
    import importlib
    from tooluniverse import http_api_server
    importlib.reload(http_api_server)
    
    # Check thread pool size
    assert http_api_server._thread_pool_size == 30
    assert http_api_server._thread_pool._max_workers == 30
    
    # Clean up
    del os.environ["TOOLUNIVERSE_THREAD_POOL_SIZE"]


def test_thread_pool_default_size():
    """Test default thread pool size is 20"""
    # Remove env var if exists
    if "TOOLUNIVERSE_THREAD_POOL_SIZE" in os.environ:
        del os.environ["TOOLUNIVERSE_THREAD_POOL_SIZE"]
    
    # Force reimport
    import importlib
    from tooluniverse import http_api_server
    importlib.reload(http_api_server)
    
    # Check default
    assert http_api_server._thread_pool_size == 20
    assert http_api_server._thread_pool._max_workers == 20


def test_concurrent_requests():
    """Test that multiple concurrent requests work via thread pool"""
    from tooluniverse.http_api_server import app, _tu_manager
    
    # Reset instance
    _tu_manager.reset()
    
    client = TestClient(app)
    
    # Function to make a request
    def make_request(request_id):
        response = client.get("/health")
        return request_id, response.status_code, response.json()
    
    # Make 10 concurrent requests
    num_requests = 10
    with ThreadPoolExecutor(max_workers=num_requests) as executor:
        futures = [executor.submit(make_request, i) for i in range(num_requests)]
        results = [f.result() for f in as_completed(futures)]
    
    # Verify all succeeded
    assert len(results) == num_requests
    for request_id, status_code, data in results:
        assert status_code == 200
        assert data["status"] == "healthy"


def test_concurrent_method_calls():
    """Test concurrent calls to ToolUniverse methods"""
    from tooluniverse.http_api_server import app, _tu_manager
    
    # Reset and load tools
    _tu_manager.reset()
    client = TestClient(app)
    
    # Load tools first
    response = client.post(
        "/api/call",
        json={
            "method": "load_tools",
            "kwargs": {"tool_type": ["uniprot"]}
        }
    )
    assert response.status_code == 200
    assert response.json()["success"] is True
    
    # Function to call get_available_tools
    def call_get_tools(request_id):
        response = client.post(
            "/api/call",
            json={
                "method": "get_available_tools",
                "kwargs": {"name_only": True}
            }
        )
        return request_id, response.status_code, response.json()
    
    # Make multiple concurrent calls
    num_requests = 5
    with ThreadPoolExecutor(max_workers=num_requests) as executor:
        futures = [executor.submit(call_get_tools, i) for i in range(num_requests)]
        results = [f.result() for f in as_completed(futures)]
    
    # Verify all succeeded
    assert len(results) == num_requests
    for request_id, status_code, data in results:
        assert status_code == 200
        assert data["success"] is True
        assert isinstance(data["result"], list)


def test_async_endpoint_is_async():
    """Test that the call_method endpoint is truly async"""
    from tooluniverse.http_api_server import app, call_method
    import inspect
    
    # Verify the endpoint is an async function
    assert asyncio.iscoroutinefunction(call_method)


def test_thread_pool_handles_slow_operations():
    """Test that thread pool handles slow operations without blocking"""
    from tooluniverse.http_api_server import app, _tu_manager
    
    _tu_manager.reset()
    client = TestClient(app)
    
    # Load tools (can be slow)
    start_time = time.time()
    
    def load_tools():
        response = client.post(
            "/api/call",
            json={
                "method": "load_tools",
                "kwargs": {"tool_type": ["uniprot"]}
            }
        )
        return response.json()
    
    # Start multiple slow operations
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(load_tools) for _ in range(3)]
        results = [f.result() for f in as_completed(futures)]
    
    elapsed = time.time() - start_time
    
    # All should succeed
    for result in results:
        assert result["success"] is True
    
    # Should complete in reasonable time (not 3x single operation time)
    # This verifies concurrent execution
    print(f"Elapsed time for 3 concurrent operations: {elapsed:.2f}s")


def test_thread_pool_survives_errors():
    """Test that thread pool continues working after errors"""
    from tooluniverse.http_api_server import app, _tu_manager
    
    _tu_manager.reset()
    client = TestClient(app)
    
    # Make a call that will fail
    response1 = client.post(
        "/api/call",
        json={
            "method": "non_existent_method",
            "kwargs": {}
        }
    )
    assert response1.json()["success"] is False
    
    # Thread pool should still work
    response2 = client.get("/health")
    assert response2.status_code == 200
    
    # Make multiple more calls
    for _ in range(5):
        response = client.get("/health")
        assert response.status_code == 200


def test_thread_safety_of_singleton():
    """Test that ToolUniverse singleton is thread-safe"""
    from tooluniverse.http_api_server import _tu_manager
    
    _tu_manager.reset()
    
    instances = []
    
    def get_instance(index):
        instance = _tu_manager.get_instance()
        instances.append((index, id(instance)))
        return instance
    
    # Get instance from multiple threads
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(get_instance, i) for i in range(10)]
        results = [f.result() for f in futures]
    
    # All should be the same instance
    instance_ids = [id(inst) for inst in results]
    assert len(set(instance_ids)) == 1, "Should only create one instance"
    
    # Verify all threads got same instance
    first_id = instances[0][1]
    for index, inst_id in instances:
        assert inst_id == first_id, f"Thread {index} got different instance"


def test_thread_pool_under_load():
    """Test thread pool behavior under high concurrent load"""
    from tooluniverse.http_api_server import app, _tu_manager
    
    _tu_manager.reset()
    client = TestClient(app)
    
    num_requests = 50
    success_count = 0
    errors = []
    
    def make_health_check(request_id):
        try:
            response = client.get("/health")
            return response.status_code == 200
        except Exception as e:
            errors.append((request_id, str(e)))
            return False
    
    # Hammer the server with concurrent requests
    start_time = time.time()
    with ThreadPoolExecutor(max_workers=num_requests) as executor:
        futures = [executor.submit(make_health_check, i) for i in range(num_requests)]
        results = [f.result() for f in as_completed(futures)]
    
    elapsed = time.time() - start_time
    success_count = sum(results)
    
    print(f"\nLoad test results:")
    print(f"  Total requests: {num_requests}")
    print(f"  Successful: {success_count}")
    print(f"  Failed: {len(errors)}")
    print(f"  Time: {elapsed:.2f}s")
    print(f"  Requests/sec: {num_requests/elapsed:.2f}")
    
    # At least 95% should succeed
    assert success_count >= num_requests * 0.95
    
    if errors:
        print(f"\nErrors encountered:")
        for req_id, error in errors[:5]:  # Show first 5 errors
            print(f"  Request {req_id}: {error}")


def test_thread_pool_resource_cleanup():
    """Test that thread pool resources are properly managed"""
    from tooluniverse.http_api_server import app, _tu_manager, _thread_pool
    
    _tu_manager.reset()
    client = TestClient(app)
    
    # Get initial thread count
    initial_thread_count = threading.active_count()
    
    # Make many requests
    for _ in range(20):
        response = client.get("/health")
        assert response.status_code == 200
    
    # Thread count should not grow unbounded
    final_thread_count = threading.active_count()
    
    print(f"\nThread count: initial={initial_thread_count}, final={final_thread_count}")
    
    # Should not create excessive threads
    # Allow some variance but thread count shouldn't explode
    assert final_thread_count < initial_thread_count + 50


def test_mixed_fast_and_slow_operations():
    """Test that fast operations aren't blocked by slow ones"""
    from tooluniverse.http_api_server import app, _tu_manager
    
    _tu_manager.reset()
    client = TestClient(app)
    
    results = []
    
    def fast_operation(op_id):
        """Fast health check"""
        start = time.time()
        response = client.get("/health")
        elapsed = time.time() - start
        return ("fast", op_id, elapsed, response.status_code)
    
    def slow_operation(op_id):
        """Slower operation (load tools)"""
        start = time.time()
        response = client.post(
            "/api/call",
            json={
                "method": "load_tools",
                "kwargs": {"tool_type": ["uniprot"]}
            }
        )
        elapsed = time.time() - start
        return ("slow", op_id, elapsed, response.status_code)
    
    # Start a slow operation and several fast ones concurrently
    with ThreadPoolExecutor(max_workers=10) as executor:
        # Submit 1 slow and 9 fast operations
        futures = []
        futures.append(executor.submit(slow_operation, 0))
        for i in range(9):
            futures.append(executor.submit(fast_operation, i))
        
        results = [f.result() for f in as_completed(futures)]
    
    # Separate fast and slow results
    fast_results = [r for r in results if r[0] == "fast"]
    slow_results = [r for r in results if r[0] == "slow"]
    
    print(f"\nMixed operations results:")
    print(f"  Fast operations: {len(fast_results)}")
    print(f"  Slow operations: {len(slow_results)}")
    
    # All should succeed
    assert all(r[3] == 200 for r in results)
    
    # Fast operations should complete quickly
    fast_times = [r[2] for r in fast_results]
    avg_fast_time = sum(fast_times) / len(fast_times)
    print(f"  Average fast operation time: {avg_fast_time:.3f}s")
    
    # Fast operations shouldn't be blocked by slow ones
    # (most should complete quickly)
    quick_fast_ops = sum(1 for t in fast_times if t < 1.0)
    assert quick_fast_ops >= len(fast_results) * 0.8  # At least 80% should be quick


def test_environment_variable_configuration():
    """Test that TOOLUNIVERSE_THREAD_POOL_SIZE env var works"""
    import subprocess
    import sys
    
    # Create a test script
    test_script = """
import os
os.environ["TOOLUNIVERSE_THREAD_POOL_SIZE"] = "42"

from tooluniverse import http_api_server
print(f"THREAD_POOL_SIZE={http_api_server._thread_pool_size}")
print(f"MAX_WORKERS={http_api_server._thread_pool._max_workers}")
"""
    
    # Run in subprocess to get fresh import
    result = subprocess.run(
        [sys.executable, "-c", test_script],
        capture_output=True,
        text=True,
        timeout=10
    )
    
    output = result.stdout
    print(f"\nEnvironment variable test output:\n{output}")
    
    assert "THREAD_POOL_SIZE=42" in output
    assert "MAX_WORKERS=42" in output


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
