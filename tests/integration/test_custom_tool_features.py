#!/usr/bin/env python3
"""
Comprehensive tests for all custom-tool integration paths in ToolUniverse.

Covers:
  A. register_custom_tool() – instantiate=True / False, duplicate, pre-instance
  B. load_tools(python_files=[...]) – explicit path parameter
  C. Workspace auto-discovery – flat and organised layout, Python and JSON files
  D. tu.run() / tu.tools – execution and namespace access
  E. Error cases – unknown tool, missing param, missing description/type in config
  F. CLI – tu list / info / run / test via subprocess
"""

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Ensure source tree is importable
# ---------------------------------------------------------------------------
_SRC = str(Path(__file__).resolve().parents[2] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from tooluniverse.base_tool import BaseTool
from tooluniverse.tool_registry import register_tool

# ---------------------------------------------------------------------------
# Minimal tool class reused across many tests
# ---------------------------------------------------------------------------

@register_tool("_EchoTool", config={
    "name": "_echo_tool",
    "description": "Echoes its input back",
    "type": "_EchoTool",
    "parameter": {
        "type": "object",
        "properties": {
            "message": {"type": "string", "description": "Message to echo"},
        },
        "required": [],
    },
})
class _EchoTool(BaseTool):
    def run(self, arguments=None, **kwargs):
        args = arguments or kwargs
        return {"status": "success", "echo": args.get("message", "ok")}


def _make_tu(workspace=None, **kwargs):
    """Create a fresh ToolUniverse with no built-in JSON categories."""
    from tooluniverse import ToolUniverse
    return ToolUniverse(tool_files={}, keep_default_tools=False, workspace=workspace, **kwargs)


# ===========================================================================
# A. register_custom_tool()
# ===========================================================================

@pytest.mark.unit
class TestRegisterCustomTool:
    """Tests for ToolUniverse.register_custom_tool()."""

    def test_register_instantiate_true_and_run(self):
        """register_custom_tool(instantiate=True) exposes tool via tu.run()."""
        tu = _make_tu()
        config = {
            "name": "my_echo",
            "description": "Echo tool",
            "type": "MyEchoClass",
            "parameter": {
                "type": "object",
                "properties": {"msg": {"type": "string"}},
                "required": [],
            },
        }

        class MyEchoClass(BaseTool):
            def run(self, arguments=None, **kwargs):
                return {"status": "success", "msg": (arguments or {}).get("msg", "hi")}

        tu.register_custom_tool(MyEchoClass, tool_config=config, instantiate=True)

        assert "my_echo" in tu.all_tool_dict
        assert "my_echo" in tu.callable_functions  # pre-instantiated

        result = tu.run({"name": "my_echo", "arguments": {"msg": "hello"}})
        assert isinstance(result, dict)
        assert result.get("status") == "success"
        assert result.get("msg") == "hello"

    def test_register_instantiate_false_lazy(self):
        """register_custom_tool(instantiate=False) instantiates on first tu.run() call."""
        tu = _make_tu()
        config = {
            "name": "lazy_tool",
            "description": "Lazy tool",
            "type": "LazyClass",
            "parameter": {"type": "object", "properties": {}, "required": []},
        }

        class LazyClass(BaseTool):
            def run(self, arguments=None, **kwargs):
                return {"status": "success", "lazy": True}

        tu.register_custom_tool(LazyClass, tool_config=config, instantiate=False)

        assert "lazy_tool" in tu.all_tool_dict
        assert "lazy_tool" not in tu.callable_functions  # not yet instantiated

        result = tu.run({"name": "lazy_tool", "arguments": {}})
        assert result.get("status") == "success"
        assert "lazy_tool" in tu.callable_functions  # now cached

    def test_register_duplicate_replaces(self):
        """Registering the same tool name twice replaces the first registration."""
        tu = _make_tu()

        class ToolV1(BaseTool):
            def run(self, arguments=None, **kwargs):
                return {"version": 1}

        class ToolV2(BaseTool):
            def run(self, arguments=None, **kwargs):
                return {"version": 2}

        cfg1 = {"name": "versioned_tool", "description": "v1", "type": "ToolV1",
                "parameter": {"type": "object", "properties": {}, "required": []}}
        cfg2 = {"name": "versioned_tool", "description": "v2", "type": "ToolV2",
                "parameter": {"type": "object", "properties": {}, "required": []}}

        tu.register_custom_tool(ToolV1, tool_config=cfg1, instantiate=True)
        tu.register_custom_tool(ToolV2, tool_config=cfg2, instantiate=True)

        assert tu.all_tool_dict["versioned_tool"]["description"] == "v2"
        assert len([t for t in tu.all_tools if t.get("name") == "versioned_tool"]) == 1
        result = tu.run({"name": "versioned_tool", "arguments": {}})
        assert result.get("version") == 2

    def test_register_pre_instantiated(self):
        """register_custom_tool with tool_instance uses the provided object."""
        tu = _make_tu()

        class PreMadeClass(BaseTool):
            def __init__(self, tool_config=None):
                super().__init__(tool_config or {})
                self.call_count = 0

            def run(self, arguments=None, **kwargs):
                self.call_count += 1
                return {"status": "success", "count": self.call_count}

        cfg = {"name": "premade", "description": "Pre-made", "type": "PreMadeClass",
               "parameter": {"type": "object", "properties": {}, "required": []}}
        instance = PreMadeClass(tool_config=cfg)

        tu.register_custom_tool(PreMadeClass, tool_instance=instance, tool_config=cfg)

        assert tu.callable_functions.get("premade") is instance

        tu.run({"name": "premade", "arguments": {}})
        tu.run({"name": "premade", "arguments": {}})
        assert instance.call_count == 2

    def test_register_no_config_warning(self):
        """register_custom_tool without tool_config does not add to all_tool_dict."""
        tu = _make_tu()

        class NoConfigTool(BaseTool):
            def run(self, arguments=None, **kwargs):
                return {}

        tu.register_custom_tool(NoConfigTool)
        assert "NoConfigTool" not in tu.all_tool_dict

    def test_type_auto_set_from_class_name(self):
        """register_custom_tool injects 'type' from class name if missing from config."""
        tu = _make_tu()

        class AutoTypeTool(BaseTool):
            def run(self, arguments=None, **kwargs):
                return {"status": "success"}

        cfg = {
            "name": "auto_type",
            "description": "Auto type tool",
            # deliberately no "type" field
            "parameter": {"type": "object", "properties": {}, "required": []},
        }
        tu.register_custom_tool(AutoTypeTool, tool_config=cfg, instantiate=False)

        assert tu.all_tool_dict["auto_type"]["type"] == "AutoTypeTool"
        result = tu.run({"name": "auto_type", "arguments": {}})
        assert result.get("status") == "success"


# ===========================================================================
# B. load_tools(python_files=[...])
# ===========================================================================

@pytest.mark.unit
class TestLoadToolsPythonFiles:
    """Tests for explicit python_files= parameter in load_tools()."""

    def test_python_files_explicit(self, tmp_path):
        """load_tools(python_files=[...]) imports the file and discovers its tools."""
        tool_file = tmp_path / "my_explicit_tool.py"
        tool_file.write_text(textwrap.dedent("""\
            import sys
            sys.path.insert(0, {src!r})
            from tooluniverse.tool_registry import register_tool
            from tooluniverse.base_tool import BaseTool

            @register_tool("ExplicitTool_9999", config={{
                "name": "explicit_tool_9999",
                "description": "Explicit load test",
                "type": "ExplicitTool_9999",
                "parameter": {{"type": "object", "properties": {{}}, "required": []}},
            }})
            class ExplicitTool_9999(BaseTool):
                def run(self, arguments=None, **kwargs):
                    return {{"status": "success", "source": "explicit"}}
        """.format(src=_SRC)))

        tu = _make_tu()
        tu.load_tools(python_files=[str(tool_file)])

        assert "explicit_tool_9999" in tu.all_tool_dict
        result = tu.run({"name": "explicit_tool_9999", "arguments": {}})
        assert result.get("status") == "success"

    def test_nonexistent_python_file_tolerated(self):
        """load_tools(python_files=['/bad/path']) logs a warning but does not raise."""
        tu = _make_tu()
        tu.load_tools(python_files=["/nonexistent/path/does_not_exist.py"])
        # Should complete without exception; built-in tools still load normally


# ===========================================================================
# C. Workspace auto-discovery
# ===========================================================================

_WORKSPACE_TOOL_PY = textwrap.dedent("""\
    import sys
    sys.path.insert(0, {src!r})
    from tooluniverse.tool_registry import register_tool
    from tooluniverse.base_tool import BaseTool

    @register_tool("WorkspacePyTool_{tag}", config={{
        "name": "workspace_py_tool_{tag}",
        "description": "Workspace Python tool {tag}",
        "type": "WorkspacePyTool_{tag}",
        "parameter": {{"type": "object",
                       "properties": {{"val": {{"type": "string"}}}},
                       "required": []}},
    }})
    class WorkspacePyTool_{tag}(BaseTool):
        def run(self, arguments=None, **kwargs):
            return {{"status": "success", "val": (arguments or {{}}).get("val", "ok")}}
""")


@pytest.mark.unit
class TestWorkspaceAutoDiscovery:
    """Workspace-based auto-discovery: flat layout, organised layout, JSON."""

    def test_flat_layout_python(self, tmp_path):
        """Python tool in flat .tooluniverse/ root is auto-discovered."""
        ws = tmp_path / ".tooluniverse"
        ws.mkdir()
        (ws / "flat_tool.py").write_text(
            _WORKSPACE_TOOL_PY.format(src=_SRC, tag="Flat")
        )

        tu = _make_tu(workspace=str(ws))
        tu.load_tools()

        assert "workspace_py_tool_Flat" in tu.all_tool_dict
        result = tu.run({"name": "workspace_py_tool_Flat", "arguments": {"val": "x"}})
        assert result.get("status") == "success"
        assert result.get("val") == "x"

    def test_organised_layout_python(self, tmp_path):
        """Python tool in .tooluniverse/tools/ subdirectory is auto-discovered."""
        ws = tmp_path / ".tooluniverse"
        tools_dir = ws / "tools"
        tools_dir.mkdir(parents=True)
        (tools_dir / "org_tool.py").write_text(
            _WORKSPACE_TOOL_PY.format(src=_SRC, tag="Org")
        )

        tu = _make_tu(workspace=str(ws))
        tu.load_tools()

        assert "workspace_py_tool_Org" in tu.all_tool_dict

    def test_workspace_json_with_type_discovered(self, tmp_path):
        """JSON config WITH 'type' field in workspace is loaded into all_tool_dict."""
        ws = tmp_path / ".tooluniverse"
        ws.mkdir()

        # Write the Python class so the type can be resolved at execution time
        (ws / "json_backed_tool.py").write_text(
            _WORKSPACE_TOOL_PY.format(src=_SRC, tag="JsonBacked")
        )
        # JSON config — deliberately separate from the Python file
        (ws / "json_only.json").write_text(json.dumps([{
            "name": "workspace_json_tool",
            "description": "A workspace JSON tool",
            "type": "WorkspacePyTool_JsonBacked",
            "parameter": {"type": "object", "properties": {"q": {"type": "string"}},
                          "required": []},
        }]))

        tu = _make_tu(workspace=str(ws))
        tu.load_tools()

        assert "workspace_json_tool" in tu.all_tool_dict

    def test_workspace_json_without_description_raises(self, tmp_path):
        """JSON config missing 'description' causes KeyError in refresh_tool_name_desc."""
        ws = tmp_path / ".tooluniverse"
        ws.mkdir()
        (ws / "nodesc.json").write_text(json.dumps([{
            "name": "nodesc_tool",
            # no "description" field
            "type": "SomeType",
            "parameter": {"type": "object", "properties": {}, "required": []},
        }]))

        tu = _make_tu(workspace=str(ws))
        with pytest.raises(KeyError):
            tu.load_tools()

    def test_workspace_json_without_type_appears_in_dict_but_fails_execution(self, tmp_path):
        """JSON config missing 'type' loads into all_tool_dict but tu.run() returns error."""
        ws = tmp_path / ".tooluniverse"
        ws.mkdir()
        (ws / "notype.json").write_text(json.dumps([{
            "name": "notype_tool",
            "description": "No type tool",
            # no "type" field
            "parameter": {"type": "object", "properties": {}, "required": []},
        }]))

        tu = _make_tu(workspace=str(ws))
        tu.load_tools()

        assert "notype_tool" in tu.all_tool_dict

        # Execution should fail gracefully (return error dict, not raise)
        result = tu.run({"name": "notype_tool", "arguments": {}})
        assert isinstance(result, (dict, str))
        # Should report an error, not succeed
        if isinstance(result, dict):
            assert result.get("status") == "error" or "error" in result


# ===========================================================================
# D. tu.run() and tu.tools namespace
# ===========================================================================

@pytest.mark.unit
class TestRunAndNamespace:
    """Tests for tu.run() and tu.tools attribute-style access."""

    def _register_echo(self, tu, suffix=""):
        name = f"ns_echo{suffix}"

        class _NSEcho(BaseTool):
            def run(self, arguments=None, **kwargs):
                return {"status": "success", "echo": (arguments or {}).get("msg", "")}

        _NSEcho.__name__ = f"_NSEcho{suffix}"
        _NSEcho.__qualname__ = f"_NSEcho{suffix}"
        cfg = {"name": name, "description": "NS echo", "type": f"_NSEcho{suffix}",
               "parameter": {"type": "object",
                             "properties": {"msg": {"type": "string"}},
                             "required": []}}
        tu.register_custom_tool(_NSEcho, tool_config=cfg, instantiate=True)
        return name

    def test_run_dict_input(self):
        """tu.run() accepts dict input and returns a result dict."""
        tu = _make_tu()
        name = self._register_echo(tu, "_dict")
        result = tu.run({"name": name, "arguments": {"msg": "hi"}})
        assert isinstance(result, dict)
        assert result.get("status") == "success"

    def test_tools_attribute_access(self):
        """tu.tools.tool_name() calls the tool directly."""
        tu = _make_tu()
        name = self._register_echo(tu, "_ns")
        callable_obj = getattr(tu.tools, name)
        assert callable(callable_obj)
        result = callable_obj(msg="world")
        assert result.get("status") == "success"
        assert result.get("echo") == "world"

    def test_tools_contains(self):
        """'tool_name' in tu.tools works after registration."""
        tu = _make_tu()
        name = self._register_echo(tu, "_in")
        assert name in tu.tools

    def test_tools_len_and_iter(self):
        """len(tu.tools) and iteration include registered custom tools."""
        tu = _make_tu()
        name = self._register_echo(tu, "_len")
        assert len(tu.tools) >= 1
        assert name in list(tu.tools)

    def test_run_unknown_tool_returns_error(self):
        """tu.run() with unknown tool name returns error dict, does not raise."""
        tu = _make_tu()
        tu.load_tools()
        result = tu.run({"name": "completely_nonexistent_xyz", "arguments": {}})
        assert isinstance(result, (dict, str))
        if isinstance(result, dict):
            assert result.get("status") == "error" or "error" in result

    def test_run_missing_required_param_returns_error(self):
        """tu.run() with missing required param returns validation error."""
        tu = _make_tu()

        class StrictTool(BaseTool):
            def run(self, arguments=None, **kwargs):
                return {"status": "success", "gene": (arguments or {}).get("gene_id")}

        cfg = {
            "name": "strict_tool",
            "description": "Requires gene_id",
            "type": "StrictTool",
            "parameter": {
                "type": "object",
                "properties": {"gene_id": {"type": "string"}},
                "required": ["gene_id"],
            },
        }
        tu.register_custom_tool(StrictTool, tool_config=cfg, instantiate=True)

        result = tu.run({"name": "strict_tool", "arguments": {}})
        assert isinstance(result, (dict, str))
        if isinstance(result, dict):
            assert result.get("status") == "error" or "error" in result


# ===========================================================================
# E. Deduplication and reload behaviour
# ===========================================================================

@pytest.mark.unit
class TestDeduplication:
    """Load_tools() called twice must not accumulate duplicates."""

    def test_double_load_no_duplicates(self, tmp_path):
        """Calling load_tools() twice does not create duplicate entries."""
        ws = tmp_path / ".tooluniverse"
        ws.mkdir()
        (ws / "dedup_tool.py").write_text(
            _WORKSPACE_TOOL_PY.format(src=_SRC, tag="Dedup")
        )

        tu = _make_tu(workspace=str(ws))
        tu.load_tools()
        tu.load_tools()

        count = sum(
            1 for t in tu.all_tools if isinstance(t, dict)
            and t.get("name") == "workspace_py_tool_Dedup"
        )
        assert count == 1, f"Expected 1 entry, got {count}"


# ===========================================================================
# F. CLI integration  (subprocess — isolated from test-process state)
# ===========================================================================

def _run_cli(args, workspace_dir, timeout=30):
    """Run the `tu` CLI as a subprocess with TOOLUNIVERSE_HOME set."""
    env = {
        **os.environ,
        "TOOLUNIVERSE_HOME": str(workspace_dir),
        "TOOLUNIVERSE_LIGHT_IMPORT": "1",
        "TOOLUNIVERSE_QUIET": "1",
        "PYTHONPATH": _SRC,
    }
    return subprocess.run(
        [sys.executable, "-m", "tooluniverse.cli"] + args,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


_CLI_TOOL_PY = textwrap.dedent("""\
    import sys
    sys.path.insert(0, {src!r})
    from tooluniverse.tool_registry import register_tool
    from tooluniverse.base_tool import BaseTool

    @register_tool("CliTestTool", config={{
        "name": "cli_test_tool",
        "description": "A CLI test tool",
        "type": "CliTestTool",
        "parameter": {{
            "type": "object",
            "properties": {{"msg": {{"type": "string", "description": "A message"}}}},
            "required": [],
        }},
        "test_examples": [{{"msg": "hello"}}],
    }})
    class CliTestTool(BaseTool):
        def run(self, arguments=None, **kwargs):
            return {{"status": "success", "msg": (arguments or {{}}).get("msg", "ok")}}
""")


@pytest.mark.integration
class TestCLICustomTools:
    """CLI commands with workspace custom tools."""

    @pytest.fixture
    def cli_workspace(self, tmp_path):
        ws = tmp_path / ".tooluniverse"
        ws.mkdir()
        (ws / "cli_tool.py").write_text(_CLI_TOOL_PY.format(src=_SRC))
        return ws

    def test_cli_list_shows_custom_tool(self, cli_workspace):
        """tu list --json includes the custom workspace tool."""
        r = _run_cli(["list", "--json"], cli_workspace)
        assert r.returncode == 0, f"stderr: {r.stderr}"
        data = json.loads(r.stdout)
        names = data if isinstance(data, list) else data.get("tools", [])
        tool_names = [t if isinstance(t, str) else t.get("name", "") for t in names]
        assert "cli_test_tool" in tool_names, f"Not found in: {tool_names[:10]}"

    def test_cli_info_shows_schema(self, cli_workspace):
        """tu info cli_test_tool --json shows the tool's parameter schema."""
        r = _run_cli(["info", "cli_test_tool", "--json"], cli_workspace)
        assert r.returncode == 0, f"stderr: {r.stderr}"
        data = json.loads(r.stdout)
        tools = data.get("tools", [data]) if isinstance(data, dict) else data
        info = tools[0] if tools else {}
        assert info.get("name") == "cli_test_tool"
        assert "parameter" in info or "parameters" in info

    def test_cli_run_executes_custom_tool(self, cli_workspace):
        """tu run cli_test_tool msg=hello returns success."""
        r = _run_cli(["run", "cli_test_tool", "msg=hello", "--json"], cli_workspace)
        assert r.returncode == 0, f"stdout: {r.stdout}\nstderr: {r.stderr}"
        result = json.loads(r.stdout)
        assert result.get("status") == "success"
        assert result.get("msg") == "hello"

    def test_cli_test_with_examples(self, cli_workspace):
        """tu test cli_test_tool runs test_examples from config."""
        r = _run_cli(["test", "cli_test_tool", "--json"], cli_workspace)
        assert r.returncode == 0, f"stdout: {r.stdout}\nstderr: {r.stderr}"
        data = json.loads(r.stdout)
        assert data.get("passed", 0) >= 1
        assert data.get("failed", 0) == 0

    def test_cli_run_nonexistent_tool_exits_nonzero(self, cli_workspace):
        """tu run nonexistent_tool exits with non-zero status."""
        r = _run_cli(["run", "nonexistent_xyz_tool", "--json"], cli_workspace)
        assert r.returncode != 0
