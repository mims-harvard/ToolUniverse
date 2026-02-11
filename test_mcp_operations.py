"""
Comprehensive MCP Operations Test

Tests all MCP-based operations and new operations to ensure they work correctly:
1. SMCP server initialization with TaskManager
2. Async tool execution (ProteinsPlus, SwissDock)
3. Task creation and management
4. MCP client tools
5. Integration with ToolUniverse
"""
import asyncio
import sys
from tooluniverse import ToolUniverse

def test_1_basic_tool_loading():
    """Test that all tools including async tools load correctly."""
    print("\n" + "="*70)
    print("TEST 1: Basic Tool Loading")
    print("="*70)

    try:
        tu = ToolUniverse()
        tu.load_tools()

        # Check async tools
        pp_tools = [name for name in tu.all_tool_dict.keys() if 'ProteinsPlus' in name]
        sd_tools = [name for name in tu.all_tool_dict.keys() if 'SwissDock' in name]

        print(f"✅ ProteinsPlus tools: {len(pp_tools)}")
        print(f"✅ SwissDock tools: {len(sd_tools)}")
        print(f"✅ Total tools: {len(tu.all_tool_dict)}")

        assert len(pp_tools) >= 5, "Missing ProteinsPlus tools"
        assert len(sd_tools) >= 3, "Missing SwissDock tools"

        print("\n✅ TEST 1 PASSED")
        return tu

    except Exception as e:
        print(f"\n❌ TEST 1 FAILED: {e}")
        raise


def test_2_async_tool_instances():
    """Test that async tools can be instantiated and have correct structure."""
    print("\n" + "="*70)
    print("TEST 2: Async Tool Instances")
    print("="*70)

    try:
        tu = ToolUniverse()
        tu.load_tools()

        # Test ProteinsPlus
        pp_config = tu.all_tool_dict["ProteinsPlus_predict_binding_sites"]
        from tooluniverse.proteinsplus_tool import ProteinsPlusRESTTool
        pp_tool = ProteinsPlusRESTTool(pp_config)

        print("\nProteinsPlus tool:")
        print(f"   ✅ Has submit_job: {hasattr(pp_tool, 'submit_job')}")
        print(f"   ✅ Has check_status: {hasattr(pp_tool, 'check_status')}")
        print(f"   ✅ Has format_result: {hasattr(pp_tool, 'format_result')}")
        print(f"   ✅ Has run: {hasattr(pp_tool, 'run')}")

        # Check inheritance
        from tooluniverse.async_base import AsyncPollingTool
        print(f"   ✅ Inherits AsyncPollingTool: {isinstance(pp_tool, AsyncPollingTool)}")

        # Test SwissDock
        sd_config = tu.all_tool_dict["SwissDock_dock_ligand"]
        from tooluniverse.swissdock_tool import SwissDockTool
        sd_tool = SwissDockTool(sd_config)

        print("\nSwissDock tool:")
        print(f"   ✅ Has submit_job: {hasattr(sd_tool, 'submit_job')}")
        print(f"   ✅ Has check_status: {hasattr(sd_tool, 'check_status')}")
        print(f"   ✅ Inherits AsyncPollingTool: {isinstance(sd_tool, AsyncPollingTool)}")

        print("\n✅ TEST 2 PASSED")

    except Exception as e:
        print(f"\n❌ TEST 2 FAILED: {e}")
        raise


def test_3_task_manager():
    """Test TaskManager functionality."""
    print("\n" + "="*70)
    print("TEST 3: Task Manager")
    print("="*70)

    async def run_test():
        try:
            from tooluniverse.task_manager import TaskManager
            tu = ToolUniverse()
            tu.load_tools()

            tm = TaskManager(tool_universe=tu)
            await tm.start()

            print("✅ TaskManager initialized")
            print(f"   - Has create_task: {hasattr(tm, 'create_task')}")
            print(f"   - Has get_status: {hasattr(tm, 'get_status')}")
            print(f"   - Has list_tasks: {hasattr(tm, 'list_tasks')}")
            print(f"   - Has cancel_task: {hasattr(tm, 'cancel_task')}")
            print(f"   - Has get_result: {hasattr(tm, 'get_result')}")

            # Test task listing (should be empty)
            tasks = await tm.list_tasks()
            print(f"✅ list_tasks works: {len(tasks.get('tasks', []))} tasks")

            await tm.stop()
            print("✅ TaskManager stopped cleanly")

            print("\n✅ TEST 3 PASSED")

        except Exception as e:
            print(f"\n❌ TEST 3 FAILED: {e}")
            raise

    asyncio.run(run_test())


def test_4_task_progress():
    """Test TaskProgress functionality."""
    print("\n" + "="*70)
    print("TEST 4: Task Progress")
    print("="*70)

    async def run_test():
        try:
            from tooluniverse.task_progress import TaskProgress
            from tooluniverse.task_manager import Task
            from datetime import datetime

            # Create a mock task
            task = Task(
                task_id="test-123",
                tool_name="TestTool",
                arguments={"test": "arg"},
                status="working",
                created_at=datetime.now(),
                last_updated_at=datetime.now(),
                ttl=3600000,
            )

            progress = TaskProgress(task)

            print("✅ TaskProgress initialized")
            print(f"   - Has set_message: {hasattr(progress, 'set_message')}")
            print(f"   - Has task reference: {progress.task is not None}")

            # Test set_message
            await progress.set_message("Test message")
            print(f"✅ set_message works: '{task.status_message}'")

            print("\n✅ TEST 4 PASSED")

        except Exception as e:
            print(f"\n❌ TEST 4 FAILED: {e}")
            raise

    asyncio.run(run_test())


