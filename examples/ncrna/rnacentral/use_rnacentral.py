from tooluniverse import ToolUniverse


def main():
    tu = ToolUniverse()
    tu.load_tools()

    res1 = tu.run_one_function({
        "name": "RNAcentral_search",
        "arguments": {"query": "let-7", "page_size": 3}
    })
    print("RNAcentral_search:", res1 if isinstance(res1, dict) else str(res1)[:500])

    # If you have an accession from search results, fetch details
    # Example accession may need to be replaced with a real one
    acc = "URS000075C808"
    res2 = tu.run_one_function({
        "name": "RNAcentral_get_by_accession",
        "arguments": {"accession": acc}
    })
    print("RNAcentral_get_by_accession:", res2 if isinstance(res2, dict) else str(res2)[:500])


if __name__ == "__main__":
    main()


