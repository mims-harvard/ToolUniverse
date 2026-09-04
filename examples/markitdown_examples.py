#!/usr/bin/env python3
"""
MarkItDown Tools Examples

This script demonstrates basic usage of MarkItDown tools in ToolUniverse.

Prerequisites:
    pip install 'markitdown[audio-transcription,az-doc-intel,docx,outlook,pdf,pptx,xls,xlsx,youtube-transcription]'

Usage:
    python examples/markitdown_examples.py
"""

import os
import tempfile
import base64
from tooluniverse import ToolUniverse
from urllib.request import pathname2url


def example_1_basic_file_conversion():
    """Example 1: Convert a text file to Markdown."""
    # Initialize ToolUniverse and load MarkItDown tools
    tu = ToolUniverse()
    tu.load_tools(include_tool_types=["MarkItDownTool"])  # load MarkItDownTool
    # Create a sample text file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("""# Research Paper

## Abstract
This study investigates machine learning applications in drug discovery.

## Methods
- Data collection from ChEMBL database
- Deep learning model training
- Performance evaluation

## Results
Our model achieved 95% accuracy in drug-target prediction.

## Conclusion
Machine learning shows great promise in accelerating drug discovery.
""")
        file_path = f.name
    
    try:
        # Convert file to Markdown
        file_uri = f"file://{pathname2url(file_path)}"
        result = tu.run_one_function({
            "name": "convert_to_markdown",
            "arguments": {
                "uri": file_uri
            }
        })
        
        # Check if conversion was successful
        if result and not result.get("error"):
            # The converted Markdown content is in result["markdown_content"]
            markdown_content = result["markdown_content"]
            # Process the markdown content as needed
            return markdown_content
        else:
            print(f"Conversion failed: {result.get('error')}")
            return None
            
    finally:
        # Clean up temporary file
        os.unlink(file_path)


def example_2_save_to_file():
    """Example 2: Convert file and save to output file."""
    tu = ToolUniverse()
    tu.load_tools(include_tool_types=["MarkItDownTool"])  # load MarkItDownTool
    
    # Create sample HTML content
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
        f.write("""<!DOCTYPE html>
<html>
<head><title>Sample Document</title></head>
<body>
    <h1>Machine Learning in Healthcare</h1>
    <p>This document discusses <strong>AI applications</strong> in medical research.</p>
    <ul>
        <li>Drug discovery</li>
        <li>Medical imaging</li>
        <li>Patient diagnosis</li>
    </ul>
</body>
</html>""")
        input_file = f.name
    
    # Create output file path
    with tempfile.NamedTemporaryFile(suffix='.md', delete=False) as f:
        output_file = f.name
    
    try:
        # Convert and save to file
        file_uri = f"file://{pathname2url(input_file)}"
        result = tu.run_one_function({
            "name": "convert_to_markdown",
            "arguments": {
                "uri": file_uri,
                "output_path": output_file
            }
        })
        
        if result and not result.get("error"):
            # Read the saved file
            with open(output_file, 'r') as f:
                saved_content = f.read()
            return saved_content
        else:
            print(f"Conversion failed: {result.get('error')}")
            return None
            
    finally:
        # Clean up files
        for file_path in [input_file, output_file]:
            if os.path.exists(file_path):
                os.unlink(file_path)


def example_3_stream_conversion():
    """Example 3: Convert content from memory using stream conversion."""
    tu = ToolUniverse()
    tu.load_tools(include_tool_types=["MarkItDownTool"])  # load MarkItDownTool
    
    # Sample CSV data
    csv_data = """Name,Age,Department,Salary
Alice,28,Research,75000
Bob,35,Engineering,85000
Carol,42,Management,95000"""
    
    # Encode as base64
    csv_b64 = base64.b64encode(csv_data.encode()).decode()
    
    # Convert from memory
    data_uri = f"data:text/csv;base64,{csv_b64}"
    result = tu.run_one_function({
        "name": "convert_to_markdown",
        "arguments": {
            "uri": data_uri
        }
    })
    
    if result and not result.get("error"):
        # The converted content is in result["markdown_content"]
        return result["markdown_content"]
    else:
        print(f"Stream conversion failed: {result.get('error')}")
        return None


def example_4_list_plugins():
    """Example 4: List available MarkItDown plugins."""
    tu = ToolUniverse()
    tu.load_tools(include_tool_types=["MarkItDownTool"])  # load MarkItDownTool
    
    # List available plugins
    # MarkItDownTool does not expose plugin listing in this implementation
    result = {"success": False, "error": "Plugin listing not supported"}
    
    if result.get("success"):
        plugins = result.get("plugins", [])
        return plugins
    else:
        print(f"Plugin listing failed: {result.get('error')}")
        return []


def example_5_with_plugins():
    """Example 5: Convert file with plugins enabled."""
    tu = ToolUniverse()
    tu.load_tools(include_tool_types=["MarkItDownTool"])  # load MarkItDownTool
    
    # Create sample content
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write("""# Enhanced Document

This document uses **enhanced features** with plugins enabled.

## Features
- Plugin support
- Advanced processing
- Better formatting
""")
        file_path = f.name
    
    try:
        # Convert with plugins enabled
        file_uri = f"file://{pathname2url(file_path)}"
        result = tu.run_one_function({
            "name": "convert_to_markdown",
            "arguments": {
                "uri": file_uri,
                "enable_plugins": True
            }
        })
        
        if result and not result.get("error"):
            return result["markdown_content"]
        else:
            print(f"Plugin conversion failed: {result.get('error')}")
            return None
            
    finally:
        os.unlink(file_path)


def main():
    """Run all examples."""
    print("MarkItDown Tools Examples")
    print("=" * 40)
    
    # Example 1: Basic file conversion
    print("\n1. Basic file conversion:")
    content1 = example_1_basic_file_conversion()
    if content1:
        print("✅ Success - converted text file to Markdown")
    
    # Example 2: Save to file
    print("\n2. Save to file:")
    content2 = example_2_save_to_file()
    if content2:
        print("✅ Success - converted HTML and saved to file")
    
    # Example 3: Stream conversion
    print("\n3. Stream conversion:")
    content3 = example_3_stream_conversion()
    if content3:
        print("✅ Success - converted CSV from memory")
    
    # Example 4: List plugins
    print("\n4. List plugins:")
    plugins = example_4_list_plugins()
    if plugins:
        print(f"✅ Success - found {len(plugins)} plugin entries")
    
    # Example 5: With plugins
    print("\n5. With plugins:")
    content5 = example_5_with_plugins()
    if content5:
        print("✅ Success - converted with plugins enabled")
    
    print("\nAll examples completed!")


if __name__ == "__main__":
    main()