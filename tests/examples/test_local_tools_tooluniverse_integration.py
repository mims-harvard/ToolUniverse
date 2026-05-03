#!/usr/bin/env python3
"""
Test ToolUniverse Integration with Local Tools

This script tests the integration between local tools and ToolUniverse,
verifying that the API described in the documentation works correctly.

Usage:
    python test_tooluniverse_integration.py
"""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from tooluniverse import ToolUniverse
from tooluniverse.tool_registry import register_tool
from tooluniverse.base_tool import BaseTool

# =============================================================================
# TEST TOOL DEFINITIONS
# =============================================================================

@register_tool('TestHelloTool', config={
    "name": "test_hello_tool",
    "description": "A test hello world tool for ToolUniverse integration"
})
class TestHelloTool(BaseTool):
    """Test hello world tool for integration testing."""
    
    def run(self, arguments=None, **kwargs):
        """Execute the hello tool."""
        return {"message": "Hello from ToolUniverse!", "success": True}

@register_tool('TestMathTool', config={
    "name": "test_math_tool",
    "description": "Test mathematical operations for ToolUniverse integration",
    "parameter": {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["add", "subtract", "multiply", "divide"],
                "description": "Mathematical operation"
            },
            "a": {"type": "number", "description": "First number"},
            "b": {"type": "number", "description": "Second number"}
        },
        "required": ["operation", "a", "b"]
    }
})
class TestMathTool(BaseTool):
    """Test math tool for integration testing."""
    
    def run(self, arguments=None, **kwargs):
        """Execute mathematical operation."""
        if arguments is None:
            arguments = kwargs
        
        if not isinstance(arguments, dict):
            return {"error": "Arguments must be a dictionary", "success": False}
        
        operation = arguments.get('operation')
        a = arguments.get('a')
        b = arguments.get('b')
        
        try:
            a = float(a)
            b = float(b)
        except (ValueError, TypeError):
            return {"error": "Invalid number format", "success": False}
        
        if operation == "add":
            result = a + b
        elif operation == "subtract":
            result = a - b
        elif operation == "multiply":
            result = a * b
        elif operation == "divide":
            if b == 0:
                return {"error": "Division by zero", "success": False}
            result = a / b
        else:
            return {"error": f"Unknown operation: {operation}", "success": False}
        
        return {
            "result": result,
            "operation": operation,
            "a": a,
            "b": b,
            "success": True
        }

# =============================================================================
# TEST FUNCTIONS
# =============================================================================

def test_tooluniverse_initialization():
    """Test ToolUniverse initialization."""
    
    print("🧪 Testing ToolUniverse Initialization")
    print("=" * 40)
    
    try:
        # Initialize ToolUniverse
        tu = ToolUniverse()
        print("✅ ToolUniverse initialized successfully")

        # Check if tools are loaded
        print(f"📊 Loaded tools: {len(tu.tools) if hasattr(tu, 'tools') else 'N/A'}")

        return True
    except Exception as e:
        print(f"❌ ToolUniverse initialization failed: {e}")
        return False
    finally:
        if 'tu' in locals():
            tu.close()

def test_tool_registration():
    """Test that our tools are registered."""
    
    print("\n🧪 Testing Tool Registration")
    print("=" * 30)
    
    try:
        from tooluniverse.tool_registry import get_tool_registry
        
        registry = get_tool_registry()
        print(f"✅ Tool registry accessible: {len(registry)} tools registered")
        
        # Check our specific tools
        test_tools = ["test_hello_tool", "test_math_tool"]
        for tool_name in test_tools:
            if tool_name in registry:
                print(f"✅ {tool_name} is registered")
            else:
                print(f"❌ {tool_name} not found in registry")
        
        return True
        
    except Exception as e:
        print(f"❌ Tool registration test failed: {e}")
        return False

