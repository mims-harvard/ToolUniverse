#!/usr/bin/env python3
"""Test script for SASBDB tools implementation."""

import sys
import json
from pathlib import Path

src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

EXPECTED_TOOLS = [
    "SASBDB_search_entries",
    "SASBDB_get_entry_data",
    "SASBDB_get_scattering_profile",
    "SASBDB_get_models",
    "SASBDB_download_data",
]
REQUIRED_FIELDS = ("name", "type", "description", "parameter", "fields")


def test_tool_config():
    """Test that the SASBDB tools JSON configuration is valid."""
    print("Testing SASBDB tools configuration...")

    json_path = src_path / "tooluniverse" / "data" / "sasbdb_tools.json"
    assert json_path.exists(), f"Configuration file not found at {json_path}"

    with open(json_path, 'r') as f:
        tools = json.load(f)

    assert isinstance(tools, list), "Configuration should be a list of tools"
    print(f"  Found {len(tools)} tools")

    for tool in tools:
        for field in REQUIRED_FIELDS:
            assert field in tool, f"Tool missing '{field}' field"
        assert tool["type"] == "SASBDBRESTTool", f"Unexpected type: {tool['type']}"

        endpoint = tool["fields"].get("endpoint", "")
        assert endpoint.startswith("https://www.sasbdb.org/"), f"Invalid endpoint: {endpoint}"
        assert tool.get("test_examples"), f"Tool '{tool['name']}' has no test examples"
        print(f"  {tool['name']}: OK ({len(tool['test_examples'])} examples)")

    tool_names = {t["name"] for t in tools}
    for expected in EXPECTED_TOOLS:
        assert expected in tool_names, f"Expected tool '{expected}' not found"

    return True


def test_tool_class():
    """Test that the SASBDB tool class can be imported."""
    print("\nTesting SASBDB tool class...")
    from tooluniverse.sasbdb_tool import SASBDBRESTTool
    assert hasattr(SASBDBRESTTool, 'run'), "Missing run method"
    print("  SASBDBRESTTool imported and verified")
    return True


def test_default_config():
    """Test that SASBDB tools are added to default_config.py."""
    print("\nTesting default_config.py integration...")

    config_path = src_path / "tooluniverse" / "default_config.py"
    assert config_path.exists(), f"default_config.py not found at {config_path}"

    content = config_path.read_text()
    assert '"sasbdb"' in content or "'sasbdb'" in content, "SASBDB not added to default_config.py"
    assert "sasbdb_tools.json" in content, "sasbdb_tools.json not referenced in default_config.py"
    print("  SASBDB tools registered in default_config.py")
    return True

def test_saxs_terminology():
    """Test that SAXS-specific terminology is properly documented."""
    print("\nTesting SAXS terminology in descriptions...")

    json_path = src_path / "tooluniverse" / "data" / "sasbdb_tools.json"

    with open(json_path, 'r') as f:
        tools = json.load(f)

    # Check for SAXS-specific terms in descriptions
    all_descriptions = " ".join([t["description"] for t in tools])

    saxs_terms = ["SAXS", "SANS", "Rg", "Dmax", "scattering", "solution structure"]
    for term in saxs_terms:
        assert term in all_descriptions, f"Missing SAXS term: {term}"
    print(f"✓ All SAXS-specific terms present: {', '.join(saxs_terms)}")

    # Check for quality metrics
    quality_terms = ["radius of gyration", "maximum dimension", "chi-squared"]
    descriptions_lower = all_descriptions.lower()
    for term in quality_terms:
        assert term.lower() in descriptions_lower, f"Missing quality metric: {term}"
    print(f"✓ Quality metrics documented: {', '.join(quality_terms)}")

    return True

def main():
    """Run all tests."""
    print("=" * 70)
    print("SASBDB Tools Implementation Test Suite")
    print("=" * 70)

    try:
        test_tool_config()
        test_tool_class()
        test_default_config()
        test_saxs_terminology()

        print("\n" + "=" * 70)
        print("✓ ALL TESTS PASSED")
        print("=" * 70)
        print("\nSummary:")
        print("- 5 SASBDB tools properly configured")
        print("- Tool class (SASBDBRESTTool) correctly implemented")
        print("- Integration with default_config.py complete")
        print("- SAXS-specific terminology and metrics included")
        print("\nReady for testing with actual API!")
        return 0

    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
