#!/usr/bin/env python3
"""Script that processes command-line arguments for testing python_script_runner."""

import sys
import argparse

def main():
    parser = argparse.ArgumentParser(description="Process data files")
    parser.add_argument("--input", help="Input file path")
    parser.add_argument("--output", help="Output file path")
    
    args = parser.parse_args()
    
    print(f"Processing data:")
    print(f"  Input: {args.input}")
    print(f"  Output: {args.output}")
    print("Processing complete!")

if __name__ == "__main__":
    main()
