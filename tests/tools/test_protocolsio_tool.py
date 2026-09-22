"""
Unit tests for the protocols.io API tool.

protocols.io requires an OAuth Bearer token for every endpoint (even
public/read-only search), so these tests mock the HTTP layer rather than
hitting the live API, following the same pattern used for other
key-gated tools in this repo (see test_uspto_tool.py).
"""

import json
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def tool_config():
    with open("src/tooluniverse/data/protocolsio_tools.json") as f:
        tools = json.load(f)
    return next(t for t in tools if t["name"] == "ProtocolsIO_search_protocols")


@pytest.fixture
def get_protocol_config():
    with open("src/tooluniverse/data/protocolsio_tools.json") as f:
        tools = json.load(f)
    return next(t for t in tools if t["name"] == "ProtocolsIO_get_protocol")


def _ok_response(body):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = body
    resp.raise_for_status.return_value = None
    return resp


def _status_response(status_code, body=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = body or {}
    resp.raise_for_status.return_value = None
    return resp


class TestMissingApiKey:
    def test_run_without_key_returns_clean_error(self, tool_config):
        from tooluniverse.protocolsio_tool import ProtocolsIOTool

        tool = ProtocolsIOTool(tool_config, api_key=None)
        result = tool.run({"operation": "search_protocols", "query": "CRISPR"})
        assert result["status"] == "error"
        assert "PROTOCOLS_IO_API_KEY" in result["error"]

    def test_key_resolved_from_environment_at_construction(self, tool_config):
        from tooluniverse.protocolsio_tool import ProtocolsIOTool

        with patch.dict("os.environ", {"PROTOCOLS_IO_API_KEY": "env-token"}, clear=False):
            tool = ProtocolsIOTool(tool_config)
        assert tool.api_key == "env-token"


class TestMissingOperation:
    def test_missing_operation_is_an_error_not_a_crash(self, tool_config):
        from tooluniverse.protocolsio_tool import ProtocolsIOTool

        tool = ProtocolsIOTool(tool_config, api_key="test-token")
        result = tool.run({})
        assert result["status"] == "error"
        assert "operation" in result["error"]

    def test_unknown_operation_is_an_error(self, tool_config):
        from tooluniverse.protocolsio_tool import ProtocolsIOTool

        tool = ProtocolsIOTool(tool_config, api_key="test-token")
        result = tool.run({"operation": "not_a_real_operation"})
        assert result["status"] == "error"
        assert "Unknown operation" in result["error"]


class TestSearchProtocols:
    def test_missing_query_is_an_error(self, tool_config):
        from tooluniverse.protocolsio_tool import ProtocolsIOTool

        tool = ProtocolsIOTool(tool_config, api_key="test-token")
        result = tool.run({"operation": "search_protocols"})
        assert result["status"] == "error"
        assert "query" in result["error"]

    def test_successful_search_returns_protocols(self, tool_config):
        from tooluniverse.protocolsio_tool import ProtocolsIOTool

        tool = ProtocolsIOTool(tool_config, api_key="test-token")
        body = {
            "items": [{"id": 65123, "title": "CRISPR knockout screen"}],
            "pagination": {"total_results": 1},
        }
        with patch("requests.get", return_value=_ok_response(body)):
            result = tool.run(
                {"operation": "search_protocols", "query": "CRISPR", "limit": 5}
            )
        assert result["status"] == "success"
        assert result["data"]["protocols"][0]["title"] == "CRISPR knockout screen"
        assert result["data"]["total_count"] == 1

    def test_auth_failure_returns_actionable_hint(self, tool_config):
        from tooluniverse.protocolsio_tool import ProtocolsIOTool

        tool = ProtocolsIOTool(tool_config, api_key="stale-token")
        with patch("requests.get", return_value=_status_response(401)):
            result = tool.run({"operation": "search_protocols", "query": "CRISPR"})
        assert result["status"] == "error"
        assert "PROTOCOLS_IO_API_KEY" in result["error"]


class TestGetProtocol:
    def test_missing_protocol_id_is_an_error(self, get_protocol_config):
        from tooluniverse.protocolsio_tool import ProtocolsIOTool

        tool = ProtocolsIOTool(get_protocol_config, api_key="test-token")
        result = tool.run({"operation": "get_protocol"})
        assert result["status"] == "error"
        assert "protocol_id" in result["error"]

    def test_not_found_returns_clean_error(self, get_protocol_config):
        from tooluniverse.protocolsio_tool import ProtocolsIOTool

        tool = ProtocolsIOTool(get_protocol_config, api_key="test-token")
        with patch("requests.get", return_value=_status_response(404)):
            result = tool.run({"operation": "get_protocol", "protocol_id": 99999999})
        assert result["status"] == "error"
        assert "not found" in result["error"].lower()

    def test_successful_get_returns_protocol_detail(self, get_protocol_config):
        from tooluniverse.protocolsio_tool import ProtocolsIOTool

        tool = ProtocolsIOTool(get_protocol_config, api_key="test-token")
        body = {"id": 65123, "title": "CRISPR knockout screen", "materials": []}
        with patch("requests.get", return_value=_ok_response(body)):
            result = tool.run({"operation": "get_protocol", "protocol_id": 65123})
        assert result["status"] == "success"
        assert result["data"]["id"] == 65123
