#!/usr/bin/env python3
"""Manual test script for ProteinsPlus and SwissDock tools."""

import re
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_tool_loading():
    """Test if tools are properly registered and loaded."""
    print("=" * 70)
    print("TEST 1: Tool Loading and Registration")
    print("=" * 70)

    try:
        from tooluniverse import ToolUniverse
        tu = ToolUniverse()

        print("\n✅ ToolUniverse imported successfully")
        print(f"📦 Loading tools...")

        tu.load_tools()

        print(f"✅ Tools loaded: {len(tu.all_tool_dict)}")

        # Check ProteinsPlus tools
        pp_tools = [name for name in tu.all_tool_dict.keys() if 'ProteinsPlus' in name]
        print(f"\n🔬 ProteinsPlus tools found: {len(pp_tools)}")
        for tool in sorted(pp_tools):
            print(f"   ✓ {tool}")

        # Check SwissDock tools
        sd_tools = [name for name in tu.all_tool_dict.keys() if 'SwissDock' in name]
        print(f"\n🧪 SwissDock tools found: {len(sd_tools)}")
        for tool in sorted(sd_tools):
            print(f"   ✓ {tool}")

        if not pp_tools and not sd_tools:
            print("\n⚠️  WARNING: No ProteinsPlus or SwissDock tools found!")
            print("   This means the tools aren't being loaded by ToolUniverse.")
            print("   Checking configuration...")

            # Check if config entries exist
            from tooluniverse import default_config
            config_has_pp = 'proteinsplus' in default_config.default_tool_files
            config_has_sd = 'swissdock' in default_config.default_tool_files

            print(f"\n   Config has 'proteinsplus': {config_has_pp}")
            print(f"   Config has 'swissdock': {config_has_sd}")

            if config_has_pp:
                pp_path = default_config.default_tool_files['proteinsplus']
                print(f"   ProteinsPlus config path: {pp_path}")
                print(f"   File exists: {os.path.exists(pp_path)}")

            if config_has_sd:
                sd_path = default_config.default_tool_files['swissdock']
                print(f"   SwissDock config path: {sd_path}")
                print(f"   File exists: {os.path.exists(sd_path)}")

        return tu, pp_tools, sd_tools

    except Exception as e:
        print(f"\n❌ ERROR loading tools: {e}")
        import traceback
        traceback.print_exc()
        return None, [], []


def test_tool_configs():
    """Test if JSON configs are valid."""
    print("\n" + "=" * 70)
    print("TEST 2: Configuration File Validation")
    print("=" * 70)

    import json

    configs = {
        'ProteinsPlus': 'src/tooluniverse/data/proteinsplus_tools.json',
        'SwissDock': 'src/tooluniverse/data/swissdock_tools.json'
    }

    for name, path in configs.items():
        print(f"\n📄 Checking {name} config: {path}")
        try:
            with open(path, 'r') as f:
                data = json.load(f)

            if isinstance(data, list):
                print(f"   ✅ Valid JSON (array with {len(data)} tools)")
                for i, tool in enumerate(data, 1):
                    tool_name = tool.get('name', 'UNNAMED')
                    tool_type = tool.get('type', 'UNTYPED')
                    print(f"      {i}. {tool_name} ({tool_type})")
            else:
                print(f"   ⚠️  Valid JSON but not an array")

        except FileNotFoundError:
            print(f"   ❌ File not found!")
        except json.JSONDecodeError as e:
            print(f"   ❌ Invalid JSON: {e}")
        except Exception as e:
            print(f"   ❌ Error: {e}")


def test_tool_classes():
    """Test if Python tool classes exist and can be imported."""
    print("\n" + "=" * 70)
    print("TEST 3: Python Tool Class Verification")
    print("=" * 70)

    sys.path.insert(0, 'src')

    tools = {
        'ProteinsPlusRESTTool': 'src/tooluniverse/proteinsplus_tool.py',
        'SwissDockTool': 'src/tooluniverse/swissdock_tool.py'
    }

    for class_name, file_path in tools.items():
        print(f"\n🔧 Checking {class_name}")
        print(f"   File: {file_path}")
        print(f"   Exists: {os.path.exists(file_path)}")

        if os.path.exists(file_path):
            # Check for @register_tool decorator
            with open(file_path, 'r') as f:
                content = f.read()
                has_register = '@register_tool' in content
                has_class = f'class {class_name}' in content
                print(f"   Has @register_tool: {has_register}")
                print(f"   Has class definition: {has_class}")

                if has_register:
                    match = re.search(r'@register_tool\(["\']([^"\']+)["\']\)', content)
                    if match:
                        registered_name = match.group(1)
                        print(f"   Registered as: '{registered_name}'")


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("ToolUniverse New Tools Testing Suite")
    print("=" * 70)

    # Test 1: Tool loading
    tu, pp_tools, sd_tools = test_tool_loading()

    # Test 2: Config validation
    test_tool_configs()

    # Test 3: Class verification
    test_tool_classes()

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    if tu:
        total_tools = len(tu.all_tool_dict)
        new_tools = len(pp_tools) + len(sd_tools)
        print(f"✅ ToolUniverse loaded: {total_tools} total tools")
        print(f"🆕 New tools loaded: {new_tools}")
        print(f"   - ProteinsPlus: {len(pp_tools)}")
        print(f"   - SwissDock: {len(sd_tools)}")

        if new_tools == 0:
            print(f"\n⚠️  ISSUE: New tools not loading despite config being present")
            print(f"   Next steps:")
            print(f"   1. Check if tool modules need to be imported in __init__.py")
            print(f"   2. Verify tool registry is picking up new classes")
            print(f"   3. Check if JSON configs have correct 'type' fields")
    else:
        print("❌ ToolUniverse failed to load")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
