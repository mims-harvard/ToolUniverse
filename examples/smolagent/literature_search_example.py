"""
Advanced Literature Search Agent Example

This example demonstrates how to use the advanced_literature_search_agent,
a sophisticated multi-agent system that performs comprehensive literature
searches across multiple academic databases with intelligent deduplication,
relevance scoring, and trend analysis.

The agent automatically determines search strategy, database selection,
filters, and result limits based on the query content - you just provide
the research query.
"""

from tooluniverse import ToolUniverse


def main():
    tu = ToolUniverse()
    tu.load_tools()

    # Example: Interdisciplinary topic
    print("\n" + "=" * 80)
    print("Example: Interdisciplinary Research Topic")
    print("=" * 80)

    result = tu.run(
        {
            "name": "advanced_literature_search_agent",
            "arguments": {
                "query": (
                    "Give me a report of single-cell RNA sequencing analysis methods"
                ),
            },
        }
    )
    print(result)


if __name__ == "__main__":
    main()
