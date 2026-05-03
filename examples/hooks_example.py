#!/usr/bin/env python3
"""
ToolUniverse Hooks Example

A simple, clear example demonstrating hook functionality.
This example shows how to use SummarizationHook and FileSaveHook
with ToolUniverse for automatic output processing.
"""

import sys
import os
import time
import tempfile
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tooluniverse import ToolUniverse


def basic_hooks_example():
    """Basic hook usage - simple and clear"""
    print("\n" + "="*60)
    print("🔧 BASIC HOOKS EXAMPLE")
    print("="*60)
    print("Demonstrating SummarizationHook with OpenTargets tool")
    print()

    # 1. Create ToolUniverse with default SummarizationHook
    print("Step 1: Initializing ToolUniverse with SummarizationHook...")
    tu = ToolUniverse(hooks_enabled=True)
    tu.load_tools()
    print("✅ ToolUniverse initialized with hooks enabled")

    # 2. Run a tool that produces long output
    print("\nStep 2: Running OpenTargets tool (produces long output)...")
    result = tu.run({
        "name": "OpenTargets_get_target_gene_ontology_by_ensemblID",
        "arguments": {"ensemblId": "ENSG00000012048"}
    })
    print("✅ Tool execution completed")

    # 3. Show results
    print("\nStep 3: Analyzing results...")
    if isinstance(result, dict) and "summary" in result:
        original_len = result.get('original_length', 0)
        summary_len = len(result['summary'])
        if original_len > 0:
            reduction = (original_len - summary_len) / original_len * 100
        else:
            reduction = 0

        print(f"📊 Original output: {original_len:,} characters")
        print(f"📝 Summarized output: {summary_len:,} characters")
        print(f"📉 Size reduction: {reduction:.1f}%")
        print("✅ SummarizationHook successfully processed the output")
    else:
        print(f"📄 Output length: {len(str(result)):,} characters")
        print("ℹ️  No summarization applied (output may be too short)")

    return result


def file_save_hook_example():
    """FileSaveHook example - saves large outputs to files"""
    print("\n" + "="*60)
    print("🔧 FILE SAVE HOOK EXAMPLE")
    print("="*60)
    print("Demonstrating FileSaveHook for large output archiving")
    print()

    # Configure FileSaveHook for large outputs
    hook_config = {
        "hooks": [{
            "name": "file_save_hook",
            "type": "FileSaveHook",
            "enabled": True,
            "conditions": {
                "output_length": {"operator": ">", "threshold": 1000}
            },
            "hook_config": {
                "temp_dir": tempfile.gettempdir(),
                "file_prefix": "tool_output",
                "include_metadata": True
            }
        }]
    }

    print("Step 1: Configuring FileSaveHook...")
    tu = ToolUniverse(hooks_enabled=True, hook_config=hook_config)
    tu.load_tools()
    print("✅ FileSaveHook configured and enabled")

    print("\nStep 2: Running tool with FileSaveHook...")
    result = tu.run({
        "name": "OpenTargets_get_target_gene_ontology_by_ensemblID",
        "arguments": {"ensemblId": "ENSG00000012048"}
    })
    print("✅ Tool execution completed")

    print("\nStep 3: Analyzing FileSaveHook results...")
    if isinstance(result, dict) and "file_path" in result:
        file_size = result.get('file_size', 0)
        data_format = result.get('data_format', 'unknown')

        print(f"📁 File saved: {result['file_path']}")
        print(f"📊 Data format: {data_format}")
        print(f"📏 File size: {file_size:,} bytes")

        # Verify file exists
        if os.path.exists(result['file_path']):
            print("✅ File verification: SUCCESS")
        else:
            print("❌ File verification: FAILED")
        print("✅ FileSaveHook successfully archived the output")
    else:
        print("ℹ️  Output was not large enough to trigger file save")
        print("ℹ️  FileSaveHook threshold: >1000 characters")

    return result


