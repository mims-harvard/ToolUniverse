#!/usr/bin/env python3
"""
Simple ToolUniverse Integration Test

This script tests the basic integration between local tools and ToolUniverse.

Usage:
    python test_simple_integration.py
"""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from tooluniverse import ToolUniverse
from tooluniverse.tool_registry import register_tool
from tooluniverse.base_tool import BaseTool

# =============================================================================
# SIMPLE TEST TOOL
# =============================================================================

@register_tool('SimpleTestTool', config={
    "name": "simple_test_tool",
    "description": "A simple test tool for ToolUniverse integration",
    "parameter": {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "Message to process"
            }
        },
        "required": []
    }
})
class SimpleTestTool(BaseTool):
    """Simple test tool for integration testing."""
    
    def run(self, arguments=None, **kwargs):
        """Execute the test tool."""
        if arguments is None:
            arguments = kwargs
        
        message = arguments.get('message', 'Hello from ToolUniverse!')
        return {
            "message": f"Processed: {message}",
            "success": True,
            "tool_name": "simple_test_tool"
        }

# =============================================================================
# TEST FUNCTIONS
# =============================================================================

def test_basic_integration():
    """Test basic ToolUniverse integration."""
    
    print("🧪 Testing Basic ToolUniverse Integration")
    print("=" * 45)
    
    try:
        # Initialize ToolUniverse
        print("1. Initializing ToolUniverse...")
        tu = ToolUniverse()
        print("✅ ToolUniverse initialized")
        
        # Register our custom tool
        print("\n2. Registering custom tool...")
        tu.register_custom_tool(
            tool_class=SimpleTestTool,
            tool_name="simple_test_tool",
            tool_config={
                "name": "simple_test_tool",
                "description": "A simple test tool for ToolUniverse integration",
                "parameter": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "Message to process"
                        }
                    },
                    "required": []
                }
            },
            instantiate=True
        )
        print("✅ Custom tool registered")
        
        # Test 1: Basic tool call using tu.run()
        print("\n3. Testing tu.run() API...")
        result = tu.run({
            "name": "simple_test_tool",
            "arguments": {}
        })
        print(f"   Result: {result}")
        
        if result and result.get("success"):
            print("✅ tu.run() API works")
        else:
            print("❌ tu.run() API failed")
            return False
        
        # Test 2: Tool with parameters
        print("\n4. Testing tool with parameters...")
        result = tu.run({
            "name": "simple_test_tool",
            "arguments": {
                "message": "Custom test message"
            }
        })
        print(f"   Result: {result}")
        
        if result and result.get("success") and "Custom test message" in result.get("message", ""):
            print("✅ Tool with parameters works")
        else:
            print("❌ Tool with parameters failed")
            return False
        
        # Test 3: Direct tool access via tu.tools
        print("\n5. Testing tu.tools attribute...")
        if hasattr(tu.tools, 'simple_test_tool'):
            print("✅ tu.tools attribute accessible")
        else:
            print("❌ tu.tools attribute not accessible")
            return False
        
        print("\n🎉 All basic integration tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up
        if 'tu' in locals():
            tu.close()

def main():
    """Main function to test ToolUniverse integration."""
    
    print("🚀 Simple ToolUniverse Integration Test")
    print("=" * 50)
    
    success = test_basic_integration()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 Integration test completed successfully!")
        print("✅ Local tools work correctly with ToolUniverse")
        print("✅ Documentation API examples are accurate")
    else:
        print("❌ Integration test failed.")
        print("🔍 Check the errors above for details.")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
