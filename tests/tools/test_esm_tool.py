"""
Tests for ESM3/ESMC protein language model tool.

Tests:
- Missing API key returns graceful error (not exception)
- Missing esm package returns graceful error
- Tools load into ToolUniverse registry when ESM_API_KEY is set
- Invalid/empty sequence inputs are rejected gracefully
- Unknown operation returns informative error
"""

import json
import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


@pytest.fixture(scope="module")
def tool_config():
    """Load tool config from JSON."""
    config_path = (
        Path(__file__).parent.parent.parent
        / "src"
        / "tooluniverse"
        / "data"
        / "esm_tools.json"
    )
    with open(config_path) as f:
        tools = json.load(f)
    return {t["name"]: t for t in tools}


@pytest.fixture(scope="module")
def esm_tool_cls():
    """Import and return the ESMTool class."""
    from tooluniverse.esm_tool import ESMTool  # noqa: F401 (triggers @register_tool)
    from tooluniverse.tool_registry import get_tool_registry
    registry = get_tool_registry()
    return registry["ESMTool"]


class TestESMToolMissingApiKey:
    """Level 1: Tests for graceful error handling when ESM_API_KEY is absent."""

    def test_get_protein_embedding_missing_key(self, tool_config, esm_tool_cls):
        """get_protein_embedding returns status=error when ESM_API_KEY not set."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ESM_API_KEY", None)
            config = tool_config["ESM_get_protein_embedding"]
            tool = esm_tool_cls(config)
            result = tool.run(
                {
                    "operation": "get_protein_embedding",
                    "sequence": "MKTAYIAKQRQISFVKSHFSRQ",
                }
            )
        assert result.get("status") == "error"
        assert isinstance(result.get("error"), str)
        # Should not raise, just return error dict

    def test_generate_protein_sequence_missing_key(self, tool_config, esm_tool_cls):
        """generate_protein_sequence returns status=error when ESM_API_KEY not set."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ESM_API_KEY", None)
            config = tool_config["ESM_generate_protein_sequence"]
            tool = esm_tool_cls(config)
            result = tool.run(
                {
                    "operation": "generate_protein_sequence",
                    "prompt_sequence": "MKTAY_____QRQISFVKSHFSRQ",
                }
            )
        assert result.get("status") == "error"
        assert isinstance(result.get("error"), str)

    def test_fold_protein_missing_key(self, tool_config, esm_tool_cls):
        """fold_protein returns status=error when ESM_API_KEY not set."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ESM_API_KEY", None)
            config = tool_config["ESM_fold_protein"]
            tool = esm_tool_cls(config)
            result = tool.run(
                {
                    "operation": "fold_protein",
                    "sequence": "MKTAYIAKQRQISFVKSHFSRQ",
                }
            )
        assert result.get("status") == "error"
        assert isinstance(result.get("error"), str)

    def test_score_sequence_missing_key(self, tool_config, esm_tool_cls):
        """score_sequence returns status=error when ESM_API_KEY not set."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ESM_API_KEY", None)
            config = tool_config["ESM_score_sequence"]
            tool = esm_tool_cls(config)
            result = tool.run(
                {
                    "operation": "score_sequence",
                    "sequence": "MKTAYIAKQRQISFVKSHFSRQ",
                }
            )
        assert result.get("status") == "error"
        assert isinstance(result.get("error"), str)


class TestESMToolMissingPackage:
    """Tests that gracefully handle missing 'esm' Python package."""

    def test_no_crash_when_esm_package_missing(self, tool_config, esm_tool_cls):
        """Tool returns error dict (not an exception) when esm package is unavailable."""
        with patch.dict("sys.modules", {"esm": None, "esm.sdk": None, "esm.sdk.forge": None,
                                         "esm.sdk.api": None, "esm.utils": None,
                                         "esm.utils.constants": None,
                                         "esm.utils.constants.esm3": None}):
            with patch.dict(os.environ, {"ESM_API_KEY": "dummy_key"}):
                config = tool_config["ESM_get_protein_embedding"]
                tool = esm_tool_cls(config)
                result = tool.run(
                    {
                        "operation": "get_protein_embedding",
                        "sequence": "MKTAYIAKQRQISFVKSHFSRQ",
                    }
                )
        assert isinstance(result, dict), "Should return a dict, not raise"
        assert "status" in result
        assert result["status"] == "error"