def test_tu_run_api():
    """Test the tu.run() API as described in documentation."""
    
    print("\n🧪 Testing tu.run() API")
    print("=" * 25)
    
    try:
        # Initialize ToolUniverse
        tu = ToolUniverse()
        
        # Register our custom tools
        print("\n--- Registering custom tools ---")
        tu.register_custom_tool(
            tool_class=TestHelloTool,
            tool_name="test_hello_tool",
            tool_config={"name": "test_hello_tool", "description": "Test hello tool"},
            instantiate=True
        )
        
        tu.register_custom_tool(
            tool_class=TestMathTool,
            tool_name="test_math_tool",
            tool_config={
                "name": "test_math_tool", 
                "description": "Test math tool",
                "parameter": {
                    "type": "object",
                    "properties": {
                        "operation": {"type": "string", "enum": ["add", "subtract", "multiply", "divide"]},
                        "a": {"type": "number"},
                        "b": {"type": "number"}
                    },
                    "required": ["operation", "a", "b"]
                }
            },
            instantiate=True
        )
        print("✅ Custom tools registered")
        
        # Test 1: Simple tool call using tu.run()
        print("\n--- Test 1: Simple tool call ---")
        result = tu.run({
            "name": "test_hello_tool",
            "arguments": {}
        })
        print(f"Result: {result}")
        
        if result and result.get("success"):
            print("✅ Simple tool call successful")
        else:
            print("❌ Simple tool call failed")
            return False
        
        # Test 2: Tool with parameters using tu.run()
        print("\n--- Test 2: Tool with parameters ---")
        result = tu.run({
            "name": "test_math_tool",
            "arguments": {
                "operation": "multiply",
                "a": 6,
                "b": 7
            }
        })
        print(f"Result: {result}")
        
        if result and result.get("success") and result.get("result") == 42:
            print("✅ Parameterized tool call successful")
        else:
            print("❌ Parameterized tool call failed")
            return False
        
        # Test 3: Error handling
        print("\n--- Test 3: Error handling ---")
        result = tu.run({
            "name": "test_math_tool",
            "arguments": {
                "operation": "divide",
                "a": 10,
                "b": 0
            }
        })
        print(f"Result: {result}")
        
        if result and not result.get("success") and "error" in result:
            print("✅ Error handling works correctly")
        else:
            print("❌ Error handling failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ tu.run() API test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if 'tu' in locals():
            tu.close()

def test_tu_tools_attribute():
    """Test the tu.tools attribute access."""
    
    print("\n🧪 Testing tu.tools Attribute")
    print("=" * 30)
    
    try:
        # Initialize ToolUniverse
        tu = ToolUniverse()
        
        # Register our custom tools
        tu.register_custom_tool(
            tool_class=TestHelloTool,
            tool_name="test_hello_tool",
            tool_config={"name": "test_hello_tool", "description": "Test hello tool"},
            instantiate=True
        )
        
        tu.register_custom_tool(
            tool_class=TestMathTool,
            tool_name="test_math_tool",
            tool_config={
                "name": "test_math_tool", 
                "description": "Test math tool",
                "parameter": {
                    "type": "object",
                    "properties": {
                        "operation": {"type": "string", "enum": ["add", "subtract", "multiply", "divide"]},
                        "a": {"type": "number"},
                        "b": {"type": "number"}
                    },
                    "required": ["operation", "a", "b"]
                }
            },
            instantiate=True
        )
        
        # Check if tu.tools exists
        if not hasattr(tu, 'tools'):
            print("❌ tu.tools attribute not found")
            return False
        
        print("✅ tu.tools attribute exists")
        
        # Try to access tools directly
        if hasattr(tu.tools, 'test_hello_tool'):
            print("✅ test_hello_tool accessible via tu.tools")
        else:
            print("❌ test_hello_tool not accessible via tu.tools")
            return False
        
        if hasattr(tu.tools, 'test_math_tool'):
            print("✅ test_math_tool accessible via tu.tools")
        else:
            print("❌ test_math_tool not accessible via tu.tools")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ tu.tools attribute test failed: {e}")
        return False
    finally:
        if 'tu' in locals():
            tu.close()

def test_parallel_execution():
    """Test parallel execution using tu.run() with list."""
    
    print("\n🧪 Testing Parallel Execution")
    print("=" * 30)
    
    try:
        # Initialize ToolUniverse
        tu = ToolUniverse()
        
        # Register our custom tools
        tu.register_custom_tool(
            tool_class=TestHelloTool,
            tool_name="test_hello_tool",
            tool_config={"name": "test_hello_tool", "description": "Test hello tool"},
            instantiate=True
        )
        
        tu.register_custom_tool(
            tool_class=TestMathTool,
            tool_name="test_math_tool",
            tool_config={
                "name": "test_math_tool", 
                "description": "Test math tool",
                "parameter": {
                    "type": "object",
                    "properties": {
                        "operation": {"type": "string", "enum": ["add", "subtract", "multiply", "divide"]},
                        "a": {"type": "number"},
                        "b": {"type": "number"}
                    },
                    "required": ["operation", "a", "b"]
                }
            },
            instantiate=True
        )
        
        # Test parallel execution
        results = tu.run([
            {
                "name": "test_hello_tool",
                "arguments": {}
            },
            {
                "name": "test_math_tool",
                "arguments": {
                    "operation": "add",
                    "a": 10,
                    "b": 20
                }
            }
        ])
        
        print(f"Parallel results: {results}")
        
        if isinstance(results, list) and len(results) == 2:
            print("✅ Parallel execution returned list of results")
            
            # Check individual results
            if results[0].get("success") and results[1].get("success"):
                print("✅ Both parallel tasks succeeded")
                return True
            else:
                print("❌ Some parallel tasks failed")
                return False
        else:
            print("❌ Parallel execution did not return expected format")
            return False
        
    except Exception as e:
        print(f"❌ Parallel execution test failed: {e}")
        return False
    finally:
        if 'tu' in locals():
            tu.close()

# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """Main function to test ToolUniverse integration."""
    
    print("🚀 ToolUniverse Integration Test")
    print("=" * 40)
    
    tests = [
        ("ToolUniverse Initialization", test_tooluniverse_initialization),
        ("Tool Registration", test_tool_registration),
        ("tu.run() API", test_tu_run_api),
        ("tu.tools Attribute", test_tu_tools_attribute),
        ("Parallel Execution", test_parallel_execution)
    ]
    
    results = []
    for test_name, test_func in tests:
        result = test_func()
        results.append((test_name, result))
    
    print("\n📊 Test Results:")
    print("-" * 20)
    
    all_passed = True
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if not result:
            all_passed = False
    
    print("\n" + "=" * 40)
    if all_passed:
        print("🎉 All integration tests passed!")
        print("✅ Local tools work correctly with ToolUniverse")
        print("✅ Documentation API examples are accurate")
    else:
        print("❌ Some integration tests failed.")
        print("🔍 Check the errors above for details.")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
