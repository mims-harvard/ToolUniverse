#!/usr/bin/env python3
"""
EMDB Cryo-EM Structure Database Example

This example shows how to use the EMDB tool to query cryo-electron microscopy
structures from the Electron Microscopy Data Bank.
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
    
    print("🔬 EMDB Cryo-EM Structure Database Examples")
    print("=" * 45)
    
    # Example 1: Query specific EMDB structure
    print("\n1. Querying EMDB structure EMD-1234")
    print("-" * 35)
    
    result = tu.run({"name": "EMDB_get_structure", "arguments": {
        "emdb_id": "EMD-1234"
    }})
    
    if result and result.get("status") == "success":
        data = result.get("data", {})
        print(f"✅ Retrieved structure information")
        
        title = data.get("title", "Unknown")
        resolution = data.get("resolution", "Unknown")
        print(f"   Title: {title}")
        print(f"   Resolution: {resolution}")
    else:
        print(f"❌ Error: {result.get('error')}")
    
    # Example 2: Query another EMDB structure
    print("\n2. Querying EMDB structure EMD-0001")
    print("-" * 35)
    
    result = tu.run({"name": "EMDB_get_structure", "arguments": {
        "emdb_id": "EMD-0001"
    }})
    
    if result and result.get("status") == "success":
        data = result.get("data", {})
        print(f"✅ Retrieved structure information")
        
        title = data.get("title", "Unknown")
        resolution = data.get("resolution", "Unknown")
        print(f"   Title: {title}")
        print(f"   Resolution: {resolution}")
    else:
        print(f"❌ Error: {result.get('error')}")
    
    # Example 3: Query with different EMDB ID
    print("\n3. Querying EMDB structure EMD-1000")
    print("-" * 35)
    
    result = tu.run({"name": "EMDB_get_structure", "arguments": {
        "emdb_id": "EMD-1000"
    }})
    
    if result and result.get("status") == "success":
        data = result.get("data", {})
        print(f"✅ Retrieved structure information")
        
        title = data.get("title", "Unknown")
        resolution = data.get("resolution", "Unknown")
        method = data.get("method", "Unknown")
        print(f"   Title: {title}")
        print(f"   Resolution: {resolution}")
        print(f"   Method: {method}")
    else:
        print(f"❌ Error: {result.get('error')}")

if __name__ == "__main__":
    main()
