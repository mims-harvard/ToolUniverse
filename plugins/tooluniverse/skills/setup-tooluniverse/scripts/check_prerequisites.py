#!/usr/bin/env python3
"""
Check prerequisites for ToolUniverse installation.

This script verifies:
- Python version (3.10-3.13 required)
- pip availability
- uv availability (optional)
- System platform
- Available disk space
"""

import sys
import subprocess
import platform
import shutil
from pathlib import Path


def check_python_version():
    """Check if Python version is compatible (3.10-3.13)."""
    version = sys.version_info
    print(f"\n🐍 Python Version: {version.major}.{version.minor}.{version.micro}")
    
    if version.major != 3:
        print("   ❌ FAIL: Python 3 required")
        return False
    
    if version.minor < 10:
        print(f"   ❌ FAIL: Python 3.10+ required (current: 3.{version.minor})")
        return False
    
    if version.minor >= 14:
        print(f"   ❌ FAIL: Python <3.14 required (current: 3.{version.minor})")
        return False
    
    print("   ✓ PASS: Python version compatible")
    return True


def check_pip():
    """Check if pip is available."""
    print("\n📦 Checking pip...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "--version"],
            capture_output=True,
            text=True,
            check=True
        )
        print(f"   ✓ PASS: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError:
        print("   ❌ FAIL: pip not available")
        print("   Install with: python3 -m ensurepip --upgrade")
        return False


def check_uv():
    """Check if uv is available (optional but recommended)."""
    print("\n⚡ Checking uv (optional)...")
    uv_path = shutil.which("uv")
    
    if uv_path:
        try:
            result = subprocess.run(
                ["uv", "--version"],
                capture_output=True,
                text=True,
                check=True
            )
            print(f"   ✓ PASS: uv found at {uv_path}")
            print(f"   Version: {result.stdout.strip()}")
            return True
        except subprocess.CalledProcessError:
            print(f"   ⚠️  WARNING: uv found but not working properly")
            return False
    else:
        print("   ⚠️  NOT FOUND: uv not installed (recommended for MCP)")
        print("   Install with: curl -LsSf https://astral.sh/uv/install.sh | sh")
        return False


def check_system():
    """Check system information."""
    print("\n💻 System Information:")
    print(f"   Platform: {platform.system()} {platform.release()}")
    print(f"   Machine: {platform.machine()}")
    print(f"   Python implementation: {platform.python_implementation()}")
    return True


def check_disk_space():
    """Check available disk space."""
    print("\n💾 Disk Space:")
    try:
        home = Path.home()
        stat = shutil.disk_usage(home)
        free_gb = stat.free / (1024**3)
        print(f"   Available: {free_gb:.2f} GB")
        
        if free_gb < 1:
            print("   ⚠️  WARNING: Less than 1 GB free space")
            return False
        else:
            print("   ✓ PASS: Sufficient disk space")
            return True
    except Exception as e:
        print(f"   ⚠️  WARNING: Could not check disk space: {e}")
        return True


def check_cursor_config_location():
    """Check if Cursor config directory exists."""
    print("\n📁 Cursor Configuration:")
    
    system = platform.system()
    if system == "Darwin":  # macOS
        cursor_dir = Path.home() / "Library" / "Application Support" / "Cursor"
    elif system == "Windows":
        cursor_dir = Path.home() / "AppData" / "Roaming" / "Cursor"
    else:  # Linux
        cursor_dir = Path.home() / ".config" / "Cursor"
    
    if cursor_dir.exists():
        print(f"   ✓ FOUND: {cursor_dir}")
        
        mcp_config = cursor_dir / "User" / "mcp.json"
        if mcp_config.exists():
            print(f"   ✓ mcp.json exists at {mcp_config}")
        else:
            print(f"   ℹ️  mcp.json not found (will need to create)")
            print(f"   Location: {mcp_config}")
        return True
    else:
        print(f"   ⚠️  Cursor directory not found: {cursor_dir}")
        print("   This is normal if using Claude Desktop instead")
        return False


def main():
    """Run all prerequisite checks."""
    print("=" * 60)
    print("ToolUniverse Installation Prerequisites Check")
    print("=" * 60)
    
    results = {
        "Python version": check_python_version(),
        "pip": check_pip(),
        "uv": check_uv(),
        "System": check_system(),
        "Disk space": check_disk_space(),
        "Cursor config": check_cursor_config_location(),
    }
    
    print("\n" + "=" * 60)
    print("Summary:")
    print("=" * 60)
    
    critical_checks = ["Python version", "pip"]
    all_critical_passed = all(results[check] for check in critical_checks)
    
    for check, passed in results.items():
        status = "✓" if passed else ("⚠️" if check not in critical_checks else "❌")
        print(f"{status} {check}")
    
    print("=" * 60)
    
    if all_critical_passed:
        print("\n✅ Ready to install ToolUniverse!")
        print("\nNext steps:")
        print("  1. Run: pip install tooluniverse")
        print("  2. Run: python scripts/verify_installation.py")
        return 0
    else:
        print("\n❌ Please fix critical issues before installing.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
