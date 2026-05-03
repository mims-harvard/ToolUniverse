from tooluniverse import ToolUniverse


def main():
    tu = ToolUniverse()
    tu.load_tools()

    # Example 1: search experiments (type=Experiment)
    res1 = tu.run_one_function({
        "name": "ENCODE_search_experiments",
        "arguments": {"assay_title": "ChIP-seq", "limit": 3}
    })
    print("ENCODE_search_experiments:", res1 if isinstance(res1, dict) else str(res1)[:500])

    # Example 2: list files from ENCODE
    res2 = tu.run_one_function({
        "name": "ENCODE_list_files",
        "arguments": {"file_type": "fastq", "limit": 3}
    })
    print("ENCODE_list_files:", res2 if isinstance(res2, dict) else str(res2)[:500])


if __name__ == "__main__":
    main()
