"""LOINC tools -- lab test and clinical observation standardization examples."""

from tooluniverse import ToolUniverse


def example_search_lab_tests():
    """Example 1: Search for lab tests by name"""
    print("\n" + "=" * 80)
    print("Example 1: Search for Cholesterol Lab Tests")
    print("=" * 80)

    tu = ToolUniverse()
    tu.load_tools()

    # Search for cholesterol tests
    result = tu.tools.LOINC_search_tests(
        terms="cholesterol",
        max_results=5
    )

    print(f"\nFound {result.get('total_count')} total cholesterol tests")
    print(f"Showing top {result.get('count')} results:\n")

    for item in result.get('results', [])[:3]:
        print(f"Code: {item.get('code')}")
        print(f"Name: {item.get('LONG_COMMON_NAME')}")
        print(f"Component: {item.get('COMPONENT')}")
        print(f"System: {item.get('SYSTEM')}")
        print(f"Scale: {item.get('SCALE_TYP')}")
        print("-" * 80)


def example_get_code_details():
    """Example 2: Get detailed information for a specific LOINC code"""
    print("\n" + "=" * 80)
    print("Example 2: Get Details for LOINC Code 2093-3 (Cholesterol)")
    print("=" * 80)

    tu = ToolUniverse()
    tu.load_tools()

    # Get details for cholesterol LOINC code
    result = tu.tools.LOINC_get_code_details(
        loinc_code="2093-3"
    )

    print(f"\nLOINC Code: {result.get('loinc_code')}")
    print(f"Full Name: {result.get('LONG_COMMON_NAME')}")
    print(f"Short Name: {result.get('SHORT_NAME')}")
    print(f"Component: {result.get('COMPONENT')}")
    print(f"Property: {result.get('PROPERTY')}")
    print(f"System: {result.get('SYSTEM')}")
    print(f"Scale Type: {result.get('SCALE_TYP')}")
    print(f"Method: {result.get('METHOD_TYP')}")
    print(f"Class: {result.get('CLASS')}")
    print(f"Status: {result.get('STATUS')}")


def example_get_answer_list():
    """Example 3: Get answer list for coded lab values"""
    print("\n" + "=" * 80)
    print("Example 3: Get Answer List for ABO Blood Group (LOINC 883-9)")
    print("=" * 80)

    tu = ToolUniverse()
    tu.load_tools()

    # Get answer list for blood type
    result = tu.tools.LOINC_get_answer_list(
        loinc_code="883-9"
    )

    if "error" not in result:
        print(f"\nLOINC Code: {result.get('loinc_code')}")
        print(f"Number of Answers: {result.get('answer_count')}")
        print("\nPermissible Values:")

        for answer in result.get('answers', []):
            print(f"  - Code: {answer.get('code')}, Display: {answer.get('display')}")
    else:
        print(f"\nNote: {result.get('error')}")
        print("This LOINC code may not have a predefined answer list.")


def example_search_clinical_forms():
    """Example 4: Search for clinical assessment forms"""
    print("\n" + "=" * 80)
    print("Example 4: Search for Depression Screening Forms (PHQ-9)")
    print("=" * 80)

    tu = ToolUniverse()
    tu.load_tools()

    # Search for PHQ-9 depression screening
    result = tu.tools.LOINC_search_forms(
        terms="PHQ-9",
        max_results=3
    )

    print(f"\nFound {result.get('count')} forms/surveys\n")

    for item in result.get('results', []):
        print(f"Code: {item.get('code')}")
        print(f"Name: {item.get('LONG_COMMON_NAME')}")
        print(f"Class: {item.get('CLASS')}")
        print(f"Status: {item.get('STATUS')}")
        print("-" * 80)


def example_workflow_lab_standardization():
    """Example 5: Workflow for standardizing lab test names"""
    print("\n" + "=" * 80)
    print("Example 5: Standardize Lab Test Names Across Studies")
    print("=" * 80)

    tu = ToolUniverse()
    tu.load_tools()

    # Common lab test variations that need standardization
    test_variations = [
        "HbA1c",
        "hemoglobin A1c",
        "glycated hemoglobin"
    ]

    print("\nStandardizing different names for the same lab test:")

    for variation in test_variations:
        result = tu.tools.LOINC_search_tests(
            terms=variation,
            max_results=1
        )

        if result.get('results'):
            top_match = result['results'][0]
            print(f"\nInput: '{variation}'")
            print(f"  → LOINC Code: {top_match.get('code')}")
            print(f"  → Standard Name: {top_match.get('LONG_COMMON_NAME')}")


def example_clinical_trial_eligibility():
    """Example 6: Use LOINC to define clinical trial lab criteria"""
    print("\n" + "=" * 80)
    print("Example 6: Define Lab-Based Eligibility Criteria")
    print("=" * 80)

    tu = ToolUniverse()
    tu.load_tools()

    # Define eligibility criteria using LOINC codes
    criteria_tests = [
        "creatinine",
        "ALT",
        "platelet count"
    ]

    print("\nIdentifying LOINC codes for trial eligibility criteria:\n")

    for test in criteria_tests:
        result = tu.tools.LOINC_search_tests(
            terms=test,
            max_results=2
        )

        print(f"Criterion: {test}")
        if result.get('results'):
            for item in result['results'][:1]:
                print(f"  LOINC: {item.get('code')}")
                print(f"  Name: {item.get('LONG_COMMON_NAME')}")
                print(f"  System: {item.get('SYSTEM')}")
        print("-" * 40)


def main():
    """Run all examples"""
    print("\n" + "=" * 80)
    print("LOINC Tools - Complete Usage Examples")
    print("=" * 80)

    try:
        # Run all examples
        example_search_lab_tests()
        example_get_code_details()
        example_get_answer_list()
        example_search_clinical_forms()
        example_workflow_lab_standardization()
        example_clinical_trial_eligibility()

        print("\n" + "=" * 80)
        print("All examples completed successfully!")
        print("=" * 80 + "\n")

    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
