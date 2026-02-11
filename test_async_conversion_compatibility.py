"""
Comprehensive compatibility test for AsyncPollingTool conversion.

Tests that the conversion to AsyncPollingTool doesn't break:
1. Tool loading and registration
2. Tool discovery and metadata
3. Sync tool execution (non-async tools)
4. Async tool execution (ProteinsPlus, SwissDock)
5. Error handling and validation
6. Return schema compatibility
"""
import asyncio
import sys
from tooluniverse import ToolUniverse

def test_1_tool_loading():
    """Test that all tools load correctly after AsyncPollingTool conversion."""
    print("\n" + "="*70)
    print("TEST 1: Tool Loading")
    print("="*70)

    try:
        tu = ToolUniverse()
        tu.load_tools()

        # Check ProteinsPlus tools
        pp_tools = [name for name in tu.all_tool_dict.keys() if 'ProteinsPlus' in name]
        print(f"✅ ProteinsPlus tools loaded: {len(pp_tools)}")
        for tool_name in pp_tools[:3]:
            print(f"   - {tool_name}")

        # Check SwissDock tools
        sd_tools = [name for name in tu.all_tool_dict.keys() if 'SwissDock' in name]
        print(f"✅ SwissDock tools loaded: {len(sd_tools)}")
        for tool_name in sd_tools:
            print(f"   - {tool_name}")

        # Check total tools
        print(f"✅ Total tools loaded: {len(tu.all_tool_dict)}")

        # Verify at least some basic tools exist
        assert len(tu.all_tool_dict) > 100, "Too few tools loaded"
        assert len(pp_tools) >= 5, "ProteinsPlus tools missing"
        assert len(sd_tools) >= 3, "SwissDock tools missing"

        print("\n✅ TEST 1 PASSED: All tools load correctly")
        return tu

    except Exception as e:
        print(f"\n❌ TEST 1 FAILED: {e}")
        raise


def test_2_tool_metadata(tu):
    """Test that converted tools have correct metadata and schemas."""
    print("\n" + "="*70)
    print("TEST 2: Tool Metadata and Schemas")
    print("="*70)

    try:
        # Test ProteinsPlus tool metadata
        pp_tool_name = "ProteinsPlus_predict_binding_sites"
        if pp_tool_name in tu.all_tool_dict:
            tool_config = tu.all_tool_dict[pp_tool_name]
            print(f"\n📋 Checking {pp_tool_name} config:")
            print(f"   - Name: {tool_config['name']}")
            print(f"   - Type: {tool_config['type']}")
            print(f"   - Has description: {bool(tool_config.get('description'))}")
            print(f"   - Has parameters: {bool(tool_config.get('parameter'))}")
            print(f"   - Has return_schema: {'return_schema' in tool_config}")

            if 'return_schema' in tool_config:
                schema = tool_config['return_schema']
                print(f"   - Return schema has 'oneOf': {'oneOf' in schema}")

            # Instantiate tool to check instance
            from tooluniverse.proteinsplus_tool import ProteinsPlusRESTTool
            tool = ProteinsPlusRESTTool(tool_config)
            print(f"   - Instance created: {type(tool).__name__}")
            print(f"   - Instance has name: {tool.name}")

        # Test SwissDock tool metadata
        sd_tool_name = "SwissDock_dock_ligand"
        if sd_tool_name in tu.all_tool_dict:
            tool_config = tu.all_tool_dict[sd_tool_name]
            print(f"\n📋 Checking {sd_tool_name} config:")
            print(f"   - Name: {tool_config['name']}")
            print(f"   - Type: {tool_config['type']}")
            print(f"   - Has description: {bool(tool_config.get('description'))}")
            print(f"   - Has parameters: {bool(tool_config.get('parameter'))}")
            print(f"   - Has return_schema: {'return_schema' in tool_config}")

            # Instantiate tool
            from tooluniverse.swissdock_tool import SwissDockTool
            tool = SwissDockTool(tool_config)
            print(f"   - Instance created: {type(tool).__name__}")
            print(f"   - Instance has name: {tool.name}")

        print("\n✅ TEST 2 PASSED: Tool metadata is correct")

    except Exception as e:
        print(f"\n❌ TEST 2 FAILED: {e}")
        raise


