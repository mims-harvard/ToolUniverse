#!/usr/bin/env python3
"""
Test script to verify ToolUniverse API for local tools
"""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

def test_imports():
    """Test that we can import the required modules."""
    
    print("🧪 Testing imports...")
    
    try:
        # Test basic imports
        from tooluniverse.tool_registry import register_tool
        print("✅ register_tool import successful")
    except Exception as e:
        print(f"❌ register_tool import failed: {e}")
        return False
    
    try:
        from tooluniverse.base_tool import BaseTool
        print("✅ BaseTool import successful")
    except Exception as e:
        print(f"❌ BaseTool import failed: {e}")
        return False
    
    try:
        from tooluniverse import ToolUniverse
        print("✅ ToolUniverse import successful")
    except Exception as e:
        print(f"❌ ToolUniverse import failed: {e}")
        return False
    
    return True

def test_basic_tool_creation():
    """Test creating a basic tool."""
    
    print("\n🧪 Testing basic tool creation...")
    
    try:
        from tooluniverse.tool_registry import register_tool
        from tooluniverse.base_tool import BaseTool
        
        @register_tool('TestTool', config={
            "name": "test_tool",
            "description": "A simple test tool"
        })
        class TestTool(BaseTool):
            def run(self, arguments=None, **kwargs):
                return {"message": "Test successful", "success": True}
        
        print("✅ Basic tool creation successful")
        return True
        
    except Exception as e:
        print(f"❌ Basic tool creation failed: {e}")
        return False

def test_tooluniverse_initialization():
    """Test ToolUniverse initialization."""
    
    print("\n🧪 Testing ToolUniverse initialization...")
    
    try:
        from tooluniverse import ToolUniverse
        
        tu = ToolUniverse()
        try:
            print("✅ ToolUniverse initialization successful")
            
            # Test load_tools method
            tu.load_tools()
            print(f"✅ load_tools successful - loaded {len(tu.all_tools)} tools")
            
            # Test run method
            if hasattr(tu, 'run'):
                print("✅ run method exists")
            else:
                print("❌ run method not found")
                return False
            
            # Test tools attribute
            if hasattr(tu, 'tools'):
                print("✅ tools attribute exists")
            else:
                print("❌ tools attribute not found")
                return False
            
            return True
        finally:
            tu.close()
        
    except Exception as e:
        print(f"❌ ToolUniverse initialization failed: {e}")
        return False

def main():
    """Run all tests."""
    
    print("🚀 ToolUniverse Local Tools API Test")
    print("=" * 40)
    
    tests = [
        ("Imports", test_imports),
        ("Basic Tool Creation", test_basic_tool_creation),
        ("ToolUniverse Initialization", test_tooluniverse_initialization)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
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
        print("🎉 All tests passed! Local tools API is working correctly.")
    else:
        print("❌ Some tests failed. Please check the errors above.")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
