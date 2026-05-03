#!/usr/bin/env python3
"""
Simplified SMCP tools/find test script

Test the new search_method parameter functionality:
- 'auto': Automatically select the best search method
- 'llm': Use LLM intelligent search
- 'embedding': Use embedding vector search
- 'keyword': Use keyword search
"""

import json
import asyncio
import sys
import os
import warnings

# Suppress RDKit warnings and pkg_resources warnings
warnings.filterwarnings(
    "ignore", category=RuntimeWarning, module="importlib._bootstrap"
)
warnings.filterwarnings("ignore", message=".*RDKit.*")
warnings.filterwarnings("ignore", message=".*pkg_resources.*")

# Add project src directory to the path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)


def print_test(title):
    """Print test title"""
    print(f"\n🔍 {title}")
    print("=" * 50)


def print_result(result):
    """Print results"""
    if isinstance(result, dict):
        # Handle both detailed and mcp_standard formats or raw list
        data = result.get("result", result)
        if isinstance(data, list):
            print(f"✅ Results: {len(data)} tools")
            for i, tool in enumerate(data[:3], 1):
                name = tool.get("name") if isinstance(tool, dict) else str(tool)
                print(f"  {i}. {name}")
        elif isinstance(data, dict):
            query = data.get("query", "unknown")
            method = data.get("search_method", "unknown")
            count = data.get("total_matches", len(data.get("tools", [])))
            print(f"✅ Query: '{query}' | Method: {method} | Results: {count}")
            tools = data.get("tools", [])
            if tools:
                print("📋 Found tools:")
                for i, tool in enumerate(tools[:3], 1):
                    print(f"  {i}. {tool.get('name', 'Unknown')}")
            else:
                print("❌ No tools found")
        elif "error" in result:
            print(f"❌ Error: {result['error']['message']}")
    else:
        print(f"Result: {result}")


from tooluniverse.smcp import SMCP  # noqa: E402


async def test_search_methods():
    """Test different search methods"""
    print("🚀 Starting SMCP search functionality tests...")

    # Initialize server
    print("\n📦 Initializing SMCP server...")
    server = SMCP(name="Test Server", search_enabled=True)
    print(
        f"✅ Server initialized, loaded {len(server._exposed_tools)} tools"
    )

    # Test query
    query = "protein analysis"

    # Test 1: Auto search method
    print_test("Test 1: Auto search (search_method='auto')")
    request = {
        "jsonrpc": "2.0",
        "id": "test_auto",
        "method": "tools/find",
        "params": {"query": query, "search_method": "auto", "limit": 3},
    }
    # Directly call the custom handler for tools/find
    result = await server._handle_tools_find(
        request_id=request["id"],
        params=request["params"],
    )  # type: ignore[attr-defined]
    print_result(result)

    # Test 2: LLM search method
    print_test("Test 2: LLM intelligent search (search_method='llm')")
    request = {
        "jsonrpc": "2.0",
        "id": "test_llm",
        "method": "tools/find",
        "params": {"query": query, "search_method": "llm", "limit": 3},
    }
    result = await server._handle_tools_find(
        request_id=request["id"],
        params=request["params"],
    )  # type: ignore[attr-defined]
    print_result(result)

    # Test 3: Keyword search method
    print_test("Test 3: Keyword search (search_method='keyword')")
    request = {
        "jsonrpc": "2.0",
        "id": "test_keyword",
        "method": "tools/find",
        "params": {"query": "tool", "search_method": "keyword", "limit": 3},
    }
    result = await server._handle_tools_find(
        request_id=request["id"],
        params=request["params"],
    )  # type: ignore[attr-defined]
    print_result(result)

    # Test 4: Embedding vector search method
    print_test("Test 4: Embedding vector search (search_method='embedding')")
    request = {
        "jsonrpc": "2.0",
        "id": "test_embedding",
        "method": "tools/find",
        "params": {"query": query, "search_method": "embedding", "limit": 3},
    }
    result = await server._handle_tools_find(
        request_id=request["id"],
        params=request["params"],
    )  # type: ignore[attr-defined]
    print_result(result)

    # Test 5: Error handling - invalid search method
    print_test("Test 5: Invalid search method (should fallback)")
    request = {
        "jsonrpc": "2.0",
        "id": "test_invalid",
        "method": "tools/find",
        "params": {"query": query, "search_method": "invalid_method", "limit": 3},
    }
    result = await server._handle_tools_find(
        request_id=request["id"],
        params=request["params"],
    )  # type: ignore[attr-defined]
    print_result(result)

    # Test 6: Error handling - missing required parameter
    print_test("Test 6: Missing query parameter (should error)")
    request = {
        "jsonrpc": "2.0",
        "id": "test_error",
        "method": "tools/find",
        "params": {"search_method": "auto", "limit": 3},  # Missing query
    }
    result = await server._handle_tools_find(request_id=request["id"], params=request["params"])  # type: ignore[attr-defined]
    print_result(result)

    print("\n✅ All tests completed!")
    await server.close()


def show_examples():
    """Show request examples"""
    print("\n📄 MCP Request Examples:")

    examples = [
        {
            "name": "Auto Search",
            "request": {
                "jsonrpc": "2.0",
                "id": "1",
                "method": "tools/find",
                "params": {
                    "query": "protein analysis",
                    "search_method": "auto",
                    "limit": 5,
                },
            },
        },
        {
            "name": "LLM Search",
            "request": {
                "jsonrpc": "2.0",
                "id": "2",
                "method": "tools/find",
                "params": {
                    "query": "gene expression",
                    "search_method": "llm",
                    "limit": 3,
                },
            },
        },
        {
            "name": "Keyword Search",
            "request": {
                "jsonrpc": "2.0",
                "id": "3",
                "method": "tools/find",
                "params": {"query": "chemical", "search_method": "keyword", "limit": 3},
            },
        },
    ]

    for example in examples:
        print(f"\n{example['name']}:")
        print(json.dumps(example["request"], indent=2, ensure_ascii=False))


async def main():
    """Main test function"""
    print("🧪 Starting SMCP search method functionality tests...")

    # Show examples
    show_examples()

    # Run tests
    await test_search_methods()


if __name__ == "__main__":
    asyncio.run(main())
