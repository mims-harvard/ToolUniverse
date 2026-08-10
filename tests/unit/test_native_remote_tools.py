import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import MagicMock, patch

import pytest

from tooluniverse import mcp_tool_registry as registry
from tooluniverse.remote_connections import (
    connection_configs,
    extract_resource_id,
    mcp_connection,
    normalize_mcp_url,
    platform_connection,
    read_connections,
    save_connection,
)
from tooluniverse.platform_remote_tool import PlatformRemoteTool
from tooluniverse.mcp_client_tool import MCPAutoLoaderTool


@pytest.fixture(autouse=True)
def clean_remote_registry():
    saved_tools = dict(registry._mcp_tool_registry)
    saved_servers = dict(registry._mcp_server_configs)
    saved_unported = list(registry._unported_tools)
    registry._mcp_tool_registry.clear()
    registry._mcp_server_configs.clear()
    registry._unported_tools.clear()
    yield
    registry._mcp_tool_registry.clear()
    registry._mcp_tool_registry.update(saved_tools)
    registry._mcp_server_configs.clear()
    registry._mcp_server_configs.update(saved_servers)
    registry._unported_tools[:] = saved_unported


def test_light_cli_entry_imports_remote_decorator_without_full_sdk():
    script = """
import sys
import tooluniverse_cli_entry
assert 'tooluniverse' not in sys.modules
os = __import__('os')
os.environ['TOOLUNIVERSE_LIGHT_IMPORT'] = '1'
from tooluniverse import remote_tool
assert callable(remote_tool)
assert 'torch' not in sys.modules
assert 'huggingface_hub' not in sys.modules
assert 'tooluniverse.profile' not in sys.modules
"""
    env = {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONPATH": str(Path(__file__).parents[2] / "src"),
        "TOOLUNIVERSE_LIGHT_IMPORT": "1",
    }
    subprocess.run([sys.executable, "-c", script], env=env, check=True)


def test_standalone_sdk_does_not_require_or_import_platform(tmp_path: Path):
    script = r"""
import builtins
import sys

real_import = builtins.__import__
def guarded_import(name, *args, **kwargs):
    if name == "tuplatform_connect" or name.startswith("tuplatform_connect."):
        raise AssertionError("standalone ToolUniverse imported the platform companion")
    return real_import(name, *args, **kwargs)
builtins.__import__ = guarded_import

import tooluniverse
assert tooluniverse._LIGHT_IMPORT is False
from tooluniverse import BaseTool, ToolUniverse, default_tool_files
instance = ToolUniverse(tool_files={}, keep_default_tools=False)
assert instance.all_tools == []
assert "tuplatform_connect" not in sys.modules
assert "tooluniverse.platform_remote_tool" not in sys.modules
"""
    env = dict(os.environ)
    for name in (
        "TU_API_KEY",
        "TU_BASE_URL",
        "TOOLUNIVERSE_LIGHT_IMPORT",
        "TOOLUNIVERSE_SERVICE_KEY",
        "TOOLUNIVERSE_SERVICE_URL",
    ):
        env.pop(name, None)
    env.update(
        {
            "PYTHONPATH": str(Path(__file__).parents[2] / "src"),
            "TOOLUNIVERSE_CONNECTIONS_FILE": str(tmp_path / "missing.json"),
            "TOOLUNIVERSE_HOME": str(tmp_path / "workspace"),
            "TOOLUNIVERSE_TESTING": "1",
        }
    )
    subprocess.run([sys.executable, "-c", script], env=env, check=True)


def test_standalone_cli_does_not_contact_or_import_platform(tmp_path: Path):
    script = r"""
import builtins
import contextlib
import io
import json
import sys

real_import = builtins.__import__
def guarded_import(name, *args, **kwargs):
    if name == "tuplatform_connect" or name.startswith("tuplatform_connect."):
        raise AssertionError("ordinary tu command imported the platform companion")
    return real_import(name, *args, **kwargs)
builtins.__import__ = guarded_import

import tooluniverse_cli_entry
sys.argv = ["tu", "list", "--limit", "2", "--json"]
output = io.StringIO()
with contextlib.redirect_stdout(output):
    tooluniverse_cli_entry.main()
payload = json.loads(output.getvalue())
assert payload["total_tools"] > 100
assert len(payload["tools"]) == 2
assert "tuplatform_connect" not in sys.modules
assert "tooluniverse.platform_remote_tool" not in sys.modules
"""
    env = dict(os.environ)
    for name in (
        "TU_API_KEY",
        "TU_BASE_URL",
        "TOOLUNIVERSE_LIGHT_IMPORT",
        "TOOLUNIVERSE_SERVICE_KEY",
        "TOOLUNIVERSE_SERVICE_URL",
    ):
        env.pop(name, None)
    env.update(
        {
            "PYTHONPATH": str(Path(__file__).parents[2] / "src"),
            "TOOLUNIVERSE_CONNECTIONS_FILE": str(tmp_path / "missing.json"),
            "TOOLUNIVERSE_HOME": str(tmp_path / "workspace"),
            "TOOLUNIVERSE_TESTING": "1",
        }
    )
    subprocess.run([sys.executable, "-c", script], env=env, check=True)


