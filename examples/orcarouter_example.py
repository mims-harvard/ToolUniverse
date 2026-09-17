"""
OrcaRouter Integration Example
================================

This example demonstrates how to use OrcaRouter with ToolUniverse to route
chat completions through OrcaRouter's gateway. OrcaRouter also runs
gateway-level, zero-trust security for AI agents on the same endpoint.

Requirements:
- OrcaRouter API key (get from https://www.orcarouter.ai)
- Set ORCAROUTER_API_KEY environment variable
"""

import os
from tooluniverse import ToolUniverse


def setup_orcarouter():
    """Set up OrcaRouter API key (replace with your actual key)."""
    if not os.getenv("ORCAROUTER_API_KEY"):
        print("⚠️  Please set ORCAROUTER_API_KEY environment variable")
        print("   export ORCAROUTER_API_KEY='your_key_here'")
        return False
    return True


def example_smart_route():
    """Example: Basic usage with OrcaRouter smart routing."""
    print("\n" + "=" * 70)
    print("Example: Using OrcaRouter smart routing (orcarouter/auto)")
    print("=" * 70)

    tu = ToolUniverse()

    # Create a simple summarization tool using OrcaRouter
    tool_config = {
        "name": "OrcaRouter_Summarizer",
        "description": "Summarize text using OrcaRouter",
        "type": "AgenticTool",
        "prompt": "Provide a concise summary of the following text in 2-3 sentences:\n\n{text}",
        "input_arguments": ["text"],
        "parameter": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The text to summarize",
                    "required": True,
                }
            },
            "required": ["text"],
        },
        "configs": {
            "api_type": "ORCAROUTER",
            "model_id": "orcarouter/auto",
            "temperature": 0.3,
            "return_json": False,
        },
    }

    # Register and use the tool
    tu.register_tool_from_config(tool_config)

    sample_text = """
    Artificial intelligence has made remarkable progress in recent years, with
    large language models demonstrating unprecedented capabilities in natural
    language understanding and generation. These models can perform a wide range
    of tasks including translation, summarization, question answering, and even
    creative writing. However, challenges remain in areas such as factual accuracy,
    reasoning capabilities, and computational efficiency.
    """

    result = tu.execute_tool("OrcaRouter_Summarizer", {"text": sample_text})
    print("\n📝 Input Text:")
    print(sample_text.strip())
    print("\n✨ Summary:")
    if isinstance(result, dict) and "result" in result:
        print(result["result"])
    else:
        print(result)


if __name__ == "__main__":
    if setup_orcarouter():
        example_smart_route()