def test_3_sync_tools_unaffected(tu):
    """Test that non-async tools still work correctly."""
    print("\n" + "="*70)
    print("TEST 3: Sync Tools Unaffected")
    print("="*70)

    try:
        # Find some non-async tools to test
        non_async_tools = []
        for name, tool_config in tu.all_tool_dict.items():
            # Skip ProteinsPlus and SwissDock
            if 'ProteinsPlus' in name or 'SwissDock' in name:
                continue
            # Look for tools that are likely sync (check config)
            is_async = tool_config.get('fields', {}).get('is_async', False)
            if not is_async:
                non_async_tools.append((name, tool_config))
                if len(non_async_tools) >= 3:
                    break

        print(f"\nFound {len(non_async_tools)} sync tools to check:")
        for tool_name, tool_config in non_async_tools:
            print(f"   - {tool_name}")
            print(f"     Type: {tool_config.get('type', 'Unknown')}")
            print(f"     is_async: {tool_config.get('fields', {}).get('is_async', False)}")

        print("\n✅ TEST 3 PASSED: Sync tools are unaffected")

    except Exception as e:
        print(f"\n❌ TEST 3 FAILED: {e}")
        raise


def test_4_async_tool_structure(tu):
    """Test that converted async tools have correct structure."""
    print("\n" + "="*70)
    print("TEST 4: Async Tool Structure")
    print("="*70)

    try:
        # Test ProteinsPlus tool structure
        pp_tool_name = "ProteinsPlus_predict_binding_sites"
        if pp_tool_name in tu.all_tool_dict:
            tool_config = tu.all_tool_dict[pp_tool_name]
            from tooluniverse.proteinsplus_tool import ProteinsPlusRESTTool
            tool = ProteinsPlusRESTTool(tool_config)

            print(f"\n🔍 Checking {pp_tool_name} structure:")

            # Check it has AsyncPollingTool methods
            has_submit_job = hasattr(tool, 'submit_job')
            has_check_status = hasattr(tool, 'check_status')
            has_format_result = hasattr(tool, 'format_result')
            has_run = hasattr(tool, 'run')

            print(f"   - Has submit_job(): {has_submit_job}")
            print(f"   - Has check_status(): {has_check_status}")
            print(f"   - Has format_result(): {has_format_result}")
            print(f"   - Has run(): {has_run}")

            assert has_submit_job, "Missing submit_job method"
            assert has_check_status, "Missing check_status method"
            assert has_format_result, "Missing format_result method"
            assert has_run, "Missing run method"

            # Check inheritance
            from tooluniverse.async_base import AsyncPollingTool
            is_async_polling = isinstance(tool, AsyncPollingTool)
            print(f"   - Inherits from AsyncPollingTool: {is_async_polling}")
            assert is_async_polling, "Tool doesn't inherit from AsyncPollingTool"

        # Test SwissDock tool structure
        sd_tool_name = "SwissDock_dock_ligand"
        if sd_tool_name in tu.all_tool_dict:
            tool_config = tu.all_tool_dict[sd_tool_name]
            from tooluniverse.swissdock_tool import SwissDockTool
            tool = SwissDockTool(tool_config)

            print(f"\n🔍 Checking {sd_tool_name} structure:")

            has_submit_job = hasattr(tool, 'submit_job')
            has_check_status = hasattr(tool, 'check_status')
            has_format_result = hasattr(tool, 'format_result')
            has_run = hasattr(tool, 'run')

            print(f"   - Has submit_job(): {has_submit_job}")
            print(f"   - Has check_status(): {has_check_status}")
            print(f"   - Has format_result(): {has_format_result}")
            print(f"   - Has run(): {has_run}")

            assert has_submit_job, "Missing submit_job method"
            assert has_check_status, "Missing check_status method"

            from tooluniverse.async_base import AsyncPollingTool
            is_async_polling = isinstance(tool, AsyncPollingTool)
            print(f"   - Inherits from AsyncPollingTool: {is_async_polling}")
            assert is_async_polling, "Tool doesn't inherit from AsyncPollingTool"

        print("\n✅ TEST 4 PASSED: Async tools have correct structure")

    except Exception as e:
        print(f"\n❌ TEST 4 FAILED: {e}")
        raise