def test_smcp_does_not_reload_a_preconfigured_remote_tool_universe():
    from tooluniverse.smcp import SMCP

    server = SMCP.__new__(SMCP)
    server.tooluniverse = type("ConfiguredTU", (), {"all_tools": [{"name": "one"}]})()
    server.profile = None
    server.tool_categories = None
    server.auto_expose_tools = True
    server.compact_mode = False
    server.search_enabled = False
    server.logger = MagicMock()
    server._load_tools_with_filters = MagicMock()
    server._ensure_compact_mode_categories = MagicMock()
    server._expose_tooluniverse_tools = MagicMock()
    server._add_search_tools = MagicMock()
    server._add_utility_tools = MagicMock()

    server._setup_smcp_tools()

    server._load_tools_with_filters.assert_not_called()
    server._expose_tooluniverse_tools.assert_called_once_with()
    server._add_utility_tools.assert_called_once_with()


def test_remote_tool_infers_schema_and_remains_callable():
    @registry.remote_tool
    def score(sequence: str, threshold: float = 0.5) -> dict:
        """Score one sequence."""
        return {"sequence": sequence, "threshold": threshold}

    assert score("ABC") == {"sequence": "ABC", "threshold": 0.5}
    info = registry._mcp_tool_registry["score"]
    schema = info["parameter_schema"]
    assert schema["properties"]["sequence"] == {"type": "string"}
    assert schema["properties"]["threshold"] == {
        "type": "number",
        "default": 0.5,
    }
    assert schema["required"] == ["sequence"]
    assert schema["additionalProperties"] is False
    assert info["description"] == "Score one sequence."


def test_remote_tool_rejects_variadic_signatures():
    with pytest.raises(TypeError, match=r"\*args or \*\*kwargs"):

        @registry.remote_tool
        def invalid(**kwargs):
            return kwargs


def test_collect_tools_for_serve_uses_one_explicit_server():
    @registry.remote_tool
    def first(value: int) -> int:
        return value

    @registry.remote_tool
    def second(value: int) -> int:
        return value * 2

    selected = registry.collect_tools_for_serve(
        9123, host="127.0.0.1", server_name="gpu pool", max_workers=12
    )
    assert [item["name"] for item in selected] == ["first", "second"]
    assert list(registry._mcp_server_configs) == [9123]
    config = registry._mcp_server_configs[9123]["config"]
    assert config["server_name"] == "gpu pool"
    assert config["max_workers"] == 12


def test_mcp_connection_is_normalized_and_secret_free():
    connection = mcp_connection(
        "https://gpu.example:8443/base", "Boltz GPU", "MY_MCP_TOKEN"
    )
    assert connection == {
        "kind": "mcp",
        "name": "Boltz GPU",
        "url": "https://gpu.example:8443/base/mcp",
        "prefix": "boltz_gpu_",
        "auth_env": "MY_MCP_TOKEN",
    }
    assert normalize_mcp_url("http://localhost:8080/mcp/") == (
        "http://localhost:8080/mcp"
    )
    with pytest.raises(ValueError, match="must not contain credentials"):
        normalize_mcp_url("https://user:secret@gpu.example/mcp")
    with pytest.raises(ValueError, match="valid variable name"):
        mcp_connection("https://gpu.example/mcp", auth_env="BAD-NAME")


def test_connections_round_trip_and_generate_configs(tmp_path: Path):
    path = tmp_path / "connections.json"
    direct = mcp_connection("http://localhost:8080", "Local model")
    published = platform_connection(
        "123e4567-e89b-42d3-a456-426614174000",
        name="Published Model",
        description="Run it",
        input_schema={"type": "object", "properties": {"x": {"type": "number"}}},
        base_url="https://api.example",
    )
    assert save_connection(direct, path)
    assert not save_connection(direct, path)
    assert save_connection(published, path)
    assert read_connections(path) == [direct, published]

    configs = connection_configs(path)
    assert configs[0]["type"] == "MCPAutoLoaderTool"
    assert configs[0]["tool_prefix"] == "local_model_"
    assert configs[1]["type"] == "PlatformRemoteTool"
    assert configs[1]["name"] == "remote_published_model"
    assert configs[1]["resource_id"] == published["resource_id"]
    assert json.loads(path.read_text())["version"] == 1
    assert path.stat().st_mode & 0o777 == 0o600


def test_extract_resource_id_from_marketplace_url():
    resource_id = "123e4567-e89b-42d3-a456-426614174000"
    assert extract_resource_id(resource_id) == resource_id
    assert (
        extract_resource_id(f"https://connect.aiscientist.tools/discover/{resource_id}")
        == resource_id
    )
    assert extract_resource_id("http://localhost:8080/mcp") is None


class _Response:
    def __init__(self, payload):
        self._body = json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, _size=-1):
        return self._body


