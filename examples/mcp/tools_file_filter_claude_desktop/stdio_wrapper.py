#!/usr/bin/env python
"""
STDIO wrapper for SMCP server integration with Claude Desktop.

This wrapper filters stdout logs, sending only JSON messages to stdout
for the MCP client, while redirecting all other output to stderr.
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """Run SMCP server with STDIO wrapper."""
    
    # Get tools file path (relative to this script)
    tools_file = Path(__file__).parent / "tools_short.txt"
    
    # Setup environment
    env = os.environ.copy()
    env.setdefault("PYTHONWARNINGS", "ignore")
    env.setdefault("FASTMCP_NO_BANNER", "1")
    
    # Build command
    cmd = [
        sys.executable,
        "-m", "tooluniverse.smcp_server",
        "--transport", "stdio",
        "--tools-file", str(tools_file),
    ]
    
    # Run subprocess with filtered output
    p = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=sys.stderr,
        text=True,
        bufsize=1,
        env=env
    )
    
    # Filter output: JSON goes to stdout, everything else to stderr
    for line in p.stdout:
        if line.lstrip().startswith(("{", "[")):
            sys.stdout.write(line)
            sys.stdout.flush()
        else:
            sys.stderr.write(line)
            sys.stderr.flush()
    
    p.wait()
    sys.exit(p.returncode)


if __name__ == "__main__":
    main()

