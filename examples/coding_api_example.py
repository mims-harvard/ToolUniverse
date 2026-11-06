#!/usr/bin/env python3
"""
ToolUniverse Coding API Examples

Demonstrates various methods for calling tools using the coding API
"""

from tooluniverse import ToolUniverse
from pathlib import Path

# =============================================================================
# Method 1: Dynamic Function-Style Calling
# =============================================================================
# Description: Call tools like regular Python functions through tu.tools
# Syntax: tu.tools.ToolName(parameter=value)
tu = ToolUniverse()
tu.load_tools()

# Basic function-style calling
result1 = tu.tools.UniProt_get_entry_by_accession(accession="P05067")

# Error handling for non-existent tools
try:
    tu.tools.NonExistentTool(some_param="test")
except AttributeError as e:
    # Handle non-existent tool error
    pass

# Caching functionality
result2 = tu.tools.UniProt_get_entry_by_accession(
    accession="P05067", 
    use_cache=True
)

# Lifecycle management
tu.tools.refresh()
tu.tools.eager_load(["UniProt_get_entry_by_accession"])

# =============================================================================
# Method 2: Generated Tools Calling
# =============================================================================
# Description: Use pre-generated tools for type-safe tool calling
# Syntax: from tooluniverse.tools import ToolName
# Note: Tools are auto-generated: python scripts/build_tools.py

# Import generated tools
from tooluniverse.tools import UniProt_get_entry_by_accession

# Call tool function directly
result3 = UniProt_get_entry_by_accession(accession="P05067")

# Structured error handling.
# A failed call RETURNS the error; it does not raise. The classes in
# tooluniverse.exceptions never reach the caller -- the call path converts them
# into this dict -- so `except ToolValidationError` here would catch nothing and
# the error would be used as if it were data.
result4 = UniProt_get_entry_by_accession(accession="invalid")
if isinstance(result4, dict) and result4.get("status") == "error":
    details = result4.get("error_details", {})
    # details["type"] is the error class name, e.g. "ToolValidationError"
    # details["next_steps"] holds suggested actions
    # details["retriable"] says whether a retry is worth making
    pass

# =============================================================================
# Method 3: Traditional JSON-Based Calling
# =============================================================================
# Description: Use original JSON-based calling method
# Syntax: tu.run_one_function({'name': 'ToolName', 'arguments': {...}})

# Basic JSON calling
result5 = tu.run_one_function({
    "name": "UniProt_get_entry_by_accession",
    "arguments": {"accession": "P05067"}
})

# Error scenarios with JSON calling
error_scenarios = [
    {
        "name": "Non-existent tool",
        "call": lambda: tu.tools.NonExistentTool(param="test")
    },
    {
        "name": "Invalid parameters",
        "call": lambda: tu.run_one_function({
            "name": "UniProt_get_entry_by_accession",
            "arguments": {"invalid_param": "test"}
        })
    },
    {
        "name": "Missing required parameter",
        "call": lambda: tu.run_one_function({
            "name": "UniProt_get_entry_by_accession", 
            "arguments": {}
        })
    }
]

# Test error scenarios
for scenario in error_scenarios:
    try:
        result = scenario["call"]()
        # Check for dual-format error response
        if isinstance(result, dict) and "error" in result:
            # Handle error response format
            error_details = result.get("error_details", {})
            # error_details contains: type, retriable, next_steps
            pass
    except Exception as e:
        # Handle exception-based errors
        pass

# =============================================================================
# Method 4: Multiple Individual Calls
# =============================================================================
# Description: Execute multiple tools individually (alternative to batch calling)
# Syntax: Multiple tu.run_one_function() calls

result6a = tu.run_one_function({
    "name": "UniProt_get_entry_by_accession",
    "arguments": {"accession": "P05067"}
})

result6b = tu.run_one_function({
    "name": "UniProt_get_entry_by_accession",
    "arguments": {"accession": "P12345"}
})

# =============================================================================
# Method 5: Tool Discovery and Dynamic Selection
# =============================================================================
# Description: Discover and call tools dynamically
# Syntax: getattr(tu.tools, 'ToolName')(parameters)

tool_name = "UniProt_get_entry_by_accession"
if hasattr(tu.tools, tool_name):
    tool_func = getattr(tu.tools, tool_name)
    result7 = tool_func(accession="P05067")

# =============================================================================
# Summary of Methods
# =============================================================================
# All methods return the same type of result objects.
# Choose the method that best fits your use case:
# - Dynamic calling: Most intuitive for single tool calls
# - Generated SDK: Type-safe with IDE support
# - JSON-based: Useful for dynamic tool selection
# - Batch calling: Efficient for multiple tool calls
# - Dynamic selection: Good for programmatic tool discovery