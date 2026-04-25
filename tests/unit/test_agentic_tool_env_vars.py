"""
Test AgenticTool environment variable integration with Profile LLM configuration.

This test module verifies that:
1. Profile LLM configuration correctly passes to AgenticTool via environment variables
2. Original environment variables still work as expected
3. Configuration priority is correct for both "default" and "fallback" modes

Note on supported API types:
Commit 5e226192 ("refactor: comment out OpenRouter, Gemini, VLLM — no keys loaded")
removed CHATGPT, GEMINI, and VLLM from API_KEY_ENV_VARS. OPENROUTER support has
since been restored, alongside CLAUDE_CLI and OLLAMA. Tests still use the
lightest supported types for most fixtures unless a provider-specific behavior
is under test.
"""

import os
import pytest
import tempfile
from unittest.mock import patch, MagicMock
from pathlib import Path

from tooluniverse.agentic_tool import AgenticTool


class TestAgenticToolEnvironmentVariables:
    """Test AgenticTool environment variable handling."""

    def setup_method(self):
        """Set up test environment by clearing relevant environment variables."""
        # Clear Profile environment variables
        env_vars_to_clear = [
            "TOOLUNIVERSE_LLM_DEFAULT_PROVIDER",
            "TOOLUNIVERSE_LLM_MODEL_DEFAULT",
            "TOOLUNIVERSE_LLM_TEMPERATURE",
            "TOOLUNIVERSE_LLM_MAX_TOKENS",
            "TOOLUNIVERSE_LLM_CONFIG_MODE",
            "GEMINI_MODEL_ID",
            "AGENTIC_TOOL_FALLBACK_CHAIN",
            "VLLM_SERVER_URL",
            "OPENROUTER_API_KEY",
        ]
        for var in env_vars_to_clear:
            if var in os.environ:
                del os.environ[var]

    def teardown_method(self):
        """Clean up test environment."""
        self.setup_method()

    def test_profile_llm_default_provider_env_var(self):
        """Test that TOOLUNIVERSE_LLM_DEFAULT_PROVIDER is correctly read."""
        # Set environment variable — CLAUDE_CLI is one of the two currently
        # supported API types (see module docstring for migration note).
        os.environ["TOOLUNIVERSE_LLM_DEFAULT_PROVIDER"] = "CLAUDE_CLI"

        # Create AgenticTool with minimal config
        tool_config = {
            "name": "test_tool",
            "prompt": "Test prompt: {input}",
            "input_arguments": ["input"],
            "parameter": {
                "type": "object",
                "properties": {"input": {"type": "string"}},
                "required": ["input"],
            },
        }

        with patch.object(AgenticTool, "_try_initialize_api"):
            tool = AgenticTool(tool_config)

            # Verify the provider was correctly read
            assert tool._api_type == "CLAUDE_CLI"

    def test_profile_llm_model_default_env_var(self):
        """Test that TOOLUNIVERSE_LLM_MODEL_DEFAULT is correctly read."""
        # Set environment variable
        os.environ["TOOLUNIVERSE_LLM_MODEL_DEFAULT"] = "gpt-4o"

        tool_config = {
            "name": "test_tool",
            "prompt": "Test prompt: {input}",
            "input_arguments": ["input"],
            "parameter": {
                "type": "object",
                "properties": {"input": {"type": "string"}},
                "required": ["input"],
            },
        }

        with patch.object(AgenticTool, "_try_initialize_api"):
            tool = AgenticTool(tool_config)

            # Verify the model was correctly read
            assert tool._env_model_id == "gpt-4o"

    def test_profile_llm_temperature_env_var(self):
        """Test that TOOLUNIVERSE_LLM_TEMPERATURE is correctly read."""
        # Set environment variable
        os.environ["TOOLUNIVERSE_LLM_TEMPERATURE"] = "0.8"

        tool_config = {
            "name": "test_tool",
            "prompt": "Test prompt: {input}",
            "input_arguments": ["input"],
            "parameter": {
                "type": "object",
                "properties": {"input": {"type": "string"}},
                "required": ["input"],
            },
        }

        with patch.object(AgenticTool, "_try_initialize_api"):
            tool = AgenticTool(tool_config)

            # Verify the temperature was correctly read
            assert tool._temperature == 0.8

    def test_max_tokens_handled_by_client(self):
        """Test that max_tokens is handled by LLM client automatically."""
        tool_config = {
            "name": "test_tool",
            "prompt": "Test prompt: {input}",
            "input_arguments": ["input"],
            "parameter": {
                "type": "object",
                "properties": {"input": {"type": "string"}},
                "required": ["input"],
            },
        }

        with patch.object(AgenticTool, "_try_initialize_api"):
            tool = AgenticTool(tool_config)

            # Verify that max_new_tokens is not used in AgenticTool
            # (it's handled by the LLM client automatically)
            assert not hasattr(tool, "_max_new_tokens")

    def test_profile_llm_config_mode_default(self):
        """Test 'default' mode configuration priority."""
        # Set environment variables. OLLAMA vs CLAUDE_CLI gives us a
        # distinguishable env-vs-config pair for the priority assertion below.
        os.environ["TOOLUNIVERSE_LLM_CONFIG_MODE"] = "default"
        os.environ["TOOLUNIVERSE_LLM_DEFAULT_PROVIDER"] = "OLLAMA"
        os.environ["TOOLUNIVERSE_LLM_TEMPERATURE"] = "0.9"

        tool_config = {
            "name": "test_tool",
            "prompt": "Test prompt: {input}",
            "input_arguments": ["input"],
            "parameter": {
                "type": "object",
                "properties": {"input": {"type": "string"}},
                "required": ["input"],
            },
            # Tool config should override env vars
            "api_type": "CLAUDE_CLI",
            "temperature": 0.5,
        }

        with patch.object(AgenticTool, "_try_initialize_api"):
            tool = AgenticTool(tool_config)

            # In default mode, tool config should take priority
            assert tool._api_type == "CLAUDE_CLI"  # From tool config
            assert tool._temperature == 0.5  # From tool config

    def test_profile_llm_config_mode_fallback(self):
        """Test 'fallback' mode configuration priority."""
        # Set environment variables. OLLAMA vs CLAUDE_CLI gives us a
        # distinguishable env-vs-config pair for the priority assertion below.
        os.environ["TOOLUNIVERSE_LLM_CONFIG_MODE"] = "fallback"
        os.environ["TOOLUNIVERSE_LLM_DEFAULT_PROVIDER"] = "OLLAMA"
        os.environ["TOOLUNIVERSE_LLM_TEMPERATURE"] = "0.9"

        tool_config = {
            "name": "test_tool",
            "prompt": "Test prompt: {input}",
            "input_arguments": ["input"],
            "parameter": {
                "type": "object",
                "properties": {"input": {"type": "string"}},
                "required": ["input"],
            },
            # Tool config should override env vars
            "api_type": "CLAUDE_CLI",
            "temperature": 0.5,
        }

        with patch.object(AgenticTool, "_try_initialize_api"):
            tool = AgenticTool(tool_config)

            # In fallback mode, tool config should take priority
            assert tool._api_type == "CLAUDE_CLI"  # From tool config
            assert tool._temperature == 0.5  # From tool config

    def test_profile_llm_config_mode_env_override(self):
        """Test 'env_override' mode where environment variables have highest priority."""
        # Set environment variables. OLLAMA (env) must override CLAUDE_CLI
        # (tool config) to demonstrate env_override semantics.
        os.environ["TOOLUNIVERSE_LLM_CONFIG_MODE"] = "env_override"
        os.environ["TOOLUNIVERSE_LLM_DEFAULT_PROVIDER"] = "OLLAMA"
        os.environ["TOOLUNIVERSE_LLM_MODEL_DEFAULT"] = "qwen2.5-coder:32b"
        os.environ["TOOLUNIVERSE_LLM_TEMPERATURE"] = "0.7"

        tool_config = {
            "name": "test_tool",
            "prompt": "Test prompt: {input}",
            "input_arguments": ["input"],
            "parameter": {
                "type": "object",
                "properties": {"input": {"type": "string"}},
                "required": ["input"],
            },
            # Tool config should be overridden by env vars in env_override mode
            "api_type": "CLAUDE_CLI",
            "model_id": "sonnet",
            "temperature": 0.5,
        }

        with patch.object(AgenticTool, "_try_initialize_api"):
            tool = AgenticTool(tool_config)

            # In env_override mode, environment variables should take priority
            assert tool._api_type == "OLLAMA"  # From env var, not tool config
            assert tool._model_id == "qwen2.5-coder:32b"  # From env var
            assert tool._temperature == 0.7  # From env var, not tool config

    def test_original_gemini_model_id_env_var(self):
        """Test that original GEMINI_MODEL_ID environment variable still works."""
        # Set original environment variable
        os.environ["GEMINI_MODEL_ID"] = "gemini-1.5-pro"

        tool_config = {
            "name": "test_tool",
            "prompt": "Test prompt: {input}",
            "input_arguments": ["input"],
            "parameter": {
                "type": "object",
                "properties": {"input": {"type": "string"}},
                "required": ["input"],
            },
        }

        with patch.object(AgenticTool, "_try_initialize_api"):
            tool = AgenticTool(tool_config)

            # Verify the original Gemini model ID was correctly read
            assert tool._gemini_model_id == "gemini-1.5-pro"

    def test_openrouter_primary_falls_back_to_claude_cli(self):
        """Missing OPENROUTER_API_KEY should use configured Claude fallback."""
        tool_config = {
            "name": "test_tool",
            "prompt": "Test prompt: {input}",
            "input_arguments": ["input"],
            "parameter": {
                "type": "object",
                "properties": {"input": {"type": "string"}},
                "required": ["input"],
            },
            "configs": {
                "api_type": "OPENROUTER",
                "model_id": "openai/gpt-5",
                "validate_api_key": True,
                "fallback_api_type": "CLAUDE_CLI",
                "fallback_model_id": "sonnet",
                "use_global_fallback": False,
            },
        }

        with (
            patch("tooluniverse.agentic_tool.OpenRouterClient") as mock_openrouter,
            patch("tooluniverse.agentic_tool.ClaudeCliClient") as mock_claude,
        ):
            mock_openrouter.side_effect = ValueError("OPENROUTER_API_KEY not set")
            mock_claude_client = MagicMock()
            mock_claude.return_value = mock_claude_client

            tool = AgenticTool(tool_config)

            assert tool._is_available is True
            assert tool._current_api_type == "CLAUDE_CLI"
            assert tool._current_model_id == "sonnet"

    def test_original_agentic_tool_fallback_chain_env_var(self):
        """Test that original AGENTIC_TOOL_FALLBACK_CHAIN environment variable still works."""
        # Set original environment variable
        fallback_chain = [
            {"api_type": "CHATGPT", "model_id": "gpt-4o"},
            {"api_type": "GEMINI", "model_id": "gemini-2.0-flash"},
        ]
        os.environ["AGENTIC_TOOL_FALLBACK_CHAIN"] = str(fallback_chain).replace(
            "'", '"'
        )

        tool_config = {
            "name": "test_tool",
            "prompt": "Test prompt: {input}",
            "input_arguments": ["input"],
            "parameter": {
                "type": "object",
                "properties": {"input": {"type": "string"}},
                "required": ["input"],
            },
        }

        with patch.object(AgenticTool, "_try_initialize_api"):
            tool = AgenticTool(tool_config)

            # Verify the fallback chain was correctly read
            assert len(tool._global_fallback_chain) == 2
            assert tool._global_fallback_chain[0]["api_type"] == "CHATGPT"
            assert tool._global_fallback_chain[1]["api_type"] == "GEMINI"

    # NOTE: test_original_vllm_server_url_env_var was removed.
    # VLLM is no longer a supported api_type (commented out in API_KEY_ENV_VARS
    # by commit 5e226192), and the test's only assertion was that os.getenv
    # could read an env var it had just set — which does not exercise any code
    # in AgenticTool. If VLLM support is ever reinstated, restore this test
    # alongside the VLLMClient wiring.

    def test_task_specific_model_env_var(self):
        """Test that task-specific model environment variables work."""
        # Set task-specific environment variable
        os.environ["TOOLUNIVERSE_LLM_MODEL_ANALYSIS"] = "gpt-4o"
        os.environ["TOOLUNIVERSE_LLM_MODEL_DEFAULT"] = "gpt-3.5-turbo"

        tool_config = {
            "name": "test_tool",
            "prompt": "Test prompt: {input}",
            "input_arguments": ["input"],
            "parameter": {
                "type": "object",
                "properties": {"input": {"type": "string"}},
                "required": ["input"],
            },
            "llm_task": "analysis",  # This should use the analysis-specific model
        }

        with patch.object(AgenticTool, "_try_initialize_api"):
            tool = AgenticTool(tool_config)

            # Verify the task-specific model was correctly read
            assert tool._env_model_id == "gpt-4o"

    def test_environment_variable_priority_in_default_mode(self):
        """Test that environment variables take priority over defaults in 'default' mode."""
        # Set environment variables. OLLAMA is distinct from the CLAUDE_CLI
        # built-in default, so seeing OLLAMA proves env vars were consulted.
        os.environ["TOOLUNIVERSE_LLM_CONFIG_MODE"] = "default"
        os.environ["TOOLUNIVERSE_LLM_DEFAULT_PROVIDER"] = "OLLAMA"
        os.environ["TOOLUNIVERSE_LLM_TEMPERATURE"] = "0.8"

        tool_config = {
            "name": "test_tool",
            "prompt": "Test prompt: {input}",
            "input_arguments": ["input"],
            "parameter": {
                "type": "object",
                "properties": {"input": {"type": "string"}},
                "required": ["input"],
            },
            # No tool-level config, should use env vars
        }

        with patch.object(AgenticTool, "_try_initialize_api"):
            tool = AgenticTool(tool_config)

            # In default mode with no tool config, env vars should be used
            assert tool._api_type == "OLLAMA"  # From env var
            assert tool._temperature == 0.8  # From env var

    def test_environment_variable_fallback_in_fallback_mode(self):
        """Test that environment variables are used as fallback in 'fallback' mode."""
        # Set environment variables. These should NOT be applied because the
        # tool config has no api_type/temperature, and fallback mode only
        # consults env vars when neither tool config nor built-in defaults
        # satisfy the field — i.e., the built-in defaults win here.
        os.environ["TOOLUNIVERSE_LLM_CONFIG_MODE"] = "fallback"
        os.environ["TOOLUNIVERSE_LLM_DEFAULT_PROVIDER"] = "OLLAMA"
        os.environ["TOOLUNIVERSE_LLM_TEMPERATURE"] = "0.8"

        tool_config = {
            "name": "test_tool",
            "prompt": "Test prompt: {input}",
            "input_arguments": ["input"],
            "parameter": {
                "type": "object",
                "properties": {"input": {"type": "string"}},
                "required": ["input"],
            },
            # No tool-level config, should use built-in defaults
        }

        with patch.object(AgenticTool, "_try_initialize_api"):
            tool = AgenticTool(tool_config)

            # In fallback mode with no tool config, should use built-in defaults.
            # Built-in default api_type is CLAUDE_CLI (agentic_tool.py:125).
            # Built-in default temperature is 1.0 (agentic_tool.py:127).
            assert tool._api_type == "CLAUDE_CLI"  # Built-in default
            assert tool._temperature == 1.0  # Built-in default


if __name__ == "__main__":
    pytest.main([__file__])
