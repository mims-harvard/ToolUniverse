#!/usr/bin/env python3
"""
Basic Local Tool Example

This example shows how to create a simple local tool using the @register_tool decorator.
It demonstrates the basic pattern for creating tools that run within ToolUniverse.

Usage:
    python basic_tool.py
"""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from tooluniverse.tool_registry import register_tool
from tooluniverse.base_tool import BaseTool
from tooluniverse import ToolUniverse

# =============================================================================
# BASIC TOOL DEFINITIONS
# =============================================================================

@register_tool('HelloTool', config={
    "name": "hello_tool",
    "description": "Say hello to the user"
})
class HelloTool(BaseTool):
    """Simple hello world tool."""
    
    def run(self, arguments=None, **kwargs):
        """Execute the hello tool."""
        return {"message": "Hello from ToolUniverse!", "success": True}

@register_tool('GreetTool', config={
    "name": "greet_tool",
    "description": "Greet a person by name",
    "parameter": {
        "type": "object",
        "properties": {
            "name": {
                "type": "string", 
                "description": "Person's name to greet"
            }
        },
        "required": ["name"]
    }
})
class GreetTool(BaseTool):
    """Tool that greets a person by name."""
    
    def run(self, arguments=None, **kwargs):
        """Execute the greet tool."""
        # Handle both direct calls and ToolUniverse calls
        if arguments is None:
            arguments = kwargs
        
        # Extract name from arguments
        if isinstance(arguments, dict):
            name = arguments.get('name', 'World')
        else:
            name = str(arguments) if arguments else 'World'
        
        return {
            "message": f"Hello, {name}!",
            "success": True,
            "greeted_person": name
        }

@register_tool('MathTool', config={
    "name": "math_tool",
    "description": "Perform basic mathematical operations",
    "parameter": {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["add", "subtract", "multiply", "divide"],
                "description": "Mathematical operation to perform"
            },
            "a": {
                "type": "number",
                "description": "First number"
            },
            "b": {
                "type": "number", 
                "description": "Second number"
            }
        },
        "required": ["operation", "a", "b"]
    }
})
class MathTool(BaseTool):
    """Tool for basic mathematical operations."""
    
    def run(self, arguments=None, **kwargs):
        """Execute mathematical operation."""
        # Handle both direct calls and ToolUniverse calls
        if arguments is None:
            arguments = kwargs
        
        if not isinstance(arguments, dict):
            return {
                "result": None,
                "error": "Arguments must be a dictionary",
                "success": False
            }
        
        operation = arguments.get('operation')
        a = arguments.get('a')
        b = arguments.get('b')
        
        try:
            a = float(a)
            b = float(b)
        except (ValueError, TypeError):
            return {
                "result": None,
                "error": "Invalid number format",
                "success": False
            }
        
        if operation == "add":
            result = a + b
        elif operation == "subtract":
            result = a - b
        elif operation == "multiply":
            result = a * b
        elif operation == "divide":
            if b == 0:
                return {
                    "result": None,
                    "error": "Division by zero",
                    "success": False
                }
            result = a / b
        else:
            return {
                "result": None,
                "error": f"Unknown operation: {operation}",
                "success": False
            }
        
        return {
            "result": result,
            "operation": operation,
            "a": a,
            "b": b,
            "success": True
        }

# =============================================================================
# TESTING FUNCTIONS
# =============================================================================

