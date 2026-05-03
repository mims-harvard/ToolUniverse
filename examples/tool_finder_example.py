#!/usr/bin/env python3
"""
Tool Finder Example

Demonstrates ToolUniverse's tool finding capabilities for discovering relevant tools
"""

from tooluniverse import ToolUniverse
import time

# =============================================================================
# Tool Initialization
# =============================================================================
# Description: Initialize ToolUniverse and load all available tools
# Syntax: tu = ToolUniverse(); tu.load_tools()
tu = ToolUniverse()
tu.load_tools()

# =============================================================================
# Method 1: Semantic Tool Discovery
# =============================================================================
# Description: Use Tool_Finder for semantic-based tool discovery
# Syntax: tu.run({"name": "Tool_Finder", "arguments": {"description": "tool description", "limit": 5, "return_call_result": False}})
result1 = tu.run({
    "name": "Tool_Finder",
    "arguments": {
        "description": "a tool for finding tools related to diseases",
        "limit": 5,
        "return_call_result": False
    }
})

# =============================================================================
# Method 2: Keyword-Based Tool Discovery
# =============================================================================
# Description: Use Tool_Finder_Keyword for keyword-based tool discovery
# Syntax: tu.run({"name": "Tool_Finder_Keyword", "arguments": {"description": "keyword", "limit": 3}})
result2 = tu.run({
    "name": "Tool_Finder_Keyword",
    "arguments": {
        "description": "disease",
        "limit": 3
    }
})

# =============================================================================
# Method 3: Performance Timing
# =============================================================================
# Description: Measure execution time for tool discovery operations
# Syntax: start_time = time.time(); result = tu.run(...); end_time = time.time()
start_time = time.time()
result3 = tu.run({
    "name": "Tool_Finder",
    "arguments": {
        "description": "machine learning tools",
        "limit": 3,
        "return_call_result": False
    }
})
end_time = time.time()
execution_time = end_time - start_time

# =============================================================================
# Method 4: Error Handling and Timeout Management
# =============================================================================
# Description: Handle potential errors and timeouts in tool discovery
# Syntax: try/except blocks around discovery calls
try:
    result4 = tu.run({
        "name": "Tool_Finder",
        "arguments": {
            "description": "complex query that might timeout",
            "limit": 100  # Large limit that might cause timeout
        }
    })
except Exception as e:
    # Handle timeout or other errors
    if "timeout" in str(e).lower():
        # Specific handling for timeout errors
        pass
    else:
        # Handle other types of errors
        pass

# =============================================================================
# Method 5: Result Processing
# =============================================================================
# Description: Process and analyze tool discovery results
# Syntax: Check result structure and extract tool information

# Process Tool_Finder results
if isinstance(result1, dict) and 'tools' in result1:
    tools = result1['tools']
    # Access tool information: tools[0]['name'], tools[0]['description'], etc.
    pass

# Process Tool_Finder_Keyword results
if isinstance(result2, dict) and 'tools' in result2:
    tools = result2['tools']
    # Access tool information: tools[0]['name'], tools[0]['description'], etc.
    pass

# =============================================================================
# Method 6: Batch Tool Discovery
# =============================================================================
# Description: Perform multiple tool discovery queries in sequence
# Syntax: Loop through multiple discovery queries
discovery_queries = [
    {
        "name": "Tool_Finder",
        "arguments": {
            "description": "data analysis tools",
            "limit": 3,
            "return_call_result": False
        }
    },
    {
        "name": "Tool_Finder_Keyword",
        "arguments": {
            "description": "protein",
            "limit": 2
        }
    },
    {
        "name": "Tool_Finder",
        "arguments": {
            "description": "visualization tools",
            "limit": 2,
            "return_call_result": False
        }
    }
]

batch_results = []
for query in discovery_queries:
    try:
        result = tu.run(query)
        batch_results.append(result)
    except Exception as e:
        # Handle individual query failures
        batch_results.append({"error": str(e)})

# =============================================================================
# Method 7: Discovery Parameter Optimization
# =============================================================================
# Description: Optimize discovery parameters for better results
# Syntax: Adjust limit and other parameters

# Small limit for quick testing
quick_result = tu.run({
    "name": "Tool_Finder",
    "arguments": {
        "description": "bioinformatics tools",
        "limit": 1,
        "return_call_result": False
    }
})

# Larger limit for comprehensive results
comprehensive_result = tu.run({
    "name": "Tool_Finder",
    "arguments": {
        "description": "bioinformatics tools",
        "limit": 10,
        "return_call_result": False
    }
})

# =============================================================================
# Method 8: Result Validation
# =============================================================================
# Description: Validate discovery results and check for errors
# Syntax: Check result structure and error conditions

def validate_discovery_result(result, tool_name):
    """Validate tool discovery result structure and content"""
    if isinstance(result, dict):
        if "error" in result:
            # Handle error response
            return False, f"Error in {tool_name}: {result['error']}"
        elif "tools" in result:
            # Valid discovery result
            tools = result['tools']
            return True, f"Found {len(tools)} tools"
        else:
            # Unexpected result structure
            return False, f"Unexpected result structure from {tool_name}"
    else:
        # Non-dictionary result
        return False, f"Unexpected result type from {tool_name}"

# Validate results
is_valid, message = validate_discovery_result(result1, "Tool_Finder")
is_valid, message = validate_discovery_result(result2, "Tool_Finder_Keyword")

# =============================================================================
# Method 9: Tool Information Extraction
# =============================================================================
# Description: Extract specific information from discovered tools
# Syntax: Access tool properties and metadata

def extract_tool_info(tools_result):
    """Extract key information from tool discovery results"""
    if isinstance(tools_result, dict) and 'tools' in tools_result:
        tools = tools_result['tools']
        tool_info = []
        for tool in tools[:3]:  # First 3 tools
            info = {
                'name': tool.get('name', 'Unknown'),
                'description': tool.get('description', 'No description')[:100] + '...',
                'type': tool.get('type', 'Unknown')
            }
            tool_info.append(info)
        return tool_info
    return []

# Extract tool information
tool_info1 = extract_tool_info(result1)
tool_info2 = extract_tool_info(result2)


# =============================================================================
# Tool_Rag Test (simple, like Tool_Finder examples)
# =============================================================================

# Try: simple Tool_Rag query
result_rag = tu.run({
    "name": "Tool_RAG",
    "arguments": {
        "description": "Find tools for gene prediction.",
        "limit": 2
    }
})
print("\n[Tool_RAG] Result:")
print(result_rag)


# =============================================================================
# Summary of Tool Discovery Tools
# =============================================================================
# Available tool discovery tools provide intelligent tool finding capabilities:
# - Tool_Finder: Semantic-based tool discovery using natural language descriptions
# - Tool_Finder_Keyword: Keyword-based tool discovery for specific terms
# 
# Common parameters:
# - description: Natural language description or keyword for tool search
# - limit: Maximum number of tools to return
# - return_call_result: Whether to return actual tool execution results
# 
# Result structures:
# - Both tools return "tools" array with tool information
# - Each tool entry contains: name, description, type, and other metadata
# 
# Error handling:
# - Check for "error" key in dictionary responses
# - Handle timeout exceptions for complex queries
# - Validate result structure before processing
# - Use appropriate limits to avoid timeouts
# 
# Performance considerations:
# - Start with small limits for testing
# - Use timing to measure discovery performance
# - Consider batch operations for multiple queries
# - Handle individual query failures gracefully
# 
# Use cases:
# - Finding tools for specific research tasks
# - Discovering available functionality
# - Tool recommendation systems
# - Automated tool selection workflows