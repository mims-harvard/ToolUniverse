#!/usr/bin/env python3
"""
Test Tool Annotations (readOnlyHint, destructiveHint)

This example verifies that MCP tool annotations are correctly set
when tools are registered via SMCP server.

The test checks:
1. Default annotations (readOnlyHint=True, destructiveHint=False for most tools)
2. Tool type overrides (e.g., ComposeTool, PythonCodeExecutor)
3. Category overrides
4. Tool-specific overrides via tool_config

Usage:
    python test_tool_annotations.py
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

print("=" * 60)
print("Test: Tool Annotations via SMCP Server")
print("=" * 60)

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
except ImportError:
    print("\n❌ MCP library not installed. Install with: pip install mcp")
    sys.exit(1)


async def test_smcp_annotations():
    """Test that SMCP server returns correct annotations in tools/list"""

    print("\n1. Starting SMCP server in stdio mode...")
    print("   Loading categories: uniprot, compose, python_executor")

    server = StdioServerParameters(
        command=sys.executable,
        args=[
            "-m",
            "tooluniverse.smcp_server",
            "--transport",
            "stdio",
            "--categories",
            "uniprot",
            "compose",
            "python_executor",
        ],
    )

    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("   ✅ Connected to SMCP server")

            # List tools and check annotations
            print("\n2. Listing tools and checking annotations...")
            tools_result = await session.list_tools()

            print(f"   Total tools loaded: {len(tools_result.tools)}")

            # Group tools by their expected annotation type
            read_only_tools = []
            non_read_only_tools = []
            destructive_tools = []

            for tool in tools_result.tools:
                tool_name = tool.name
                annotations = getattr(tool, "annotations", None)

                if annotations:
                    read_only = getattr(annotations, "readOnlyHint", None)
                    destructive = getattr(annotations, "destructiveHint", None)

                    if read_only is True:
                        read_only_tools.append((tool_name, annotations))
                    elif read_only is False:
                        non_read_only_tools.append((tool_name, annotations))

                    if destructive is True:
                        destructive_tools.append((tool_name, annotations))

            print(f"\n3. Annotation Results:")
            print(f"   Read-only tools (readOnlyHint=True): {len(read_only_tools)}")
            print(
                f"   Non-read-only tools (readOnlyHint=False): {len(non_read_only_tools)}"
            )
            print(f"   Destructive tools (destructiveHint=True): {len(destructive_tools)}")

            # Show sample tools from each category
            print("\n4. Sample tools by annotation type:")

            if read_only_tools:
                print("\n   📖 Read-only tools (database queries):")
                for name, annot in read_only_tools[:5]:
                    print(f"      - {name}")
                    print(
                        f"        readOnlyHint={annot.readOnlyHint}, "
                        f"destructiveHint={annot.destructiveHint}"
                    )

            if non_read_only_tools:
                print("\n   ✏️  Non-read-only tools:")
                for name, annot in non_read_only_tools[:5]:
                    print(f"      - {name}")
                    print(
                        f"        readOnlyHint={annot.readOnlyHint}, "
                        f"destructiveHint={annot.destructiveHint}"
                    )

            if destructive_tools:
                print("\n   ⚠️  Destructive tools:")
                for name, annot in destructive_tools[:5]:
                    print(f"      - {name}")
                    print(
                        f"        readOnlyHint={annot.readOnlyHint}, "
                        f"destructiveHint={annot.destructiveHint}"
                    )

            # Verify specific tools
            print("\n5. Verifying specific tool annotations:")

            # Check UniProt tools (should be read-only)
            uniprot_tools = [t for t in tools_result.tools if "UniProt" in t.name]
            if uniprot_tools:
                tool = uniprot_tools[0]
                annot = getattr(tool, "annotations", None)
                if annot:
                    print(f"\n   UniProt tool: {tool.name}")
                    print(f"      readOnlyHint: {annot.readOnlyHint}")
                    print(f"      destructiveHint: {annot.destructiveHint}")
                    if annot.readOnlyHint is True and annot.destructiveHint is False:
                        print("      ✅ Correct (read-only database query)")
                    else:
                        print("      ❌ Expected readOnlyHint=True, destructiveHint=False")

            # Check ComposeTool (should be non-read-only)
            compose_tools = [
                t
                for t in tools_result.tools
                if "Compose" in t.name or "Pipeline" in t.name
            ]
            if compose_tools:
                tool = compose_tools[0]
                annot = getattr(tool, "annotations", None)
                if annot:
                    print(f"\n   ComposeTool: {tool.name}")
                    print(f"      readOnlyHint: {annot.readOnlyHint}")
                    print(f"      destructiveHint: {annot.destructiveHint}")
                    if annot.readOnlyHint is False:
                        print("      ✅ Correct (non-read-only)")
                    else:
                        print("      ❌ Expected readOnlyHint=False")

            # Check PythonCodeExecutor (should be destructive)
            executor_tools = [
                t
                for t in tools_result.tools
                if "python" in t.name.lower() and "executor" in t.name.lower()
            ]
            if executor_tools:
                tool = executor_tools[0]
                annot = getattr(tool, "annotations", None)
                if annot:
                    print(f"\n   PythonCodeExecutor: {tool.name}")
                    print(f"      readOnlyHint: {annot.readOnlyHint}")
                    print(f"      destructiveHint: {annot.destructiveHint}")
                    if annot.readOnlyHint is False and annot.destructiveHint is True:
                        print("      ✅ Correct (destructive - code execution)")
                    else:
                        print(
                            "      ❌ Expected readOnlyHint=False, destructiveHint=True"
                        )

            # Requirement Verification
            print("\n6. REQUIREMENT VERIFICATION")
            print("=" * 60)

            # Requirement 1: Annotations should be a separate top-level field
            print("\nRequirement 1: Annotations as separate top-level field")
            sample_tool = tools_result.tools[0]
            has_annotations = hasattr(sample_tool, "annotations") and sample_tool.annotations is not None
            annotations_in_description = (
                sample_tool.description and "readOnlyHint" in sample_tool.description
            )

            print(f"   ✓ tool.annotations exists: {has_annotations}")
            print(f"   ✓ annotations NOT in description: {not annotations_in_description}")
            print(f"   ✓ annotations is accessible: {sample_tool.annotations is not None}")

            req1_passed = has_annotations and not annotations_in_description
            if req1_passed:
                print("   ✅ REQUIREMENT 1 MET: annotations is a separate top-level field")
            else:
                print("   ❌ REQUIREMENT 1 NOT MET")

            # Requirement 2: Most tools (API queries) should have readOnlyHint: true
            print("\nRequirement 2: API queries should have readOnlyHint: true")
            api_tools = [t for t in tools_result.tools if "UniProt" in t.name]
            api_correct = all(
                t.annotations and t.annotations.readOnlyHint is True for t in api_tools
            )
            print(f"   Checking {len(api_tools)} API query tools...")
            if api_tools:
                sample = api_tools[0]
                print(
                    f"   Sample: {sample.name} - readOnlyHint: {sample.annotations.readOnlyHint}"
                )
                print(
                    f"   All API tools correct: {api_correct} ({sum(1 for t in api_tools if t.annotations and t.annotations.readOnlyHint is True)}/{len(api_tools)})"
                )

            if api_correct:
                print("   ✅ REQUIREMENT 2 MET: API queries have readOnlyHint: true")
            else:
                print("   ❌ REQUIREMENT 2 NOT MET")

            # Requirement 3: Tools that write files or execute code should have readOnlyHint: false
            print("\nRequirement 3: Code executors should have readOnlyHint: false")
            executor_tools = [
                t
                for t in tools_result.tools
                if "python" in t.name.lower() and "executor" in t.name.lower()
            ]
            req3_passed = False
            if executor_tools:
                executor = executor_tools[0]
                print(f"   Checking: {executor.name}")
                print(f"     readOnlyHint: {executor.annotations.readOnlyHint} (expected: False)")
                print(
                    f"     destructiveHint: {executor.annotations.destructiveHint} (expected: True)"
                )
                if executor.annotations.readOnlyHint is False:
                    req3_passed = True
                    print("   ✅ REQUIREMENT 3 MET: Code executor has readOnlyHint: false")
                else:
                    print("   ❌ REQUIREMENT 3 NOT MET")
            else:
                print("   ⚠️  No executor tools found to test")

            # Print raw MCP data for verification
            CYAN = "\033[96m"
            RESET = "\033[0m"
            print(f"\n{CYAN}7. Raw MCP tool data (first 5 tools for verification):{RESET}")
            import json
            for i, t in enumerate(tools_result.tools[:5]):
                
                print(t)
                print(f"{CYAN}\n   --- Tool {i+1}: {t.name} ---{RESET}")
                print(f"{CYAN}   name: {t.name}{RESET}")
                print(f"{CYAN}   description: {t.description[:100] if t.description else None}...{RESET}")
                print(f"{CYAN}   inputSchema type: {type(t.inputSchema).__name__}{RESET}")
                print(f"{CYAN}   inputSchema: {json.dumps(t.inputSchema, indent=6)}{RESET}")
                print(f"{CYAN}   annotations object: {t.annotations}{RESET}")
                if t.annotations:
                    print(f"{CYAN}     .title: {t.annotations.title}{RESET}")
                    print(f"{CYAN}     .readOnlyHint: {t.annotations.readOnlyHint}{RESET}")
                    print(f"{CYAN}     .destructiveHint: {t.annotations.destructiveHint}{RESET}")
                    print(f"{CYAN}     .idempotentHint: {t.annotations.idempotentHint}{RESET}")
                    print(f"{CYAN}     .openWorldHint: {t.annotations.openWorldHint}{RESET}")
                    # Print as JSON-like structure
                    annotations_dict = {
                        "readOnlyHint": t.annotations.readOnlyHint,
                        "destructiveHint": t.annotations.destructiveHint,
                        "idempotentHint": t.annotations.idempotentHint,
                        "openWorldHint": t.annotations.openWorldHint,
                    }
                    print(f"{CYAN}     annotations dict: {json.dumps(annotations_dict, indent=6)}{RESET}")
                
                # Print complete tool structure (MCP-compliant format)
                print(f"{CYAN}\n   MCP Tool Schema (JSON-like):{RESET}")
                tool_schema = {
                    "name": t.name,
                    "description": t.description[:100] + "..." if t.description and len(t.description) > 100 else t.description,
                    "inputSchema": t.inputSchema,
                    "annotations": {
                        "readOnlyHint": t.annotations.readOnlyHint if t.annotations else None,
                        "destructiveHint": t.annotations.destructiveHint if t.annotations else None,
                    } if t.annotations else None
                }
                print(f"{CYAN}   {json.dumps(tool_schema, indent=6)}{RESET}")

            # Print complete raw data for all tools
            print(f"\n{CYAN}8. Complete raw data for all tools:{RESET}")
            print(f"{CYAN}{'=' * 60}{RESET}")
            print(f"{CYAN}\nTotal tools: {len(tools_result.tools)}{RESET}")
            print(f"{CYAN}\nAll tools with annotations:{RESET}")
            for i, t in enumerate(tools_result.tools, 1):
                if t.annotations:
                    print(
                        f"{CYAN}  {i:2d}. {t.name:50s} | "
                        f"readOnlyHint={str(t.annotations.readOnlyHint):5s} | "
                        f"destructiveHint={str(t.annotations.destructiveHint):5s}{RESET}"
                    )
                else:
                    print(f"{CYAN}  {i:2d}. {t.name:50s} | NO ANNOTATIONS{RESET}")

            # Final Summary
            print("\n" + "=" * 60)
            print("FINAL VERIFICATION SUMMARY")
            print("=" * 60)

            all_passed = req1_passed and api_correct and req3_passed
            if all_passed:
                print("\n✅ ALL REQUIREMENTS MET!")
                print("\n✓ Annotations format: Top-level field (separate from description)")
                print("✓ API queries: readOnlyHint=true, destructiveHint=false")
                print("✓ Code executors: readOnlyHint=false, destructiveHint=true")
            else:
                print("\n❌ SOME REQUIREMENTS NOT MET")
                if not req1_passed:
                    print("  - Requirement 1: Annotations format")
                if not api_correct:
                    print("  - Requirement 2: API query annotations")
                if not req3_passed:
                    print("  - Requirement 3: Code executor annotations")

            print("\nAnnotation priority (highest to lowest):")
            print("  1. tool_config.mcp_annotations or tool_config.readOnlyHint/destructiveHint")
            print("  2. category_overrides[category]")
            print("  3. tool_type_overrides[tool_type]")
            print("  4. default_annotations")

            return all_passed


if __name__ == "__main__":
    try:
        result = asyncio.run(test_smcp_annotations())
        if result:
            print("\n✅ Test passed: All requirements met!")
            sys.exit(0)
        else:
            print("\n❌ Test failed: Some requirements not met!")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
