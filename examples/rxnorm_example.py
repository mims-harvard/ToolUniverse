# rxnorm_example.py

from tooluniverse import ToolUniverse

# Step 1: Initialize ToolUniverse and load all tools (including RxNorm tools)
tooluni = ToolUniverse()
# Load all tools - RxNorm tools will be included automatically
tooluni.load_tools()

# Step 2: Define test queries for RxNorm tool
test_queries = [
    # Generic names (lowercase)
    {
        "name": "RxNorm_get_drug_names",
        "arguments": {"drug_name": "ibuprofen"},
    },
    {
        "name": "RxNorm_get_drug_names",
        "arguments": {"drug_name": "aspirin"},
    },
    {
        "name": "RxNorm_get_drug_names",
        "arguments": {"drug_name": "acetaminophen"},
    },
    # Generic names (uppercase)
    {
        "name": "RxNorm_get_drug_names",
        "arguments": {"drug_name": "IBUPROFEN"},
    },
    # Generic names (title case)
    {
        "name": "RxNorm_get_drug_names",
        "arguments": {"drug_name": "Metformin"},
    },
    # Brand names
    {
        "name": "RxNorm_get_drug_names",
        "arguments": {"drug_name": "Advil"},
    },
    {
        "name": "RxNorm_get_drug_names",
        "arguments": {"drug_name": "Tylenol"},
    },
    {
        "name": "RxNorm_get_drug_names",
        "arguments": {"drug_name": "Lipitor"},
    },
    # Names with dosage information (should be preprocessed automatically)
    {
        "name": "RxNorm_get_drug_names",
        "arguments": {"drug_name": "ibuprofen 200mg"},
    },
    {
        "name": "RxNorm_get_drug_names",
        "arguments": {"drug_name": "aspirin 81mg"},
    },
    # Brand name with modifier
    {
        "name": "RxNorm_get_drug_names",
        "arguments": {"drug_name": "Tylenol Extra Strength"},
    },
    # Complex drug names
    {
        "name": "RxNorm_get_drug_names",
        "arguments": {"drug_name": "lisinopril"},
    },
    {
        "name": "RxNorm_get_drug_names",
        "arguments": {"drug_name": "amlodipine"},
    },
    # International names
    {
        "name": "RxNorm_get_drug_names",
        "arguments": {"drug_name": "paracetamol"},
    },
]

# Step 3: Iterate over all test queries and print results
for idx, query in enumerate(test_queries):
    name = query["name"]
    args = query["arguments"]
    print(f"\n[{idx+1}] Running tool: {name}")
    print(f"Arguments: {args}")
    print("-" * 60)
    try:
        result = tooluni.run_one_function(query)
        if isinstance(result, dict):
            if "error" in result:
                print("Error:", result["error"])
            else:
                print("RXCUI:", result.get("rxcui"))
                print("Drug name:", result.get("drug_name"))
                if "processed_name" in result:
                    print("Processed name:", result.get("processed_name"))
                names = result.get("names", [])
                print(f"Number of names found: {len(names)}")
                if names:
                    print("Names:", names)
        else:
            print("Result:", result)
    except Exception as e:
        print(f"Exception occurred: {e}")

print("\nRxNorm example complete!")

