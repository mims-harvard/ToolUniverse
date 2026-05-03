from tooluniverse import ToolUniverse


def main():
    tu = ToolUniverse()
    tu.load_tools()

    # Example 1: search studies by biome
    res1 = tu.run_one_function({
        "name": "MGnify_search_studies",
        "arguments": {"biome": "root:Host-associated", "size": 3}
    })
    print("MGnify_search_studies:", res1 if isinstance(res1, dict) else str(res1)[:500])

    # Example 2: list analyses for a study (replace with an actual study accession)
    res2 = tu.run_one_function({
        "name": "MGnify_list_analyses",
        "arguments": {"study_accession": "MGYS00000001", "size": 3}
    })
    print("MGnify_list_analyses:", res2 if isinstance(res2, dict) else str(res2)[:500])


if __name__ == "__main__":
    main()
