"""
Utility to validate ToolUniverse tool name lengths.

This script loads tools via ToolUniverse and checks that every tool name
is at most MAX_LEN characters (default: 64). It prints a concise report
and returns a non-zero exit code if any violations are found.
"""

from __future__ import annotations

import argparse
import sys
from typing import List, Tuple


def check_tool_name_lengths(max_len: int = 64) -> Tuple[List[str], List[str]]:
    """
    Load all tools via ToolUniverse and check their name lengths.

    Returns a tuple of (valid_names, invalid_names) where invalid_names are
    those exceeding max_len.
    """
    # Import locally to avoid import overhead when used as a library
    from tooluniverse import ToolUniverse

    tool_universe = ToolUniverse()
    # Load all built-in/configured tools
    tool_universe.load_tools()

    # Retrieve only names for efficient scanning
    tool_names = tool_universe.get_available_tools(name_only=True)

    valid: List[str] = []
    invalid: List[str] = []

    for name in tool_names:
        if len(name) <= max_len:
            valid.append(name)
        else:
            invalid.append(name)

    return valid, invalid


def check_tool_name_lengths_with_shortening(max_len: int = 55) -> Tuple[int, int, List[Tuple[str, str, int]]]:
    """
    Check tool names with automatic shortening enabled.
    Validates that all shortened names fit within max_len.
    
    Returns:
        Tuple of (total_tools, shortened_count, invalid_tools)
        where invalid_tools is a list of (original, shortened, length) tuples
        for tools that still exceed max_len after shortening.
    """
    from tooluniverse import ToolUniverse
    from tooluniverse.tool_name_utils import ToolNameMapper
    
    tu = ToolUniverse()
    tu.load_tools()
    
    # Enable name shortening
    tu.enable_name_shortening(max_length=max_len)
    
    tool_names = tu.get_available_tools(name_only=True, shortened=False)  # Get original names
    
    shortened_count = 0
    invalid_tools = []
    
    for original_name in tool_names:
        shortened = tu.get_tool_name(original_name, shorten=True)
        
        if shortened != original_name:
            shortened_count += 1
        
        if len(shortened) > max_len:
            invalid_tools.append((original_name, shortened, len(shortened)))
    
    return len(tool_names), shortened_count, invalid_tools


def _format_report(valid: List[str], invalid: List[str], max_len: int) -> str:
    lines: List[str] = []
    lines.append(f"Max allowed length: {max_len}")
    lines.append(f"Total tools scanned: {len(valid) + len(invalid)}")
    lines.append(f"Valid (≤{max_len}): {len(valid)}")
    lines.append(f"Invalid (>{max_len}): {len(invalid)}")
    if invalid:
        lines.append("")
        lines.append("Invalid tool names:")
        for name in sorted(invalid):
            lines.append(f"  - {name} ({len(name)} chars)")
    return "\n".join(lines)


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate ToolUniverse tool name lengths",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--max-len",
        type=int,
        default=64,
        help="Maximum allowed tool name length",
    )
    parser.add_argument(
        "--test-shortening",
        action="store_true",
        help="Test with automatic name shortening enabled (for MCP compatibility)",
    )
    parser.add_argument(
        "--shortening-max-len",
        type=int,
        default=55,
        help="Maximum length for shortened names (default: 55 for mcp__tu__ prefix)",
    )
    args = parser.parse_args(argv)

    if args.test_shortening:
        # Test with shortening enabled
        total, shortened_count, invalid = check_tool_name_lengths_with_shortening(
            max_len=args.shortening_max_len
        )
        
        print(f"Testing with automatic name shortening enabled")
        print(f"Max allowed length: {args.shortening_max_len}")
        print(f"Total tools scanned: {total}")
        print(f"Tools shortened: {shortened_count}")
        print(f"Valid after shortening: {total - len(invalid)}")
        print(f"Still invalid: {len(invalid)}")
        
        if invalid:
            print("\nTools still exceeding limit after shortening:")
            for orig, short, length in sorted(invalid, key=lambda x: x[2], reverse=True):
                print(f"  - {orig}")
                print(f"    → {short} ({length} chars)")
        else:
            print("\n✅ All tools fit within limit after shortening!")
        
        return 1 if invalid else 0
    else:
        # Test without shortening (original behavior)
        valid, invalid = check_tool_name_lengths(max_len=args.max_len)
        report = _format_report(valid, invalid, args.max_len)
        print(report)
        
        # Non-zero exit when violations are present (useful in CI)
        return 1 if invalid else 0


if __name__ == "__main__":
    sys.exit(main())


