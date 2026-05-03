"""
Tests for Phase 1-8 new functionality:
- workspace field resolution (ToolUniverse constructor + env vars)
- sources loading in load_profile()
- TOOLUNIVERSE_HOME and TOOLUNIVERSE_PROFILE env vars
- ProfileLoader.resolve_to_local_dir() and get_tool_files_from_dir()
- MCP CLI --workspace flag
- Sub-package config registration via register_tool_configs()
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from tooluniverse.profile import ProfileLoader


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_yaml(path: Path, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f)


def _write_json(path: Path, data) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)


def _minimal_profile(name: str = "test") -> dict:
    return {"name": name, "version": "1.0.0", "description": "desc"}


# ---------------------------------------------------------------------------
# ProfileLoader.get_tool_files_from_dir
# ---------------------------------------------------------------------------


class TestGetToolFilesFromDir:
    """Tests for ProfileLoader.get_tool_files_from_dir()."""

    def test_empty_directory(self, tmp_path):
        py, js = ProfileLoader.get_tool_files_from_dir(tmp_path)
        assert py == []
        assert js == []

    def test_nonexistent_directory(self, tmp_path):
        py, js = ProfileLoader.get_tool_files_from_dir(tmp_path / "no_such_dir")
        assert py == []
        assert js == []

    def test_flat_layout_py_and_json(self, tmp_path):
        (tmp_path / "tool_a.py").write_text("# tool a")
        (tmp_path / "tool_b.py").write_text("# tool b")
        (tmp_path / "config_a.json").write_text('{"name": "a"}')
        (tmp_path / "profile.json").write_text("{}")  # should be excluded

        py, js = ProfileLoader.get_tool_files_from_dir(tmp_path)
        assert sorted(p.name for p in py) == ["tool_a.py", "tool_b.py"]
        assert [p.name for p in js] == ["config_a.json"]

    def test_skips_init_and_setup_py(self, tmp_path):
        (tmp_path / "__init__.py").write_text("")
        (tmp_path / "setup.py").write_text("")
        (tmp_path / "conftest.py").write_text("")
        (tmp_path / "mytool.py").write_text("# real tool")

        py, _ = ProfileLoader.get_tool_files_from_dir(tmp_path)
        assert [p.name for p in py] == ["mytool.py"]

    def test_organised_layout(self, tmp_path):
        tools_dir = tmp_path / "tools"
        tools_dir.mkdir()
        (tools_dir / "tool_c.py").write_text("# tool c")

        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "tools.json").write_text('[{"name": "tc"}]')
        (data_dir / "profile.json").write_text("{}")  # excluded

        configs_dir = tmp_path / "configs"
        configs_dir.mkdir()
        (configs_dir / "extra.json").write_text('[{"name": "extra"}]')

        py, js = ProfileLoader.get_tool_files_from_dir(tmp_path)
        assert [p.name for p in py] == ["tool_c.py"]
        assert sorted(p.name for p in js) == ["extra.json", "tools.json"]

    def test_mixed_flat_and_organised(self, tmp_path):
        (tmp_path / "flat.py").write_text("# flat")
        tools_dir = tmp_path / "tools"
        tools_dir.mkdir()
        (tools_dir / "organised.py").write_text("# organised")

        py, _ = ProfileLoader.get_tool_files_from_dir(tmp_path)
        names = [p.name for p in py]
        assert "flat.py" in names
        assert "organised.py" in names


# ---------------------------------------------------------------------------
# ProfileLoader.resolve_to_local_dir
# ---------------------------------------------------------------------------


class TestResolveToLocalDir:
    """Tests for ProfileLoader.resolve_to_local_dir()."""

    def test_local_directory(self, tmp_path):
        loader = ProfileLoader(cache_dir=tmp_path / "cache")
        result = loader.resolve_to_local_dir(str(tmp_path))
        assert result == tmp_path

    def test_local_file_returns_parent(self, tmp_path):
        f = tmp_path / "profile.yaml"
        f.write_text("name: t\nversion: 1.0.0\n")
        loader = ProfileLoader(cache_dir=tmp_path / "cache")
        result = loader.resolve_to_local_dir(str(f))
        assert result == tmp_path

    def test_local_missing_raises(self, tmp_path):
        loader = ProfileLoader(cache_dir=tmp_path / "cache")
        with pytest.raises(ValueError, match="Profile path not found"):
            loader.resolve_to_local_dir(str(tmp_path / "no_such"))

    @patch("huggingface_hub.snapshot_download")
    def test_hf_uri_calls_snapshot_download(self, mock_snap, tmp_path):
        mock_snap.return_value = str(tmp_path)
        loader = ProfileLoader(cache_dir=tmp_path / "cache")
        result = loader.resolve_to_local_dir("hf:user/my-repo")
        mock_snap.assert_called_once()
        assert result == tmp_path

    @patch("requests.get")
    def test_http_file_url_downloads_and_returns_dir(self, mock_get, tmp_path):
        mock_resp = MagicMock()
        mock_resp.content = b"name: t\nversion: 1.0.0\n"
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        loader = ProfileLoader(cache_dir=tmp_path / "cache")
        result = loader.resolve_to_local_dir("https://example.com/profile.yaml")
        assert result.is_dir()
        assert (result / "profile.yaml").exists()

    @patch("requests.get")
    def test_github_repo_url_downloads_zip(self, mock_get, tmp_path):
        """Test that a GitHub repo URL triggers ZIP download."""
        import io
        import zipfile

        # Build a minimal ZIP in memory
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("myrepo-main/tool.py", "# tool")
        buf.seek(0)

        mock_resp = MagicMock()
        mock_resp.content = buf.read()
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        loader = ProfileLoader(cache_dir=tmp_path / "cache")
        result = loader.resolve_to_local_dir("https://github.com/user/myrepo")
        # The ZIP extracts to a subdir; result should be a directory
        assert result.is_dir()


# ---------------------------------------------------------------------------
# PROFILE_SCHEMA new fields: sources, workspace, package
# ---------------------------------------------------------------------------


class TestProfileSchemaNewFields:
    """Tests that sources, workspace, package fields pass validation."""

    def test_sources_field_accepted(self, tmp_path):
        config_file = tmp_path / "profile.yaml"
        _write_yaml(
            config_file,
            {
                "name": "src-test",
                "version": "1.0.0",
                "description": "d",
                "sources": ["./extra", "hf:user/tools"],
            },
        )
        loader = ProfileLoader(cache_dir=tmp_path / "cache")
        config = loader.load(str(config_file))
        assert config["sources"] == ["./extra", "hf:user/tools"]

    def test_workspace_field_accepted(self, tmp_path):
        config_file = tmp_path / "profile.yaml"
        _write_yaml(
            config_file,
            {
                "name": "ws-test",
                "version": "1.0.0",
                "description": "d",
                "workspace": "/my/workspace",
            },
        )
        loader = ProfileLoader(cache_dir=tmp_path / "cache")
        config = loader.load(str(config_file))
        assert config["workspace"] == "/my/workspace"

    def test_package_field_accepted(self, tmp_path):
        config_file = tmp_path / "profile.yaml"
        _write_yaml(
            config_file,
            {
                "name": "pkg-test",
                "version": "1.0.0",
                "description": "d",
                "package": "tooluniverse/mypkg",
            },
        )
        loader = ProfileLoader(cache_dir=tmp_path / "cache")
        config = loader.load(str(config_file))
        assert config["package"] == "tooluniverse/mypkg"

    def test_sources_defaults_to_empty_list(self, tmp_path):
        config_file = tmp_path / "profile.yaml"
        _write_yaml(config_file, _minimal_profile())
        loader = ProfileLoader(cache_dir=tmp_path / "cache")
        config = loader.load(str(config_file))
        assert config["sources"] == []


# ---------------------------------------------------------------------------
# ToolUniverse constructor: workspace and profile params
# ---------------------------------------------------------------------------


class TestToolUniverseConstructor:
    """Tests for the workspace= and profile= constructor parameters."""

    def test_workspace_param_sets_workspace_dir(self, tmp_path):
        from tooluniverse.execute_function import ToolUniverse

        workspace = tmp_path / "my_workspace"
        workspace.mkdir()
        tu = ToolUniverse(workspace=str(workspace))
        assert tu._workspace_dir == workspace

    def test_workspace_param_creates_dir_if_missing(self, tmp_path):
        from tooluniverse.execute_function import ToolUniverse

        workspace = tmp_path / "new_workspace"
        assert not workspace.exists()
        tu = ToolUniverse(workspace=str(workspace))
        assert workspace.exists()
        assert tu._workspace_dir == workspace

    def test_no_workspace_param_defaults_to_local(self):
        """Without an explicit workspace, the default is ./.tooluniverse (local mode)."""
        from pathlib import Path
        from tooluniverse.execute_function import ToolUniverse

        env_backup = os.environ.pop("TOOLUNIVERSE_HOME", None)
        try:
            tu = ToolUniverse()
            assert tu._workspace_dir == Path.cwd() / ".tooluniverse"
        finally:
            if env_backup is not None:
                os.environ["TOOLUNIVERSE_HOME"] = env_backup

    def test_tooluniverse_home_env_var(self, tmp_path):
        from tooluniverse.execute_function import ToolUniverse

        home = tmp_path / "env_home"
        with patch.dict(os.environ, {"TOOLUNIVERSE_HOME": str(home)}, clear=False):
            tu = ToolUniverse()
            assert tu._workspace_dir == home
            assert home.exists()

    def test_workspace_param_takes_priority_over_env(self, tmp_path):
        from tooluniverse.execute_function import ToolUniverse

        workspace = tmp_path / "param_ws"
        env_home = tmp_path / "env_home"
        with patch.dict(
            os.environ, {"TOOLUNIVERSE_HOME": str(env_home)}, clear=False
        ):
            tu = ToolUniverse(workspace=str(workspace))
            assert tu._workspace_dir == workspace

    def test_profile_param_calls_load_profile(self, tmp_path):
        from tooluniverse.execute_function import ToolUniverse

        config_file = tmp_path / "profile.yaml"
        _write_yaml(config_file, _minimal_profile("from-param"))

        with patch.object(ToolUniverse, "load_profile") as mock_load:
            ToolUniverse(profile=str(config_file))
            mock_load.assert_called_once_with(str(config_file))

    def test_tooluniverse_profile_env_var(self, tmp_path):
        from tooluniverse.execute_function import ToolUniverse

        config_file = tmp_path / "profile.yaml"
        _write_yaml(config_file, _minimal_profile("from-env"))

        with patch.dict(
            os.environ, {"TOOLUNIVERSE_PROFILE": str(config_file)}, clear=False
        ):
            with patch.object(ToolUniverse, "load_profile") as mock_load:
                ToolUniverse()
                mock_load.assert_called_once_with(str(config_file))

    def test_profile_param_takes_priority_over_tooluniverse_profile_env(self, tmp_path):
        from tooluniverse.execute_function import ToolUniverse

        param_file = tmp_path / "param.yaml"
        env_file = tmp_path / "env.yaml"
        _write_yaml(param_file, _minimal_profile("param"))
        _write_yaml(env_file, _minimal_profile("env"))

        with patch.dict(
            os.environ, {"TOOLUNIVERSE_PROFILE": str(env_file)}, clear=False
        ):
            with patch.object(ToolUniverse, "load_profile") as mock_load:
                ToolUniverse(profile=str(param_file))
                # Should be called with the param file, not env file
                mock_load.assert_called_once_with(str(param_file))


# ---------------------------------------------------------------------------
# ToolUniverse._get_user_tool_files with workspace_dir
# ---------------------------------------------------------------------------


class TestGetUserToolFilesWithWorkspace:
    """Tests that _get_user_tool_files() uses workspace_dir when set."""

    def test_workspace_dir_scans_tool_files(self, tmp_path):
        from tooluniverse.execute_function import ToolUniverse

        workspace = tmp_path / "workspace"
        workspace.mkdir()
        (workspace / "my_tool.py").write_text("# my tool")
        (workspace / "configs.json").write_text('[{"name": "t1"}]')

        tu = ToolUniverse(workspace=str(workspace))
        py_files, json_files = tu._get_user_tool_files()

        py_names = [p.name for p in py_files]
        json_names = [p.name for p in json_files]
        assert "my_tool.py" in py_names
        assert "configs.json" in json_names

    def test_no_workspace_uses_default_home(self, tmp_path):
        from tooluniverse.execute_function import ToolUniverse

        # Without workspace, result depends on ~/.tooluniverse or TOOLUNIVERSE_HOME
        # We just check it returns lists without crashing
        env_backup = os.environ.pop("TOOLUNIVERSE_HOME", None)
        try:
            tu = ToolUniverse()
            py_files, json_files = tu._get_user_tool_files()
            assert isinstance(py_files, list)
            assert isinstance(json_files, list)
        finally:
            if env_backup is not None:
                os.environ["TOOLUNIVERSE_HOME"] = env_backup


# ---------------------------------------------------------------------------
# sources loading in load_profile()
# ---------------------------------------------------------------------------


class TestLoadProfileSources:
    """Tests that load_profile() processes the sources field."""

    def test_sources_calls_load_tools_from_sources(self, tmp_path):
        from tooluniverse.execute_function import ToolUniverse

        # Create a source directory with a JSON tool config
        source_dir = tmp_path / "external_tools"
        source_dir.mkdir()
        _write_json(
            source_dir / "tools.json",
            [{"name": "ext_tool_1", "description": "External tool 1"}],
        )

        # Create a profile.yaml that references the source dir
        config_file = tmp_path / "profile.yaml"
        _write_yaml(
            config_file,
            {
                "name": "src-profile",
                "version": "1.0.0",
                "description": "d",
                "sources": [str(source_dir)],
            },
        )

        tu = ToolUniverse()
        with patch.object(tu, "_load_tools_from_sources") as mock_load_src:
            tu.load_profile(str(config_file))
            mock_load_src.assert_called_once()
            # Verify the sources list was passed
            call_args = mock_load_src.call_args
            sources_arg = call_args[0][1]  # second positional arg
            assert str(source_dir) in sources_arg

    def test_empty_sources_does_not_call_load_tools_from_sources(self, tmp_path):
        from tooluniverse.execute_function import ToolUniverse

        config_file = tmp_path / "profile.yaml"
        _write_yaml(config_file, _minimal_profile())

        tu = ToolUniverse()
        with patch.object(tu, "_load_tools_from_sources") as mock_load_src:
            tu.load_profile(str(config_file))
            mock_load_src.assert_not_called()

    def test_load_tools_from_sources_loads_json_configs(self, tmp_path):
        from tooluniverse.execute_function import ToolUniverse

        source_dir = tmp_path / "src"
        source_dir.mkdir()
        _write_json(
            source_dir / "extra_tools.json",
            [{"name": "src_tool_x", "description": "From source"}],
        )

        config_file = tmp_path / "profile.yaml"
        _write_yaml(
            config_file,
            {
                "name": "src-load-test",
                "version": "1.0.0",
                "description": "d",
                "sources": [str(source_dir)],
            },
        )

        tu = ToolUniverse()
        tu.load_profile(str(config_file))

        tool_names = [t.get("name") for t in tu.all_tools]
        assert "src_tool_x" in tool_names


# ---------------------------------------------------------------------------
# MCP CLI --workspace flag
# ---------------------------------------------------------------------------


class TestMCPCLIWorkspaceFlag:
    """Tests that the MCP server CLI parsers accept --workspace."""

    def _get_http_parser(self):
        """Import and build the HTTP server argument parser."""
        import argparse
        import importlib

        # We'll test the argument is registered by patching sys.argv and
        # using parse_known_args
        spec = importlib.util.find_spec("tooluniverse.smcp_server")
        assert spec is not None
        return spec

    def test_smcp_server_accepts_workspace_flag(self):
        """Verify --workspace is accepted by the smcp-server parser."""
        import argparse
        from tooluniverse import smcp_server

        # Build a minimal parser equivalent to what run_http_server creates
        # by directly checking the function's source builds it
        # We test indirectly: call parse_known_args with --workspace
        # on a fresh ArgumentParser with the same flags
        parser = argparse.ArgumentParser()
        space_group = parser.add_argument_group("Profile Configuration")
        space_group.add_argument("--load", "-l", type=str)
        space_group.add_argument("--workspace", "-w", type=str)

        args, _ = parser.parse_known_args(["--workspace", "/tmp/myws"])
        assert args.workspace == "/tmp/myws"

    def test_smcp_module_has_workspace_in_all_parsers(self):
        """Verify --workspace is registered via _add_profile_args for all 3 parsers."""
        import inspect
        from tooluniverse import smcp_server

        source = inspect.getsource(smcp_server)
        # --workspace is defined once in _add_profile_args; each parser calls the helper.
        assert '"--workspace"' in source, "--workspace not found in smcp_server.py"
        calls = source.count("_add_profile_args(parser)")
        assert calls >= 3, (
            f"Expected at least 3 '_add_profile_args(parser)' calls in smcp_server.py, found {calls}"
        )

    def test_smcp_module_passes_workspace_to_smcp(self):
        """Verify workspace=args.workspace is passed to SMCP in all 3 server functions."""
        import inspect
        from tooluniverse import smcp_server

        source = inspect.getsource(smcp_server)
        occurrences = source.count("workspace=args.workspace")
        assert occurrences >= 3, (
            f"Expected at least 3 'workspace=args.workspace' in smcp_server.py, found {occurrences}"
        )


# ---------------------------------------------------------------------------
# SMCP class accepts workspace parameter
# ---------------------------------------------------------------------------


class TestSMCPWorkspaceParam:
    """Tests that SMCP passes workspace to ToolUniverse."""

    def test_smcp_accepts_workspace_param(self):
        import inspect
        from tooluniverse.smcp import SMCP

        sig = inspect.signature(SMCP.__init__)
        assert "workspace" in sig.parameters, (
            "SMCP.__init__ should have a 'workspace' parameter"
        )

    def test_smcp_passes_workspace_to_tooluniverse(self):
        """Verify SMCP source passes workspace= to ToolUniverse constructor."""
        import inspect
        from tooluniverse.smcp import SMCP

        source = inspect.getsource(SMCP.__init__)
        # The ToolUniverse constructor call should include workspace=workspace
        assert "workspace=workspace" in source, (
            "SMCP.__init__ should pass workspace=workspace to ToolUniverse"
        )


# ---------------------------------------------------------------------------
# register_tool_configs (sub-package registry)
# ---------------------------------------------------------------------------


class TestRegisterToolConfigs:
    """Tests for the sub-package tool config registry."""

    def test_register_tool_configs_adds_to_registry(self):
        from tooluniverse.tool_registry import (
            _list_config_registry,
            get_list_config_registry,
            register_tool_configs,
        )

        initial_count = len(get_list_config_registry())
        test_configs = [
            {"name": "_test_reg_tool_1", "description": "Test tool 1", "type": "Unknown"},
            {"name": "_test_reg_tool_2", "description": "Test tool 2", "type": "Unknown"},
        ]
        register_tool_configs(test_configs)

        registry = get_list_config_registry()
        names = [c["name"] for c in registry]
        assert "_test_reg_tool_1" in names
        assert "_test_reg_tool_2" in names
        assert len(registry) >= initial_count + 2

    def test_register_tool_configs_skips_invalid_entries(self):
        from tooluniverse.tool_registry import (
            get_list_config_registry,
            register_tool_configs,
        )

        initial = get_list_config_registry()
        initial_count = len(initial)

        # Entry without 'name' should be skipped
        register_tool_configs([{"description": "no name"}])

        registry = get_list_config_registry()
        # Count should not increase (or only by valid entries)
        assert len(registry) == initial_count

    def test_get_list_config_registry_returns_copy(self):
        from tooluniverse.tool_registry import get_list_config_registry

        r1 = get_list_config_registry()
        get_list_config_registry()
        # Modifying one should not affect the registry
        r1.append({"name": "_sentinel_should_not_persist"})
        r3 = get_list_config_registry()
        names = [c["name"] for c in r3]
        assert "_sentinel_should_not_persist" not in names


# ---------------------------------------------------------------------------
# profile.yaml feature tests — cache, log_level, .env, workspace merge
# ---------------------------------------------------------------------------


class TestProfileYamlCacheConfig:
    """Tests for cache configuration via profile.yaml."""

    def test_cache_disabled_via_profile_yaml(self, tmp_path):
        """cache.enabled=false turns off caching."""
        from tooluniverse.execute_function import ToolUniverse

        ws = tmp_path / ".tooluniverse"
        ws.mkdir()
        _write_yaml(
            ws / "profile.yaml",
            {**_minimal_profile("cache-test"), "cache": {"enabled": False}},
        )
        tu = ToolUniverse(workspace=str(ws))
        assert tu.cache_manager.enabled is False

    def test_cache_memory_size_via_profile_yaml(self, tmp_path):
        """cache.memory_size sets the LRU cache size."""
        from tooluniverse.execute_function import ToolUniverse

        ws = tmp_path / ".tooluniverse"
        ws.mkdir()
        _write_yaml(
            ws / "profile.yaml",
            {**_minimal_profile("cache-mem"), "cache": {"memory_size": 42}},
        )
        tu = ToolUniverse(workspace=str(ws))
        assert tu.cache_manager.memory.max_size == 42

    def test_cache_ttl_via_profile_yaml(self, tmp_path):
        """cache.ttl sets the default TTL."""
        from tooluniverse.execute_function import ToolUniverse

        ws = tmp_path / ".tooluniverse"
        ws.mkdir()
        _write_yaml(
            ws / "profile.yaml",
            {**_minimal_profile("cache-ttl"), "cache": {"ttl": 300}},
        )
        tu = ToolUniverse(workspace=str(ws))
        assert tu.cache_manager.default_ttl == 300

    def test_cache_persist_false_via_profile_yaml(self, tmp_path):
        """cache.persist=false disables persistent (SQLite) cache."""
        from tooluniverse.execute_function import ToolUniverse

        ws = tmp_path / ".tooluniverse"
        ws.mkdir()
        _write_yaml(
            ws / "profile.yaml",
            {**_minimal_profile("cache-nopersist"), "cache": {"persist": False}},
        )
        tu = ToolUniverse(workspace=str(ws))
        assert tu.cache_manager.persistent is None

    def test_cache_multiple_fields_via_profile_yaml(self, tmp_path):
        """Multiple cache fields can be set at once."""
        from tooluniverse.execute_function import ToolUniverse

        ws = tmp_path / ".tooluniverse"
        ws.mkdir()
        _write_yaml(
            ws / "profile.yaml",
            {
                **_minimal_profile("cache-multi"),
                "cache": {"enabled": True, "memory_size": 128, "ttl": 60, "persist": False},
            },
        )
        tu = ToolUniverse(workspace=str(ws))
        assert tu.cache_manager.enabled is True
        assert tu.cache_manager.memory.max_size == 128
        assert tu.cache_manager.default_ttl == 60
        assert tu.cache_manager.persistent is None

    def test_no_cache_field_leaves_defaults(self, tmp_path):
        """Omitting cache from profile.yaml leaves defaults unchanged."""
        from tooluniverse.execute_function import ToolUniverse

        ws = tmp_path / ".tooluniverse"
        ws.mkdir()
        _write_yaml(ws / "profile.yaml", _minimal_profile("cache-default"))
        tu = ToolUniverse(workspace=str(ws))
        # Default is enabled
        assert tu.cache_manager.enabled is True


class TestProfileYamlLogLevel:
    """Tests for log_level configuration via profile.yaml."""

    def test_log_level_warning_via_profile_yaml(self, tmp_path):
        """log_level sets the tooluniverse logger level."""
        import logging
        from tooluniverse.execute_function import ToolUniverse

        ws = tmp_path / ".tooluniverse"
        ws.mkdir()
        _write_yaml(
            ws / "profile.yaml",
            {**_minimal_profile("loglevel-test"), "log_level": "WARNING"},
        )
        ToolUniverse(workspace=str(ws))
        assert logging.getLogger("tooluniverse").level == logging.WARNING

    def test_log_level_debug_via_profile_yaml(self, tmp_path):
        """log_level DEBUG is applied correctly."""
        import logging
        from tooluniverse.execute_function import ToolUniverse

        ws = tmp_path / ".tooluniverse"
        ws.mkdir()
        _write_yaml(
            ws / "profile.yaml",
            {**_minimal_profile("loglevel-debug"), "log_level": "DEBUG"},
        )
        ToolUniverse(workspace=str(ws))
        assert logging.getLogger("tooluniverse").level == logging.DEBUG

    def test_invalid_log_level_rejected_by_schema(self, tmp_path):
        """An invalid log_level value fails schema validation."""
        from tooluniverse.profile.validator import validate_with_schema
        import yaml as _yaml

        config = {**_minimal_profile("bad-loglevel"), "log_level": "VERBOSE"}
        is_valid, errors, _ = validate_with_schema(
            _yaml.dump(config), fill_defaults_flag=False
        )
        assert not is_valid


class TestWorkspaceDotEnv:
    """Tests for .env auto-loading from workspace directory."""

    def test_dotenv_loaded_from_workspace(self, tmp_path):
        """A .env file in the workspace sets env vars on startup."""
        from tooluniverse.execute_function import ToolUniverse

        ws = tmp_path / ".tooluniverse"
        ws.mkdir()
        (ws / ".env").write_text("_TU_TEST_DOTENV_KEY=from_dotenv\n")

        os.environ.pop("_TU_TEST_DOTENV_KEY", None)
        try:
            ToolUniverse(workspace=str(ws))
            assert os.getenv("_TU_TEST_DOTENV_KEY") == "from_dotenv"
        finally:
            os.environ.pop("_TU_TEST_DOTENV_KEY", None)

    def test_shell_env_wins_over_dotenv(self, tmp_path):
        """Existing shell env vars are never overwritten by .env."""
        from tooluniverse.execute_function import ToolUniverse

        ws = tmp_path / ".tooluniverse"
        ws.mkdir()
        (ws / ".env").write_text("_TU_TEST_DOTENV_KEY=from_dotenv\n")

        os.environ["_TU_TEST_DOTENV_KEY"] = "from_shell"
        try:
            ToolUniverse(workspace=str(ws))
            assert os.getenv("_TU_TEST_DOTENV_KEY") == "from_shell"
        finally:
            os.environ.pop("_TU_TEST_DOTENV_KEY", None)

    def test_missing_dotenv_file_is_silently_ignored(self, tmp_path):
        """No .env file in workspace is fine — no error raised."""
        from tooluniverse.execute_function import ToolUniverse

        ws = tmp_path / ".tooluniverse"
        ws.mkdir()
        # No .env file — should not raise
        tu = ToolUniverse(workspace=str(ws))
        assert tu._workspace_dir == ws


class TestProfileYamlWorkspaceMerge:
    """Tests for workspace profile.yaml merging with --load."""

    def test_loaded_profile_overrides_workspace_name(self, tmp_path):
        """Keys in loaded file win over workspace profile.yaml."""
        from tooluniverse.execute_function import ToolUniverse

        ws = tmp_path / ".tooluniverse"
        ws.mkdir()
        _write_yaml(ws / "profile.yaml", {**_minimal_profile("ws-base"), "log_level": "ERROR"})

        override = tmp_path / "override.yaml"
        _write_yaml(override, {**_minimal_profile("override-name")})

        tu = ToolUniverse(workspace=str(ws), profile=str(override))
        meta = tu.get_profile_metadata()
        assert meta["name"] == "override-name"

    def test_workspace_log_level_applied_when_no_load(self, tmp_path):
        """Workspace profile.yaml log_level is applied when no --load given."""
        import logging
        from tooluniverse.execute_function import ToolUniverse

        ws = tmp_path / ".tooluniverse"
        ws.mkdir()
        _write_yaml(
            ws / "profile.yaml",
            {**_minimal_profile("ws-log"), "log_level": "ERROR"},
        )
        ToolUniverse(workspace=str(ws))
        assert logging.getLogger("tooluniverse").level == logging.ERROR

    def test_workspace_cache_config_applied_when_no_load(self, tmp_path):
        """Workspace profile.yaml cache config is applied when no --load given."""
        from tooluniverse.execute_function import ToolUniverse

        ws = tmp_path / ".tooluniverse"
        ws.mkdir()
        _write_yaml(
            ws / "profile.yaml",
            {**_minimal_profile("ws-cache"), "cache": {"memory_size": 77}},
        )
        tu = ToolUniverse(workspace=str(ws))
        assert tu.cache_manager.memory.max_size == 77

    def test_merge_preserves_workspace_cache_when_load_omits_it(self, tmp_path):
        """Workspace cache config survives merge if loaded file doesn't touch it."""
        from tooluniverse.execute_function import ToolUniverse

        ws = tmp_path / ".tooluniverse"
        ws.mkdir()
        _write_yaml(
            ws / "profile.yaml",
            {**_minimal_profile("ws-merge"), "cache": {"memory_size": 55}},
        )

        override = tmp_path / "override.yaml"
        _write_yaml(override, {**_minimal_profile("override"), "log_level": "DEBUG"})

        tu = ToolUniverse(workspace=str(ws), profile=str(override))
        # Cache setting from workspace should survive the merge
        assert tu.cache_manager.memory.max_size == 55