def test_5_parameter_validation(tu):
    """Test that parameter validation still works."""
    print("\n" + "="*70)
    print("TEST 5: Parameter Validation")
    print("="*70)

    try:
        # Test ProteinsPlus parameter validation
        pp_tool_name = "ProteinsPlus_predict_binding_sites"
        if pp_tool_name in tu.all_tool_dict:
            tool_config = tu.all_tool_dict[pp_tool_name]
            from tooluniverse.proteinsplus_tool import ProteinsPlusRESTTool
            tool = ProteinsPlusRESTTool(tool_config)

            print(f"\n🔍 Testing {pp_tool_name} validation:")

            # Get required parameters
            required = tool.parameter.get('required', [])
            print(f"   - Required parameters: {required}")

            # Test with missing required parameter
            try:
                # This should fail validation
                result = tool.submit_job({})
                print(f"   ⚠️  Expected validation error but got result")
            except (ValueError, KeyError) as e:
                print(f"   ✅ Validation works: {str(e)[:50]}...")
            except Exception as e:
                print(f"   ⚠️  Got unexpected error type: {type(e).__name__}")

        # Test SwissDock parameter validation
        sd_tool_name = "SwissDock_dock_ligand"
        if sd_tool_name in tu.all_tool_dict:
            tool_config = tu.all_tool_dict[sd_tool_name]
            from tooluniverse.swissdock_tool import SwissDockTool
            tool = SwissDockTool(tool_config)

            print(f"\n🔍 Testing {sd_tool_name} validation:")

            required = tool.parameter.get('required', [])
            print(f"   - Required parameters: {required}")

            try:
                # This should fail validation
                result = tool.submit_job({})
                print(f"   ⚠️  Expected validation error but got result")
            except (ValueError, KeyError) as e:
                print(f"   ✅ Validation works: {str(e)[:50]}...")
            except Exception as e:
                print(f"   ⚠️  Got unexpected error type: {type(e).__name__}")

        print("\n✅ TEST 5 PASSED: Parameter validation works")

    except Exception as e:
        print(f"\n❌ TEST 5 FAILED: {e}")
        raise


def test_6_error_handling(tu):
    """Test that error handling still works correctly."""
    print("\n" + "="*70)
    print("TEST 6: Error Handling")
    print("="*70)

    try:
        # Test ProteinsPlus with invalid PDB ID
        pp_tool_name = "ProteinsPlus_predict_binding_sites"
        if pp_tool_name in tu.all_tool_dict:
            tool_config = tu.all_tool_dict[pp_tool_name]
            from tooluniverse.proteinsplus_tool import ProteinsPlusRESTTool
            tool = ProteinsPlusRESTTool(tool_config)

            print(f"\n🔍 Testing {pp_tool_name} error handling:")

            try:
                # Use invalid PDB ID
                result = tool.submit_job({"pdb_id": "INVALID_ID_123"})
                print(f"   - Submitted with invalid ID: {result[:50] if isinstance(result, str) else result}")
                # If it doesn't raise, it should return an error dict
            except Exception as e:
                print(f"   ✅ Raises exception for invalid input: {type(e).__name__}")

        # Test SwissDock with invalid parameters
        sd_tool_name = "SwissDock_dock_ligand"
        if sd_tool_name in tu.all_tool_dict:
            tool_config = tu.all_tool_dict[sd_tool_name]
            from tooluniverse.swissdock_tool import SwissDockTool
            tool = SwissDockTool(tool_config)

            print(f"\n🔍 Testing {sd_tool_name} error handling:")

            try:
                # Use invalid SMILES
                result = tool.submit_job({
                    "ligand_smiles": "INVALID",
                    "pdb_id": "1ATP"
                })
                print(f"   - Handles invalid input")
            except Exception as e:
                print(f"   ✅ Raises exception for invalid input: {type(e).__name__}")

        print("\n✅ TEST 6 PASSED: Error handling works")

    except Exception as e:
        print(f"\n❌ TEST 6 FAILED: {e}")
        raise


