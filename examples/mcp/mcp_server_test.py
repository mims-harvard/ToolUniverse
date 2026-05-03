#!/usr/bin/env python3
# Import generated MCP wrapper
import sys
import os
sys.path.append(os.path.dirname(__file__))

# Read generated code and execute
with open("mcp_wrappers_generated.txt", "r") as f:
    generated_code = f.read()

# Execute generated code
exec(generated_code)

# Start server
if __name__ == "__main__":
    print("🚀 Starting ToolUniverse MCP server...")
    print(f"Server address: http://127.0.0.1:8000")
    print("Press Ctrl+C to stop server")
    run_server()
