#!/usr/bin/env python3
"""
Test MCP connection and configuration.

This script verifies:
- MCP configuration file exists
- Configuration is valid JSON
- ToolUniverse server is configured
- Compact mode is enabled (recommended)
- Can execute basic MCP operations
"""

import sys
import json
import platform
from pathlib import Path


def find_mcp_config():
    """Find MCP configuration file for Cursor or Claude Desktop."""
    print("\n📁 Looking for MCP configuration...")
    
    system = platform.system()
    
    # Cursor locations
    if system == "Darwin":  # macOS
        cursor_config = Path.home() / "Library" / "Application Support" / "Cursor" / "User" / "mcp.json"
        claude_config = Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    elif system == "Windows":
        cursor_config = Path.home() / "AppData" / "Roaming" / "Cursor" / "User" / "mcp.json"
        claude_config = Path.home() / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json"
    else:  # Linux
        cursor_config = Path.home() / ".config" / "Cursor" / "User" / "mcp.json"
        claude_config = Path.home() / ".config" / "Claude" / "claude_desktop_config.json"
    
    # Check which config exists
    configs = []
    if cursor_config.exists():
        configs.append(("Cursor", cursor_config))
    if claude_config.exists():
        configs.append(("Claude Desktop", claude_config))
    
    if not configs:
        print(f"   ❌ No MCP config found")
        print(f"   Expected locations:")
        print(f"     Cursor: {cursor_config}")
        print(f"     Claude: {claude_config}")
        return None
    
    # Return all found configs
    for app, path in configs:
        print(f"   ✓ Found {app} config: {path}")
    
    return configs


def parse_config(config_path):
    """Parse and validate MCP configuration."""
    print(f"\n📝 Parsing configuration: {config_path.name}")
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        print("   ✓ Valid JSON format")
        return config
    except json.JSONDecodeError as e:
        print(f"   ❌ Invalid JSON: {e}")
        return None
    except Exception as e:
        print(f"   ❌ Error reading file: {e}")
        return None


def check_tooluniverse_config(config):
    """Check if ToolUniverse is configured."""
    print("\n🔍 Checking ToolUniverse configuration...")
    
    if "mcpServers" not in config:
        print("   ❌ No 'mcpServers' section found")
        return False
    
    servers = config["mcpServers"]
    
    if "tooluniverse" not in servers:
        print("   ❌ ToolUniverse not configured")
        print(f"   Found servers: {', '.join(servers.keys())}")
        return False
    
    tu_config = servers["tooluniverse"]
    print("   ✓ ToolUniverse server found")
    
    # Check command
    if "command" not in tu_config:
        print("   ❌ No 'command' specified")
        return False
    
    command = tu_config["command"]
    print(f"   Command: {command}")
    
    # Check args
    args = tu_config.get("args", [])
    print(f"   Arguments: {args}")
    
    # Check for compact mode
    has_compact_mode = "--compact-mode" in args
    if has_compact_mode:
        print("   ✓ Compact mode ENABLED (recommended)")
    else:
        print("   ⚠️  Compact mode NOT enabled")
        print("   WARNING: May cause context window overflow!")
        print('   Add "--compact-mode" to args array')
    
    # Check environment variables
    env = tu_config.get("env", {})
    if env:
        print(f"   Environment variables: {list(env.keys())}")
    
    return True


def test_command_availability(config):
    """Test if the configured command is available."""
    print("\n🖥️  Testing command availability...")
    
    if "mcpServers" not in config or "tooluniverse" not in config["mcpServers"]:
        return False
    
    import shutil
    
    tu_config = config["mcpServers"]["tooluniverse"]
    command = tu_config.get("command")
    
    if not command:
        return False
    
    cmd_path = shutil.which(command)
    if cmd_path:
        print(f"   ✓ Command found: {cmd_path}")
        return True
    else:
        print(f"   ❌ Command not found: {command}")
        print("   Solution: Ensure ToolUniverse is installed")
        return False


def check_working_directory(config):
    """Check if working directory exists (for uv configurations)."""
    print("\n📂 Checking working directory...")
    
    if "mcpServers" not in config or "tooluniverse" not in config["mcpServers"]:
        return True
    
    tu_config = config["mcpServers"]["tooluniverse"]
    args = tu_config.get("args", [])
    
    # Look for --directory flag
    try:
        dir_index = args.index("--directory")
        if dir_index + 1 < len(args):
            work_dir = Path(args[dir_index + 1])
            
            if work_dir.exists():
                print(f"   ✓ Directory exists: {work_dir}")
                return True
            else:
                print(f"   ❌ Directory not found: {work_dir}")
                print(f"   Create with: mkdir -p {work_dir}")
                return False
    except ValueError:
        # No --directory flag, that's fine
        print("   ℹ️  No working directory specified (using system)")
        return True


def test_basic_import():
    """Test if ToolUniverse can be imported in MCP context."""
    print("\n🐍 Testing ToolUniverse import...")
    
    try:
        from tooluniverse import ToolUniverse
        _tu = ToolUniverse()
        print("   ✓ Import successful")
        return True
    except ImportError as e:
        print(f"   ❌ Import failed: {e}")
        return False


def generate_sample_config():
    """Generate a sample MCP configuration."""
    print("\n📋 Sample MCP Configuration:")
    print("-" * 60)
    
    sample = {
        "mcpServers": {
            "tooluniverse": {
                "command": "tooluniverse-smcp-stdio",
                "args": ["--compact-mode"],
                "env": {
                    "PYTHONIOENCODING": "utf-8"
                }
            }
        }
    }
    
    print(json.dumps(sample, indent=2))
    print("-" * 60)


def main():
    """Run all MCP connection tests."""
    print("=" * 60)
    print("ToolUniverse MCP Connection Test")
    print("=" * 60)
    
    # Find config
    configs = find_mcp_config()
    
    if not configs:
        print("\n❌ No MCP configuration found")
        generate_sample_config()
        print("\nCreate mcp.json with the configuration above and restart your application.")
        return 1
    
    # Test each config found
    all_passed = True
    
    for app_name, config_path in configs:
        print(f"\n{'=' * 60}")
        print(f"Testing {app_name} Configuration")
        print(f"{'=' * 60}")
        
        config = parse_config(config_path)
        if not config:
            all_passed = False
            continue
        
        results = {
            "ToolUniverse config": check_tooluniverse_config(config),
            "Command available": test_command_availability(config),
            "Working directory": check_working_directory(config),
            "Import test": test_basic_import(),
        }
        
        print(f"\n{'-' * 60}")
        print(f"{app_name} Summary:")
        print(f"{'-' * 60}")
        
        for check, passed in results.items():
            status = "✓" if passed else "❌"
            print(f"{status} {check}")
        
        if not all(results.values()):
            all_passed = False
    
    print("\n" + "=" * 60)
    
    if all_passed:
        print("\n✅ MCP configuration verified!")
        print("\nNext steps:")
        print("  1. Restart Cursor or Claude Desktop")
        print("  2. Look for 'tooluniverse' in MCP servers list")
        print("  3. Try a test query:")
        print("     - list_tools")
        print("     - grep_tools with keyword 'protein'")
        print("     - execute_tool with any tool name")
        return 0
    else:
        print("\n❌ MCP configuration has issues")
        print("\nFix the errors above, then:")
        print("  1. Save your mcp.json changes")
        print("  2. Restart Cursor or Claude Desktop")
        print("  3. Run this script again")
        return 1


if __name__ == "__main__":
    sys.exit(main())
