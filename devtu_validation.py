"""devtu systematic tool validation script."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from tooluniverse import ToolUniverse

def check_tool_structure(tool_name, tool_config):
    """Validate tool structure according to devtu requirements."""
    issues = []
    warnings = []

    # Check 1: Type specified
    if 'type' not in tool_config:
        issues.append("Missing 'type' field")

    # Check 2: Description quality
    desc = tool_config.get('description', '')
    if len(desc) < 50:
        warnings.append(f"Description too short ({len(desc)} chars)")
    if not desc.endswith('.'):
        warnings.append("Description doesn't end with period")

    # Check 3: Parameter schema
    param_schema = tool_config.get('parameter', {})
    if not param_schema:
        issues.append("Missing parameter schema")
    else:
        # Check required field
        if 'required' not in param_schema:
            warnings.append("'required' field not specified in parameter schema")

        # Check properties
        if 'properties' not in param_schema:
            issues.append("Missing 'properties' in parameter schema")
        else:
            # Check each property has description
            for prop_name, prop_def in param_schema.get('properties', {}).items():
                if 'description' not in prop_def:
                    warnings.append(f"Property '{prop_name}' missing description")

    # Check 4: Return schema
    return_schema = tool_config.get('return_schema', {})
    if not return_schema:
        warnings.append("Missing return_schema")
    else:
        # Check for oneOf with success/error paths
        if 'oneOf' not in return_schema:
            warnings.append("return_schema missing 'oneOf' structure for success/error handling")
        else:
            # Check first schema (success) has 'data' wrapper
            success_schema = return_schema['oneOf'][0]
            if 'data' not in success_schema.get('properties', {}):
                issues.append("Return schema missing 'data' wrapper (devtu requirement)")

    # Check 5: Test examples
    test_examples = tool_config.get('test_examples', [])
    if not test_examples:
        warnings.append("No test examples provided")
    elif len(test_examples) < 2:
        warnings.append("Only 1 test example (devtu recommends 2-3)")

    # Check 6: Fields for REST tools (SOAP tools use 'operation' instead)
    fields = tool_config.get('fields', {})
    tool_type = tool_config.get('type', '')

    if 'SOAP' not in tool_type and 'Dock' not in tool_type:  # REST tools
        if 'endpoint' not in fields:
            issues.append("Missing 'endpoint' in fields")
        if 'method' not in fields:
            warnings.append("Missing 'method' in fields")
    else:  # SOAP/special tools
        if 'operation' not in fields and 'endpoint' not in fields:
            warnings.append("Missing 'operation' or 'endpoint' in fields")

    # Check 7: Async configuration if needed
    if fields.get('is_async', False):
        if 'poll_interval' not in fields:
            warnings.append("Async tool missing 'poll_interval'")
        if 'max_wait_time' not in fields:
            warnings.append("Async tool missing 'max_wait_time'")

    return issues, warnings

def validate_test_examples(tool_name, test_examples):
    """Check if test examples use valid, real IDs."""
    issues = []
    warnings = []

    for i, example in enumerate(test_examples, 1):
        # Check for placeholder/dummy values
        for key, value in example.items():
            if isinstance(value, str):
                if value.upper() in ['TEST', 'DUMMY', 'EXAMPLE', 'PLACEHOLDER', 'XXX', 'TODO']:
                    issues.append(f"Test example {i} uses placeholder value: {key}={value}")

                # Check PDB IDs are valid format
                if 'pdb' in key.lower() and len(value) == 4:
                    # Valid PDB format: 4 characters, first digit, rest alphanumeric
                    if not (value[0].isdigit() and value[1:].isalnum()):
                        warnings.append(f"Test example {i} PDB ID '{value}' may be invalid format")

    return issues, warnings

def main():
    print("=" * 80)
    print("devtu SYSTEMATIC TOOL VALIDATION")
    print("Following devtu-fix-tool workflow")
    print("=" * 80)

    # Load ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    # Get all new tools
    new_tools = [
        'ProteinsPlus_predict_binding_sites',
        'ProteinsPlus_predict_binding_sites_v3',
        'ProteinsPlus_generate_interaction_diagram',
        'ProteinsPlus_analyze_binding_site_similarity',
        'ProteinsPlus_profile_structure_quality',
        'SwissDock_dock_ligand',
        'SwissDock_check_job_status',
        'SwissDock_retrieve_results',
    ]

    validation_results = {}

    for tool_name in new_tools:
        if tool_name not in tu.all_tool_dict:
            print(f"\n❌ {tool_name}: NOT FOUND in tool registry")
            continue

        print(f"\n{'=' * 80}")
        print(f"VALIDATING: {tool_name}")
        print('=' * 80)

        tool_config = tu.all_tool_dict[tool_name]

        # Run structure checks
        issues, warnings = check_tool_structure(tool_name, tool_config)

        # Validate test examples
        test_examples = tool_config.get('test_examples', [])
        test_issues, test_warnings = validate_test_examples(tool_name, test_examples)
        issues.extend(test_issues)
        warnings.extend(test_warnings)

        # Display results
        print(f"\n📋 Configuration:")
        print(f"  Type: {tool_config.get('type')}")
        print(f"  Endpoint: {tool_config.get('fields', {}).get('endpoint', 'N/A')}")
        print(f"  Method: {tool_config.get('fields', {}).get('method', 'N/A')}")
        print(f"  Async: {tool_config.get('fields', {}).get('is_async', False)}")
        print(f"  Test Examples: {len(test_examples)}")

        print(f"\n🔍 Validation Results:")

        if issues:
            print(f"  ❌ ISSUES ({len(issues)}):")
            for issue in issues:
                print(f"     - {issue}")
        else:
            print(f"  ✅ No critical issues")

        if warnings:
            print(f"  ⚠️  WARNINGS ({len(warnings)}):")
            for warning in warnings:
                print(f"     - {warning}")
        else:
            print(f"  ✅ No warnings")

        # Store results
        validation_results[tool_name] = {
            'issues': len(issues),
            'warnings': len(warnings),
            'status': '✅ PASS' if len(issues) == 0 else '❌ FAIL'
        }

    # Summary
    print(f"\n{'=' * 80}")
    print("VALIDATION SUMMARY")
    print('=' * 80)

    total_tools = len(new_tools)
    passed = sum(1 for r in validation_results.values() if r['status'] == '✅ PASS')
    failed = total_tools - passed

    print(f"\nTotal Tools Validated: {total_tools}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")

    print(f"\nDetailed Results:")
    for tool_name, result in validation_results.items():
        print(f"  {result['status']} {tool_name}")
        if result['issues'] > 0:
            print(f"     └─ {result['issues']} critical issue(s)")
        if result['warnings'] > 0:
            print(f"     └─ {result['warnings']} warning(s)")

    print(f"\n{'=' * 80}")
    if failed == 0:
        print("✅ ALL TOOLS PASS devtu VALIDATION")
        print("Ready for production use")
    else:
        print(f"⚠️  {failed} tool(s) need fixes before production")
        print("Review issues above and apply fixes")
    print('=' * 80)

    return 0 if failed == 0 else 1

if __name__ == '__main__':
    sys.exit(main())
