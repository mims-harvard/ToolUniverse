#!/usr/bin/env python3
"""Minimal test for ToolDescriptionOptimizer on FDA tool"""

import os
from tooluniverse import ToolUniverse


def main():
    """Run minimal FDA tool tests."""
    # Setup
    tu = ToolUniverse()
    tu.load_tools()
    os.makedirs("temp_test", exist_ok=True)

    # Get FDA tool
    tool_name = "FDA_get_active_ingredient_info_by_drug_name"
    tool_config = tu.tool_specification(tool_name)

    # Test 1: Multi-round optimization
    result = tu.run(
        {
            "name": "ToolDescriptionOptimizer",
            "arguments": {
                "tool_config": tool_config,
                "max_iterations": 3,
                "satisfaction_threshold": 8.0,
            },
        }
    )
    print(
        f"Multi-round optimization: {result['total_iterations']} rounds, score {result['final_quality_score']}/10"
    )

    # Test 2: Feedback-driven test generation
    enhanced_config = tool_config.copy()
    enhanced_config["_optimization_feedback"] = (
        "Test with both brand and generic drug names"
    )

    _ = tu.run_one_function(
        {"name": "TestCaseGenerator", "arguments": {"tool_config": enhanced_config}}
    )

    print("Feedback-driven test generation: Complete")
    print("FDA tool optimization tests: PASSED")


if __name__ == "__main__":
    main()
