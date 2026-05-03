"""
Robustness tests — deliberate bad inputs to expose fragile error handling.

Categories tested:
  1. Wrong YAML setup     — bad syntax, wrong types, invalid values, missing fields
  2. Wrong workspace      — broken .tooluniverse/ layouts and .env files
  3. Wrong Python calls   — bad API usage and invalid arguments
  4. Wrong config logic   — contradictory or nonsensical but valid-looking configs
"""

import os
import stat
import pytest
import tempfile
import textwrap
from pathlib import Path

from tooluniverse.profile.validator import validate_with_schema
from tooluniverse.execute_function import ToolUniverse


# ─────────────────────────────────────────────────────────────────────────────
# 1. Wrong YAML Setup
# ─────────────────────────────────────────────────────────────────────────────

class TestBadYamlSyntax:
    """Syntactically broken YAML — the parser should return an error, not crash."""

    def test_tabs_instead_of_spaces(self):
        yaml = "name: test\nversion: '1.0'\ntools:\n\tcategories: [literature]"
        ok, errors, _ = validate_with_schema(yaml)
        assert not ok
        assert errors

    def test_unclosed_quote(self):
        yaml = "name: 'test\nversion: '1.0'"
        ok, errors, _ = validate_with_schema(yaml)
        assert not ok
        assert errors

    def test_duplicate_keys(self):
        # PyYAML silently takes the last value; validate should still pass or warn
        yaml = "name: first\nname: second\nversion: '1.0'"
        ok, errors, cfg = validate_with_schema(yaml)
        # should not crash; if valid the last key wins
        assert isinstance(ok, bool)

    def test_empty_yaml(self):
        ok, errors, _ = validate_with_schema("")
        assert not ok

    def test_yaml_is_a_list_not_dict(self):
        yaml = "- item1\n- item2\n"
        ok, errors, _ = validate_with_schema(yaml)
        assert not ok

    def test_yaml_is_a_scalar(self):
        ok, errors, _ = validate_with_schema("just a string")
        assert not ok

    def test_deeply_nested_garbage(self):
        yaml = "name: x\nversion: '1.0'\ntools:\n  categories:\n    - {bad: [1, 2, {even: worse}]}"
        ok, errors, _ = validate_with_schema(yaml)
        # categories items must be strings — should fail
        assert not ok


class TestMissingRequiredFields:
    """Required fields: name and version."""

    def test_missing_name(self):
        yaml = "version: '1.0'"
        ok, errors, _ = validate_with_schema(yaml)
        assert not ok
        assert any("name" in e for e in errors)

    def test_missing_version(self):
        # version is optional — omitting it is fine; fill_defaults injects "1.0.0"
        yaml = "name: test"
        ok, errors, cfg = validate_with_schema(yaml)
        assert ok
        assert cfg.get("version") == "1.0.0"

    def test_missing_both(self):
        yaml = "description: no name or version"
        ok, errors, _ = validate_with_schema(yaml)
        assert not ok

    def test_name_is_empty_string(self):
        # Empty string passes type check but is semantically bad
        yaml = "name: ''\nversion: '1.0'"
        ok, errors, _ = validate_with_schema(yaml)
        # JSON schema allows empty string — document the behavior
        assert isinstance(ok, bool)

    def test_name_is_integer(self):
        yaml = "name: 42\nversion: '1.0'"
        ok, errors, _ = validate_with_schema(yaml)
        assert not ok

    def test_version_is_integer(self):
        yaml = "name: test\nversion: 1"
        ok, errors, _ = validate_with_schema(yaml)
        assert not ok


