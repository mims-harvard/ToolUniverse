from tooluniverse import ToolUniverse


def main():
    tu = ToolUniverse()
    tu.load_tools()

    # Example 1: search marine taxa
    res1 = tu.run_one_function({
        "name": "OBIS_search_taxa",
        "arguments": {"scientificname": "Gadus", "size": 1},
    })
    print("OBIS_search_taxa:", res1 if isinstance(res1, dict) else str(res1)[:500])

    # Example 2: search occurrences (small page)
    res2 = tu.run_one_function({
        "name": "OBIS_search_occurrences",
        "arguments": {"size": 1},
    })
    print("OBIS_search_occurrences:", res2 if isinstance(res2, dict) else str(res2)[:500])


if __name__ == "__main__":
    main()


