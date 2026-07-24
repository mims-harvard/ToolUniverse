#!/usr/bin/env python3
"""
Verify ToolUniverse installation.

This script checks:
- ToolUniverse import
- Version information
- Tool loading
- Basic functionality
- CLI commands availability
"""

import sys
import subprocess
import shutil
from pathlib import Path


def check_import():
    """Check if ToolUniverse can be imported."""
    print("\n📦 Checking ToolUniverse import...")
    try:
        import tooluniverse
        print(f"   ✓ PASS: ToolUniverse imported successfully")
        print(f"   Version: {tooluniverse.__version__}")
        return True, tooluniverse
    except ImportError as e:
        print(f"   ❌ FAIL: Cannot import tooluniverse")
        print(f"   Error: {e}")
        print("\n   Solution: Install with 'pip install tooluniverse'")
        return False, None


def check_tool_loading(tooluniverse):
    """Check if tools can be loaded."""
    print("\n🔧 Checking tool loading...")
    try:
        from tooluniverse import ToolUniverse
        tu = ToolUniverse()
        
        # Load tools (may take 10-30 seconds on first run)
        print("   Loading tools (this may take a moment)...")
        tu.load_tools()
        
        tool_count = len(tu.tools)
        print(f"   ✓ PASS: Loaded {tool_count} tools")
        
        if tool_count < 700:
            print(f"   ⚠️  WARNING: Expected ~764 tools, got {tool_count}")
            print("   Some tool categories may not be loaded")
        
        return True
    except Exception as e:
        print(f"   ❌ FAIL: Could not load tools")
        print(f"   Error: {e}")
        return False


def check_basic_execution(tooluniverse):
    """Test basic tool execution."""
    print("\n⚙️  Testing basic tool execution...")
    try:
        from tooluniverse import ToolUniverse
        tu = ToolUniverse()
        tu.load_tools()
        
        # Try to find a tool
        result = tu.run({
            "name": "Tool_Finder_Keyword",
            "arguments": {"description": "protein", "limit": 3}
        })
        
        if result and "error" not in result:
            print("   ✓ PASS: Tool execution successful")
            return True
        else:
            print("   ⚠️  WARNING: Tool execution returned unexpected result")
            print(f"   Result: {result}")
            return False
    except Exception as e:
        print(f"   ❌ FAIL: Tool execution failed")
        print(f"   Error: {e}")
        return False


def check_cli_commands():
    """Check if CLI commands are available."""
    print("\n🖥️  Checking CLI commands...")
    
    commands = [
        "tooluniverse-smcp-stdio",
        "tooluniverse-smcp-server",
        "tooluniverse-http-api",
    ]
    
    available = []
    missing = []
    
    for cmd in commands:
        cmd_path = shutil.which(cmd)
        if cmd_path:
            print(f"   ✓ {cmd}: {cmd_path}")
            available.append(cmd)
        else:
            print(f"   ❌ {cmd}: not found")
            missing.append(cmd)
    
    if missing:
        print(f"\n   ⚠️  Missing commands: {', '.join(missing)}")
        print("   This may indicate scripts directory is not in PATH")
        print("   Solution: pip install --force-reinstall tooluniverse")
        return False
    
    return True


def check_stdio_command():
    """Test if stdio command runs without errors."""
    print("\n🔌 Testing MCP stdio command...")
    
    cmd_path = shutil.which("tooluniverse-smcp-stdio")
    if not cmd_path:
        print("   ❌ FAIL: tooluniverse-smcp-stdio not found")
        return False
    
    try:
        # Start the command and immediately terminate it
        process = subprocess.Popen(
            ["tooluniverse-smcp-stdio", "--compact-mode"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Give it a moment to start
        import time
        time.sleep(2)
        
        # Terminate
        process.terminate()
        process.wait(timeout=5)
        
        # Check if it started without immediate errors
        if process.returncode in [0, -15, 143]:  # 0 = clean exit, -15/143 = SIGTERM
            print("   ✓ PASS: MCP stdio command starts successfully")
            return True
        else:
            print(f"   ⚠️  WARNING: Command exited with code {process.returncode}")
            stderr = process.stderr.read()
            if stderr:
                print(f"   Error output: {stderr[:200]}")
            return False
            
    except subprocess.TimeoutExpired:
        process.kill()
        print("   ⚠️  WARNING: Command timed out (may be running)")
        return True
    except Exception as e:
        print(f"   ❌ FAIL: Could not test command")
        print(f"   Error: {e}")
        return False


def check_optional_dependencies():
    """Check for optional dependencies."""
    print("\n📚 Checking optional dependencies...")
    
    optional_deps = {
        "sentence_transformers": "embedding/ml features",
        "cellxgene_census": "single-cell tools",
        "biopython": "bioinformatics tools",
        "rdkit": "chemistry visualization",
    }
    
    installed = []
    missing = []
    
    for package, purpose in optional_deps.items():
        try:
            __import__(package)
            print(f"   ✓ {package}: installed ({purpose})")
            installed.append(package)
        except ImportError:
            print(f"   ℹ️  {package}: not installed ({purpose})")
            missing.append(package)
    
    if missing:
        print(f"\n   ℹ️  Optional dependencies not installed: {', '.join(missing)}")
        print("   Install with: pip install tooluniverse[all]")
    
    return True  # Optional deps don't fail the check


def main():
    """Run all installation verification checks."""
    print("=" * 60)
    print("ToolUniverse Installation Verification")
    print("=" * 60)
    
    # Check import first
    import_ok, tooluniverse = check_import()
    if not import_ok:
        print("\n❌ Installation verification FAILED")
        print("ToolUniverse is not installed or cannot be imported.")
        return 1
    
    # Run other checks
    results = {
        "Import": True,  # Already checked above
        "Tool loading": check_tool_loading(tooluniverse),
        "Basic execution": check_basic_execution(tooluniverse),
        "CLI commands": check_cli_commands(),
        "MCP stdio": check_stdio_command(),
        "Optional deps": check_optional_dependencies(),
    }
    
    print("\n" + "=" * 60)
    print("Summary:")
    print("=" * 60)
    
    critical_checks = ["Import", "Tool loading", "CLI commands", "MCP stdio"]
    all_critical_passed = all(results.get(check, False) for check in critical_checks)
    
    for check, passed in results.items():
        status = "✓" if passed else ("❌" if check in critical_checks else "ℹ️")
        print(f"{status} {check}")
    
    print("=" * 60)
    
    if all_critical_passed:
        print("\n✅ Installation verified successfully!")
        print("\nNext steps:")
        print("  1. Configure MCP in Cursor/Claude Desktop")
        print("  2. Add this to mcp.json:")
        print('     {"mcpServers": {"tooluniverse": {')
        print('       "command": "tooluniverse-smcp-stdio",')
        print('       "args": ["--compact-mode"]')
        print('     }}}')
        print("  3. Restart Cursor/Claude Desktop")
        print("  4. Run: python scripts/test_mcp_connection.py")
        return 0
    else:
        print("\n❌ Installation has issues. Please fix the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