class TestWrongFieldTypes:
    """Type mismatches that the schema should reject."""

    def _base(self, extra):
        return f"name: test\nversion: '1.0'\n{extra}"

    def test_cache_memory_size_string(self):
        ok, errors, _ = validate_with_schema(self._base("cache:\n  memory_size: 'big'"))
        assert not ok

    def test_cache_memory_size_float(self):
        ok, errors, _ = validate_with_schema(self._base("cache:\n  memory_size: 1.5"))
        assert not ok

    def test_cache_enabled_string(self):
        ok, errors, _ = validate_with_schema(self._base("cache:\n  enabled: 'yes'"))
        assert not ok

    def test_cache_ttl_string(self):
        ok, errors, _ = validate_with_schema(self._base("cache:\n  ttl: 'forever'"))
        assert not ok

    def test_tags_is_string_not_list(self):
        ok, errors, _ = validate_with_schema(self._base("tags: biology"))
        assert not ok

    def test_required_env_is_dict(self):
        ok, errors, _ = validate_with_schema(self._base("required_env:\n  KEY: value"))
        assert not ok

    def test_hooks_is_dict_not_list(self):
        ok, errors, _ = validate_with_schema(
            self._base("hooks:\n  type: SummarizationHook\n  enabled: true")
        )
        assert not ok

    def test_tools_categories_contains_integer(self):
        ok, errors, _ = validate_with_schema(
            self._base("tools:\n  categories:\n    - 42")
        )
        assert not ok


class TestOutOfRangeValues:
    """Values that fail min/max constraints."""

    def _base(self, extra):
        return f"name: test\nversion: '1.0'\n{extra}"

    def test_cache_memory_size_zero(self):
        ok, errors, _ = validate_with_schema(self._base("cache:\n  memory_size: 0"))
        assert not ok

    def test_cache_memory_size_negative(self):
        ok, errors, _ = validate_with_schema(self._base("cache:\n  memory_size: -10"))
        assert not ok

    def test_cache_ttl_negative(self):
        ok, errors, _ = validate_with_schema(self._base("cache:\n  ttl: -1"))
        assert not ok

    def test_llm_temperature_too_high(self):
        ok, errors, _ = validate_with_schema(
            self._base("llm_config:\n  temperature: 5.0")
        )
        assert not ok

    def test_llm_temperature_negative(self):
        ok, errors, _ = validate_with_schema(
            self._base("llm_config:\n  temperature: -0.5")
        )
        assert not ok


class TestInvalidEnumValues:
    def _base(self, extra):
        return f"name: test\nversion: '1.0'\n{extra}"

    def test_invalid_log_level(self):
        ok, errors, _ = validate_with_schema(self._base("log_level: VERBOSE"))
        assert not ok

    def test_log_level_lowercase(self):
        # Schema enums are case-sensitive — lowercase should fail
        ok, errors, _ = validate_with_schema(self._base("log_level: debug"))
        assert not ok

    def test_invalid_llm_mode(self):
        ok, errors, _ = validate_with_schema(
            self._base("llm_config:\n  mode: turbo")
        )
        assert not ok


class TestHookValidation:
    def _base(self, extra):
        return f"name: test\nversion: '1.0'\n{extra}"

    def test_hook_missing_type(self):
        ok, errors, _ = validate_with_schema(
            self._base("hooks:\n  - enabled: true\n    config:\n      max_length: 500")
        )
        assert not ok

    def test_hook_enabled_is_string(self):
        ok, errors, _ = validate_with_schema(
            self._base("hooks:\n  - type: SummarizationHook\n    enabled: 'yes'")
        )
        assert not ok


# ─────────────────────────────────────────────────────────────────────────────
# 2. Wrong Workspace / .tooluniverse Structure
# ─────────────────────────────────────────────────────────────────────────────

class TestBadWorkspacePaths:
    """Non-existent or invalid workspace paths passed to ToolUniverse()."""

    def test_workspace_does_not_exist(self):
        tu = ToolUniverse(workspace="/tmp/this_path_does_not_exist_xyz_123")
        # Should not raise; workspace simply doesn't auto-seed anything
        assert tu is not None

    def test_workspace_is_a_file_not_dir(self):
        # _resolve_workspace() must raise a clear ValueError (not a bare
        # FileExistsError) when the supplied path is an existing file.
        with tempfile.NamedTemporaryFile(suffix=".tooluniverse") as f:
            with pytest.raises(ValueError, match="not a directory"):
                ToolUniverse(workspace=f.name)

    def test_workspace_is_empty_string(self):
        # Empty string workspace — should not crash
        try:
            tu = ToolUniverse(workspace="")
            assert tu is not None
        except Exception as e:
            # If it raises, it should be a clear error, not an AttributeError
            assert not isinstance(e, AttributeError)

    def test_workspace_is_none(self):
        tu = ToolUniverse(workspace=None)
        assert tu is not None


