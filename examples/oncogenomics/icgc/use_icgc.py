from tooluniverse import ToolUniverse


def main():
    tu = ToolUniverse()
    tu.load_tools()

    query = "query { _info { apiVersion } }"
    res = tu.run_one_function({
        "name": "ICGCARGO_query",
        "arguments": {"graphql": query, "variables": {}},
    })
    print("ICGCARGO_query:", res if isinstance(res, dict) else str(res)[:500])


if __name__ == "__main__":
    main()