def test_basic_tools(tu):
    """Test basic tool functionality."""
    
    print("🧪 Testing Basic Tools")
    print("=" * 30)
    
    # Test HelloTool
    print("\n1. Testing HelloTool:")
    try:
        result = tu.run({
            "name": "hello_tool",
            "arguments": {}
        })
        print(f"   Result: {result}")
        if result.get("success"):
            print("   ✅ HelloTool works")
        else:
            print("   ❌ HelloTool failed")
    except Exception as e:
        print(f"   ❌ HelloTool error: {e}")
    
    # Test GreetTool
    print("\n2. Testing GreetTool:")
    test_cases = [
        {"name": "Alice"},
        {"name": "Bob"},
        {"name": "World"}
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        try:
            result = tu.run({
                "name": "greet_tool",
                "arguments": test_case
            })
            print(f"   Test {i}: {result}")
            if result.get("success"):
                print(f"   ✅ GreetTool test {i} works")
            else:
                print(f"   ❌ GreetTool test {i} failed")
        except Exception as e:
            print(f"   ❌ GreetTool test {i} error: {e}")
    
    # Test MathTool
    print("\n3. Testing MathTool:")
    math_tests = [
        {"operation": "add", "a": 10, "b": 5},
        {"operation": "subtract", "a": 10, "b": 3},
        {"operation": "multiply", "a": 4, "b": 6},
        {"operation": "divide", "a": 15, "b": 3},
        {"operation": "divide", "a": 10, "b": 0}  # Error case
    ]
    
    for i, test_case in enumerate(math_tests, 1):
        try:
            result = tu.run({
                "name": "math_tool",
                "arguments": test_case
            })
            print(f"   Test {i}: {result}")
            if result.get("success") or "error" in result:
                print(f"   ✅ MathTool test {i} works")
            else:
                print(f"   ❌ MathTool test {i} failed")
        except Exception as e:
            print(f"   ❌ MathTool test {i} error: {e}")

def test_direct_access(tu):
    """Test direct tool access via tu.tools attribute."""
    
    print("\n🔧 Testing Direct Access (tu.tools)")
    print("=" * 40)
    
    try:
        # Test direct access
        result = tu.tools.hello_tool()
        print(f"Direct hello_tool(): {result}")
        
        result = tu.tools.greet_tool(name="Direct Access")
        print(f"Direct greet_tool(): {result}")
        
        result = tu.tools.math_tool(operation="add", a=100, b=200)
        print(f"Direct math_tool(): {result}")
        
        print("✅ Direct access works")
        
    except Exception as e:
        print(f"❌ Direct access failed: {e}")

def test_batch_processing(tu):
    """Test batch processing with multiple tools."""
    
    print("\n🔄 Testing Batch Processing")
    print("=" * 30)
    
    try:
        # Create batch requests
        batch_requests = [
            {"name": "hello_tool", "arguments": {}},
            {"name": "greet_tool", "arguments": {"name": "Batch User"}},
            {"name": "math_tool", "arguments": {"operation": "add", "a": 1, "b": 2}}
        ]
        
        print(f"Processing {len(batch_requests)} requests...")
        
        # Execute batch
        results = tu.run(batch_requests)
        
        print("Batch results:")
        for i, result in enumerate(results):
            print(f"  {i+1}: {result}")
        
        print("✅ Batch processing completed")
        
    except Exception as e:
        print(f"❌ Batch processing failed: {e}")

# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """Main function to demonstrate basic local tools."""
    
    print("🚀 Basic Local Tools Example")
    print("=" * 40)
    
    try:
        # Initialize ToolUniverse
        print("\n📦 Initializing ToolUniverse...")
        tu = ToolUniverse()
        
        # Load tools (this will automatically discover our registered tools)
        print("🔄 Loading tools...")
        tu.load_tools()
        
        print(f"✅ Loaded {len(tu.all_tools)} tools")
        
        # Check if our tools are available
        expected_tools = ["hello_tool", "greet_tool", "math_tool"]
        available_tools = list(tu.all_tool_dict.keys())
        
        print(f"\n📋 Available tools: {available_tools}")
        
        for tool_name in expected_tools:
            if tool_name in available_tools:
                print(f"✅ {tool_name} is available")
            else:
                print(f"❌ {tool_name} not found")
        
        # Run tests
        test_basic_tools(tu)
        test_direct_access(tu)
        test_batch_processing(tu)
        
        print("\n🎉 Basic local tools example completed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up global ToolUniverse
        if 'tu' in locals():
            tu.close()

if __name__ == "__main__":
    main()
