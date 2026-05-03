"""Examples for using IMGT immunogenetics tools."""
from tooluniverse import ToolUniverse

def main():
    tu = ToolUniverse()
    tu.load_tools()

    print("=" * 60)
    print("IMGT (Immunogenetics Database) Examples")
    print("=" * 60)

    # Get gene info
    print("\n1. Get IMGT database information:")
    result = tu.tools.IMGT_get_gene_info(operation="get_gene_info")
    if result["status"] == "success":
        print(f"Databases: {list(result['data']['databases'].keys())}")
    else:
        print(f"Error: {result['error']}")

    # Search for human IGHV genes
    print("\n2. Search for human IGHV genes:")
    result = tu.tools.IMGT_search_genes(operation="search_genes", gene_type="IGHV")
    if result["status"] == "success":
        print(f"Search URL: {result['data']['search_url']}")
    else:
        print(f"Error: {result['error']}")

if __name__ == "__main__":
    main()
