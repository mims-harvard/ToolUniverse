#!/usr/bin/env python3
"""
Test file for MCP Tools in ToolUniverse

This file tests the MCP (Model Context Protocol) integration functionality,
including MCPClientTool and MCPAutoLoaderTool.

Usage:
    python test_mcp_tool.py
"""

from tooluniverse import ToolUniverse
from typing import Any, Dict, List
import time
import json

# Step 1: Initialize tool universe
print("🔧 Initializing ToolUniverse...")
tooluni = ToolUniverse()
tooluni.load_tools()

print("✅ ToolUniverse initialized successfully")
print(f"📊 Total tools loaded: {len(tooluni.all_tool_dict)}")

# Step 2: Check if MCP tools are available
mcp_tools = [
    name for name in list(tooluni.all_tool_dict.keys()) if "mcp" in name.lower()
]
print(f"🔍 Found {len(mcp_tools)} MCP-related tools: {mcp_tools}")

# Step 3: Define test queries for MCP tools
test_queries: List[Dict[str, Any]] = [
    # Test mock MCP tools (these should work without requiring external servers)
    # {
    #     "name": "mcp_mock_calculator",
    #     "arguments": {
    #         "operation": "add",
    #         "a": 10,
    #         "b": 5
    #     }
    # },
    # {
    #     "name": "mcp_mock_greeter",
    #     "arguments": {
    #         "name": "ToolUniverse User"
    #     }
    # },
    # Test auto-discovered MCP tools from server 1
    # {
    #     "name": "mcp_s1_calculate",
    #     "arguments": {
    #         "expression": "2 + 3 * 4"
    #     }
    # },
    # {
    #     "name": "mcp_s1_get_weather",
    #     "arguments": {
    #         "city": "New York",
    #         "units": "celsius"
    #     }
    # },
    # Test MCP client tool (if available)
    # {
    #     "name": "mcp_client_example",
    #     "arguments": {
    #         "operation": "list_tools"
    #     }
    # },
    # Test MCPAutoLoaderTool - Discover tools (will show connection errors if servers not running)
    # {
    #     "name": "mcp_auto_loader_server1",
    #     "arguments": {
    #         "operation": "discover"
    #     }
    # },
    # {
    #     "name": "mcp_mock_greeter",
    #     "arguments": {
    #         "name": "ToolUniverse User"
    #     }
    # },
    # # Test MCP client tool (if available)
    # {
    #     "name": "mcp_client_example",
    #     "arguments": {
    #         "operation": "list_tools"
    #     }
    # },
    # # Test MCPAutoLoaderTool - Discover tools (will show connection errors if servers not running)
    # {
    #     "name": "mcp_auto_loader_server1",
    #     "arguments": {
    #         "operation": "discover"
    #     }
    # },
    # Test MCP client with simple operations
    # {
    #     "name": "mcp_client_example",
    #     "arguments": {
    #         "operation": "call_tool",
    #         "tool_name": "get_weather",
    #         "tool_arguments": {
    #             "city": "New York",
    #             "units": "celsius"
    #         }
    #     }
    # },
    # # Test calculator operation
    # {
    #     "name": "mcp_client_example",
    #     "arguments": {
    #         "operation": "call_tool",
    #         "tool_name": "calculate",
    #         "tool_arguments": {
    #             "expression": "10 * 5 + 2"
    #         }
    #     }
    # },
    # # Test Official SDK server (if running)
    # {
    #     "name": "mcp_auto_loader_official_sdk",
    #     "arguments": {
    #         "operation": "discover"
    #     }
    # },
    # # Test file listing operation
    # {
    #     "name": "mcp_client_example",
    #     "arguments": {
    #         "operation": "call_tool",
    #         "tool_name": "list_files",
    #         "tool_arguments": {
    #             "directory": ".",
    #             "pattern": "*.py"
    #         }
    #     }
    # }
    # Test US Patent and Trademark Office (USPTO) tools (if uspto_downloader_MCP.py is running)
    {
        "name": "mcp_download_abst",
        "arguments": {"query": {"applicationNumberText": "19053071"}},
    },
    {
        "name": "mcp_download_claims",
        "arguments": {"query": {"applicationNumberText": "19053071"}},
    },
    # {
    #     "name": "mcp_download_full_text",
    #     "arguments": {
    #         "query": {"applicationNumberText": "19053071"}
    #     }
    # },
    {
        "name": "mcp_download_full_text",
        "arguments": {
            "query": {
                "applicationNumberText": "18837017"
            }  # This one should not have a full text document
        },
    },
    # # Test Boltz2 tool (if boltz_mcp_server.py is running)
    # {
    #     "name": "mcp_run_boltz2",
    #     "arguments": {
    #         "query": {
    #             "protein_sequence": "MLSRLFRMHGLFVASHPWEVIVGTVTLTICMMSMNMFTGNNKICGWNYECPKFEEDVLSSDIIILTITRCIAILYIYFQFQNLRQLGSKYILGIAGLFTIFSSFVFSTVVIHFLDKELTGLNEALPFFLLLIDLSRASTLAKFALSSNSQDEVRENIARGMAILGPTFTLDALVECLVIGVGTMSGVRQLEIMCCFGCMSVLANYFVFMTFFPACVSLVLELSRESREGRPIWQLSHFARVLEEEENKPNPVTQRVKMIMSLGLVLVHAHSRWIADPSPQNSTADTSKVSLGLDENVSKRIEPSVSLWQFYLSKMISMDIEQVITLSLALLLAVKYIFFEQTETESTLSLKNPITSPVVTQKKVPDNCCRREPMLVRNNQKCDSVEEETGINRERKVEVIKPLVAETDTPNRATFVVGNSSLLDTSSVLVTQEPEIELPREPRPNEECLQILGNAEKGAKFLSDAEIIQLVNAKHIPAYKLETLMETHERGVSIRRQLLSKKLSEPSSLQYLPYRDYNYSLVMGACCENVIGYMPIPVGVAGPLCLDEKEFQVPMATTEGCLVASTNRGCRAIGLGGGASSRVLADGMTRGPVVRLPRACDSAEVKAWLETSEGFAVIKEAFDSTSRFARLQKLHTSIAGRNLYIRFQSRSGDAMGMNMISKGTEKALSKLHEYFPEMQILAVSGNYCTDKKPAAINWIEGRGKSVVCEAVIPAKVVREVLKTTTEAMIEVNINKNLVGSAMAGSIGGYNAHAANIVTAIYIACGQDAAQNVGSSNCITLMEASGPTNEDLYISCTMPSIEIGTVGGGTNLLPQQACLQMLGVQGACKDNPGENARQLARIVCGTVMAGELSLMAALAAGHLVKSHMIHNRSKINLQDLQGACTKKTA",
    #             "ligands": [
    #                 {"id": "L1", "smiles": "CC[C@H](C)C(=O)O[C@H]1C[C@@H](C=C2[C@H]1[C@H]([C@H](C=C2)C)CC[C@H](C[C@H](CC(=O)O)O)O)O"},
    #             ],
    #             "use_potentials": True,
    #             "diffusion_samples": 1,
    #             "return_structure": False
    #         }
    #     }
    # }
]

