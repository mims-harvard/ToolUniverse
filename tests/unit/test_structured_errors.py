#!/usr/bin/env python3
"""
TDD: Structured error response contract tests.

RED phase — these tests define the contract:
  Every tool failure path must return a dict with
  {"status": "error", "error": str, "error_type": str}.

Tests are written BEFORE fixing the code. They must FAIL first,
then pass after each fix (GREEN), then we refactor.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


def _is_structured_error(result) -> bool:
    """Check if result matches the structured error contract."""
    return (
        isinstance(result, dict)
        and result.get("status") == "error"
        and isinstance(result.get("error"), str)
        and isinstance(result.get("error_type"), str)
    )


# ---------------------------------------------------------------------------
# tool_error() helper
# ---------------------------------------------------------------------------


class TestToolErrorHelper:
    def test_basic_error(self):
        from tooluniverse.base_tool import tool_error

        err = tool_error("something broke")
        assert _is_structured_error(err)
        assert err["error"] == "something broke"
        assert err["error_type"] == "ToolError"

    def test_custom_type_and_suggestion(self):
        from tooluniverse.base_tool import tool_error

        err = tool_error("oops", error_type="Timeout", suggestion="retry later")
        assert err["error_type"] == "Timeout"
        assert err["suggestion"] == "retry later"

    def test_accessible_via_base_tool(self):
        from tooluniverse.base_tool import BaseTool

        err = BaseTool.tool_error("test")
        assert _is_structured_error(err)


# ---------------------------------------------------------------------------
# tool_finder_llm.py: find_tools() failure paths
# ---------------------------------------------------------------------------


class TestToolFinderLLMErrors:
    def _make_finder(self):
        from datetime import datetime

        from tooluniverse.tool_finder_llm import ToolFinderLLM

        finder = object.__new__(ToolFinderLLM)
        finder.tool_config = {"name": "Tool_Finder_LLM"}
        finder.tooluniverse = None
        finder.exclude_tools = set()
        finder.include_categories = None
        finder.exclude_categories = None
        finder._tool_cache = None
        finder._cache_timestamp = None
        finder._cache_ttl = 300
        finder._fallback_api_type = None
        finder._fallback_model_id = None
        return finder

    def test_extract_llm_response_structured_error_returns_none(self):
        """Structured AgenticTool errors must trigger fallback logic."""
        finder = self._make_finder()
        result = finder._extract_llm_response(
            {
                "status": "error",
                "error": "All LLM backends returned empty",
                "error_type": "LLMBackendFailure",
            }
        )
        assert result is None

    def test_get_available_tools_no_tooluniverse(self):
        """_get_available_tools with tooluniverse=None must return structured error."""
        finder = self._make_finder()
        result = finder._get_available_tools()
        assert _is_structured_error(result), (
            f"Expected structured error, got {type(result)}: {result}"
        )

    def test_get_available_tools_exception(self, monkeypatch):
        """_get_available_tools exception path must return structured error."""
        finder = self._make_finder()
        finder.tooluniverse = MagicMock()
        finder.tooluniverse.refresh_tool_name_desc.side_effect = RuntimeError("boom")
        result = finder._get_available_tools()
        assert _is_structured_error(result), (
            f"Expected structured error, got {type(result)}: {result}"
        )

    def test_find_tools_llm_structured_error_falls_back_to_keyword_ranking(self):
        """Structured LLM failures must degrade to keyword-ranked tool selection."""
        finder = self._make_finder()
        finder.agentic_tool = MagicMock()
        finder.agentic_tool.run.return_value = {
            "status": "error",
            "error": "All LLM backends returned empty",
            "error_type": "LLMBackendFailure",
        }
        finder.tooluniverse = MagicMock()
        finder.tooluniverse.all_tool_dict = {
            "PubMed_search_articles": {},
            "ClinicalTrials_search_studies": {},
        }
        finder.tooluniverse.get_tool_specification_by_names.return_value = [
            {"name": "PubMed_search_articles"},
            {"name": "ClinicalTrials_search_studies"},
        ]
        finder.tooluniverse.prepare_tool_prompts.return_value = [
            {"name": "PubMed_search_articles"},
            {"name": "ClinicalTrials_search_studies"},
        ]
        finder._get_available_tools = MagicMock(
            return_value=[
                {
                    "name": "PubMed_search_articles",
                    "description": "Search PubMed for biomedical literature articles",
                },
                {
                    "name": "ClinicalTrials_search_studies",
                    "description": "Search clinical trials by condition and sponsor",
                },
            ]
        )

        result = finder.find_tools_llm("pubmed cancer biomarkers", limit=2)

        assert result["success"] is True
        assert result["fallback"] == "keyword_ranking"
        assert result["selected_tools"] == [
            "PubMed_search_articles",
            "ClinicalTrials_search_studies",
        ]


class TestClaudeCliClientErrors:
    def test_infer_logs_stdout_error_when_stderr_empty(self):
        """Claude CLI stdout-only failures must be surfaced in logs."""
        from tooluniverse.llm_clients import ClaudeCliClient

        logger = MagicMock()
        client = object.__new__(ClaudeCliClient)
        client._subprocess = MagicMock()
        client._claude_path = "claude"
        client.model_name = "sonnet"
        client.logger = logger
        client.timeout = 1
        client.budget = "0.10"
        client._strip_markdown_fences = lambda text: text
        client._subprocess.run.return_value = MagicMock(
            returncode=1,
            stdout='{"error":{"message":"usage capped until 2026-05-01"}}',
            stderr="",
        )

        result = client.infer(
            [{"role": "user", "content": "ping"}],
            temperature=0,
            max_tokens=8,
            return_json=False,
            max_retries=1,
            retry_delay=0,
        )

        assert result is None
        logger.error.assert_any_call(
            "claude CLI error: usage capped until 2026-05-01"
        )


# ---------------------------------------------------------------------------
# agentic_tool.py: run() failure paths
# ---------------------------------------------------------------------------


class TestAgenticToolErrors:
    def _make_tool(self, *, available=False, return_metadata=False):
        from tooluniverse.agentic_tool import AgenticTool

        tool = object.__new__(AgenticTool)
        tool.tool_config = {"name": "test_agentic"}
        tool.name = "test_agentic"
        tool._is_available = available
        tool._initialization_error = "test init error"
        tool.return_metadata = return_metadata
        tool._api_type = "CLAUDE_CLI"
        tool._model_id = "sonnet"
        tool._temperature = 0.1
        tool._input_arguments = []
        tool._required_arguments = []
        tool._system_prompt = ""
        tool._prompt_template = "{query}"
        tool._output_format = "text"
        tool._max_retries = 1
        tool._retry_delay = 0
        tool._return_json = False
        tool._llm_client = None
        tool.logger = MagicMock()
        return tool

    def test_unavailable_returns_structured_error(self):
        """run() with unavailable tool + return_metadata=False must not return a string."""
        tool = self._make_tool(available=False, return_metadata=False)
        result = tool.run({"query": "test"})
        assert _is_structured_error(result), (
            f"Expected structured error dict, got: {result!r}"
        )

    def test_none_response_returns_structured_error(self):
        """run() when LLM returns None must not propagate None."""
        tool = self._make_tool(available=True, return_metadata=False)
        tool._llm_client = MagicMock()
        tool._llm_client.infer.return_value = None
        result = tool.run({"query": "test"})
        assert result is not None, "run() must never return None"
        assert _is_structured_error(result), (
            f"Expected structured error dict, got: {result!r}"
        )


# ---------------------------------------------------------------------------
# tool_finder_embedding.py: run() exception handling
# ---------------------------------------------------------------------------


class TestToolFinderEmbeddingErrors:
    def test_run_catches_import_error(self, monkeypatch):
        """run() must catch ImportError and return structured error, not crash."""
        from tooluniverse.tool_finder_embedding import ToolFinderEmbedding

        finder = object.__new__(ToolFinderEmbedding)
        finder.tool_config = {"name": "Tool_Finder"}
        finder._dependencies_available = False
        finder._dependency_error = ImportError("no torch")
        finder.tooluniverse = None
        finder.tool_desc_embedding = None
        finder.rag_model = None
        finder._embedding_version = None
        finder._tool_names_at_embedding = set()

        result = finder.run({"description": "test query", "limit": 5})
        assert _is_structured_error(result), (
            f"Expected structured error, got exception or: {result!r}"
        )
        assert (
            "dependencies" in result["error"].lower()
            or "import" in result["error"].lower()
        )
