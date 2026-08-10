import asyncio
import json
import multiprocessing
import os
from pathlib import Path
import subprocess
import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tooluniverse import mcp_tool_registry as registry
from tooluniverse.remote_connections import (
    connection_configs,
    extract_resource_id,
    mcp_connection,
    normalize_mcp_url,
    platform_connection,
    read_connections,
    remove_connection,
    save_connection,
)
from tooluniverse.platform_remote_tool import PlatformRemoteTool
from tooluniverse.mcp_client_tool import MCPAutoLoaderTool, _unwrap_mcp_tool_result


@pytest.fixture(autouse=True)
def clean_remote_registry():
    saved_tools = dict(registry._mcp_tool_registry)
    saved_servers = dict(registry._mcp_server_configs)
    saved_unported = list(registry._unported_tools)
    saved_instances = dict(registry._mcp_server_instances)
    registry._mcp_tool_registry.clear()
    registry._mcp_server_configs.clear()
    registry._unported_tools.clear()
    registry._mcp_server_instances.clear()
    yield
    registry._mcp_tool_registry.clear()
    registry._mcp_tool_registry.update(saved_tools)
    registry._mcp_server_configs.clear()
    registry._mcp_server_configs.update(saved_servers)
    registry._unported_tools[:] = saved_unported
    registry._mcp_server_instances.clear()
    registry._mcp_server_instances.update(saved_instances)


def _save_connection_worker(path: str, index: int, start_event) -> None:
    """Process target for the persisted-connection race regression test."""
    start_event.wait()
    save_connection(
        mcp_connection(f"http://localhost:{12000 + index}", f"server {index}"),
        Path(path),
    )


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


def test_light_import_preserves_public_provider_class_api():
    """Class-based provider files can keep importing BaseTool from the package."""
    script = """
import sys
from tooluniverse import BaseTool, register_remote_tool
assert BaseTool.__module__ == 'tooluniverse.base_tool'
assert callable(register_remote_tool)
assert 'tooluniverse.execute_function' not in sys.modules
assert 'faiss' not in sys.modules
"""
    env = dict(os.environ)
    env.update(
        {
            "PYTHONPATH": str(Path(__file__).parents[2] / "src"),
            "TOOLUNIVERSE_LIGHT_IMPORT": "1",
        }
    )
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


def test_standard_sdk_import_keeps_heavy_builtin_subpackages_lazy():
    """A normal SDK import must not initialize optional native runtimes."""
    script = r"""
import sys
import tooluniverse

assert tooluniverse._LIGHT_IMPORT is False
assert "tooluniverse.database_setup" not in sys.modules
assert "tooluniverse.database_setup.vector_store" not in sys.modules
assert "faiss" not in sys.modules
"""
    env = dict(os.environ)
    env.pop("TOOLUNIVERSE_LIGHT_IMPORT", None)
    env.pop("TOOLUNIVERSE_LAZY_LOADING", None)
    env["PYTHONPATH"] = str(Path(__file__).parents[2] / "src")
    subprocess.run([sys.executable, "-c", script], env=env, check=True)


def test_lazy_registry_still_imports_external_namespace_plugins(tmp_path, monkeypatch):
    """Skipping built-ins must not disable separately installed TU plugins."""
    from tooluniverse import tool_registry

    builtin = tmp_path / "builtin" / "tooluniverse"
    external = tmp_path / "external" / "tooluniverse"
    builtin.mkdir(parents=True)
    external.mkdir(parents=True)
    (builtin / "__init__.py").touch()
    for marker in ("execute_function.py", "default_config.py", "tool_registry.py"):
        (builtin / marker).touch()
    (builtin / "built_in_feature").mkdir()
    (builtin / "built_in_feature" / "__init__.py").touch()
    (external / "community_tools").mkdir()
    (external / "community_tools" / "__init__.py").touch()

    package = types.SimpleNamespace(
        __file__=str(builtin / "__init__.py"),
        __path__=[str(builtin), str(external)],
    )
    imported = []

    def fake_import(name):
        if name == "tooluniverse":
            return package
        imported.append(name)
        return types.SimpleNamespace()

    monkeypatch.setattr(tool_registry.importlib, "import_module", fake_import)
    tool_registry._auto_import_subpackages()

    assert imported == ["tooluniverse.community_tools"]