# Step 4: Run test queries with error handling
print(f"\n🧪 Running {len(test_queries)} MCP tool tests...")
print("=" * 60)

successful_tests = 0
failed_tests = 0

for idx, query in enumerate(test_queries):
    print(f"\n[Test {idx+1}/{len(test_queries)}] {query['name']}")
    print(f"Operation: {query['arguments'].get('operation', 'N/A')}")

    if "tool_name" in query["arguments"]:
        print(f"Tool: {query['arguments']['tool_name']}")

    try:
        # Add timeout to prevent hanging
        start_time = time.time()
        result = tooluni.run(query)
        execution_time = time.time() - start_time

        print(f"✅ Success in {execution_time:.2f}s")

        # Format output nicely
        if isinstance(result, dict):
            if "error" in result:
                print(f"⚠️  Tool returned error: {result['error']}")
            else:
                # Show a snippet of the result
                result_str = json.dumps(result, indent=2)
                print(f"📊 Result: {result_str}")
        else:
            result_str = str(result)
            print(f"📊 Result: {result_str}")

        if "error" not in result:
            successful_tests += 1
        else:
            failed_tests += 1
            print(f"❌ Test failed with error: {result['error']}")

    except Exception as e:
        print(f"❌ Failed: {str(e)}")
        failed_tests += 1

    # Small delay between tests
    time.sleep(0.5)

# Step 5: Test Summary
print("\n" + "=" * 60)
print("🎯 MCP Tool Test Summary")
print("=" * 60)
print(f"✅ Successful tests: {successful_tests}")
print(f"❌ Failed tests: {failed_tests}")
print(
    f"📊 Success rate: {(successful_tests/(successful_tests + failed_tests)*100):.1f}%"
)

# if failed_tests > 0:
#     print("\n💡 Tips for failed tests:")
#     print("- Make sure MCP servers are running (e.g., python fastmcp_official_example.py)")
#     print("- Check server URLs and ports in mcp_client_tools.json")
#     print("- Verify network connectivity to MCP servers")
#     print("- Some tools may require specific arguments or server capabilities")

# print("\n🔧 Available MCP tools in ToolUniverse:")
# for tool_name in mcp_tools:
#     tool_config = tooluni.all_tool_dict.get(tool_name, {})
#     print(f"  - {tool_name}: {tool_config.get('description', 'No description')}")

print("\n✨ MCP integration test completed!")