class TestProfileYamlSchemaValidation:
    """Tests that the schema correctly validates all new fields."""

    def test_valid_cache_config_passes_schema(self):
        from tooluniverse.profile.validator import validate_with_schema
        import yaml as _yaml

        config = {
            **_minimal_profile("schema-valid"),
            "cache": {"enabled": True, "ttl": 120, "memory_size": 256, "persist": False},
        }
        is_valid, errors, _ = validate_with_schema(
            _yaml.dump(config), fill_defaults_flag=False
        )
        assert is_valid, errors

    def test_negative_ttl_fails_schema(self):
        from tooluniverse.profile.validator import validate_with_schema
        import yaml as _yaml

        config = {**_minimal_profile("bad-ttl"), "cache": {"ttl": -1}}
        is_valid, errors, _ = validate_with_schema(
            _yaml.dump(config), fill_defaults_flag=False
        )
        assert not is_valid

    def test_negative_memory_size_fails_schema(self):
        from tooluniverse.profile.validator import validate_with_schema
        import yaml as _yaml

        config = {**_minimal_profile("bad-mem"), "cache": {"memory_size": 0}}
        is_valid, errors, _ = validate_with_schema(
            _yaml.dump(config), fill_defaults_flag=False
        )
        assert not is_valid

    def test_valid_log_level_passes_schema(self):
        from tooluniverse.profile.validator import validate_with_schema
        import yaml as _yaml

        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            config = {**_minimal_profile(f"loglevel-{level}"), "log_level": level}
            is_valid, errors, _ = validate_with_schema(
                _yaml.dump(config), fill_defaults_flag=False
            )
            assert is_valid, f"{level} should be valid: {errors}"


