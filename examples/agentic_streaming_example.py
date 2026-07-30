"""AgenticTool Streaming Example
================================

This example shows how to run an AgenticTool in streaming mode so that
intermediate chunks are printed as soon as the underlying LLM sends them.
The tool is registered via the recommended ``@register_tool`` decorator,
so it will be discoverable just like any first-class ToolUniverse tool.

The script uses the OpenRouter client because it already supports a broad set
of models and only requires a single API key. To try it with Azure OpenAI or
Gemini you can adjust the configuration in ``StreamingAgenticTool``.

Setup
-----

1. Obtain an OpenRouter API key from https://openrouter.ai/
2. Export it before running the script::

       export OPENROUTER_API_KEY="sk-..."

   (Optional) You can also export ``OPENROUTER_SITE_URL`` and
   ``OPENROUTER_SITE_NAME`` for attribution, but they are not required.

3. Run the example::

       python examples/agentic_streaming_example.py

You should see the streamed chunks appear immediately, followed by the final
assembled answer.
"""

from __future__ import annotations

import os
import sys
import textwrap
from pathlib import Path
import types


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if SRC_DIR.exists():
    sys.path.insert(0, str(SRC_DIR))


# Stub out rcsbapi to avoid network requests when importing tooluniverse
if "rcsbapi" not in sys.modules:
    rcsbapi_module = types.ModuleType("rcsbapi")
    rcsbapi_data_module = types.ModuleType("rcsbapi.data")

    class _DummyDataQuery:
        def __init__(self, *args, **kwargs):
            pass

        def exec(self):  # pragma: no cover
            return {}

    rcsbapi_data_module.DataQuery = _DummyDataQuery
    rcsbapi_module.data = rcsbapi_data_module
    sys.modules["rcsbapi"] = rcsbapi_module
    sys.modules["rcsbapi.data"] = rcsbapi_data_module


from tooluniverse import ToolUniverse
from tooluniverse.agentic_tool import AgenticTool
from tooluniverse.tool_registry import register_tool


API_TYPE = "GEMINI"  # Change to "OPENROUTER" or "CHATGPT" to test other providers
MODEL_ID = "gemini-3.6-flash"  # Adjust to any model supported by the chosen API type


def ensure_provider_config() -> None:
    if API_TYPE == "OPENROUTER":
        if os.getenv("OPENROUTER_API_KEY"):
            return
        msg = textwrap.dedent(
            """
            ❌ OPENROUTER_API_KEY is not set.

            Please export your OpenRouter API key before running the streaming example:
                export OPENROUTER_API_KEY="sk-..."

            You can create or retrieve a key at https://openrouter.ai/
            """
        ).strip()
        print(msg)
        sys.exit(1)

    if API_TYPE == "GEMINI":
        if os.getenv("GEMINI_API_KEY"):
            return
        msg = textwrap.dedent(
            """
            ❌ GEMINI_API_KEY is not set.

            Please export your Google AI Studio API key before running the streaming example:
                export GEMINI_API_KEY="your-gemini-key"

            Visit https://aistudio.google.com/ to create a key.
            """
        ).strip()
        print(msg)
        sys.exit(1)


TOOL_NAME = "StreamingAgenticTool"


@register_tool(
    TOOL_NAME,
    config={
        "name": TOOL_NAME,
        "description": "Streamed response generator using OpenRouter",
        "type": "AgenticTool",
        "prompt": """You are an experienced research mentor. The user has requested:\n\n{request}\n\nProduce a thorough, structured response that includes:\n1. A short contextual introduction\n2. At least 6 detailed bullet points (2-3 sentences each) covering different angles\n3. A succinct wrap-up with an extra actionable insight\n\nWrite in a clear, professional tone and avoid markdown headings.""",
        "input_arguments": ["request"],
        "parameter": {
            "type": "object",
            "properties": {
                "request": {
                    "type": "string",
                    "description": "User question or task description",
                }
            },
            "required": ["request"],
        },
        "configs": {
            "api_type": API_TYPE,
            "model_id": MODEL_ID,
            "temperature": 0.4,
            "return_json": False,
            "return_metadata": True,
        },
    },
)
class StreamingAgenticTool(AgenticTool):
    """Static registration wrapper using the recommended decorator."""


def load_streaming_tool(tu: ToolUniverse) -> None:
    # ToolUniverse will pick up the decorator config during load_tools
    tu.load_tools(include_tools=[TOOL_NAME])


def main() -> None:
    ensure_provider_config()

    print("🚀 Starting AgenticTool streaming demo\n")
    print(f"API Type: {API_TYPE}")
    print(f"Model: {MODEL_ID}")

    tu = ToolUniverse(tool_files={}, keep_default_tools=False)
    load_streaming_tool(tu)

    question = (
        "Suggest productivity techniques for a research scientist who wants to"
        " keep up with literature while managing experiments."
    )

    print("\n📨 Prompt:")
    print(textwrap.fill(question, width=80))

    print("\n📡 Streaming chunks:\n")

    chunks: list[str] = []

    def handle_stream(chunk: str) -> None:
        chunks.append(chunk)
        print(chunk, end="", flush=True)

    result = tu.run_one_function(
        {"name": TOOL_NAME, "arguments": {"request": question, "_tooluniverse_stream": True}},
        stream_callback=handle_stream,
    )

    print("\n\n✅ Final assembled response:\n")
    print(result if isinstance(result, str) else result.get("result", result))

    if isinstance(result, dict):
        metadata = result.get("metadata", {})
        model_info = metadata.get("model_info", {})
        print("\n📊 Metadata:")
        print(f"  Model: {model_info.get('model_id', 'unknown')}")
        print(f"  API Type: {model_info.get('api_type', 'unknown')}")
        print(
            f"  Execution Time: {metadata.get('execution_time_seconds', 'unknown')} seconds"
        )


if __name__ == "__main__":
    main()
