from tooluniverse import ToolUniverse


def main():
    tu = ToolUniverse()
    tu.load_tools()

    # Example 1: search cases with simple filters
    res1 = tu.run_one_function({
        "name": "GDC_search_cases",
        "arguments": {"project_id": "TCGA-BRCA", "size": 3}
    })
    print("GDC_search_cases:", res1 if isinstance(res1, dict) else str(res1)[:500])

    # Example 2: list files
    res2 = tu.run_one_function({
        "name": "GDC_list_files",
        "arguments": {"data_type": "Gene Expression Quantification", "size": 3}
    })
    print("GDC_list_files:", res2 if isinstance(res2, dict) else str(res2)[:500])


if __name__ == "__main__":
    main()
