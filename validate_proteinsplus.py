#!/usr/bin/env python3
"""Validation script for ProteinsPlus: file structure, JSON, imports."""

import json
import os
import sys


def validate_files():
    """Check that all required files exist."""
    print("=" * 80)
    print("File Structure Validation")
    print("=" * 80)

    files = [
        "src/tooluniverse/proteinsplus_tool.py",
        "src/tooluniverse/data/proteinsplus_tools.json",
        "examples/proteinsplus_tools_example.py",
        "docs/proteinsplus_implementation.md",
    ]

    all_exist = True
    for file_path in files:
        exists = os.path.exists(file_path)
        status = "✅" if exists else "❌"
        print(f"{status} {file_path}")
        if not exists:
            all_exist = False

    return all_exist


def validate_json():
    """Validate JSON configuration."""
    print("\n" + "=" * 80)
    print("JSON Configuration Validation")
    print("=" * 80)

    json_path = "src/tooluniverse/data/proteinsplus_tools.json"

    try:
        with open(json_path, 'r') as f:
            data = json.load(f)

        print(f"✅ Valid JSON structure")
        print(f"✅ Number of tools: {len(data)}")

        # Check each tool
        required_fields = ["name", "description", "type", "parameter", "fields"]
        for tool in data:
            tool_name = tool.get("name", "Unknown")
            print(f"\n  Tool: {tool_name}")

            for field in required_fields:
                has_field = field in tool
                status = "✅" if has_field else "❌"
                print(f"    {status} {field}")

            # Check test_examples
            has_examples = "test_examples" in tool and len(tool["test_examples"]) > 0
            status = "✅" if has_examples else "⚠️"
            count = len(tool.get("test_examples", []))
            print(f"    {status} test_examples ({count})")

        return True

    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def validate_registration():
    """Check registration in default_config.py."""
    print("\n" + "=" * 80)
    print("Registration Validation")
    print("=" * 80)

    config_path = "src/tooluniverse/default_config.py"

    try:
        with open(config_path, 'r') as f:
            content = f.read()

        if 'proteinsplus' in content.lower():
            print("✅ Found 'proteinsplus' in default_config.py")

            # Find the line
            for i, line in enumerate(content.split('\n'), 1):
                if 'proteinsplus' in line.lower() and 'proteinsplus_tools.json' in line:
                    print(f"✅ Registered at line {i}")
                    print(f"   {line.strip()}")
                    return True

            print("⚠️ Found reference but not properly registered")
            return False
        else:
            print("❌ Not found in default_config.py")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def validate_imports():
    """Check that imports work."""
    print("\n" + "=" * 80)
    print("Import Validation")
    print("=" * 80)

    try:
        # Add src to path
        sys.path.insert(0, 'src')

        # Try importing the tool class
        from tooluniverse.proteinsplus_tool import ProteinsPlusRESTTool
        print("✅ Successfully imported ProteinsPlusRESTTool")

        # Check if it has required methods
        methods = ['run', '__init__']
        for method in methods:
            has_method = hasattr(ProteinsPlusRESTTool, method)
            status = "✅" if has_method else "❌"
            print(f"  {status} Method: {method}")

        return True

    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Run all validations."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "ProteinsPlus Implementation Validator" + " " * 21 + "║")
    print("╚" + "=" * 78 + "╝")
    print()

    results = []

    results.append(("File Structure", validate_files()))
    results.append(("JSON Configuration", validate_json()))
    results.append(("Registration", validate_registration()))
    results.append(("Imports", validate_imports()))

    # Summary
    print("\n" + "=" * 80)
    print("Validation Summary")
    print("=" * 80)

    all_passed = all(result[1] for result in results)

    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status:8} {name}")

    print("\n" + "=" * 80)
    if all_passed:
        print("✅ All validations passed!")
        print("✅ ProteinsPlus tools are ready for testing")
    else:
        print("❌ Some validations failed")
        print("⚠️ Please review the errors above")
    print("=" * 80)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