def test_standalone_cli_does_not_contact_or_import_platform(tmp_path: Path):
    script = r"""
import builtins
import contextlib
import io
import json
import os
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
assert "TOOLUNIVERSE_LIGHT_IMPORT" not in os.environ
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
    with pytest.raises(TypeError, match=r"\*args, or \*\*kwargs"):

        @registry.remote_tool
        def invalid(**kwargs):
            return kwargs


def test_remote_tool_rejects_positional_only_parameters():
    with pytest.raises(TypeError, match="positional-only"):

        @registry.remote_tool
        def invalid(value: int, /):
            return value


def test_remote_tool_rejects_unbound_methods():
    with pytest.raises(TypeError, match="unbound instance"):

        @registry.remote_tool
        def invalid(self, value: int):
            return value


def test_remote_tool_preserves_async_execution():
    @registry.remote_tool
    async def async_score(value: int) -> int:
        await asyncio.sleep(0)
        return value * 2

    tool_class = registry._mcp_tool_registry["async_score"]["class"]
    assert asyncio.iscoroutinefunction(tool_class.run)
    assert asyncio.run(tool_class().run({"value": 4})) == 8


def test_remote_tool_emits_json_schema_for_nullable_union_and_tuple():
    from typing import Optional, Tuple, Union

    @registry.remote_tool
    def typed(
        optional: Optional[int], mixed: Union[int, str, None], pair: Tuple[int, str]
    ) -> dict:
        return {"optional": optional, "mixed": mixed, "pair": pair}

    properties = registry._mcp_tool_registry["typed"]["parameter_schema"]["properties"]
    assert properties["optional"] == {"type": ["integer", "null"]}
    assert properties["mixed"] == {"type": ["integer", "string", "null"]}
    assert properties["pair"] == {
        "type": "array",
        "prefixItems": [{"type": "integer"}, {"type": "string"}],
        "minItems": 2,
        "maxItems": 2,
    }
    json.dumps(registry._mcp_tool_registry["typed"]["parameter_schema"])


def test_remote_tool_rejects_non_json_default():
    with pytest.raises(TypeError, match="default for 'value'.*JSON-serializable"):

        @registry.remote_tool
        def invalid_default(value=object()):
            return str(value)


def test_remote_tool_rejects_duplicate_function_names():
    def first(value: int) -> int:
        return value

    def second(value: int) -> int:
        return value * 2

    first.__name__ = "duplicate"
    second.__name__ = "duplicate"
    registry.remote_tool(first)
    with pytest.raises(ValueError, match="already registered"):
        registry.remote_tool(second)


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
    with pytest.raises(ValueError, match="must use https"):
        mcp_connection("http://gpu.example/mcp", auth_env="PRIVATE_MCP_TOKEN")


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


def test_connection_namespaces_cannot_silently_replace_each_other(tmp_path: Path):
    path = tmp_path / "connections.json"
    assert save_connection(mcp_connection("http://localhost:8080", "GPU model"), path)

    with pytest.raises(ValueError, match="name collision"):
        save_connection(mcp_connection("http://localhost:8081", "GPU-model"), path)

    assert len(read_connections(path)) == 1


def test_remove_connection_by_supported_selectors(tmp_path: Path):
    path = tmp_path / "connections.json"
    direct = mcp_connection("http://localhost:8080", "Local model")
    published = platform_connection(
        "123e4567-e89b-42d3-a456-426614174000",
        name="Published Model",
        description="Run it",
        input_schema={"type": "object"},
        base_url="https://api.example",
    )
    save_connection(direct, path)
    save_connection(published, path)

    assert remove_connection("http://localhost:8080/", path) == direct
    assert remove_connection(published["resource_id"], path) == published
    assert remove_connection("missing", path) is None
    assert read_connections(path) == []


def test_disconnect_rejects_ambiguous_legacy_names(tmp_path: Path):
    path = tmp_path / "connections.json"
    first = mcp_connection("http://localhost:8080", "same")
    second = platform_connection(
        "123e4567-e89b-42d3-a456-426614174000",
        name="same",
        description="",
        input_schema={"type": "object"},
        base_url="https://api.example",
    )
    path.write_text(json.dumps({"version": 1, "connections": [first, second]}))

    with pytest.raises(ValueError, match="ambiguous"):
        remove_connection("same", path)


def test_save_connection_does_not_overwrite_corrupt_file(tmp_path: Path):
    path = tmp_path / "connections.json"
    original = "{not-json\n"
    path.write_text(original)

    with pytest.raises(ValueError, match="cannot update invalid"):
        save_connection(mcp_connection("http://localhost:8080", "local"), path)

    assert path.read_text() == original


@pytest.mark.skipif(
    "fork" not in multiprocessing.get_all_start_methods(),
    reason="cross-process race test requires fork",
)
def test_concurrent_connection_saves_do_not_lose_updates(tmp_path: Path):
    path = tmp_path / "connections.json"
    context = multiprocessing.get_context("fork")
    start_event = context.Event()
    processes = [
        context.Process(
            target=_save_connection_worker,
            args=(str(path), index, start_event),
        )
        for index in range(16)
    ]
    for process in processes:
        process.start()
    start_event.set()
    for process in processes:
        process.join(10)
        assert process.exitcode == 0

    assert len(read_connections(path)) == len(processes)


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
    monkeypatch.setattr(
        "tooluniverse.platform_remote_tool.time.sleep", lambda _seconds: None
    )
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


def test_platform_remote_poll_uses_remaining_total_deadline(monkeypatch):
    tool = PlatformRemoteTool(
        {
            "name": "remote_gpu_model",
            "resource_id": "123e4567-e89b-42d3-a456-426614174000",
            "base_url": "https://api.example",
            "timeout": 30,
        }
    )
    job_id = "019f8123-cfa2-7502-af19-7be93c844c6c"
    tool._request = MagicMock(side_effect=[{"status": "running"}, {}])
    monkeypatch.setattr(
        "tooluniverse.platform_remote_tool.time.monotonic",
        MagicMock(side_effect=[0, 1, 2, 10]),
    )
    monkeypatch.setattr(
        "tooluniverse.platform_remote_tool.time.sleep", lambda _seconds: None
    )

    result = tool._wait_for_job(
        "test-key",
        {"job_id": job_id, "status_url": f"/remote-tool-jobs/{job_id}"},
        deadline=10,
    )

    assert result["status"] == "error"
    assert tool._request.call_args_list[0].kwargs["timeout"] == 9
    assert tool._request.call_args_list[1].kwargs["method"] == "DELETE"


def test_platform_remote_poll_failure_requests_job_cancellation():
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
        side_effect=[TimeoutError("poll timed out"), {"status": "cancelled"}]
    )

    with pytest.raises(TimeoutError, match="poll timed out"):
        tool._wait_for_job(
            "test-key",
            {"job_id": job_id, "status_url": f"/remote-tool-jobs/{job_id}"},
            deadline=10**12,
        )

    assert tool._request.call_args_list[1].kwargs["method"] == "DELETE"


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


def test_mcp_proxy_unwraps_standard_text_and_error_results():
    assert _unwrap_mcp_tool_result(
        {
            "content": [{"type": "text", "text": '{"score": 0.9}'}],
            "structuredContent": None,
            "isError": False,
        }
    ) == {"score": 0.9}
    assert _unwrap_mcp_tool_result(
        {
            "content": [{"type": "text", "text": "provider failed"}],
            "isError": True,
        }
    ) == {"status": "error", "error": "provider failed"}
    assert _unwrap_mcp_tool_result(
        {
            "content": [],
            "structuredContent": {"code": "GPU_OOM"},
            "isError": True,
        }
    ) == {"status": "error", "error": {"code": "GPU_OOM"}}


def test_mcp_proxy_preserves_multi_part_content_envelope():
    result = {
        "content": [
            {"type": "text", "text": "caption"},
            {"type": "image", "data": "abc", "mimeType": "image/png"},
        ],
        "isError": False,
    }
    assert _unwrap_mcp_tool_result(result) is result


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


def test_provider_isolation_does_not_load_workspace_connections(tmp_path, monkeypatch):
    from tooluniverse import ToolUniverse

    path = tmp_path / "connections.json"
    save_connection(mcp_connection("http://localhost:8080", "consumer tool"), path)
    monkeypatch.setenv("TOOLUNIVERSE_CONNECTIONS_FILE", str(path))
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "profile.yaml").write_text("name: should-not-load\n")

    tu = ToolUniverse(
        tool_files={},
        keep_default_tools=False,
        workspace=str(workspace),
        load_workspace=False,
    )

    assert tu.all_tools == []
    assert tu._workspace_profile_config is None


def test_tooluniverse_preserves_required_nullable_arguments():
    from tooluniverse import ToolUniverse

    class NullableEcho:
        def run(self, arguments):
            return arguments

    tu = ToolUniverse(tool_files={}, keep_default_tools=False, load_workspace=False)
    tu.register_custom_tool(
        tool_class=NullableEcho,
        tool_name="nullable_echo",
        tool_config={
            "name": "nullable_echo",
            "type": "nullable_echo",
            "description": "echo",
            "parameter": {
                "type": "object",
                "properties": {"value": {"type": ["integer", "null"]}},
                "required": ["value"],
            },
        },
        instantiate=True,
    )

    assert tu.run_one_function(
        {"name": "nullable_echo", "arguments": {"value": None}}
    ) == {"value": None}


def test_ipv6_local_mcp_endpoint_is_connectable():
    from tooluniverse.cli import _local_mcp_endpoint

    assert _local_mcp_endpoint("::", 8080) == (
        "::1",
        "http://[::1]:8080/mcp",
    )
    assert _local_mcp_endpoint("0.0.0.0", 8080) == (
        "127.0.0.1",
        "http://127.0.0.1:8080/mcp",
    )


def test_start_mcp_server_without_registered_tools_is_safe(capsys):
    registry.start_mcp_server()
    assert "No MCP tools registered" in capsys.readouterr().out


def test_failed_server_start_does_not_poison_retry(monkeypatch):
    class FakeToolUniverse:
        def __init__(self, **_kwargs):
            self.all_tools = []
            self.all_tool_dict = {}
            self.callable_functions = {}

        def register_custom_tool(self, **kwargs):
            config = kwargs["tool_config"]
            self.all_tools.append(config)
            self.all_tool_dict[config["name"]] = config

    class FailingServer:
        def __init__(self, **_kwargs):
            pass

        def run_simple(self, **_kwargs):
            raise OSError("address already in use")

    class Tool:
        def run(self, arguments):
            return arguments

    port = 18888
    tool_info = {
        "name": "retry_tool",
        "type": "retry_tool",
        "class": Tool,
        "description": "test",
        "parameter_schema": {"type": "object", "properties": {}},
        "server_config": {
            "server_name": "retry",
            "host": "127.0.0.1",
            "port": port,
            "transport": "http",
            "max_workers": 1,
        },
    }
    registry._mcp_server_configs[port] = {
        "config": tool_info["server_config"],
        "tools": [tool_info],
    }
    monkeypatch.setattr(registry, "_get_tooluniverse", lambda: FakeToolUniverse)
    monkeypatch.setattr(registry, "_get_smcp", lambda: FailingServer)

    with pytest.raises(OSError, match="address already in use"):
        registry._start_server_for_port(port)

    assert port not in registry._mcp_server_instances


def test_smcp_run_simple_propagates_startup_failure():
    from tooluniverse.smcp import SMCP

    server = SMCP.__new__(SMCP)
    server.logger = MagicMock()
    server._mcp_server = MagicMock(name="mcp_server")
    server._mcp_server.name = "failing"
    server._exposed_tools = set()
    server.search_enabled = False
    server.hooks_enabled = False
    server.hook_type = None
    server.hook_config = None
    server.run = MagicMock(side_effect=OSError("address already in use"))
    server.close = AsyncMock()

    with pytest.raises(OSError, match="address already in use"):
        server.run_simple(transport="http", port=18889)

    server.close.assert_awaited_once()
