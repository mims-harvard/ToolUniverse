"""Unit tests for WFGY ProblemMap prompt-bundle triage tool.

This tool is local-only (no external API or LLM calls), so all tests
run deterministically without any network dependency.
"""

import json
import pytest
from tooluniverse import ToolUniverse
from tooluniverse.wfgy_promptbundle_tool import WFGYPromptBundleTool


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def tool_config():
    """Load the tool config from the JSON file."""
    import os
    json_path = os.path.join(
        os.path.dirname(__file__),
        "../../src/tooluniverse/data/wfgy_promptbundle_tools.json",
    )
    with open(json_path) as f:
        configs = json.load(f)
    return next(c for c in configs if c["name"] == "WFGY_triage_llm_rag_failure")


@pytest.fixture(scope="module")
def tool(tool_config):
    """Instantiate WFGYPromptBundleTool directly (Level 1)."""
    return WFGYPromptBundleTool(tool_config)


@pytest.fixture(scope="module")
def tu():
    """ToolUniverse instance with all tools loaded (Level 2)."""
    tu = ToolUniverse()
    tu.load_tools()
    return tu


# ---------------------------------------------------------------------------
# Level 1 – Direct class tests
# ---------------------------------------------------------------------------

class TestWFGYPromptBundleToolDirect:
    """Test the WFGYPromptBundleTool class directly (no ToolUniverse runtime)."""

    def test_inherits_base_tool(self):
        """Class must inherit BaseTool."""
        from tooluniverse.base_tool import BaseTool
        assert issubclass(WFGYPromptBundleTool, BaseTool)

    def test_successful_response_structure(self, tool):
        """Happy path: required response keys and standard format."""
        result = tool.run({
            "bug_description": "RAG chatbot returns hallucinated facts.",
            "audience": "engineer",
        })

        assert result["status"] == "success"
        assert "data" in result
        assert "error" not in result

        data = result["data"]
        assert data["mode"] == "prompt_bundle_only"
        assert isinstance(data["system_prompt"], str)
        assert isinstance(data["user_prompt"], str)
        assert isinstance(data["how_to_use"], list)
        assert isinstance(data["checklist"], list)
        assert isinstance(data["links"], dict)
        assert isinstance(data["examples"], list)

    def test_system_prompt_contains_incident(self, tool):
        """user_prompt must embed the supplied bug_description."""
        incident = "Model returns Bitcoin info when only credit card docs retrieved."
        result = tool.run({"bug_description": incident})

        assert result["status"] == "success"
        assert incident in result["data"]["user_prompt"]

    def test_links_are_valid_urls(self, tool):
        """All link values must start with https://."""
        result = tool.run({"bug_description": "Some failure."})
        links = result["data"]["links"]

        assert len(links) > 0
        for key, url in links.items():
            assert url.startswith("https://"), f"Link '{key}' is not HTTPS: {url}"

    def test_system_prompt_references_wfgy_codes(self, tool):
        """System prompt must mention the WFGY ProblemMap codes."""
        result = tool.run({"bug_description": "Test."})
        system_prompt = result["data"]["system_prompt"]

        assert "No.1" in system_prompt
        assert "No.16" in system_prompt

    # --- audience variations ---

    @pytest.mark.parametrize("audience", ["beginner", "engineer", "infra"])
    def test_valid_audience_values(self, tool, audience):
        """All three valid audience values must succeed."""
        result = tool.run({
            "bug_description": "LLM gives wrong answer.",
            "audience": audience,
        })
        assert result["status"] == "success"
        assert result["data"]["system_prompt"]

    def test_invalid_audience_falls_back_to_engineer(self, tool):
        """Unknown audience must silently default to 'engineer'."""
        result = tool.run({
            "bug_description": "Some failure.",
            "audience": "alien",
        })
        assert result["status"] == "success"

    def test_default_audience_when_omitted(self, tool):
        """Omitting audience must still succeed."""
        result = tool.run({"bug_description": "Some failure."})
        assert result["status"] == "success"

    def test_beginner_tone_in_system_prompt(self, tool):
        """Beginner audience must include plain-language tone marker."""
        result = tool.run({"bug_description": "Test.", "audience": "beginner"})
        assert "simple" in result["data"]["system_prompt"].lower() or \
               "jargon" in result["data"]["system_prompt"].lower()

    def test_infra_tone_in_system_prompt(self, tool):
        """Infra audience must include ops-focused marker."""
        result = tool.run({"bug_description": "Test.", "audience": "infra"})
        assert "ops" in result["data"]["system_prompt"].lower() or \
               "rollout" in result["data"]["system_prompt"].lower() or \
               "readiness" in result["data"]["system_prompt"].lower()

    # --- error handling ---

    def test_missing_bug_description_returns_error(self, tool):
        """Missing required field must return error dict, not raise."""
        result = tool.run({})
        assert result["status"] == "error"
        assert "error" in result
        assert "data" not in result

    def test_empty_bug_description_returns_error(self, tool):
        """Empty string bug_description must return error."""
        result = tool.run({"bug_description": "   "})
        assert result["status"] == "error"

    def test_none_bug_description_returns_error(self, tool):
        """None bug_description must return error."""
        result = tool.run({"bug_description": None})
        assert result["status"] == "error"

    def test_no_exception_raised_on_bad_input(self, tool):
        """run() must never raise — always return a dict."""
        for bad in [{}, {"bug_description": ""}, {"bug_description": None}]:
            result = tool.run(bad)
            assert isinstance(result, dict)
            assert "status" in result


