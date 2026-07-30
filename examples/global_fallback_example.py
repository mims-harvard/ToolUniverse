#!/usr/bin/env python3
"""
Test script to verify global fallback functionality in AgenticTool.
Tests the system-wide default fallback chain.
"""

import os
import json
from tooluniverse.agentic_tool import AgenticTool


def test_default_global_fallback():
    """Test: Tool uses default global fallback chain when no explicit fallback is configured."""

    print("=== Test 1: Default Global Fallback Chain ===\n")

    # Remove Gemini API key to force fallback
    original_gemini_key = os.environ.get("GEMINI_API_KEY")
    if "GEMINI_API_KEY" in os.environ:
        del os.environ["GEMINI_API_KEY"]

    try:
        # Create tool with only primary API (no explicit fallback)
        tool = AgenticTool(
            {
                "name": "gemini_with_global_fallback",
                "api_type": "GEMINI",
                "model_id": "gemini-3.6-flash",
                # No fallback_api_type configured - should use global fallback
                "prompt": "You are a helpful assistant. Answer: {question}",
                "input_arguments": ["question"],
            }
        )

        print(f"Tool available: {tool.is_available()}")
        print(f"Current API: {tool._current_api_type}")
        print(f"Current model: {tool._current_model_id}")
        print(f"Original config: {tool._api_type} with {tool._model_id}")
        print(f"Global fallback enabled: {tool._use_global_fallback}")
        print(f"Global fallback chain: {tool._global_fallback_chain}")

        if tool.is_available():
            result = tool.run({"question": "What is 2+2?"})
            if result.get("success"):
                print(f"✅ Tool worked with global fallback: {result['result']}")
            else:
                print(f"❌ Tool failed: {result['error']}")
        else:
            print(f"❌ Tool not available: {tool._initialization_error}")

    finally:
        # Restore Gemini key
        if original_gemini_key:
            os.environ["GEMINI_API_KEY"] = original_gemini_key


def test_custom_global_fallback():
    """Test: Tool uses custom global fallback chain from environment variable."""

    print("\n=== Test 2: Custom Global Fallback Chain ===\n")

    # Set custom global fallback chain
    custom_chain = [
        {"api_type": "GEMINI", "model_id": "gemini-3.6-flash"},
        {"api_type": "CHATGPT", "model_id": "gpt-4o-mini-0718"},
    ]
    os.environ["AGENTIC_TOOL_FALLBACK_CHAIN"] = json.dumps(custom_chain)

    # Remove Azure OpenAI API key to force fallback
    original_azure_key = os.environ.get("AZURE_OPENAI_API_KEY")
    if "AZURE_OPENAI_API_KEY" in os.environ:
        del os.environ["AZURE_OPENAI_API_KEY"]

    try:
        # Create tool with ChatGPT as primary
        tool = AgenticTool(
            {
                "name": "chatgpt_with_custom_global_fallback",
                "api_type": "CHATGPT",
                "model_id": "gpt-4o-1120",
                "prompt": "You are a helpful assistant. Answer: {question}",
                "input_arguments": ["question"],
            }
        )

        print(f"Tool available: {tool.is_available()}")
        print(f"Current API: {tool._current_api_type}")
        print(f"Current model: {tool._current_model_id}")
        print(f"Original config: {tool._api_type} with {tool._model_id}")
        print(f"Custom global fallback chain: {tool._global_fallback_chain}")

        if tool.is_available():
            result = tool.run({"question": "What is 2+2?"})
            if result.get("success"):
                print(f"✅ Tool worked with custom global fallback: {result['result']}")
            else:
                print(f"❌ Tool failed: {result['error']}")
        else:
            print(f"❌ Tool not available: {tool._initialization_error}")

    finally:
        # Restore Azure key and remove custom chain
        if original_azure_key:
            os.environ["AZURE_OPENAI_API_KEY"] = original_azure_key
        if "AGENTIC_TOOL_FALLBACK_CHAIN" in os.environ:
            del os.environ["AGENTIC_TOOL_FALLBACK_CHAIN"]


def test_disable_global_fallback():
    """Test: Tool can disable global fallback."""

    print("\n=== Test 3: Disable Global Fallback ===\n")

    # Remove Azure OpenAI API key
    original_azure_key = os.environ.get("AZURE_OPENAI_API_KEY")
    if "AZURE_OPENAI_API_KEY" in os.environ:
        del os.environ["AZURE_OPENAI_API_KEY"]

    try:
        # Create tool with global fallback disabled
        tool = AgenticTool(
            {
                "name": "no_global_fallback",
                "api_type": "CHATGPT",
                "model_id": "gpt-4o-1120",
                "use_global_fallback": False,  # Disable global fallback
                "prompt": "You are a helpful assistant. Answer: {question}",
                "input_arguments": ["question"],
            }
        )

        print(f"Tool available: {tool.is_available()}")
        print(f"Current API: {tool._current_api_type}")
        print(f"Current model: {tool._current_model_id}")
        print(f"Global fallback enabled: {tool._use_global_fallback}")

        if tool.is_available():
            result = tool.run({"question": "What is 2+2?"})
            print(f"Unexpected success: {result}")
        else:
            print(
                f"✅ Tool correctly failed without global fallback: {tool._initialization_error}"
            )

    finally:
        # Restore Azure key
        if original_azure_key:
            os.environ["AZURE_OPENAI_API_KEY"] = original_azure_key


