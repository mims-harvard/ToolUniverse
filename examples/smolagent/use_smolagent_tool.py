from tooluniverse import ToolUniverse


def main():
    tu = ToolUniverse()
    tu.load_tools()

    # Run example agent defined in src/tooluniverse/data/smolagent_tools.json
    result = tu.run_one_function(
        {
            "name": "open_deep_research_agent",
            "arguments": {
                "task": (
                    "How many seconds for a leopard at full speed to run "
                    "through Pont des Arts?"
                )
            },
        }
    )
    print(result)


if __name__ == "__main__":
    main()

