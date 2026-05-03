#!/usr/bin/env python3
"""
Tests for ToolUniverse HTTP API Server

Run:
    pytest tests/test_http_api_server.py -v
"""

import pytest
from fastapi.testclient import TestClient
from tooluniverse.http_api_server import app, _tu_manager


@pytest.fixture
def client():
    """Create test client"""
    # Reset instance before each test
    _tu_manager.reset()
    return TestClient(app)


def test_root_endpoint(client):
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "ToolUniverse HTTP API"
    assert data["status"] == "running"


def test_health_check(client):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "tooluniverse_initialized" in data


def test_list_methods(client):
    """Test listing available methods"""
    response = client.get("/api/methods")
    assert response.status_code == 200
    data = response.json()
    assert "methods" in data
    assert "total" in data
    assert len(data["methods"]) > 0
    
    # Check first method structure
    method = data["methods"][0]
    assert "name" in method
    assert "parameters" in method
    assert "docstring" in method


def test_call_method_load_tools(client):
    """Test calling load_tools method"""
    response = client.post(
        "/api/call",
        json={
            "method": "load_tools",
            "kwargs": {
                "tool_type": ["uniprot"]
            }
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    # load_tools returns None but should succeed
    assert "error" not in data or data["error"] is None


def test_call_method_get_available_tools(client):
    """Test calling get_available_tools method"""
    # First load some tools
    client.post(
        "/api/call",
        json={
            "method": "load_tools",
            "kwargs": {"tool_type": ["uniprot"]}
        }
    )
    
    # Then get available tools
    response = client.post(
        "/api/call",
        json={
            "method": "get_available_tools",
            "kwargs": {"name_only": True}
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "result" in data
    assert isinstance(data["result"], list)


def test_call_invalid_method(client):
    """Test calling non-existent method"""
    response = client.post(
        "/api/call",
        json={
            "method": "non_existent_method",
            "kwargs": {}
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert "error" in data
    assert "not found" in data["error"].lower()


def test_call_private_method(client):
    """Test calling private method (should fail)"""
    response = client.post(
        "/api/call",
        json={
            "method": "_private_method",
            "kwargs": {}
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert "private" in data["error"].lower()


def test_call_method_with_invalid_args(client):
    """Test calling method with invalid arguments"""
    response = client.post(
        "/api/call",
        json={
            "method": "load_tools",
            "kwargs": {
                "invalid_param": "value"
            }
        }
    )
    assert response.status_code == 200
    data = response.json()
    # Should fail due to invalid parameter
    assert data["success"] is False
    assert "error" in data


def test_reset_endpoint(client):
    """Test reset endpoint"""
    response = client.post("/api/reset")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


def test_method_discovery():
    """Test that method discovery finds expected methods"""
    from tooluniverse.http_api_server import discover_public_methods
    from tooluniverse.execute_function import ToolUniverse
    
    methods = discover_public_methods(ToolUniverse)
    
    # Check some key methods are discovered
    expected_methods = [
        "load_tools",
        "run_one_function",
        "tool_specification",
        "prepare_tool_prompts",
        "get_available_tools",
        "list_built_in_tools"
    ]
    
    for method_name in expected_methods:
        assert method_name in methods, f"Method '{method_name}' not discovered"
        assert "parameters" in methods[method_name]
        assert "docstring" in methods[method_name]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
