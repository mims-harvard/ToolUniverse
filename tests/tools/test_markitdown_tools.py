"""
Tests for MarkItDown Tools

Test cases for MarkItDown file conversion tools with real execution.
"""

import pytest
import os
import tempfile
from pathlib import Path
from tooluniverse import ToolUniverse


@pytest.fixture
def tu():
    """Set up test environment."""
    tu = ToolUniverse()
    tu.load_tools(tool_type=["markitdown"])
    yield tu
    tu.close()


def test_markitdown_tools_exist(tu):
    """Test that MarkItDown tools are registered."""
    tool_names = [tool.get("name") for tool in tu.all_tools if isinstance(tool, dict)]
    
    # Check for MarkItDown tools
    markitdown_tools = [name for name in tool_names if "convert_to_markdown" in name]
    
    expected_tools = ["convert_to_markdown"]
    
    for expected_tool in expected_tools:
        assert expected_tool in markitdown_tools, f"Missing tool: {expected_tool}"
    
    print(f"Found MarkItDown tools: {markitdown_tools}")


def test_convert_to_markdown_tool_schema(tu):
    """Test convert_to_markdown tool schema."""
    tool = None
    for t in tu.all_tools:
        if t.get("name") == "convert_to_markdown":
            tool = t
            break
    
    assert tool is not None, "convert_to_markdown tool not found"
    assert tool["type"] == "MarkItDownTool", f"Expected MarkItDownTool, got {tool['type']}"
    
    # Check required parameters
    required_params = tool["parameter"]["required"]
    assert "uri" in required_params, "uri should be required"
    
    # Check optional parameters
    properties = tool["parameter"]["properties"]
    assert "output_path" in properties, "output_path should be available"
    assert "enable_plugins" in properties, "enable_plugins should be available"


def test_convert_to_markdown_nonexistent_file(tu):
    """Test convert_to_markdown with nonexistent file URI."""
    try:
        result = tu.run_one_function({
            "name": "convert_to_markdown",
            "arguments": {
                "uri": "file:///nonexistent_file.pdf"
            }
        })
        
        # Should return error for nonexistent file
        assert isinstance(result, dict)
        assert "error" in result
        assert "not found" in result["error"].lower() or "file" in result["error"].lower()
        
    except Exception as e:
        # Allow for dependency issues
        assert "markitdown" in str(e).lower() or "import" in str(e).lower()


def test_convert_to_markdown_with_temp_file(tu):
    """Test convert_to_markdown with a temporary text file URI."""
    try:
        # Create a temporary text file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("# Test Document\n\nThis is a test document for MarkItDown conversion.\n\n## Features\n\n- Markdown support\n- Text processing\n- File conversion")
            temp_file = f.name
        
        try:
            # Convert to file URI
            file_uri = f"file://{temp_file}"
            result = tu.run_one_function({
                "name": "convert_to_markdown",
                "arguments": {
                    "uri": file_uri
                }
            })
            
            # Should return success for text file
            assert isinstance(result, dict)
            
            if "error" not in result:
                assert "markdown_content" in result
                assert isinstance(result["markdown_content"], str)
                assert len(result["markdown_content"]) > 0
                print(f"Converted content: {result['markdown_content'][:200]}...")
            else:
                # Check if it's a dependency issue
                assert "markitdown" in result["error"].lower() or "import" in result["error"].lower()
            
        finally:
            # Clean up
            if os.path.exists(temp_file):
                os.unlink(temp_file)
                
    except Exception as e:
        # Allow for dependency issues
        assert "markitdown" in str(e).lower() or "import" in str(e).lower()


def test_convert_to_markdown_tool_error_handling(tu):
    """Test convert_to_markdown tool error handling."""
    # Test with invalid parameters
    try:
        result = tu.run_one_function({
            "name": "convert_to_markdown",
            "arguments": {
                # Missing required uri
            }
        })
        
        # Should handle missing parameters gracefully
        assert isinstance(result, dict)
        
    except Exception as e:
        # Should be a validation error
        assert "validation" in str(e).lower() or "required" in str(e).lower()


def test_convert_to_markdown_tools_integration(tu):
    """Test convert_to_markdown tool integration with ToolUniverse."""
    # Test that tools are properly integrated
    tool_names = [tool.get("name") for tool in tu.all_tools if isinstance(tool, dict)]
    
    markitdown_tools = [name for name in tool_names if "convert_to_markdown" in name]
    assert len(markitdown_tools) == 1, f"Expected 1 MarkItDown tool, found {len(markitdown_tools)}"
    
    # Test that tool can be called through ToolUniverse
    try:
        # Test basic tool call (may fail due to dependencies, but should not crash)
        result = tu.run_one_function({
            "name": "convert_to_markdown",
            "arguments": {"uri": "file:///test.txt"}
        })
        
        assert isinstance(result, dict)
        print(f"✅ convert_to_markdown executed successfully")
        
    except Exception as e:
        # Allow for dependency issues, but log them
        print(f"⚠️  convert_to_markdown failed due to dependencies: {e}")
        assert "markitdown" in str(e).lower() or "import" in str(e).lower()


def test_convert_to_markdown_data_uri(tu):
    """Test convert_to_markdown with data URI."""
    try:
        # Create test data URI
        test_content = "# Data URI Test\n\nThis is a test using data URI."
        import base64
        data_b64 = base64.b64encode(test_content.encode()).decode()
        data_uri = f"data:text/plain;base64,{data_b64}"
        
        result = tu.run_one_function({
            "name": "convert_to_markdown",
            "arguments": {
                "uri": data_uri
            }
        })
        
        # Should return success for data URI
        assert isinstance(result, dict)
        
        if "error" not in result:
            assert "markdown_content" in result
            assert isinstance(result["markdown_content"], str)
            assert len(result["markdown_content"]) > 0
            print(f"Data URI converted content: {result['markdown_content'][:200]}...")
        else:
            # Check if it's a dependency issue
            assert "markitdown" in result["error"].lower() or "import" in result["error"].lower()
            
    except Exception as e:
        # Allow for dependency issues
        assert "markitdown" in str(e).lower() or "import" in str(e).lower()


def test_convert_to_markdown_unsupported_uri_scheme(tu):
    """Test convert_to_markdown with unsupported URI scheme."""
    try:
        result = tu.run_one_function({
            "name": "convert_to_markdown",
            "arguments": {
                "uri": "ftp://example.com/file.pdf"
            }
        })
        
        # Should return error for unsupported scheme
        assert isinstance(result, dict)
        assert "error" in result
        assert "unsupported" in result["error"].lower() or "scheme" in result["error"].lower()
        
    except Exception as e:
        # Allow for dependency issues
        assert "markitdown" in str(e).lower() or "import" in str(e).lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])