#!/usr/bin/env python3
"""
Test script for [DOMAIN] tools
Following TDD: test ALL tools BEFORE creating skill documentation

INSTRUCTIONS:
1. Replace [DOMAIN] with your domain name
2. Replace [DATABASE] with actual database names
3. Replace TOOL_NAME with actual tool names from ToolUniverse
4. Add test functions for each database
5. Run this script BEFORE implementing python_implementation.py
6. Document all discoveries in parameter corrections table
7. Only proceed to implementation after 100% tool verification
"""

from tooluniverse import ToolUniverse


def _load_tools() -> ToolUniverse:
    """Load ToolUniverse once and return the instance."""
    tu = ToolUniverse()
    tu.load_tools()
    return tu


def test_database1_tools(tu: ToolUniverse):
    """Test [Database 1] tools"""
    print("\n" + "="*80)
    print("TESTING [DATABASE 1] TOOLS")
    print("="*80)

    # Test 1: [Tool purpose]
    print("\n1. Testing TOOL_NAME_1...")
    result = tu.tools.TOOL_NAME_1(
        param1="test_value",
        param2="test_value2"
    )

    # Check response format and document
    if isinstance(result, dict) and result.get('status') == 'success':
        print(f"Status: {result.get('status')}")
        data = result.get('data', [])
        print(f"Found {len(data)} results")
        if data:
            print(f"First result: {data[0]}")
            print(f"Data structure: {data[0].keys() if isinstance(data[0], dict) else type(data[0])}")
    elif isinstance(result, list):
        print(f"Status: success (direct list response)")
        print(f"Found {len(result)} results")
        if result:
            print(f"First result: {result[0]}")
    elif isinstance(result, dict) and 'field_name' in result:
        print(f"Status: success (direct dict response)")
        print(f"Keys: {result.keys()}")
    else:
        print(f"ERROR: Unexpected response format: {type(result)}")
        print(f"Response: {result}")

    # Test 2: [Another tool]
    print("\n2. Testing TOOL_NAME_2...")
    result = tu.tools.TOOL_NAME_2(param="test_value")
    # Similar format checks

    return True

def test_database2_tools(tu: ToolUniverse):
    """Test [Database 2] tools"""
    print("\n" + "="*80)
    print("TESTING [DATABASE 2] TOOLS")
    print("="*80)

    # Test tools from Database 2
    print("\n1. Testing TOOL_NAME_3...")
    result = tu.tools.TOOL_NAME_3(param="test_value")

    # Check if SOAP tool (requires operation parameter)
    if isinstance(result, dict) and 'error' in result:
        error_msg = str(result.get('error', ''))
        if "'operation' is a required property" in error_msg:
            print("⚠️  SOAP TOOL DETECTED - Requires 'operation' parameter")
            print("Retrying with operation parameter...")

            result = tu.tools.TOOL_NAME_3(
                operation="method_name",  # Add operation
                param="test_value"
            )
            print(f"Status with operation: {result.get('status')}")

    return True

def test_database3_tools(tu: ToolUniverse):
    """Test [Database 3] tools"""
    print("\n" + "="*80)
    print("TESTING [DATABASE 3] TOOLS")
    print("="*80)

    # Test tools
    print("\n1. Testing TOOL_NAME_4...")
    try:
        result = tu.tools.TOOL_NAME_4(param="test_value")
        print(f"Status: {result.get('status') if isinstance(result, dict) else 'success'}")
    except Exception as e:
        print(f"ERROR: {e}")
        print("⚠️  Tool may not work - document for fallback strategy")

    return True

def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("[DOMAIN] TOOLS TEST SUITE")
    print("Following TDD: Test tools FIRST before creating skill documentation")
    print("="*80)

    tu = _load_tools()

    tests = [
        ("Database 1", test_database1_tools),
        ("Database 2", test_database2_tools),
        ("Database 3", test_database3_tools),
    ]

    results = {}

    for name, test_func in tests:
        try:
            success = test_func(tu)
            results[name] = "PASS" if success else "FAIL"
        except Exception as e:
            print(f"\nEXCEPTION in {name}: {e}")
            results[name] = f"EXCEPTION: {str(e)[:100]}"

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    for name, result in results.items():
        print(f"{name:25} {result}")

    # Document discoveries
    print("\n" + "="*80)
    print("DISCOVERIES - DOCUMENT THESE IN SKILL.md")
    print("="*80)

    print("\n## Parameter Corrections Needed:")
    print("| Tool | Common Mistake | Correct Parameter | Evidence |")
    print("|------|----------------|-------------------|----------|")
    print("| TOOL_NAME_1 | assumed_param | actual_param | Test output |")
    print("| [Add more as discovered] | | | |")

    print("\n## Response Format Notes:")
    print("- **TOOL_NAME_1**: [Standard / Direct list / Direct dict] - [Description]")
    print("- **TOOL_NAME_2**: [Format] - [Description]")

    print("\n## SOAP Tools Detected:")
    print("- **TOOL_NAME_X**: Requires operation='method_name'")

    print("\n## Failing Tools:")
    print("- **TOOL_NAME_Y**: [Error description] - Need fallback strategy")

    print("\n" + "="*80)
    print("NEXT STEPS:")
    print("1. Document all discoveries above in SKILL.md Tool Parameter Reference")
    print("2. Add SOAP tool warnings to QUICK_START.md")
    print("3. Design fallback strategies for failing tools")
    print("4. Create python_implementation.py using VERIFIED tools only")
    print("5. Create test_skill.py for end-to-end testing")
    print("6. ONLY THEN write SKILL.md and QUICK_START.md documentation")
    print("="*80)

    print("\n✅ Tool testing completed. Ready to proceed to implementation.")

if __name__ == "__main__":
    main()
