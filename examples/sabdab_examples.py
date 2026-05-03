"""Examples for using SAbDab structural antibody database tools."""
from tooluniverse import ToolUniverse

def main():
    tu = ToolUniverse()
    tu.load_tools()

    print("=" * 60)
    print("SAbDab (Structural Antibody Database) Examples")
    print("=" * 60)

    # Get database summary
    print("\n1. Get SAbDab summary:")
    result = tu.tools.SAbDab_get_summary(operation="get_summary")
    if result["status"] == "success":
        print(f"Description: {result['data'].get('description', 'N/A')}")
    else:
        print(f"Error: {result['error']}")

    # Search for structures
    print("\n2. Search for anti-CD20 antibodies:")
    result = tu.tools.SAbDab_search_structures(operation="search_structures", query="anti-CD20")
    if result["status"] == "success":
        print(f"Results: {result['data']}")
    else:
        print(f"Error: {result['error']}")

if __name__ == "__main__":
    main()
