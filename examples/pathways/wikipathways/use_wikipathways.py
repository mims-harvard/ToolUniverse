from tooluniverse import ToolUniverse


def main():
    tu = ToolUniverse()
    tu.load_tools()

    res1 = tu.run_one_function({
        "name": "WikiPathways_search",
        "arguments": {"query": "p53"}
    })
    print("WikiPathways_search:", res1 if isinstance(res1, dict) else str(res1)[:500])

    # Optionally fetch a pathway by ID if known (replace WP254 if needed)
    res2 = tu.run_one_function({
        "name": "WikiPathways_get_pathway",
        "arguments": {"wpid": "WP254", "format": "json"}
    })
    print("WikiPathways_get_pathway:", res2 if isinstance(res2, dict) else str(res2)[:500])


if __name__ == "__main__":
    main()


