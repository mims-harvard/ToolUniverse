#!/usr/bin/env python3
"""
Advanced Local Tool Example

This example demonstrates advanced features of local tools including:
- Parameter validation
- Custom error handling
- Complex data processing
- Multiple tool methods

Usage:
    python advanced_tool.py
"""

import sys
import os
import json
import math
from typing import Dict, Any, List, Optional

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from tooluniverse.tool_registry import register_tool
from tooluniverse.base_tool import BaseTool
from tooluniverse import ToolUniverse

# =============================================================================
# ADVANCED TOOL DEFINITIONS
# =============================================================================

@register_tool('DataProcessorTool', config={
    "name": "data_processor_tool",
    "type": "DataProcessorTool",
    "description": "Process and analyze data with validation and error handling",
    "parameter": {
        "type": "object",
        "properties": {
            "data": {
                "type": "array",
                "description": "List of numbers to process",
                "items": {"type": "number"}
            },
            "operation": {
                "type": "string",
                "enum": ["mean", "median", "std", "min", "max", "sum", "count"],
                "description": "Statistical operation to perform"
            },
            "format_output": {
                "type": "boolean",
                "default": True,
                "description": "Whether to format the output nicely"
            }
        },
        "required": ["data", "operation"]
    }
})
class DataProcessorTool(BaseTool):
    """Advanced tool for data processing with validation and error handling."""
    
    def validate_parameters(self, arguments: Dict[str, Any]) -> Optional[str]:
        """Custom parameter validation."""
        if not isinstance(arguments, dict):
            return "Arguments must be a dictionary"
        
        data = arguments.get('data')
        operation = arguments.get('operation')
        
        if not isinstance(data, list):
            return "Data must be a list"
        
        if not data:
            return "Data list cannot be empty"
        
        if not all(isinstance(x, (int, float)) for x in data):
            return "All data items must be numbers"
        
        if operation not in ["mean", "median", "std", "min", "max", "sum", "count"]:
            return f"Invalid operation: {operation}"
        
        return None  # No errors
    
    def handle_error(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """Custom error handling."""
        return {
            "result": None,
            "error": f"Data processing error: {str(error)}",
            "context": context,
            "success": False
        }
    
    def run(self, arguments: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Execute data processing operation."""
        try:
            # Validate parameters
            validation_error = self.validate_parameters(arguments)
            if validation_error:
                return {
                    "result": None,
                    "error": validation_error,
                    "success": False
                }
            
            data = arguments['data']
            operation = arguments['operation']
            format_output = arguments.get('format_output', True)
            
            # Perform the operation
            if operation == "mean":
                result = sum(data) / len(data)
            elif operation == "median":
                sorted_data = sorted(data)
                n = len(sorted_data)
                if n % 2 == 0:
                    result = (sorted_data[n//2-1] + sorted_data[n//2]) / 2
                else:
                    result = sorted_data[n//2]
            elif operation == "std":
                mean = sum(data) / len(data)
                variance = sum((x - mean) ** 2 for x in data) / len(data)
                result = math.sqrt(variance)
            elif operation == "min":
                result = min(data)
            elif operation == "max":
                result = max(data)
            elif operation == "sum":
                result = sum(data)
            elif operation == "count":
                result = len(data)
            
            # Format output
            if format_output:
                if isinstance(result, float):
                    result = round(result, 4)
            
            return {
                "result": result,
                "operation": operation,
                "data_length": len(data),
                "formatted": format_output,
                "success": True
            }
            
        except Exception as e:
            return self.handle_error(e, {"arguments": arguments})

@register_tool('TextAnalyzerTool', config={
    "name": "text_analyzer_tool",
    "type": "TextAnalyzerTool",
    "description": "Analyze text content with various metrics",
    "parameter": {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "Text to analyze"
            },
            "metrics": {
                "type": "array",
                "description": "Metrics to calculate",
                "items": {
                    "type": "string",
                    "enum": ["word_count", "char_count", "sentence_count", "avg_word_length", "unique_words"]
                },
                "default": ["word_count", "char_count"]
            },
            "case_sensitive": {
                "type": "boolean",
                "default": False,
                "description": "Whether to consider case when counting unique words"
            }
        },
        "required": ["text"]
    }
})
class TextAnalyzerTool(BaseTool):
    """Tool for analyzing text content."""
    
    def run(self, arguments: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Execute text analysis."""
        try:
            text = arguments.get('text', '')
            metrics = arguments.get('metrics', ['word_count', 'char_count'])
            case_sensitive = arguments.get('case_sensitive', False)
            
            if not text:
                return {
                    "result": {},
                    "error": "Text cannot be empty",
                    "success": False
                }
            
            results = {}
            
            if "word_count" in metrics:
                words = text.split()
                results["word_count"] = len(words)
            
            if "char_count" in metrics:
                results["char_count"] = len(text)
            
            if "sentence_count" in metrics:
                sentences = [s.strip() for s in text.split('.') if s.strip()]
                results["sentence_count"] = len(sentences)
            
            if "avg_word_length" in metrics:
                words = text.split()
                if words:
                    avg_length = sum(len(word) for word in words) / len(words)
                    results["avg_word_length"] = round(avg_length, 2)
                else:
                    results["avg_word_length"] = 0
            
            if "unique_words" in metrics:
                words = text.split()
                if case_sensitive:
                    unique_words = set(words)
                else:
                    unique_words = set(word.lower() for word in words)
                results["unique_words"] = len(unique_words)
            
            return {
                "result": results,
                "text_preview": text[:100] + "..." if len(text) > 100 else text,
                "metrics_calculated": metrics,
                "case_sensitive": case_sensitive,
                "success": True
            }
            
        except Exception as e:
            return {
                "result": {},
                "error": f"Text analysis error: {str(e)}",
                "success": False
            }

@register_tool('FileProcessorTool', config={
    "name": "file_processor_tool",
    "type": "FileProcessorTool",
    "description": "Process files with various operations",
    "parameter": {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["read", "write", "append", "info"],
                "description": "File operation to perform"
            },
            "filename": {
                "type": "string",
                "description": "Name of the file"
            },
            "content": {
                "type": "string",
                "description": "Content to write (for write/append operations)"
            },
            "encoding": {
                "type": "string",
                "default": "utf-8",
                "description": "File encoding"
            }
        },
        "required": ["operation", "filename"]
    }
})
class FileProcessorTool(BaseTool):
    """Tool for file operations."""
    
    def run(self, arguments: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Execute file operation."""
        try:
            operation = arguments.get('operation')
            filename = arguments.get('filename')
            content = arguments.get('content', '')
            encoding = arguments.get('encoding', 'utf-8')
            
            if operation == "read":
                with open(filename, 'r', encoding=encoding) as f:
                    file_content = f.read()
                return {
                    "result": file_content,
                    "operation": "read",
                    "filename": filename,
                    "file_size": len(file_content),
                    "success": True
                }
            
            elif operation == "write":
                with open(filename, 'w', encoding=encoding) as f:
                    f.write(content)
                return {
                    "result": f"Written {len(content)} characters to {filename}",
                    "operation": "write",
                    "filename": filename,
                    "content_length": len(content),
                    "success": True
                }
            
            elif operation == "append":
                with open(filename, 'a', encoding=encoding) as f:
                    f.write(content)
                return {
                    "result": f"Appended {len(content)} characters to {filename}",
                    "operation": "append",
                    "filename": filename,
                    "content_length": len(content),
                    "success": True
                }
            
            elif operation == "info":
                if os.path.exists(filename):
                    stat = os.stat(filename)
                    return {
                        "result": {
                            "exists": True,
                            "size": stat.st_size,
                            "modified": stat.st_mtime
                        },
                        "operation": "info",
                        "filename": filename,
                        "success": True
                    }
                else:
                    return {
                        "result": {"exists": False},
                        "operation": "info",
                        "filename": filename,
                        "success": True
                    }
            
            else:
                return {
                    "result": None,
                    "error": f"Unknown operation: {operation}",
                    "success": False
                }
                
        except Exception as e:
            return {
                "result": None,
                "error": f"File operation error: {str(e)}",
                "success": False
            }

# =============================================================================
# TESTING FUNCTIONS
# =============================================================================

def run_test_advanced_tools(tu):
    """Test advanced tool functionality."""
    
    print("🧪 Testing Advanced Tools")
    print("=" * 30)
    
    # Test DataProcessorTool
    print("\n1. Testing DataProcessorTool:")
    test_cases = [
        {
            "data": [1, 2, 3, 4, 5],
            "operation": "mean",
            "format_output": True
        },
        {
            "data": [10, 20, 30, 40, 50],
            "operation": "std",
            "format_output": True
        },
        {
            "data": [1, 2, 3, 4, 5, 6],
            "operation": "median",
            "format_output": True
        },
        {
            "data": [],  # Error case
            "operation": "mean",
            "format_output": True
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        try:
            result = tu.run({
                "name": "data_processor_tool",
                "arguments": test_case
            })
            print(f"   Test {i}: {result}")
            if result.get("success") or "error" in result:
                print(f"   ✅ DataProcessorTool test {i} works")
            else:
                print(f"   ❌ DataProcessorTool test {i} failed")
        except Exception as e:
            print(f"   ❌ DataProcessorTool test {i} error: {e}")
    
    # Test TextAnalyzerTool
    print("\n2. Testing TextAnalyzerTool:")
    text_tests = [
        {
            "text": "Hello world! This is a test sentence.",
            "metrics": ["word_count", "char_count", "sentence_count"],
            "case_sensitive": False
        },
        {
            "text": "The quick brown fox jumps over the lazy dog.",
            "metrics": ["unique_words", "avg_word_length"],
            "case_sensitive": True
        }
    ]
    
    for i, test_case in enumerate(text_tests, 1):
        try:
            result = tu.run({
                "name": "text_analyzer_tool",
                "arguments": test_case
            })
            print(f"   Test {i}: {result}")
            if result.get("success"):
                print(f"   ✅ TextAnalyzerTool test {i} works")
            else:
                print(f"   ❌ TextAnalyzerTool test {i} failed")
        except Exception as e:
            print(f"   ❌ TextAnalyzerTool test {i} error: {e}")
    
    # Test FileProcessorTool
    print("\n3. Testing FileProcessorTool:")
    test_filename = "test_file.txt"
    test_content = "This is a test file content.\nLine 2.\nLine 3."
    
    try:
        # Write test file
        result = tu.run({
            "name": "file_processor_tool",
            "arguments": {
                "operation": "write",
                "filename": test_filename,
                "content": test_content
            }
        })
        print(f"   Write test: {result}")
        
        # Read test file
        result = tu.run({
            "name": "file_processor_tool",
            "arguments": {
                "operation": "read",
                "filename": test_filename
            }
        })
        print(f"   Read test: {result}")
        
        # Get file info
        result = tu.run({
            "name": "file_processor_tool",
            "arguments": {
                "operation": "info",
                "filename": test_filename
            }
        })
        print(f"   Info test: {result}")
        
        # Clean up
        if os.path.exists(test_filename):
            os.remove(test_filename)
            print("   🧹 Cleaned up test file")
        
        print("   ✅ FileProcessorTool tests completed")
        
    except Exception as e:
        print(f"   ❌ FileProcessorTool error: {e}")

def run_test_direct_access(tu):
    """Test direct tool access."""
    
    print("\n🔧 Testing Direct Access")
    print("=" * 25)
    
    try:
        # Test direct access
        result = tu.tools.data_processor_tool(
            data=[1, 2, 3, 4, 5],
            operation="mean"
        )
        print(f"Direct data_processor_tool(): {result}")
        
        result = tu.tools.text_analyzer_tool(
            text="Hello world!",
            metrics=["word_count", "char_count"]
        )
        print(f"Direct text_analyzer_tool(): {result}")
        
        print("✅ Direct access works")
        
    except Exception as e:
        print(f"❌ Direct access failed: {e}")

# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """Main function to demonstrate advanced local tools."""
    
    print("🚀 Advanced Local Tools Example")
    print("=" * 40)
    
    try:
        # Initialize ToolUniverse
        print("\n📦 Initializing ToolUniverse...")
        tu = ToolUniverse()
        
        # Load tools
        print("🔄 Loading tools...")
        tu.load_tools()
        
        print(f"✅ Loaded {len(tu.all_tools)} tools")
        
        # Check if our tools are available
        expected_tools = ["data_processor_tool", "text_analyzer_tool", "file_processor_tool"]
        available_tools = list(tu.all_tool_dict.keys())
        
        print(f"\n📋 Available tools: {available_tools}")
        
        for tool_name in expected_tools:
            if tool_name in available_tools:
                print(f"✅ {tool_name} is available")
            else:
                print(f"❌ {tool_name} not found")
        
        # Run tests
        run_test_advanced_tools(tu)
        run_test_direct_access(tu)
        
        print("\n🎉 Advanced local tools example completed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up
        if 'tu' in locals():
            tu.close()

if __name__ == "__main__":
    main()