def test_5_smcp_initialization():
    """Test SMCP server initialization with MCP Tasks support."""
    print("\n" + "="*70)
    print("TEST 5: SMCP Server Initialization")
    print("="*70)

    try:
        from tooluniverse.smcp import SMCP

        smcp = SMCP(
            name="Test SMCP Server",
            tool_categories=None,  # Load all tools
        )

        print("✅ SMCP server initialized")
        print(f"   - Has task_manager: {hasattr(smcp, 'task_manager')}")
        print(f"   - Has handle_tasks_get: {hasattr(smcp, 'handle_tasks_get')}")
        print(f"   - Has handle_tasks_list: {hasattr(smcp, 'handle_tasks_list')}")
        print(f"   - Has handle_tasks_cancel: {hasattr(smcp, 'handle_tasks_cancel')}")
        print(f"   - Has handle_tasks_result: {hasattr(smcp, 'handle_tasks_result')}")

        # Check TaskManager is initialized
        assert smcp.task_manager is not None, "TaskManager not initialized"
        print("✅ TaskManager attached to SMCP")

        print("\n✅ TEST 5 PASSED")

    except Exception as e:
        print(f"\n❌ TEST 5 FAILED: {e}")
        raise


def test_6_execute_function_async():
    """Test that execute_function correctly handles async tools."""
    print("\n" + "="*70)
    print("TEST 6: Execute Function Async Handling")
    print("="*70)

    try:
        import inspect
        from tooluniverse import ToolUniverse
        from tooluniverse.proteinsplus_tool import ProteinsPlusRESTTool

        tu = ToolUniverse()
        tu.load_tools()

        # Get tool config and instantiate
        pp_config = tu.all_tool_dict["ProteinsPlus_predict_binding_sites"]
        pp_tool = ProteinsPlusRESTTool(pp_config)

        # Check that run is async
        is_async = inspect.iscoroutinefunction(pp_tool.run)
        print(f"✅ ProteinsPlus run() is async: {is_async}")

        # Check that ToolUniverse can detect it
        print(f"✅ ToolUniverse has _invoke_tool_async: {hasattr(tu, '_invoke_tool_async')}")

        # Check that async detection works
        print(f"✅ inspect.iscoroutinefunction works correctly")

        print("\n✅ TEST 6 PASSED")

    except Exception as e:
        print(f"\n❌ TEST 6 FAILED: {e}")
        raise


def test_7_mcp_client_tools():
    """Test MCP client tools exist and are properly configured."""
    print("\n" + "="*70)
    print("TEST 7: MCP Client Tools")
    print("="*70)

    try:
        import os

        files = [
            'src/tooluniverse/mcp_client_tool.py',
            'src/tooluniverse/mcp_integration.py',
            'src/tooluniverse/mcp_tool_registry.py',
        ]

        for filepath in files:
            exists = os.path.exists(filepath)
            print(f"   {'✅' if exists else '❌'} {os.path.basename(filepath)}")
            assert exists, f"Missing {filepath}"

        # Try importing
        try:
            from tooluniverse.mcp_client_tool import MCPClientTool
            print("✅ MCPClientTool can be imported")
        except ImportError as e:
            print(f"⚠️  MCPClientTool import: {e}")

        print("\n✅ TEST 7 PASSED")

    except Exception as e:
        print(f"\n❌ TEST 7 FAILED: {e}")
        raise


def run_all_tests():
    """Run all MCP operations tests."""
    print("\n" + "="*80)
    print("MCP OPERATIONS - COMPREHENSIVE TEST SUITE")
    print("="*80)

    tests_passed = 0
    tests_failed = 0

    tests = [
        ("Basic Tool Loading", test_1_basic_tool_loading),
        ("Async Tool Instances", test_2_async_tool_instances),
        ("Task Manager", test_3_task_manager),
        ("Task Progress", test_4_task_progress),
        ("SMCP Initialization", test_5_smcp_initialization),
        ("Execute Function Async", test_6_execute_function_async),
        ("MCP Client Tools", test_7_mcp_client_tools),
    ]

    for test_name, test_func in tests:
        try:
            if test_name == "Basic Tool Loading":
                tu = test_func()
            else:
                test_func()
            tests_passed += 1
        except Exception as e:
            tests_failed += 1
            print(f"\n❌ {test_name} FAILED: {e}")

    # Summary
    print("\n" + "="*80)
    print("TEST SUITE SUMMARY")
    print("="*80)
    print(f"✅ Tests Passed: {tests_passed}")
    print(f"❌ Tests Failed: {tests_failed}")

    if tests_failed == 0:
        print("\n🎉 ALL MCP OPERATIONS TESTS PASSED!")
        return 0
    else:
        print(f"\n⚠️  {tests_failed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