class TestESMToolInputValidation:
    """Tests for missing/invalid input parameters."""

    def test_embedding_missing_sequence(self, tool_config, esm_tool_cls):
        """get_protein_embedding returns error when sequence is not provided."""
        with patch.dict(os.environ, {"ESM_API_KEY": "dummy"}):
            config = tool_config["ESM_get_protein_embedding"]
            tool = esm_tool_cls(config)
            result = tool.run({"operation": "get_protein_embedding"})
        assert result.get("status") == "error"

    def test_generate_missing_prompt(self, tool_config, esm_tool_cls):
        """generate_protein_sequence returns error when prompt_sequence is not provided."""
        with patch.dict(os.environ, {"ESM_API_KEY": "dummy"}):
            config = tool_config["ESM_generate_protein_sequence"]
            tool = esm_tool_cls(config)
            result = tool.run({"operation": "generate_protein_sequence"})
        assert result.get("status") == "error"

    def test_fold_missing_sequence(self, tool_config, esm_tool_cls):
        """fold_protein returns error when sequence is not provided."""
        with patch.dict(os.environ, {"ESM_API_KEY": "dummy"}):
            config = tool_config["ESM_fold_protein"]
            tool = esm_tool_cls(config)
            result = tool.run({"operation": "fold_protein"})
        assert result.get("status") == "error"

    def test_score_missing_sequence(self, tool_config, esm_tool_cls):
        """score_sequence returns error when sequence is not provided."""
        with patch.dict(os.environ, {"ESM_API_KEY": "dummy"}):
            config = tool_config["ESM_score_sequence"]
            tool = esm_tool_cls(config)
            result = tool.run({"operation": "score_sequence"})
        assert result.get("status") == "error"

    def test_unknown_operation(self, tool_config, esm_tool_cls):
        """Unknown operation returns informative error."""
        with patch.dict(os.environ, {"ESM_API_KEY": "dummy"}):
            config = tool_config["ESM_get_protein_embedding"]
            tool = esm_tool_cls(config)
            result = tool.run({"operation": "fly_to_the_moon"})
        assert result.get("status") == "error"
        assert "Unknown operation" in result.get("error", "") or "fly_to_the_moon" in result.get("error", "")


class TestESMToolRegistration:
    """Level 2: Tests through ToolUniverse registration system."""

    @pytest.fixture(scope="class")
    def tu_with_key(self):
        """Load ToolUniverse with a dummy ESM_API_KEY so ESM tools are loaded."""
        with patch.dict(os.environ, {"ESM_API_KEY": "dummy_test_key_for_registration"}):
            from tooluniverse import ToolUniverse
            tu = ToolUniverse()
            tu.load_tools()
        return tu

    def test_esm_tools_registered_with_key(self, tu_with_key):
        """All 4 ESM tools appear in registry when ESM_API_KEY is set."""
        expected = [
            "ESM_get_protein_embedding",
            "ESM_generate_protein_sequence",
            "ESM_fold_protein",
            "ESM_score_sequence",
        ]
        for name in expected:
            assert name in tu_with_key.all_tool_dict, (
                f"Tool '{name}' not found in ToolUniverse registry"
            )

    def test_esm_tools_not_registered_without_key(self):
        """ESM tools are absent from registry when ESM_API_KEY is not set."""
        env_backup = os.environ.pop("ESM_API_KEY", None)
        try:
            from tooluniverse import ToolUniverse
            tu = ToolUniverse()
            tu.load_tools()
            for name in [
                "ESM_get_protein_embedding",
                "ESM_generate_protein_sequence",
                "ESM_fold_protein",
                "ESM_score_sequence",
            ]:
                assert name not in tu.all_tool_dict, (
                    f"Tool '{name}' should not be in registry without API key"
                )
        finally:
            if env_backup is not None:
                os.environ["ESM_API_KEY"] = env_backup

    def test_esm_tool_graceful_error_via_registry(self, tu_with_key):
        """ESM tool called through registry returns error dict, not an exception."""
        result = tu_with_key.run_one_function(
            {
                "name": "ESM_get_protein_embedding",
                "arguments": {
                    "operation": "get_protein_embedding",
                    "sequence": "MKTAYIAKQRQISFVKSHFSRQ",
                },
            }
        )
        # esm package is not installed, so we expect a graceful error
        assert isinstance(result, dict), "Should return a dict, not raise"
        assert "status" in result
        if result["status"] == "error":
            assert isinstance(result["error"], str)


class TestESMToolJsonConfig:
    """Level 5: Verify JSON config structure and test_examples."""

    def test_all_tools_have_required_fields(self, tool_config):
        """Each ESM tool entry has required name, type, description, parameter fields."""
        for name, cfg in tool_config.items():
            assert "name" in cfg, f"{name}: missing 'name' field"
            assert "type" in cfg, f"{name}: missing 'type' field"
            assert cfg["type"] == "ESMTool", f"{name}: type should be 'ESMTool'"
            assert "description" in cfg, f"{name}: missing 'description' field"
            assert "parameter" in cfg, f"{name}: missing 'parameter' field"
            assert "required_api_keys" in cfg, f"{name}: missing 'required_api_keys' field"
            assert "ESM_API_KEY" in cfg["required_api_keys"], (
                f"{name}: 'ESM_API_KEY' should be in required_api_keys"
            )

    def test_all_tools_have_test_examples(self, tool_config):
        """Each ESM tool has at least one test_example."""
        for name, cfg in tool_config.items():
            examples = cfg.get("test_examples", [])
            assert len(examples) > 0, f"{name}: should have at least one test_example"

    def test_test_examples_have_operation_field(self, tool_config):
        """Each test_example includes an 'operation' field."""
        for name, cfg in tool_config.items():
            for i, ex in enumerate(cfg.get("test_examples", [])):
                assert "operation" in ex, (
                    f"{name} example {i}: test_example should include 'operation' field"
                )