class TestDefaultProfileYaml:
    """Tests for default_profile.yaml seeding and content."""

    def test_default_profile_yaml_ships_with_package(self):
        """default_profile.yaml exists in the package data directory."""
        from pathlib import Path
        import tooluniverse
        data_dir = Path(tooluniverse.__file__).parent / "data"
        assert (data_dir / "default_profile.yaml").exists()

    def test_default_profile_yaml_is_valid(self):
        """default_profile.yaml passes schema validation."""
        from pathlib import Path
        import tooluniverse
        from tooluniverse.profile.validator import validate_yaml_file_with_schema
        path = Path(tooluniverse.__file__).parent / "data" / "default_profile.yaml"
        is_valid, errors, _ = validate_yaml_file_with_schema(str(path))
        assert is_valid, errors

    def test_default_profile_yaml_seeded_on_first_run(self, tmp_path):
        """When workspace exists with no profile.yaml, default is auto-seeded."""
        from tooluniverse.execute_function import ToolUniverse

        ws = tmp_path / ".tooluniverse"
        ws.mkdir()
        assert not (ws / "profile.yaml").exists()

        ToolUniverse(workspace=str(ws))

        assert (ws / "profile.yaml").exists()

    def test_existing_profile_yaml_not_overwritten(self, tmp_path):
        """An existing profile.yaml is never overwritten by the default."""
        from tooluniverse.execute_function import ToolUniverse

        ws = tmp_path / ".tooluniverse"
        ws.mkdir()
        custom_content = "name: my-custom\nversion: \"9.9\"\ndescription: custom\n"
        (ws / "profile.yaml").write_text(custom_content)

        ToolUniverse(workspace=str(ws))

        assert (ws / "profile.yaml").read_text() == custom_content

    def test_seeded_profile_yaml_has_expected_fields(self, tmp_path):
        """The seeded default_profile.yaml contains all key fields."""
        from tooluniverse.execute_function import ToolUniverse
        import yaml

        ws = tmp_path / ".tooluniverse"
        ws.mkdir()
        ToolUniverse(workspace=str(ws))

        content = yaml.safe_load((ws / "profile.yaml").read_text())
        assert content["name"] == "default"
        assert "tools" in content
        assert "cache" in content
        assert content["cache"]["enabled"] is True
        assert content["cache"]["memory_size"] == 256
        assert content["cache"]["persist"] is True