class TestBrokenDotEnv:
    """Various malformed .env files — should not crash, should just skip/warn."""

    def _make_ws(self, env_content):
        d = tempfile.mkdtemp()
        Path(d, ".env").write_text(env_content)
        return d

    def test_env_with_no_equals(self):
        ws = self._make_ws("NOTAKEY\n")
        tu = ToolUniverse(workspace=ws)
        assert tu is not None

    def test_env_with_binary_garbage(self):
        d = tempfile.mkdtemp()
        Path(d, ".env").write_bytes(b"\xff\xfe INVALID_UTF8 \x00\x01")
        tu = ToolUniverse(workspace=d)
        assert tu is not None

    def test_env_completely_empty(self):
        ws = self._make_ws("")
        tu = ToolUniverse(workspace=ws)
        assert tu is not None

    def test_env_with_spaces_in_key(self):
        ws = self._make_ws("MY KEY = value\n")
        tu = ToolUniverse(workspace=ws)
        assert tu is not None


class TestBrokenProfileYaml:
    """Broken profile.yaml in workspace — load_profile should surface a clear error."""

    def _ws_with_profile(self, content):
        d = tempfile.mkdtemp()
        Path(d, "profile.yaml").write_text(content)
        return d

    def test_load_profile_with_invalid_syntax(self):
        ws = self._ws_with_profile("name: test\n\ttabs: break: yaml")
        tu = ToolUniverse(workspace=ws)
        with pytest.raises(Exception):
            tu.load_profile(str(Path(ws, "profile.yaml")))

    def test_load_profile_with_missing_name(self):
        ws = self._ws_with_profile("version: '1.0'\ntools:\n  categories: []\n")
        tu = ToolUniverse(workspace=ws)
        with pytest.raises(Exception):
            tu.load_profile(str(Path(ws, "profile.yaml")))

    def test_load_profile_with_wrong_cache_type(self):
        ws = self._ws_with_profile(
            "name: x\nversion: '1.0'\ncache:\n  memory_size: 'not-a-number'\n"
        )
        tu = ToolUniverse(workspace=ws)
        with pytest.raises(Exception):
            tu.load_profile(str(Path(ws, "profile.yaml")))

    def test_load_profile_nonexistent_file(self):
        tu = ToolUniverse()
        with pytest.raises(Exception):
            tu.load_profile("/tmp/totally_missing_file_xyz.yaml")

    def test_load_profile_empty_path(self):
        tu = ToolUniverse()
        with pytest.raises(Exception):
            tu.load_profile("")

    def test_load_profile_directory_not_file(self):
        tu = ToolUniverse()
        with pytest.raises(Exception):
            tu.load_profile(tempfile.mkdtemp())


# ─────────────────────────────────────────────────────────────────────────────
# 3. Wrong Python API Usage
# ─────────────────────────────────────────────────────────────────────────────

class TestBadApiCalls:
    """Wrong arguments to ToolUniverse methods."""

    def setup_method(self):
        self.tu = ToolUniverse()
        self.tu.load_tools(categories=["special_tools"])

    def test_run_nonexistent_tool(self):
        result = self.tu.run({"name": "this_tool_does_not_exist_xyz", "arguments": {}})
        # Should return an error result, not raise
        assert result is not None

    def test_run_empty_tool_name(self):
        result = self.tu.run({"name": "", "arguments": {}})
        assert result is not None

    def test_run_none_tool_name(self):
        try:
            result = self.tu.run({"name": None, "arguments": {}})
            assert result is not None
        except Exception as e:
            assert not isinstance(e, AttributeError)

    def test_run_with_none_arguments(self):
        result = self.tu.run({"name": "this_tool_does_not_exist_xyz", "arguments": None})
        assert result is not None

    def test_run_empty_dict(self):
        result = self.tu.run({})
        assert result is not None

    def test_run_none_input(self):
        try:
            result = self.tu.run(None)
            assert result is not None
        except Exception as e:
            assert not isinstance(e, AttributeError)

    def test_load_tools_nonexistent_category(self):
        tu = ToolUniverse()
        # Should warn/log but not raise
        tu.load_tools(categories=["category_that_does_not_exist_xyz"])
        assert tu is not None

    def test_load_tools_empty_categories(self):
        tu = ToolUniverse()
        tu.load_tools(categories=[])
        assert tu is not None

    def test_load_tools_categories_contains_none(self):
        tu = ToolUniverse()
        try:
            tu.load_tools(categories=[None])
            assert tu is not None
        except Exception as e:
            assert not isinstance(e, AttributeError)

    def test_load_tools_categories_contains_integer(self):
        tu = ToolUniverse()
        try:
            tu.load_tools(categories=[42])
            assert tu is not None
        except Exception as e:
            assert not isinstance(e, AttributeError)


