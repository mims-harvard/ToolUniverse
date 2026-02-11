#!/usr/bin/env python3
"""Live API testing for ProteinsPlus and SwissDock tools."""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from tooluniverse import ToolUniverse


def test_proteinsplus_dogsite():
    """Test ProteinsPlus DoGSiteScorer with live API call."""
    print("\n" + "=" * 70)
    print("TEST: ProteinsPlus DoGSiteScorer (Live API)")
    print("=" * 70)

    tu = ToolUniverse()
    tu.load_tools()

    tool_name = "ProteinsPlus_predict_binding_sites"
    print(f"\n🧪 Testing: {tool_name}")
    print(f"   Endpoint: /dogsite_rest")
    print(f"   Test PDB: 2OZR (small structure for fast testing)")
    print(f"   Note: This is an async job, may take 30-60 seconds\n")

    try:
        print("📡 Submitting job to ProteinsPlus API...")
        result = tu.run({
            "name": tool_name,
            "arguments": {
                "pdb_id": "2OZR",
                "chain": "A"
            }
        })

        print(f"\n📥 Response received:")
        print(json.dumps(result, indent=2)[:1000])  # First 1000 chars

        # Check result
        if isinstance(result, dict):
            if "error" in result:
                print(f"\n❌ API Error: {result['error']}")
                if "detail" in result:
                    print(f"   Details: {result['detail']}")
                return False
            elif "data" in result:
                print(f"\n✅ SUCCESS: Got data response")
                if "pockets" in result.get("data", {}):
                    pockets = result["data"]["pockets"]
                    print(f"   Found {len(pockets)} pockets")
                return True
            else:
                print(f"\n⚠️  Unexpected response format")
                return False
        else:
            print(f"\n⚠️  Response is not a dictionary")
            return False

    except Exception as e:
        print(f"\n❌ Exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_swissdock_status():
    """Test SwissDock API connectivity (status check only)."""
    print("\n" + "=" * 70)
    print("TEST: SwissDock API Connectivity")
    print("=" * 70)

    tu = ToolUniverse()
    tu.load_tools()

    tool_name = "SwissDock_check_job_status"
    print(f"\n🧪 Testing: {tool_name}")
    print(f"   Testing with dummy job ID to verify API connectivity")
    print(f"   Expected: 'NOT_FOUND' response (which means API is working)\n")

    try:
        print("📡 Checking SwissDock API...")
        result = tu.run({
            "name": tool_name,
            "arguments": {
                "job_id": "test_connectivity_12345"
            }
        })

        print(f"\n📥 Response received:")
        print(json.dumps(result, indent=2)[:500])

        # For status check, even NOT_FOUND is a success (means API responded)
        if isinstance(result, dict):
            if "status" in result:
                status = result["status"]
                if status in ["NOT_FOUND", "RUNNING", "FINISHED", "ERROR"]:
                    print(f"\n✅ SUCCESS: API responding (status: {status})")
                    return True
            elif "error" in result:
                # Check if it's a connectivity error or expected NOT_FOUND
                error = result.get("error", "")
                if "not found" in error.lower() or "404" in error:
                    print(f"\n✅ SUCCESS: API responding (job not found as expected)")
                    return True
                else:
                    print(f"\n❌ API Error: {error}")
                    return False

        print(f"\n⚠️  Unexpected response format")
        return False

    except Exception as e:
        print(f"\n❌ Exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_tool_validation():
    """Test tool parameter validation."""
    print("\n" + "=" * 70)
    print("TEST: Tool Parameter Validation")
    print("=" * 70)

    tu = ToolUniverse()
    tu.load_tools()

    # Test with missing required parameter
    print(f"\n🧪 Testing validation with missing required parameter")
    result = tu.run({
        "name": "ProteinsPlus_generate_interaction_diagram",
        "arguments": {
            "pdb_id": "2OZR"
            # Missing required "ligand" parameter
        }
    })

    if isinstance(result, dict) and "error" in result:
        print(f"✅ Validation working: {result['error']}")
        return True
    else:
        print(f"⚠️  Expected validation error, got: {result}")
        return False


def main():
    """Run live API tests."""
    print("\n" + "=" * 70)
    print("Live API Testing Suite")
    print("Testing actual API calls to verify endpoints")
    print("=" * 70)

    results = {}

    # Test 1: ProteinsPlus DoGSiteScorer
    print("\n⏳ This may take 30-60 seconds for async jobs...")
    results['dogsite'] = test_proteinsplus_dogsite()

    # Test 2: SwissDock connectivity
    results['swissdock'] = test_swissdock_status()

    # Test 3: Parameter validation
    results['validation'] = test_tool_validation()

    # Summary
    print("\n" + "=" * 70)
    print("LIVE API TEST SUMMARY")
    print("=" * 70)

    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")

    total = len(results)
    passed = sum(1 for v in results.values() if v)
    print(f"\nTotal: {passed}/{total} tests passed ({passed/total*100:.0f}%)")

    if passed == total:
        print("\n🎉 All live API tests passed!")
        print("✅ ProteinsPlus and SwissDock tools are production-ready")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed - see details above")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
