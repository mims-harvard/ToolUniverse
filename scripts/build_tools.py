#!/usr/bin/env python3
"""Build ToolUniverse tools."""
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def main():
    from tooluniverse.generate_tools import main as generate
    
    parser = argparse.ArgumentParser(
        description="Build ToolUniverse tools",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/build_tools.py              # Normal build (only changed tools)
  python scripts/build_tools.py --force      # Force regenerate all tools
  python scripts/build_tools.py --verbose    # Show detailed change information
  python scripts/build_tools.py --force -v   # Force rebuild with verbose output
        """
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force regeneration of all tools regardless of changes detected",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print detailed change information for each tool",
    )
    parser.add_argument(
        "--no-format",
        action="store_true",
        help="Skip formatting generated files",
    )
    
    args = parser.parse_args()
    
    print("🔧 Building ToolUniverse tools...")
    generate(
        format_enabled=not args.no_format,
        force_regenerate=args.force,
        verbose=args.verbose
    )
    print("✅ Build complete!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