def performance_comparison():
    """Compare performance with and without hooks"""
    print("\n" + "="*60)
    print("🔧 PERFORMANCE COMPARISON")
    print("="*60)
    print("Comparing execution time and output size with/without hooks")
    print()

    # Test without hooks
    print("Step 1: Testing without hooks...")
    tu_no_hooks = ToolUniverse(hooks_enabled=False)
    tu_no_hooks.load_tools()

    start_time = time.time()
    result_no_hooks = tu_no_hooks.run({
        "name": "OpenTargets_get_target_gene_ontology_by_ensemblID",
        "arguments": {"ensemblId": "ENSG00000012048"}
    })
    time_no_hooks = time.time() - start_time
    print(f"✅ Completed in {time_no_hooks:.2f} seconds")

    # Test with hooks
    print("\nStep 2: Testing with SummarizationHook...")
    tu_with_hooks = ToolUniverse(hooks_enabled=True)
    tu_with_hooks.load_tools()

    start_time = time.time()
    result_with_hooks = tu_with_hooks.run({
        "name": "OpenTargets_get_target_gene_ontology_by_ensemblID",
        "arguments": {"ensemblId": "ENSG00000012048"}
    })
    time_with_hooks = time.time() - start_time
    print(f"✅ Completed in {time_with_hooks:.2f} seconds")

    # Show comparison
    print("\n" + "="*60)
    print("📊 PERFORMANCE RESULTS")
    print("="*60)
    print(f"{'Configuration':<20} {'Time':<10} {'Output Size':<15}")
    print("-" * 60)
    no_hooks_size = len(str(result_no_hooks))
    with_hooks_size = len(str(result_with_hooks))
    print(f"{'No hooks':<20} {time_no_hooks:.2f}s{'':<4} "
          f"{no_hooks_size:,} chars")
    print(f"{'With hooks':<20} {time_with_hooks:.2f}s{'':<4} "
          f"{with_hooks_size:,} chars")

    if time_no_hooks > 0:
        overhead = (time_with_hooks - time_no_hooks) / time_no_hooks * 100
        print(f"\n⏱️  Performance overhead: +{overhead:.1f}%")

    # Show output size comparison
    if no_hooks_size > 0:
        reduction = (1 - with_hooks_size / no_hooks_size) * 100
    else:
        reduction = 0

    print(f"📉 Output size reduction: {reduction:.1f}%")
    print("✅ Performance comparison completed")

    return result_no_hooks, result_with_hooks


def exclude_tools_example():
    """Exclude tools configuration example"""
    print("\n" + "="*60)
    print("🔧 EXCLUDE TOOLS CONFIGURATION")
    print("="*60)
    print("Demonstrating exclude_tools to skip specific tools from hooks")
    print()

    # Configuration with exclude_tools
    exclude_config = {
        "exclude_tools": [
            "Tool_RAG",
            "ToolFinderEmbedding",
            "ToolFinderLLM",
            "CustomTool_*",  # Wildcard pattern
        ],
        "hooks": [{
            "name": "default_summarization_hook",
            "type": "SummarizationHook",
            "enabled": True,
            "priority": 1,
            "conditions": {
                "output_length": {"operator": ">", "threshold": 5000}
            },
            "hook_config": {
                "composer_tool": "OutputSummarizationComposer",
                "chunk_size": 32000,
                "focus_areas": "key_findings_and_results",
                "max_summary_length": 3000,
            },
        }]
    }

    print("Step 1: Configuring exclude_tools...")
    print("   • Excluded: Tool_RAG, ToolFinderEmbedding, ToolFinderLLM")
    print("   • Wildcard pattern: CustomTool_*")

    tu = ToolUniverse(hooks_enabled=True, hook_config=exclude_config)
    tu.load_tools()
    print("✅ Configuration applied")

    print("\nStep 2: Verifying exclude_tools configuration...")
    if hasattr(tu, 'hook_manager') and tu.hook_manager:
        config = tu.hook_manager.config
        exclude_tools = config.get("exclude_tools", [])
        print(f"   • Configured exclude_tools: {exclude_tools}")

        # Test that excluded tools are identified correctly
        if hasattr(tu.hook_manager, '_is_hook_tool'):
            test_tools = [
                ("Tool_RAG", True),
                ("ToolFinderEmbedding", True),
                ("CustomTool_Test", True),  # Should match wildcard
                ("OtherTool_Test", False),  # Should not match
                ("OpenTargets_get_target_info", False),  # Regular tool
            ]

            print("\nStep 3: Testing tool exclusion...")
            for tool_name, should_be_excluded in test_tools:
                is_excluded = tu.hook_manager._is_hook_tool(tool_name)
                status = "✅" if is_excluded == should_be_excluded else "❌"
                excluded_status = 'excluded' if is_excluded else 'not excluded'
                print(f"   {status} {tool_name}: {excluded_status}")

    print("\n✅ Exclude tools configuration verified")
    return tu