def test_platform_remote_tool_calls_only_configured_resource(monkeypatch):
    monkeypatch.setenv("TU_API_KEY", "test-key")
    tool = PlatformRemoteTool(
        {
            "name": "remote_model",
            "resource_id": "123e4567-e89b-42d3-a456-426614174000",
            "base_url": "https://api.example",
        }
    )
    with patch.object(
        tool._opener, "open", return_value=_Response({"result": {"score": 0.9}})
    ) as opened:
        assert tool.run({"sequence": "ABC"}) == {"score": 0.9}
    request = opened.call_args.args[0]
    assert request.full_url == "https://api.example/tools/call"
    assert json.loads(request.data) == {
        "tool": "123e4567-e89b-42d3-a456-426614174000",
        "arguments": {"sequence": "ABC"},
    }
    assert request.get_header("Authorization") == "Bearer test-key"


def test_platform_remote_tool_requires_key(monkeypatch):
    monkeypatch.delenv("TU_API_KEY", raising=False)
    monkeypatch.delenv("TOOLUNIVERSE_SERVICE_KEY", raising=False)
    tool = PlatformRemoteTool(
        {
            "name": "remote_model",
            "resource_id": "123e4567-e89b-42d3-a456-426614174000",
            "base_url": "https://api.example",
        }
    )
    result = tool.run({})
    assert result["status"] == "error"
    assert "TU_API_KEY" in result["error"]


@pytest.mark.parametrize("timeout", [0, 901, float("inf"), float("nan")])
def test_platform_remote_tool_rejects_unsafe_timeout(timeout):
    with pytest.raises(ValueError, match="between 1 and 900"):
        PlatformRemoteTool(
            {
                "name": "remote_model",
                "resource_id": "123e4567-e89b-42d3-a456-426614174000",
                "base_url": "https://api.example",
                "timeout": timeout,
            }
        )


def test_platform_remote_tool_waits_for_async_job(monkeypatch):
    monkeypatch.setenv("TU_API_KEY", "test-key")
    monkeypatch.setattr("tooluniverse.platform_remote_tool.time.sleep", lambda _seconds: None)
    tool = PlatformRemoteTool(
        {
            "name": "remote_gpu_model",
            "resource_id": "123e4567-e89b-42d3-a456-426614174000",
            "base_url": "https://api.example",
            "timeout": 30,
        }
    )
    job_id = "019f8123-cfa2-7502-af19-7be93c844c6c"
    tool._request = MagicMock(
        side_effect=[
            {"job_id": job_id, "status_url": f"/remote-tool-jobs/{job_id}"},
            {"status": "running"},
            {"status": "succeeded", "result": {"value": {"score": 0.91}}},
        ]
    )

    assert tool.run({"sequence": "ABC"}) == {"score": 0.91}
    assert tool._request.call_args_list[1].args[0] == f"/remote-tool-jobs/{job_id}"


def test_platform_remote_tool_rejects_cross_origin_async_status(monkeypatch):
    monkeypatch.setenv("TU_API_KEY", "test-key")
    tool = PlatformRemoteTool(
        {
            "name": "remote_gpu_model",
            "resource_id": "123e4567-e89b-42d3-a456-426614174000",
            "base_url": "https://api.example",
        }
    )
    tool._request = MagicMock(
        return_value={
            "job_id": "019f8123-cfa2-7502-af19-7be93c844c6c",
            "status_url": "https://attacker.example/steal-key",
        }
    )
    result = tool.run({})
    assert result["status"] == "error"
    assert "invalid asynchronous job handle" in result["error"]


def test_mcp_auth_env_propagates_without_copying_secret(monkeypatch):
    monkeypatch.setenv("PRIVATE_MCP_TOKEN", "super-secret")
    loader = MCPAutoLoaderTool(
        {
            "name": "loader",
            "server_url": "https://gpu.example/mcp",
            "tool_prefix": "gpu_",
            "auth_env": "PRIVATE_MCP_TOKEN",
        }
    )
    assert loader.headers["Authorization"] == "Bearer super-secret"
    loader._discovered_tools = {
        "predict": {
            "name": "predict",
            "description": "Predict",
            "inputSchema": {"type": "object"},
        }
    }
    proxy = loader.generate_proxy_tool_configs()[0]
    assert proxy["auth_env"] == "PRIVATE_MCP_TOKEN"
    assert "headers" not in proxy
    assert "super-secret" not in json.dumps(proxy)


def test_tooluniverse_loads_explicit_platform_connection(tmp_path, monkeypatch):
    from tooluniverse import ToolUniverse

    path = tmp_path / "connections.json"
    save_connection(
        platform_connection(
            "123e4567-e89b-42d3-a456-426614174000",
            name="Published Model",
            description="Run it",
            input_schema={"type": "object"},
            base_url="https://api.example",
        ),
        path,
    )
    monkeypatch.setenv("TOOLUNIVERSE_CONNECTIONS_FILE", str(path))
    monkeypatch.chdir(tmp_path)
    tu = ToolUniverse(tool_files={}, keep_default_tools=False)
    tu.load_tools()
    assert tu.all_tool_dict["remote_published_model"]["type"] == ("PlatformRemoteTool")
