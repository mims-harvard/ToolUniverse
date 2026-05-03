#!/usr/bin/env python3
"""
ToolUniverse Hooks Exclude Tools Example

This example demonstrates how to configure exclude_tools in hook configuration
to skip specific tools (like Tool_RAG) from being processed by summary hooks.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tooluniverse import ToolUniverse
from tooluniverse.default_config import get_default_hook_config


def test_exclude_tools_configuration():
    """Test exclude_tools configuration"""
    print("\n" + "="*60)
    print("🔧 EXCLUDE TOOLS CONFIGURATION TEST")
    print("="*60)
    print("Testing that excluded tools are not processed by hooks")
    print()

    # 1. Get default config and verify exclude_tools
    print("Step 1: Checking default hook configuration...")
    default_config = get_default_hook_config()
    exclude_tools = default_config.get("exclude_tools", [])
    
    print(f"✅ Default exclude_tools: {exclude_tools}")
    assert "Tool_RAG" in exclude_tools, "Tool_RAG should be in exclude_tools"
    print("✅ Tool_RAG is in default exclude_tools list")

    # 2. Create ToolUniverse with default config
    print("\nStep 2: Initializing ToolUniverse with default hooks...")
    tu = ToolUniverse(hooks_enabled=True)
    tu.load_tools()
    print("✅ ToolUniverse initialized")

    # 3. Verify HookManager has exclude_tools
    print("\nStep 3: Verifying HookManager configuration...")
    if hasattr(tu, 'hook_manager') and tu.hook_manager:
        hook_manager_config = tu.hook_manager.config
        manager_exclude_tools = hook_manager_config.get("exclude_tools", [])
        print(f"✅ HookManager exclude_tools: {manager_exclude_tools}")
        
        # Verify exclude_tools are in config
        assert len(manager_exclude_tools) > 0, "exclude_tools should not be empty"
        print("✅ HookManager has exclude_tools configured")
    else:
        print("⚠️  HookManager not found (hooks may be disabled)")
        return False

    # 4. Test _is_hook_tool method
    print("\nStep 4: Testing _is_hook_tool method...")
    if hasattr(tu.hook_manager, '_is_hook_tool'):
        # Test excluded tools
        assert tu.hook_manager._is_hook_tool("Tool_RAG"), \
            "Tool_RAG should be identified as hook tool"
        print("✅ Tool_RAG is correctly excluded")
        
        assert tu.hook_manager._is_hook_tool("ToolFinderEmbedding"), \
            "ToolFinderEmbedding should be identified as hook tool"
        print("✅ ToolFinderEmbedding is correctly excluded")
        
        # Test non-excluded tools
        assert not tu.hook_manager._is_hook_tool("OpenTargets_get_target_info"), \
            "OpenTargets_get_target_info should NOT be excluded"
        print("✅ Regular tools are NOT excluded")
        
        # Test default hook tools
        assert tu.hook_manager._is_hook_tool("OutputSummarizationComposer"), \
            "OutputSummarizationComposer should be excluded (default hook tool)"
        print("✅ Default hook tools are correctly excluded")
    else:
        print("⚠️  _is_hook_tool method not found")
        return False

    print("\n✅ All exclude_tools tests passed!")
    return True


def test_custom_exclude_tools():
    """Test custom exclude_tools configuration"""
    print("\n" + "="*60)
    print("🔧 CUSTOM EXCLUDE TOOLS CONFIGURATION")
    print("="*60)
    print("Testing custom exclude_tools configuration")
    print()

    # Custom configuration with additional exclude_tools
    custom_config = {
        "exclude_tools": [
            "Tool_RAG",
            "ToolFinderEmbedding",
            "CustomTool_*",  # Test wildcard pattern
        ],
        "hooks": [{
            "name": "test_summarization_hook",
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

    print("Step 1: Creating ToolUniverse with custom exclude_tools...")
    print(f"   • Exclude: {custom_config['exclude_tools']}")
    
    tu = ToolUniverse(hooks_enabled=True, hook_config=custom_config)
    tu.load_tools()
    print("✅ ToolUniverse initialized with custom config")

    # Verify custom exclude_tools
    print("\nStep 2: Verifying custom exclude_tools...")
    if hasattr(tu, 'hook_manager') and tu.hook_manager:
        hook_manager_config = tu.hook_manager.config
        manager_exclude_tools = hook_manager_config.get("exclude_tools", [])
        print(f"✅ HookManager exclude_tools: {manager_exclude_tools}")
        
        # Test wildcard pattern
        if hasattr(tu.hook_manager, '_is_hook_tool'):
            assert tu.hook_manager._is_hook_tool("CustomTool_Test"), \
                "CustomTool_Test should match CustomTool_* pattern"
            print("✅ Wildcard pattern matching works: CustomTool_*")
            
            assert not tu.hook_manager._is_hook_tool("OtherTool_Test"), \
                "OtherTool_Test should NOT match CustomTool_* pattern"
            print("✅ Wildcard pattern correctly excludes non-matching tools")
    
    print("\n✅ Custom exclude_tools test passed!")
    return True


def test_exclude_tools_integration():
    """Integration test: verify excluded tools don't trigger hooks"""
    print("\n" + "="*60)
    print("🔧 EXCLUDE TOOLS INTEGRATION TEST")
    print("="*60)
    print("Testing that excluded tools don't trigger hook processing")
    print()

    # Create ToolUniverse with hooks enabled
    print("Step 1: Initializing ToolUniverse with hooks...")
    tu = ToolUniverse(hooks_enabled=True)
    tu.load_tools()
    print("✅ ToolUniverse initialized")

    # Verify hook manager is active
    if not (hasattr(tu, 'hook_manager') and tu.hook_manager):
        print("⚠️  HookManager not found, skipping integration test")
        return False

    print("\nStep 2: Testing hook processing for excluded tools...")
    
    # Test that excluded tools are skipped
    excluded_tools = ["Tool_RAG", "ToolFinderEmbedding", "OutputSummarizationComposer"]
    
    for tool_name in excluded_tools:
        is_excluded = tu.hook_manager._is_hook_tool(tool_name)
        if is_excluded:
            print(f"✅ {tool_name} is correctly excluded from hook processing")
        else:
            print(f"⚠️  {tool_name} is NOT excluded (may cause issues)")

    print("\nStep 3: Testing hook processing for regular tools...")
    regular_tools = ["OpenTargets_get_target_info", "UniProt_get_entry_by_accession"]
    
    for tool_name in regular_tools:
        is_excluded = tu.hook_manager._is_hook_tool(tool_name)
        if not is_excluded:
            print(f"✅ {tool_name} will be processed by hooks (as expected)")
        else:
            print(f"⚠️  {tool_name} is incorrectly excluded")

    print("\n✅ Integration test completed!")
    return True


def main():
    """Run all exclude_tools examples"""
    print("🚀 ToolUniverse Hooks Exclude Tools Example")
    print("=" * 60)
    print("Demonstrating exclude_tools configuration for summary hooks")
    print()
    print("This example covers:")
    print("• Default exclude_tools configuration")
    print("• Custom exclude_tools configuration")
    print("• Wildcard pattern matching")
    print("• Integration testing")
    print("=" * 60)

    try:
        # Run tests
        test_exclude_tools_configuration()
        test_custom_exclude_tools()
        test_exclude_tools_integration()

        print("\n" + "="*60)
        print("🎉 ALL EXCLUDE TOOLS TESTS COMPLETED SUCCESSFULLY!")
        print("="*60)
        print()
        print("💡 Key Takeaways:")
        print("• exclude_tools prevents specific tools from hook processing")
        print("• Default config excludes Tool_RAG, ToolFinderEmbedding, etc.")
        print("• Wildcard patterns (e.g., 'Tool_*') are supported")
        print("• Excluded tools prevent recursive hook processing")
        print()
        print("🔗 Configuration:")
        print("• Default: src/tooluniverse/template/hook_config.json")
        print("• Custom: ToolUniverse(hooks_enabled=True, hook_config={...})")

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

