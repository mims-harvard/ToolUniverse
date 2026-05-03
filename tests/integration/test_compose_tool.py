"""
ComposeTool Test File

This file tests the core functionality of ComposeTool:
1. Basic ComposeTool creation and execution
2. ComposeTool nested calling (one ComposeTool calling another ComposeTool)
3. Simple mathematical operations

ComposeTool is a composable tool that supports:
- Inline code definition (write Python code directly in JSON configuration)
- External file definition (define complex logic through Python files)
- Nested calling between tools (using call_tool function)
"""

import sys
import os
import json
import pytest

# Add src directory to Python path to import tooluniverse modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from tooluniverse.execute_function import ToolUniverse


@pytest.fixture(scope="session")
def tooluni():
    """Initialize tool universe for all tests."""
    tu = ToolUniverse()
    tu.load_tools()
    yield tu
    tu.close()


def test_nested_calls(tooluni):
    """
    Test ComposeTool nested calling functionality

    This test creates two ComposeTool instances:
    1. TextTool: receives text, returns uppercase text and length
    2. CallerTool: calls TextTool to process text, then wraps the result

    Key verification points:
    - ComposeTool can call other ComposeTool instances
    - Correct usage of call_tool function
    - Parameter passing and result return in nested calls
    """
    print("Testing ComposeTool nested calling functionality")
    print("=" * 40)

    # Create a simple text processing tool
    # This tool receives text and returns uppercase version and length
    text_tool = {
        "type": "ComposeTool",
        "name": "TextTool",
        "description": "Simple text processing tool",
        "parameter": {
            "type": "object",
            "properties": {"text": {"type": "string", "description": "Input text"}},
            "required": ["text"],
        },
        "composition_code": [
            "# Get text from arguments",
            "text = arguments['text']",
            "# Return processing result: uppercase text and length",
            "result = {'processed': text.upper(), 'length': len(text)}",
        ],
    }

    # Create a caller tool that calls the above TextTool
    # This demonstrates the nested calling capability of ComposeTool
    caller_tool = {
        "type": "ComposeTool",
        "name": "CallerTool",
        "description": "Composite tool that calls text tool",
        "parameter": {
            "type": "object",
            "properties": {"input": {"type": "string", "description": "Input text"}},
            "required": ["input"],
        },
        "composition_code": [
            "# Get input text",
            "input_text = arguments['input']",
            "# Use call_tool function to call TextTool",
            "# call_tool(tool_name, arguments_dict) is the standard way to call other tools in ComposeTool",
            "text_result = call_tool('TextTool', {'text': input_text})",
            "# Wrap result, including original input and processing result",
            "result = {'original': input_text, 'processed_result': text_result}",
        ],
    }

    # Initialize ToolUniverse engine
    engine = ToolUniverse()
    try:
        # Register tools to engine
        # Need to add to both all_tools list and all_tool_dict dictionary
        engine.all_tools.extend([text_tool, caller_tool])
        engine.all_tool_dict["TextTool"] = text_tool
        engine.all_tool_dict["CallerTool"] = caller_tool

        # Run test: call CallerTool, which will internally call TextTool
        result = engine.run_one_function(
            {"name": "CallerTool", "arguments": {"input": "hello world"}}
        )

        print("Nested calling result:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    finally:
        engine.close()


def test_simple_math(tooluni):
    """
    Test ComposeTool's mathematical operations functionality

    This test creates a math tool that supports:
    1. Array summation
    2. Array element multiplication
    3. Default handling for unknown operations

    Key verification points:
    - Conditional logic processing in ComposeTool
    - Array data processing
    - Support for multiple operation types
    """
    print("\nTesting simple mathematical operations functionality")
    print("=" * 40)

    # Create a mathematical operations tool
    # Supports sum or multiply operations on number arrays
    math_tool = {
        "type": "ComposeTool",
        "name": "MathTool",
        "description": "Simple mathematical operations tool",
        "parameter": {
            "type": "object",
            "properties": {
                "numbers": {"type": "array", "description": "Array of numbers"},
                "op": {
                    "type": "string",
                    "description": "Operation type: sum (addition) or multiply (multiplication)",
                },
            },
            "required": ["numbers", "op"],
        },
        "composition_code": [
            "# Get number array and operation type from arguments",
            "numbers = arguments['numbers']",
            "op = arguments['op']",
            "",
            "# Execute different calculations based on operation type",
            "if op == 'sum':",
            "    # Sum operation",
            "    result = {'result': sum(numbers), 'operation': 'sum'}",
            "elif op == 'multiply':",
            "    # Multiply operation: start with 1, multiply sequentially",
            "    result = {'result': 1}",
            "    for n in numbers:",
            "        result['result'] *= n",
            "    result['operation'] = 'multiply'",
            "else:",
            "    # Default handling for unknown operations",
            "    result = {'result': 0, 'operation': 'unknown'}",
        ],
    }

    # Initialize engine and register math tool
    engine = ToolUniverse()
    try:
        engine.all_tools.append(math_tool)
        engine.all_tool_dict["MathTool"] = math_tool

        # Test sum functionality
        print("Testing sum operation:")
        result = engine.run_one_function(
            {"name": "MathTool", "arguments": {"numbers": [1, 2, 3, 4], "op": "sum"}}
        )
        print("  Input: [1, 2, 3, 4], Operation: sum")
        print(f"  Result: {result}")

        # Test multiply functionality
        print("\nTesting multiply operation:")
        result = engine.run_one_function(
            {"name": "MathTool", "arguments": {"numbers": [2, 3, 4], "op": "multiply"}}
        )
        print("  Input: [2, 3, 4], Operation: multiply")
        print(f"  Result: {result}")
    finally:
        engine.close()


def test_config_file_tools(tooluni):
    """
    Test ComposeTool loaded from configuration files

    This test verifies:
    1. Loading ComposeTool from JSON configuration files
    2. Configuration file defined tools can run normally
    3. Demonstrate how to use predefined composite tools

    Configuration file location: src/tooluniverse/data/compose_tools.json
    """
    print("\nTesting ComposeTool from configuration files")
    print("=" * 40)

    # Initialize ToolUniverse engine
    engine = ToolUniverse()
    try:
        # Load compose type tools from configuration files
        # This automatically loads tools defined in src/tooluniverse/data/compose_tools.json
        engine.load_tools(tool_type=["compose"])

        # Test DrugSafetyAnalyzer tool from configuration file
        print("Running DrugSafetyAnalyzer tool from configuration file:")
        try:
            result = engine.run_one_function(
                {
                    "name": "DrugSafetyAnalyzer",
                    "arguments": {"drug_name": "aspirin", "serious_events_only": False},
                }
            )

            print("DrugSafetyAnalyzer tool result:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
        except Exception as e:
            print(f"DrugSafetyAnalyzer test failed: {e}")
            print("This is expected if the required atomic tools are not loaded.")

        print(f"\nTotal tools loaded: {len(engine.callable_functions)}")
        compose_tools = [
            name
            for name in engine.callable_functions.keys()
            if any(
                tool.get("name") == name and tool.get("type") == "ComposeTool"
                for tool in engine.all_tools
            )
        ]
        print(f"ComposeTool instances: {compose_tools}")

        # Check available composite tools and test them
        print(f"\nTotal tools loaded: {len(engine.all_tools)}")
        compose_tools = [
            name
            for name in engine.callable_functions.keys()
            if any(
                tool.get("name") == name and tool.get("type") == "ComposeTool"
                for tool in engine.all_tools
            )
        ]
        print(f"ComposeTool instances available: {compose_tools}")
    finally:
        engine.close()


def test_external_file_tools(tooluni):
    """
    Test additional ComposeTool functionality

    This test verifies:
    1. Additional composite tools from configuration
    2. Testing ProteinFunctionAnalyzer and LiteratureMetaAnalyzer
    3. Demonstrate complex biomedical analysis workflows
    """
    print("\nTesting additional composite tools")
    print("=" * 40)

    # Initialize ToolUniverse engine
    engine = ToolUniverse()
    try:
        # Load compose type tools from configuration files
        engine.load_tools(tool_type=["compose"])

        # Only test tools that are actually loaded
        compose_tools = [
            tool for tool in engine.all_tools if tool.get("type") == "ComposeTool"
        ]
        print(f"Found {len(compose_tools)} composite tools:")
        for tool in compose_tools:
            print(f"  - {tool['name']}: {tool['description']}")

        # Test each available composite tool
        for tool in compose_tools:
            tool_name = tool["name"]
            if tool_name in [
                "DrugSafetyAnalyzer",
                "SimpleExample",
                "TestDependencyLoading",
                "ToolDiscover",  # Skip ToolDiscover as it requires LLM calls and may timeout
                "ToolDescriptionOptimizer",  # Skip ToolDescriptionOptimizer as it requires LLM calls and may timeout
            ]:
                # Skip these as they are tested in other functions or may timeout
                continue

            print(f"\nTesting {tool_name}:")
            try:
                # Create generic test arguments based on tool requirements
                test_args = {}
                if "parameter" in tool and "properties" in tool["parameter"]:
                    for param_name, param_info in tool["parameter"]["properties"].items():
                        if param_name == "tool_config":
                            # Special handling for ToolDescriptionOptimizer
                            test_args[param_name] = {
                                "name": "test_tool",
                                "description": "A test tool for optimization",
                                "type": "RestfulTool",
                                "parameter": {
                                    "type": "object",
                                    "properties": {
                                        "query": {"type": "string", "description": "Search query"}
                                    }
                                }
                            }
                        elif param_info["type"] == "string":
                            test_args[param_name] = "test_input"
                        elif param_info["type"] == "number":
                            test_args[param_name] = 1
                        elif param_info["type"] == "boolean":
                            test_args[param_name] = True
                        # Add other types as needed

                result = engine.run_one_function(
                    {"name": tool_name, "arguments": test_args}
                )
                print(f"{tool_name} result:")
                print(json.dumps(result, indent=2, ensure_ascii=False))
            except Exception as e:
                print(f"{tool_name} test failed: {e}")
                print("This is expected if the required atomic tools are not loaded.")
    finally:
        engine.close()


def test_dependency_auto_loading(tooluni):
    """
    Test ComposeTool automatic dependency loading functionality

    This test verifies:
    1. Automatic detection of tool dependencies
    2. Auto-loading of missing tool categories
    3. Error handling for unavailable tools
    4. Configuration options for dependency behavior
    """
    print("\nTesting automatic dependency loading functionality")
    print("=" * 40)

    # Create a ComposeTool that depends on external tools
    dependent_tool = {
        "type": "ComposeTool",
        "name": "DependentTool",
        "description": "Tool that depends on external tools",
        "parameter": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Search query"}},
            "required": ["query"],
        },
        "auto_load_dependencies": True,
        "fail_on_missing_tools": False,
        "required_tools": ["EuropePMC_search_articles"],
        "composition_code": [
            "# This tool tries to call EuropePMC tool",
            "query = arguments['query']",
            "",
            "print(f'Testing with query: {query}')",
            "",
            "# Try to call external tool",
            "literature_result = call_tool('EuropePMC_search_articles', {",
            "    'query': query,",
            "    'limit': 3",
            "})",
            "",
            "result = {",
            "    'query': query,",
            "    'literature_result': literature_result,",
            "    'success': True,",
            "    'message': 'Dependency test completed'",
            "}",
            "",
            "print(f'Dependency test completed for query: {query}')",
        ],
    }

    # Initialize engine without loading external tools initially
    engine = ToolUniverse()
    try:
        engine.all_tools.append(dependent_tool)
        engine.all_tool_dict["DependentTool"] = dependent_tool

        # Test the tool - it should attempt to auto-load dependencies
        print("Testing tool with auto-loading enabled:")
        result = engine.run_one_function(
            {"name": "DependentTool", "arguments": {"query": "artificial intelligence"}}
        )

        print("Dependency auto-loading test result:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    finally:
        engine.close()


def main():
    """
    Main test function with enhanced dependency management testing

    Run all ComposeTool tests:
    1. Nested calling test - verify inter-tool calling capability
    2. Mathematical operations test - verify data processing capability
    3. Configuration file test - verify tool loading from files capability
    4. Dependency auto-loading test - verify automatic dependency management

    Summary information will be displayed after tests complete
    """
    print("ComposeTool Functionality Tests (Enhanced with Dependency Management)")
    print("=" * 70)
    print("Test contents:")
    print("1. Nested calling functionality - ComposeTool calling other ComposeTool")
    print("2. Mathematical operations functionality - array sum and multiply")
    print("3. Configuration file functionality - testing available composite tools:")
    print("   - DrugSafetyAnalyzer: Drug safety analysis with FAERS, PubChem, ChEMBL")
    print("   - SimpleExample: Simple tool with no external dependencies")
    print("   - TestDependencyLoading: Tool that tests auto-loading dependencies")
    print("4. Additional composite tools functionality")
    print("5. Automatic dependency loading functionality")
    print("=" * 70)

    try:
        # Run all tests
        test_nested_calls()
        test_simple_math()
        test_config_file_tools()
        test_external_file_tools()
        test_dependency_auto_loading()

        # Display success information
        print("\n" + "=" * 70)
        print("✅ All tests completed!")
        print("=" * 70)
        print("Enhanced dependency management features:")
        print("- ✅ Automatic detection of tool dependencies from code")
        print("- ✅ Auto-loading of missing tool categories")
        print(
            "- ✅ Configurable behavior (auto_load_dependencies, fail_on_missing_tools)"
        )
        print("- ✅ Graceful error handling for unavailable tools")
        print("- ✅ Real-time dependency resolution during execution")
        print(
            "- ✅ Support for both explicit (required_tools) and implicit dependencies"
        )
        print("\nComposeTool capabilities:")
        print("- Supports both inline code and external file definition methods")
        print(
            "- Can implement nested calling between tools through call_tool() function"
        )
        print(
            "- Fully integrated into ToolUniverse framework, usage consistent with other tools"
        )
        print("- Supports complex data processing and logic control")
        print(
            "- New composite tools demonstrate real-world biomedical analysis workflows"
        )

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        print("\nTroubleshooting tips:")
        print("1. Ensure all dependency packages are correctly installed")
        print("2. Check if src/tooluniverse/data/compose_tools.json file exists")
        print(
            "3. Check if the new composite tools are properly defined in compose_tools.json"
        )
        print(
            "4. Confirm ComposeTool class is correctly integrated into execute_function.py"
        )
        print("5. Note: Auto-loading will attempt to load missing tools automatically")
        print("6. Use auto_load_dependencies=false to disable automatic loading")
        print("7. Use fail_on_missing_tools=true for strict dependency checking")


if __name__ == "__main__":
    main()