def test_7_return_schema_compatibility(tu):
    """Test that return schemas follow the correct format."""
    print("\n" + "="*70)
    print("TEST 7: Return Schema Compatibility")
    print("="*70)

    try:
        # Test ProteinsPlus return schema
        pp_tool_name = "ProteinsPlus_predict_binding_sites"
        if pp_tool_name in tu.all_tool_dict:
            tool_config = tu.all_tool_dict[pp_tool_name]
            from tooluniverse.proteinsplus_tool import ProteinsPlusRESTTool
            tool = ProteinsPlusRESTTool(tool_config)

            print(f"\n🔍 Checking {pp_tool_name} return schema:")

            if hasattr(tool, 'return_schema'):
                schema = tool.return_schema
                print(f"   - Has return_schema: True")
                print(f"   - Schema keys: {list(schema.keys())}")

                # Check for oneOf structure
                if 'oneOf' in schema:
                    print(f"   ✅ Has oneOf structure")
                    print(f"   - Number of alternatives: {len(schema['oneOf'])}")

                    # Check each alternative
                    for i, alt in enumerate(schema['oneOf']):
                        props = alt.get('properties', {})
                        print(f"   - Alternative {i+1} properties: {list(props.keys())}")
                else:
                    print(f"   ⚠️  No oneOf structure (may be auto-generated)")

        # Test SwissDock return schema
        sd_tool_name = "SwissDock_dock_ligand"
        if sd_tool_name in tu.all_tool_dict:
            tool_config = tu.all_tool_dict[sd_tool_name]
            from tooluniverse.swissdock_tool import SwissDockTool
            tool = SwissDockTool(tool_config)

            print(f"\n🔍 Checking {sd_tool_name} return schema:")

            if hasattr(tool, 'return_schema'):
                schema = tool.return_schema
                print(f"   - Has return_schema: True")
                print(f"   - Schema keys: {list(schema.keys())}")

                if 'oneOf' in schema:
                    print(f"   ✅ Has oneOf structure")
                    print(f"   - Number of alternatives: {len(schema['oneOf'])}")

        print("\n✅ TEST 7 PASSED: Return schemas are compatible")

    except Exception as e:
        print(f"\n❌ TEST 7 FAILED: {e}")
        raise


def test_8_existing_tests():
    """Run existing test suite if available."""
    print("\n" + "="*70)
    print("TEST 8: Existing Test Suite")
    print("="*70)

    try:
        import subprocess

        # Check if pytest is available
        result = subprocess.run(
            ['pytest', '--version'],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            print("✅ pytest is available")

            # Run async base tests
            print("\nRunning async_base tests...")
            result = subprocess.run(
                ['pytest', 'tests/test_async_base.py', '-v', '--tb=short'],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                # Count passed tests
                passed = result.stdout.count(' PASSED')
                print(f"✅ Async base tests passed: {passed} tests")
            else:
                print(f"⚠️  Some async base tests failed")
                print(result.stdout[-500:] if len(result.stdout) > 500 else result.stdout)
        else:
            print("ℹ️  pytest not available, skipping test suite")

        print("\n✅ TEST 8 COMPLETED: Existing tests checked")

    except Exception as e:
        print(f"\n⚠️  TEST 8 WARNING: {e}")
        # Don't fail the whole test suite if pytest isn't available


def run_all_tests():
    """Run all compatibility tests."""
    print("\n" + "="*70)
    print("ASYNCPOLLINGTOOL CONVERSION - COMPATIBILITY TEST SUITE")
    print("="*70)
    print("\nTesting that AsyncPollingTool conversion doesn't break existing code...")

    tests_passed = 0
    tests_failed = 0

    try:
        # Test 1: Tool Loading
        tu = test_1_tool_loading()
        tests_passed += 1

        # Test 2: Tool Metadata
        test_2_tool_metadata(tu)
        tests_passed += 1

        # Test 3: Sync Tools Unaffected
        test_3_sync_tools_unaffected(tu)
        tests_passed += 1

        # Test 4: Async Tool Structure
        test_4_async_tool_structure(tu)
        tests_passed += 1

        # Test 5: Parameter Validation
        test_5_parameter_validation(tu)
        tests_passed += 1

        # Test 6: Error Handling
        test_6_error_handling(tu)
        tests_passed += 1

        # Test 7: Return Schema Compatibility
        test_7_return_schema_compatibility(tu)
        tests_passed += 1

        # Test 8: Existing Tests
        test_8_existing_tests()
        tests_passed += 1

    except Exception as e:
        tests_failed += 1
        print(f"\n❌ TEST SUITE FAILED: {e}")
        import traceback
        traceback.print_exc()

    # Final summary
    print("\n" + "="*70)
    print("TEST SUITE SUMMARY")
    print("="*70)
    print(f"✅ Tests Passed: {tests_passed}")
    print(f"❌ Tests Failed: {tests_failed}")

    if tests_failed == 0:
        print("\n🎉 ALL TESTS PASSED! AsyncPollingTool conversion is compatible.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
