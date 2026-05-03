#!/usr/bin/env python
"""
STDIO wrapper for SMCP server with compact mode.

This wrapper runs the SMCP server in compact mode via STDIO transport,
filtering stdout logs to stderr, keeping only JSON messages on stdout
for the MCP client (e.g., Claude Desktop).

Compact mode only exposes 4 core tools instead of 1000+ tools,
significantly reducing context window usage while maintaining full
functionality through search and execute capabilities.
"""

import os
import sys
import subprocess
from pathlib import Path


def main():
    """Run SMCP server with compact mode in STDIO mode."""
    
    # Setup environment
    env = os.environ.copy()
    env.setdefault("PYTHONWARNINGS", "ignore")
    env.setdefault("FASTMCP_NO_BANNER", "1")
    
    # Build command with compact mode enabled
    cmd = [
        sys.executable,
        "-m", "tooluniverse.smcp_server",
        "--transport", "stdio",
        "--compact-mode",  # Enable compact mode
    ]
    
    # Run subprocess with filtered output
    # JSON messages go to stdout, logs go to stderr
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
            # JSON message - send to stdout for MCP client
            sys.stdout.write(line)
            sys.stdout.flush()
        else:
            # Log message - send to stderr
            sys.stderr.write(line)
            sys.stderr.flush()
    
    p.wait()
    sys.exit(p.returncode)


if __name__ == "__main__":
    main()