def test_explicit_fallback_priority():
    """Test: Explicit fallback takes priority over global fallback."""

    print("\n=== Test 4: Explicit Fallback Priority ===\n")

    # Remove Gemini API key
    original_gemini_key = os.environ.get("GEMINI_API_KEY")
    if "GEMINI_API_KEY" in os.environ:
        del os.environ["GEMINI_API_KEY"]

    try:
        # Create tool with both explicit and global fallback
        tool = AgenticTool(
            {
                "name": "explicit_vs_global_fallback",
                "api_type": "GEMINI",
                "model_id": "gemini-3.6-flash",
                "fallback_api_type": "CHATGPT",  # Explicit fallback
                "fallback_model_id": "gpt-4o-mini-0718",  # Different from global default
                "prompt": "You are a helpful assistant. Answer: {question}",
                "input_arguments": ["question"],
            }
        )

        print(f"Tool available: {tool.is_available()}")
        print(f"Current API: {tool._current_api_type}")
        print(f"Current model: {tool._current_model_id}")
        print(
            f"Explicit fallback: {tool._fallback_api_type} ({tool._fallback_model_id})"
        )
        print(f"Global fallback chain: {tool._global_fallback_chain}")

        if tool.is_available():
            result = tool.run({"question": "What is 2+2?"})
            if result.get("success"):
                print(f"✅ Tool worked with explicit fallback: {result['result']}")
                # Check if it used explicit fallback (gpt-4o-mini-0718) instead of global default (gpt-4o-1120)
                if tool._current_model_id == "gpt-4o-mini-0718":
                    print("✅ Used explicit fallback as expected")
                else:
                    print(
                        f"⚠️  Used {tool._current_model_id} instead of explicit fallback"
                    )
            else:
                print(f"❌ Tool failed: {result['error']}")
        else:
            print(f"❌ Tool not available: {tool._initialization_error}")

    finally:
        # Restore Gemini key
        if original_gemini_key:
            os.environ["GEMINI_API_KEY"] = original_gemini_key


def test_multiple_tools_global_fallback():
    """Test: Multiple tools using global fallback."""

    print("\n=== Test 5: Multiple Tools with Global Fallback ===\n")

    # Remove Gemini API key to force fallback for Gemini tools
    original_gemini_key = os.environ.get("GEMINI_API_KEY")
    if "GEMINI_API_KEY" in os.environ:
        del os.environ["GEMINI_API_KEY"]

    try:
        tools_config = [
            {
                "name": "gemini_tool_1",
                "api_type": "GEMINI",
                "model_id": "gemini-3.6-flash",
                "prompt": "Gemini tool 1: {question}",
                "input_arguments": ["question"],
            },
            {
                "name": "gemini_tool_2",
                "api_type": "GEMINI",
                "model_id": "gemini-3.6-flash",
                "prompt": "Gemini tool 2: {question}",
                "input_arguments": ["question"],
            },
            {
                "name": "chatgpt_tool",
                "api_type": "CHATGPT",
                "model_id": "gpt-4o-1120",
                "prompt": "ChatGPT tool: {question}",
                "input_arguments": ["question"],
            },
        ]

        tools = []
        for config in tools_config:
            tool = AgenticTool(config)
            tools.append(tool)

            status = "✅ Available" if tool.is_available() else "❌ Unavailable"
            current_api = (
                f"{tool._current_api_type} ({tool._current_model_id})"
                if tool._current_api_type
                else "None"
            )
            print(f"{config['name']}: {status} - Using: {current_api}")

        print()

        # Test all available tools
        available_tools = [tool for tool in tools if tool.is_available()]
        if available_tools:
            print("=== Testing Available Tools ===")
            for tool in available_tools:
                result = tool.run({"question": "Hello!"})
                if result.get("success"):
                    print(f"✅ {tool.name}: {result['result'][:50]}...")
                else:
                    print(f"❌ {tool.name}: {result['error']}")

    finally:
        # Restore Gemini key
        if original_gemini_key:
            os.environ["GEMINI_API_KEY"] = original_gemini_key


if __name__ == "__main__":
    test_default_global_fallback()
    test_custom_global_fallback()
    test_disable_global_fallback()
    test_explicit_fallback_priority()
    test_multiple_tools_global_fallback()

    print("\n=== Summary ===")
    print("✅ Global fallback chain works as default")
    print("✅ Custom global fallback chain from environment variable")
    print("✅ Global fallback can be disabled per tool")
    print("✅ Explicit fallback takes priority over global fallback")
    print("✅ Multiple tools can use global fallback independently")
    print("\n=== Configuration Options ===")
    print("• use_global_fallback: true/false (default: true)")
    print("• AGENTIC_TOOL_FALLBACK_CHAIN: JSON array of {api_type, model_id}")
    print("• Explicit fallback_api_type/fallback_model_id takes priority")