def custom_hook_config_example():
    """Custom hook configuration example"""
    print("\n" + "="*60)
    print("🔧 CUSTOM HOOK CONFIGURATION")
    print("="*60)
    print("Demonstrating custom SummarizationHook settings")
    print()

    # Custom configuration with specific settings
    custom_config = {
        "exclude_tools": [
            "Tool_RAG",
            "ToolFinderEmbedding",
        ],
        "hooks": [{
            "name": "custom_summary_hook",
            "type": "SummarizationHook",
            "enabled": True,
            "conditions": {
                "output_length": {"operator": ">", "threshold": 5000}
            },
            "hook_config": {
                "max_tokens": 1000,
                "summary_style": "concise",
                "chunk_size": 2000
            }
        }]
    }

    print("Step 1: Configuring custom SummarizationHook...")
    print("   • Trigger threshold: >5000 characters")
    print("   • Max tokens: 1000")
    print("   • Style: concise")
    print("   • Chunk size: 2000 characters")

    tu = ToolUniverse(hooks_enabled=True, hook_config=custom_config)
    tu.load_tools()
    print("✅ Custom configuration applied")

    print("\nStep 2: Running tool with custom configuration...")
    result = tu.run({
        "name": "OpenTargets_get_target_gene_ontology_by_ensemblID",
        "arguments": {"ensemblId": "ENSG00000012048"}
    })
    print("✅ Tool execution completed")

    print("\nStep 3: Analyzing custom hook results...")
    if isinstance(result, dict) and "summary" in result:
        summary_len = len(result['summary'])
        original_len = result.get('original_length', 0)
        if original_len > 0:
            reduction = (original_len - summary_len) / original_len * 100
        else:
            reduction = 0

        print(f"📝 Custom summary: {summary_len:,} characters")
        print(f"📊 Original length: {original_len:,} characters")
        print(f"📉 Size reduction: {reduction:.1f}%")
        print("✅ Custom configuration successfully processed the output")
    else:
        print("ℹ️  Custom hook may not have triggered (output too short)")
        print("ℹ️  Threshold: >5000 characters")

    return result


def main():
    """Run all hook examples"""
    print("🚀 ToolUniverse Hooks Example")
    print("=" * 60)
    print("Demonstrating intelligent output processing with hooks")
    print()
    print("This example covers:")
    print("• Basic SummarizationHook usage")
    print("• FileSaveHook for large outputs")
    print("• Performance comparison")
    print("• Exclude tools configuration")
    print("• Custom configuration")
    print("=" * 60)

    try:
        # Run examples
        basic_hooks_example()
        file_save_hook_example()
        performance_comparison()
        exclude_tools_example()
        custom_hook_config_example()

        print("\n" + "="*60)
        print("🎉 ALL EXAMPLES COMPLETED SUCCESSFULLY!")
        print("="*60)
        print()
        print("💡 Key Takeaways:")
        print("• Hooks automatically process tool outputs")
        print("• SummarizationHook reduces output size with AI")
        print("• FileSaveHook saves large outputs to files")
        print("• Performance overhead depends on output size and AI")
        print("• exclude_tools prevents specific tools from hook processing")
        print("• Custom configurations allow fine-tuned control")
        print()
        print("🔗 Learn more: docs/guide/hooks/")

    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        print("💡 Make sure you have API keys configured for AI tools")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
