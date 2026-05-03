"""Examples for using BRENDA enzyme database tools."""
from tooluniverse import ToolUniverse

def main():
    tu = ToolUniverse()
    tu.load_tools()

    print("=" * 60)
    print("BRENDA (Enzyme Kinetics Database) Examples")
    print("=" * 60)

    # Get Km values for alcohol dehydrogenase
    print("\n1. Get Km values for EC 1.1.1.1 (alcohol dehydrogenase):")
    result = tu.tools.BRENDA_get_km(operation="get_km", ec_number="1.1.1.1")
    if result["status"] == "success":
        print(f"Km values found: {result['data']['count']}")
    else:
        print(f"Error: {result['error']}")

    # Get kcat values
    print("\n2. Get kcat (turnover numbers):")
    result = tu.tools.BRENDA_get_kcat(operation="get_kcat", ec_number="1.1.1.1")
    if result["status"] == "success":
        print(f"kcat values found: {result['data']['count']}")
    else:
        print(f"Error: {result['error']}")

if __name__ == "__main__":
    main()
