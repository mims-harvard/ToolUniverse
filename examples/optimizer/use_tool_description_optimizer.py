#!/usr/bin/env python3
"""
Minimal example: load optimizer tools and run ToolDescriptionOptimizer

How to run:
  python examples/optimizer/use_tool_description_optimizer.py
"""
from pathlib import Path

import sys
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    from src.tooluniverse.execute_function import ToolUniverse

    # Use default config which includes optimizer_tools.json
    tu = ToolUniverse(log_level="INFO")

    # Pick a tool with a simple description that can be improved
    # get_webpage_title has brief description:
    # "Fetch a webpage and return the content of its <title> tag."
    tool_name = "get_webpage_title"
    # Ensure tools are loaded
    tu.load_tools()
    try:
        tool_config = tu.tool_specification(tool_name)
        if tool_config is None:
            tool_count = len(tu.all_tool_dict)
            print(f"Tool '{tool_name}' not found.")
            print(f"Available tools: {tool_count}")
            return
    except Exception as e:
        print(f"Failed to fetch tool description for {tool_name}: {e}")
        return

    # Call the ComposeTool: ToolDescriptionOptimizer on a real tool
    result = tu.run_one_function(
        {
            "name": "ToolDescriptionOptimizer",
            "arguments": {
                "tool_config": tool_config,
                "max_iterations": 1,
                "satisfaction_threshold": 8,
                # Optionally save a report next to this example
                "save_to_file": True,
                "output_file": str(
                    (
                        Path(__file__).parent
                        / f"{tool_name}_optimized_description.txt"
                    ).resolve()
                ),
            },
        }
    )

    print("=== Optimizer Result (keys) ===")
    if isinstance(result, dict):
        print(list(result.keys()))
        # Print error details if present
        if "error" in result:
            print("ERROR:", result.get("error"))
            print("ERROR DETAILS:", result.get("error_details"))
            return
        # Show a brief preview
        preview = result.get("optimized_description", "<none>")[:160]
        print("optimized_description:", preview)
        print("final_quality_score:", result.get("final_quality_score"))
        print("saved_to:", result.get("saved_to"))
    else:
        print(result)


if __name__ == "__main__":
    main()
