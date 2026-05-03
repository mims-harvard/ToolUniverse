#!/usr/bin/env python3
"""
Wikipedia tools example for ToolUniverse.

This example demonstrates how to use Wikipedia tools to search and
extract content from Wikipedia articles.
"""

import sys
from pathlib import Path

from tooluniverse import ToolUniverse


def main():
    """Run Wikipedia tools examples."""
    # Initialize ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()
    
    print("=" * 60)
    print("Wikipedia Tools Example")
    print("=" * 60)
    
    # Example 1: Search Wikipedia
    print("\n1. Searching Wikipedia for 'artificial intelligence'...")
    result = tu.run({
        "name": "Wikipedia_search",
        "arguments": {
            "query": "artificial intelligence",
            "limit": 3,
            "language": "en"
        }
    })
    print(result)
    
    # Example 2: Get article content (intro)
    print("\n2. Getting introduction from 'Artificial intelligence' article...")
    result = tu.run({
        "name": "Wikipedia_get_content",
        "arguments": {
            "title": "Artificial intelligence",
            "extract_type": "intro",
            "max_chars": 500,
            "language": "en"
        }
    })
    print(result)
    
    # Example 3: Get article summary
    print("\n3. Getting summary from 'Renaissance' article...")
    result = tu.run({
        "name": "Wikipedia_get_summary",
        "arguments": {
            "title": "Renaissance",
            "max_chars": 300,
            "language": "en"
        }
    })
    print(result)
    
    # Example 4: Get full summary
    print("\n4. Getting summary from 'Machine learning' article...")
    result = tu.run({
        "name": "Wikipedia_get_content",
        "arguments": {
            "title": "Machine learning",
            "extract_type": "summary",
            "max_chars": 1000,
            "language": "en"
        }
    })
    print(result)
    
    # Example 5: Search in different language
    print("\n5. Searching Chinese Wikipedia for '量子计算'...")
    result = tu.run({
        "name": "Wikipedia_search",
        "arguments": {
            "query": "量子计算",
            "limit": 2,
            "language": "zh"
        }
    })
    print(result)


if __name__ == "__main__":
    main()

