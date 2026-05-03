#!/usr/bin/env python3
"""Script that uses environment variables for testing python_script_runner."""

import os

def main():
    debug = os.environ.get("DEBUG", "false")
    log_level = os.environ.get("LOG_LEVEL", "info")
    
    print(f"Configuration:")
    print(f"  DEBUG: {debug}")
    print(f"  LOG_LEVEL: {log_level}")
    print("Script executed with environment configuration!")

if __name__ == "__main__":
    main()
