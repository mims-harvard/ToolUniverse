from tooluniverse import ToolUniverse


def main():
    tu = ToolUniverse()
    tu.load_tools()

    # Example 1: search species
    res1 = tu.run_one_function({
        "name": "GBIF_search_species",
        "arguments": {"query": "Homo", "limit": 3}
    })
    print(
        "GBIF_search_species:",
        res1 if isinstance(res1, dict) else str(res1)[:500],
    )

    # Example 2: search occurrences (no filters, small page)
    res2 = tu.run_one_function({
        "name": "GBIF_search_occurrences",
        "arguments": {"hasCoordinate": True, "limit": 3}
    })
    print(
        "GBIF_search_occurrences:",
        res2 if isinstance(res2, dict) else str(res2)[:500],
    )


if __name__ == "__main__":
    main()


