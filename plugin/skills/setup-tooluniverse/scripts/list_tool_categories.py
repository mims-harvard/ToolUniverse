#!/usr/bin/env python3
"""
List all available ToolUniverse tool categories.

Shows categories with tool counts to help users choose which to load.
"""

import sys


def list_categories():
    """List all tool categories with counts."""
    print("=" * 60)
    print("ToolUniverse Tool Categories")
    print("=" * 60)
    
    try:
        from tooluniverse import ToolUniverse
        
        print("\nLoading ToolUniverse...")
        tu = ToolUniverse()
        tu.load_tools()
        
        # Group tools by category
        categories = {}
        for tool_name, tool_info in tu.tools.items():
            # Extract category from tool name (usually prefix before first underscore)
            parts = tool_name.split('_')
            if len(parts) > 1:
                category = parts[0]
            else:
                category = "uncategorized"
            
            if category not in categories:
                categories[category] = []
            categories[category].append(tool_name)
        
        # Sort by tool count (descending)
        sorted_categories = sorted(
            categories.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )
        
        print(f"\nTotal categories: {len(categories)}")
        print(f"Total tools: {len(tu.tools)}")
        print("\n" + "-" * 60)
        print(f"{'Category':<30} {'Tool Count':>10}")
        print("-" * 60)
        
        for category, tools in sorted_categories:
            print(f"{category:<30} {len(tools):>10}")
        
        print("-" * 60)
        
        # Show usage examples
        print("\n📋 Usage Examples:")
        print("-" * 60)
        
        # Get top 5 categories
        top_categories = [cat for cat, _ in sorted_categories[:5]]
        
        print("\n1. Load specific categories:")
        print(f'   --categories {" ".join(top_categories[:3])}')
        
        print("\n2. Load all except specific:")
        print(f'   --exclude-categories {" ".join(top_categories[:2])}')
        
        print("\n3. Use compact mode (recommended):")
        print('   --compact-mode')
        
        print("\n💡 Recommendation:")
        print("   Use --compact-mode to avoid context window overflow.")
        print("   This exposes 5 core tools while keeping all 764+ tools")
        print("   accessible via execute_tool.")
        
        return 0
        
    except ImportError:
        print("\n❌ ToolUniverse not installed")
        print("Install with: pip install tooluniverse")
        return 1
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1


def main():
    """Main entry point."""
    return list_categories()


if __name__ == "__main__":
    sys.exit(main())
