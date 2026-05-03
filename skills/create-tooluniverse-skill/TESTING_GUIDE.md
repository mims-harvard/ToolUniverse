# Testing Guide

Comprehensive testing procedures for ToolUniverse skills. This phase is MANDATORY -- no skill is complete without passing comprehensive tests.

## Comprehensive Test Suite Template

**File**: `test_skill_comprehensive.py`

Test ALL use cases from documentation + edge cases.

```python
#!/usr/bin/env python3
"""
Comprehensive Test Suite for [Domain] Skill
Tests all use cases from SKILL.md + edge cases
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from python_implementation import skill_function
from tooluniverse import ToolUniverse

def test_1_use_case_from_skill_md():
    """Test Case 1: [Use case name from SKILL.md]"""
    print("\n" + "="*80)
    print("TEST 1: [Use Case Name]")
    print("="*80)
    print("Expected: [What should happen]")

    tu = ToolUniverse()
    result = skill_function(tu=tu, input_param="value")

    # Validation
    assert isinstance(result, ExpectedType), "Should return expected type"
    assert result.field_name is not None, "Should have required field"

    print(f"\nPASS: [What passed]")
    return result

def test_2_documentation_accuracy():
    """Test Case 2: QUICK_START.md example works exactly as documented"""
    print("\n" + "="*80)
    print("TEST 2: Documentation Accuracy")
    print("="*80)

    # Exact copy-paste from QUICK_START.md
    tu = ToolUniverse()
    result = skill_function(tu=tu, param="value")  # From docs

    # Verify documented attributes exist
    assert hasattr(result, 'documented_field'), "Doc says this field exists"

    print(f"\nPASS: Documentation examples work")
    return result

def test_3_edge_case_invalid_input():
    """Test Case 3: Error handling with invalid inputs"""
    print("\n" + "="*80)
    print("TEST 3: Error Handling")
    print("="*80)

    tu = ToolUniverse()
    result = skill_function(tu=tu, input_param="INVALID")

    # Should handle gracefully, not crash
    assert isinstance(result, ExpectedType), "Should still return result"
    assert len(result.warnings) > 0, "Should have warnings"

    print(f"\nPASS: Handled invalid input gracefully")
    return result

def test_4_result_structure():
    """Test Case 4: Result structure matches documentation"""
    print("\n" + "="*80)
    print("TEST 4: Result Structure")
    print("="*80)

    tu = ToolUniverse()
    result = skill_function(tu=tu, input_param="value")

    # Check all documented fields
    required_fields = ['field1', 'field2', 'field3']
    for field in required_fields:
        assert hasattr(result, field), f"Missing field: {field}"

    print(f"\nPASS: All documented fields present")
    return result

def test_5_parameter_validation():
    """Test Case 5: All documented parameters work"""
    print("\n" + "="*80)
    print("TEST 5: Parameter Validation")
    print("="*80)

    tu = ToolUniverse()
    result = skill_function(
        tu=tu,
        param1="value1",  # All documented params
        param2="value2",
        param3=True
    )

    assert isinstance(result, ExpectedType), "Should work with all params"

    print(f"\nPASS: All parameters accepted")
    return result

def run_all_tests():
    """Run all tests and generate report"""
    print("\n" + "="*80)
    print("[DOMAIN] SKILL - COMPREHENSIVE TEST SUITE")
    print("="*80)

    tests = [
        ("Use Case 1", test_1_use_case_from_skill_md),
        ("Documentation Accuracy", test_2_documentation_accuracy),
        ("Error Handling", test_3_edge_case_invalid_input),
        ("Result Structure", test_4_result_structure),
        ("Parameter Validation", test_5_parameter_validation),
    ]

    results = {}
    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            result = test_func()
            results[test_name] = {"status": "PASS", "result": result}
            passed += 1
        except Exception as e:
            results[test_name] = {"status": "FAIL", "error": str(e)}
            failed += 1
            print(f"\nFAIL: {test_name}")
            print(f"   Error: {e}")

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Passed: {passed}/{len(tests)}")
    print(f"Failed: {failed}/{len(tests)}")
    print(f"Success Rate: {passed/len(tests)*100:.1f}%")

    if failed == 0:
        print("\nALL TESTS PASSED! Skill is production-ready.")
    else:
        print("\nSome tests failed. Review errors above.")

    return passed, failed

if __name__ == "__main__":
    passed, failed = run_all_tests()
    sys.exit(0 if failed == 0 else 1)
```

## Test Requirements Checklist

- [ ] Test ALL use cases from SKILL.md (typically 4-6 use cases)
- [ ] Test QUICK_START.md example (exact copy-paste must work)
- [ ] Test error handling (invalid inputs don't crash)
- [ ] Test result structure (all fields present, correct types)
- [ ] Test all parameters (documented params accepted)
- [ ] Test edge cases (empty results, partial failures)

## Running Tests

```bash
cd skills/tooluniverse-[domain]
python test_skill_comprehensive.py > test_output.txt 2>&1
```

**Pass criteria**:
- 100% test pass rate
- All use cases pass
- Documentation examples work exactly as written
- No exceptions or crashes
- Edge cases handled gracefully

## Test Report Template

**File**: `SKILL_TESTING_REPORT.md`

```markdown
# [Domain] Skill - Testing Report

**Date**: [Date]
**Status**: PASS / FAIL
**Success Rate**: X/Y tests passed (100%)

## Executive Summary

[Brief summary of testing results]

## Test Results

### Test 1: [Use Case Name] - PASS
**Use Case**: [Description from SKILL.md]
**Result**: [What happened]
**Validation**: [What was verified]

### Test 2-5: [Similar format]

## Quality Metrics
- **Code quality**: [Assessment]
- **Documentation accuracy**: [All examples work / Issues found]
- **Robustness**: [Error handling assessment]
- **User experience**: [Assessment]

## Recommendation
PRODUCTION-READY / NEEDS FIXES
```

## Manual Verification

Test with fresh environment:
1. Load ToolUniverse
2. Import python_implementation
3. Run exact example from QUICK_START (copy-paste)
4. Verify output matches expectations
5. Verify all documented fields accessible

**CRITICAL**: If documentation example doesn't work, fix EITHER:
- The documentation (update to match implementation), OR
- The implementation (update to match documentation)

**NEVER release with documentation that doesn't work.**