# ─────────────────────────────────────────────────────────────────────────────
# 4. Wrong Config Logic (valid YAML, nonsensical semantics)
# ─────────────────────────────────────────────────────────────────────────────

class TestContradictoryConfig:
    """Configs that are schema-valid but semantically contradictory."""

    def _valid(self, extra=""):
        return f"name: test\nversion: \"1.0\"\n{extra}"

    def test_same_tool_in_include_and_exclude(self):
        """Including and excluding the same tool — exclude should win."""
        yaml = self._valid(
            "tools:\n  include_tools: [UniProt_search]\n  exclude_tools: [UniProt_search]\n"
        )
        ok, errors, cfg = validate_with_schema(yaml)
        assert ok  # schema doesn't catch this — it's a semantic issue
        with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
            f.write(yaml)
            f.flush()
            tu = ToolUniverse()
            tu.load_profile(f.name)  # should not raise

    def test_same_type_in_include_and_exclude_tool_types(self):
        """Including and excluding the same tool type."""
        yaml = self._valid(
            "tools:\n  include_tool_types: [RESTTool]\n  exclude_tool_types: [RESTTool]\n"
        )
        ok, errors, _ = validate_with_schema(yaml)
        assert ok
        with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
            f.write(yaml)
            f.flush()
            tu = ToolUniverse()
            tu.load_profile(f.name)  # should not raise

    def test_nonexistent_category_silently_skipped(self):
        """Loading a non-existent category name should warn but not crash."""
        yaml = self._valid("tools:\n  categories: [this_category_does_not_exist_xyz]\n")
        ok, _, _ = validate_with_schema(yaml)
        assert ok  # schema doesn't validate category names
        with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
            f.write(yaml)
            f.flush()
            tu = ToolUniverse()
            tu.load_profile(f.name)  # should not raise

    def test_extends_nonexistent_file(self):
        """extends pointing to a file that doesn't exist."""
        yaml = self._valid("extends: /tmp/does_not_exist_xyz.yaml\n")
        ok, _, _ = validate_with_schema(yaml)
        assert ok  # schema accepts any string for extends
        with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
            f.write(yaml)
            f.flush()
            tu = ToolUniverse()
            # Should raise a clear error, not a silent AttributeError or KeyError
            try:
                tu.load_profile(f.name)
            except Exception as e:
                assert not isinstance(e, (AttributeError, KeyError))

    def test_cache_ttl_zero(self):
        """ttl=0 means 'cache forever' per the schema description — should be valid."""
        yaml = self._valid("cache:\n  ttl: 0\n")
        ok, errors, _ = validate_with_schema(yaml)
        assert ok

    def test_very_large_memory_size(self):
        """Unreasonably large memory_size — valid per schema, system should handle it."""
        yaml = self._valid("cache:\n  memory_size: 9999999\n")
        ok, errors, _ = validate_with_schema(yaml)
        assert ok

    def test_empty_tool_lists(self):
        """All tool lists empty — effectively loads nothing, should not crash."""
        yaml = self._valid(
            "tools:\n"
            "  categories: []\n"
            "  include_tools: []\n"
            "  exclude_tools: []\n"
            "  include_tool_types: []\n"
            "  exclude_tool_types: []\n"
        )
        ok, errors, _ = validate_with_schema(yaml)
        assert ok
