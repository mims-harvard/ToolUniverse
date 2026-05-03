#!/usr/bin/env python3
"""
GtoPdb Pharmacology Database Example

This example shows how to use the GtoPdb tool to query drug targets
and pharmacological information from the Guide to Pharmacology database.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.tooluniverse import ToolUniverse

def main():
    # Initialize ToolUniverse
    tu = ToolUniverse()
    
    # Load tools first
    tu.load_tools()
    
    print("💊 GtoPdb Pharmacology Database Examples")
    print("=" * 40)
    
    # Example 1: Query drug targets
    print("\n1. Querying drug targets")
    print("-" * 25)
    
    result = tu.run({"name": "GtoPdb_get_targets", "arguments": {
        "limit": 5
    }})
    
    if result and result.get("status") == "success":
        data = result.get("data", [])
        print(f"✅ Found {len(data)} drug targets")
        
        for i, target in enumerate(data[:3], 1):
            name = target.get("name", "Unknown")
            target_id = target.get("targetId", "Unknown")
            print(f"   {i}. {name} (ID: {target_id})")
    else:
        print(f"❌ Error: {result.get('error')}")
    
    # Example 2: Query specific target types
    print("\n2. Querying specific target types")
    print("-" * 30)
    
    result = tu.run({"name": "GtoPdb_get_targets", "arguments": {
        "limit": 8
    }})
    
    if result and result.get("status") == "success":
        data = result.get("data", [])
        print(f"✅ Found {len(data)} drug targets")
        
        # Show different target types
        for i, target in enumerate(data[:4], 1):
            name = target.get("name", "Unknown")
            target_id = target.get("targetId", "Unknown")
            target_type = target.get("targetType", "Unknown")
            print(f"   {i}. {name} ({target_type}) - {target_id}")
    else:
        print(f"❌ Error: {result.get('error')}")
    
    # Example 3: Query with different limits
    print("\n3. Querying with different limits")
    print("-" * 30)
    
    result = tu.run({"name": "GtoPdb_get_targets", "arguments": {
        "limit": 3
    }})
    
    if result and result.get("status") == "success":
        data = result.get("data", [])
        print(f"✅ Found {len(data)} drug targets")
        
        for i, target in enumerate(data, 1):
            name = target.get("name", "Unknown")
            target_id = target.get("targetId", "Unknown")
            print(f"   {i}. {name} - {target_id}")

if __name__ == "__main__":
    main()