# ---------------------------------------------------------------------------
# Level 2 – ToolUniverse interface tests
# ---------------------------------------------------------------------------

class TestWFGYPromptBundleToolInterface:
    """Test the tool through the ToolUniverse runtime (as end-users would)."""

    def test_tool_registered_in_all_tools(self, tu):
        """WFGY_triage_llm_rag_failure must appear in tu.all_tools."""
        tool_names = [t.get("name") for t in tu.all_tools if isinstance(t, dict)]
        assert "WFGY_triage_llm_rag_failure" in tool_names

    def test_wrapper_accessible_on_tu_tools(self, tu):
        """Wrapper attribute must exist on tu.tools."""
        assert hasattr(tu.tools, "WFGY_triage_llm_rag_failure")

    def test_wrapper_is_callable(self, tu):
        """tu.tools.WFGY_triage_llm_rag_failure must be callable."""
        assert callable(tu.tools.WFGY_triage_llm_rag_failure)

    def test_execution_via_wrapper(self, tu):
        """End-to-end call through ToolUniverse wrapper must succeed."""
        result = tu.tools.WFGY_triage_llm_rag_failure(
            bug_description=(
                "RAG chatbot answers with facts not present in retrieved context. "
                "Retrieved chunks talk about credit cards only, "
                "but model claims Bitcoin is supported."
            ),
            audience="engineer",
        )

        assert result["status"] == "success"
        assert "data" in result
        data = result["data"]
        assert "system_prompt" in data
        assert "user_prompt" in data

    def test_wrapper_error_on_missing_required_param(self, tu):
        """Calling wrapper without bug_description must return error, not raise."""
        result = tu.tools.WFGY_triage_llm_rag_failure()
        assert result["status"] == "error"

    def test_all_audience_values_via_wrapper(self, tu):
        """All audience values must work via the ToolUniverse wrapper."""
        for audience in ("beginner", "engineer", "infra"):
            result = tu.tools.WFGY_triage_llm_rag_failure(
                bug_description="Model hallucinates on retrieval.",
                audience=audience,
            )
            assert result["status"] == "success", f"Failed for audience={audience}"


# ---------------------------------------------------------------------------
# JSON config schema tests
# ---------------------------------------------------------------------------

class TestWFGYPromptBundleJSONConfig:
    """Validate the JSON configuration follows ToolUniverse conventions."""

    def test_name_length_under_55_chars(self, tool_config):
        """Tool name must be ≤ 55 characters for MCP compatibility."""
        assert len(tool_config["name"]) <= 55, (
            f"Name too long ({len(tool_config['name'])} chars): {tool_config['name']}"
        )

    def test_type_matches_class_name(self, tool_config):
        """'type' field must match the @register_tool class name."""
        from tooluniverse.tool_registry import get_tool_registry
        import tooluniverse.wfgy_promptbundle_tool  # ensure module is imported
        registry = get_tool_registry()
        assert tool_config["type"] in registry, (
            f"Type '{tool_config['type']}' not found in tool registry"
        )

    def test_required_parameter_present(self, tool_config):
        """bug_description must be listed in required parameters."""
        required = tool_config["parameter"]["required"]
        assert "bug_description" in required

    def test_return_schema_is_object(self, tool_config):
        """return_schema must be of type 'object'."""
        assert tool_config["return_schema"]["type"] == "object"

    def test_test_examples_are_real_and_valid(self, tool_config):
        """test_examples must be non-empty and use real values."""
        examples = tool_config.get("test_examples", [])
        assert len(examples) >= 1, "At least one test_example required"
        for ex in examples:
            assert "bug_description" in ex, "test_example missing bug_description"
            assert ex["bug_description"].strip(), "bug_description must not be empty"
