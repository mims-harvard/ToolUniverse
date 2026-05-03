#!/usr/bin/env python3
"""
Data Processing Tool Example

This example shows how to create tools for data analysis and processing.
It demonstrates real-world data processing scenarios with ToolUniverse.

Usage:
    python data_processing_tool.py
"""

import sys
import os
import json
import csv
import math
from typing import Dict, Any, List, Optional

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from tooluniverse.tool_registry import register_tool
from tooluniverse.base_tool import BaseTool
from tooluniverse import ToolUniverse

# =============================================================================
# DATA PROCESSING TOOL DEFINITIONS
# =============================================================================

@register_tool('CSVProcessorTool', config={
    "name": "csv_processor_tool",
    "description": "Process CSV files with various operations",
    "parameter": {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["read", "write", "analyze", "filter", "transform"],
                "description": "CSV operation to perform"
            },
            "filename": {
                "type": "string",
                "description": "CSV file path"
            },
            "data": {
                "type": "array",
                "description": "Data to write (for write operation)",
                "items": {"type": "object"}
            },
            "filter_column": {
                "type": "string",
                "description": "Column to filter by (for filter operation)"
            },
            "filter_value": {
                "type": "string",
                "description": "Value to filter by (for filter operation)"
            },
            "transform_operation": {
                "type": "string",
                "enum": ["uppercase", "lowercase", "add_prefix", "add_suffix"],
                "description": "Transformation to apply (for transform operation)"
            },
            "transform_column": {
                "type": "string",
                "description": "Column to transform (for transform operation)"
            },
            "transform_value": {
                "type": "string",
                "description": "Value to add (for add_prefix/add_suffix operations)"
            }
        },
        "required": ["operation", "filename"]
    }
})
class CSVProcessorTool(BaseTool):
    """Tool for processing CSV files."""
    
    def run(self, arguments: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Execute CSV processing operation."""
        try:
            operation = arguments.get('operation')
            filename = arguments.get('filename')
            
            if operation == "read":
                data = []
                with open(filename, 'r', newline='', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        data.append(row)
                
                return {
                    "result": data,
                    "operation": "read",
                    "filename": filename,
                    "row_count": len(data),
                    "columns": list(data[0].keys()) if data else [],
                    "success": True
                }
            
            elif operation == "write":
                data = arguments.get('data', [])
                if not data:
                    return {
                        "result": None,
                        "error": "No data provided for write operation",
                        "success": False
                    }
                
                with open(filename, 'w', newline='', encoding='utf-8') as f:
                    if data:
                        fieldnames = data[0].keys()
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writeheader()
                        writer.writerows(data)
                
                return {
                    "result": f"Written {len(data)} rows to {filename}",
                    "operation": "write",
                    "filename": filename,
                    "row_count": len(data),
                    "success": True
                }
            
            elif operation == "analyze":
                data = []
                with open(filename, 'r', newline='', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        data.append(row)
                
                if not data:
                    return {
                        "result": {"error": "No data found"},
                        "success": False
                    }
                
                # Analyze data
                analysis = {
                    "row_count": len(data),
                    "column_count": len(data[0].keys()),
                    "columns": list(data[0].keys()),
                    "sample_data": data[:3]  # First 3 rows
                }
                
                # Try to analyze numeric columns
                numeric_analysis = {}
                for col in data[0].keys():
                    try:
                        values = [float(row[col]) for row in data if row[col]]
                        if values:
                            numeric_analysis[col] = {
                                "min": min(values),
                                "max": max(values),
                                "mean": sum(values) / len(values),
                                "count": len(values)
                            }
                    except (ValueError, TypeError):
                        pass  # Not a numeric column
                
                analysis["numeric_columns"] = numeric_analysis
                
                return {
                    "result": analysis,
                    "operation": "analyze",
                    "filename": filename,
                    "success": True
                }
            
            elif operation == "filter":
                filter_column = arguments.get('filter_column')
                filter_value = arguments.get('filter_value')
                
                if not filter_column or filter_value is None:
                    return {
                        "result": None,
                        "error": "filter_column and filter_value are required for filter operation",
                        "success": False
                    }
                
                data = []
                filtered_data = []
                
                with open(filename, 'r', newline='', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        data.append(row)
                        if str(row.get(filter_column, '')) == str(filter_value):
                            filtered_data.append(row)
                
                return {
                    "result": filtered_data,
                    "operation": "filter",
                    "filename": filename,
                    "original_count": len(data),
                    "filtered_count": len(filtered_data),
                    "filter_column": filter_column,
                    "filter_value": filter_value,
                    "success": True
                }
            
            elif operation == "transform":
                transform_operation = arguments.get('transform_operation')
                transform_column = arguments.get('transform_column')
                transform_value = arguments.get('transform_value', '')
                
                if not transform_operation or not transform_column:
                    return {
                        "result": None,
                        "error": "transform_operation and transform_column are required",
                        "success": False
                    }
                
                data = []
                with open(filename, 'r', newline='', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        data.append(row)
                
                # Apply transformation
                for row in data:
                    if transform_column in row:
                        if transform_operation == "uppercase":
                            row[transform_column] = str(row[transform_column]).upper()
                        elif transform_operation == "lowercase":
                            row[transform_column] = str(row[transform_column]).lower()
                        elif transform_operation == "add_prefix":
                            row[transform_column] = transform_value + str(row[transform_column])
                        elif transform_operation == "add_suffix":
                            row[transform_column] = str(row[transform_column]) + transform_value
                
                # Write transformed data back
                output_filename = filename.replace('.csv', '_transformed.csv')
                with open(output_filename, 'w', newline='', encoding='utf-8') as f:
                    if data:
                        fieldnames = data[0].keys()
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writeheader()
                        writer.writerows(data)
                
                return {
                    "result": f"Transformed {len(data)} rows and saved to {output_filename}",
                    "operation": "transform",
                    "filename": filename,
                    "output_filename": output_filename,
                    "transform_operation": transform_operation,
                    "transform_column": transform_column,
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
                "error": f"CSV processing error: {str(e)}",
                "success": False
            }

@register_tool('JSONProcessorTool', config={
    "name": "json_processor_tool",
    "description": "Process JSON data with various operations",
    "parameter": {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["read", "write", "validate", "extract", "merge"],
                "description": "JSON operation to perform"
            },
            "filename": {
                "type": "string",
                "description": "JSON file path"
            },
            "data": {
                "description": "Data to write (for write operation)"
            },
            "extract_path": {
                "type": "string",
                "description": "JSON path to extract (e.g., 'users[0].name')"
            },
            "merge_data": {
                "description": "Data to merge (for merge operation)"
            }
        },
        "required": ["operation", "filename"]
    }
})
class JSONProcessorTool(BaseTool):
    """Tool for processing JSON files."""
    
    def run(self, arguments: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Execute JSON processing operation."""
        try:
            operation = arguments.get('operation')
            filename = arguments.get('filename')
            
            if operation == "read":
                with open(filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                return {
                    "result": data,
                    "operation": "read",
                    "filename": filename,
                    "data_type": type(data).__name__,
                    "success": True
                }
            
            elif operation == "write":
                data = arguments.get('data')
                if data is None:
                    return {
                        "result": None,
                        "error": "No data provided for write operation",
                        "success": False
                    }
                
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                return {
                    "result": f"Written data to {filename}",
                    "operation": "write",
                    "filename": filename,
                    "data_type": type(data).__name__,
                    "success": True
                }
            
            elif operation == "validate":
                try:
                    with open(filename, 'r', encoding='utf-8') as f:
                        json.load(f)
                    return {
                        "result": "Valid JSON",
                        "operation": "validate",
                        "filename": filename,
                        "success": True
                    }
                except json.JSONDecodeError as e:
                    return {
                        "result": f"Invalid JSON: {str(e)}",
                        "operation": "validate",
                        "filename": filename,
                        "success": False
                    }
            
            elif operation == "extract":
                extract_path = arguments.get('extract_path')
                if not extract_path:
                    return {
                        "result": None,
                        "error": "extract_path is required for extract operation",
                        "success": False
                    }
                
                with open(filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Simple path extraction (supports basic dot notation and array indexing)
                try:
                    result = data
                    for part in extract_path.split('.'):
                        if '[' in part and ']' in part:
                            key = part[:part.index('[')]
                            index = int(part[part.index('[')+1:part.index(']')])
                            result = result[key][index]
                        else:
                            result = result[part]
                    
                    return {
                        "result": result,
                        "operation": "extract",
                        "filename": filename,
                        "extract_path": extract_path,
                        "success": True
                    }
                except (KeyError, IndexError, TypeError) as e:
                    return {
                        "result": None,
                        "error": f"Extraction failed: {str(e)}",
                        "success": False
                    }
            
            elif operation == "merge":
                merge_data = arguments.get('merge_data')
                if merge_data is None:
                    return {
                        "result": None,
                        "error": "merge_data is required for merge operation",
                        "success": False
                    }
                
                with open(filename, 'r', encoding='utf-8') as f:
                    original_data = json.load(f)
                
                # Simple merge (assumes both are dictionaries)
                if isinstance(original_data, dict) and isinstance(merge_data, dict):
                    merged_data = {**original_data, **merge_data}
                else:
                    # If not dictionaries, create a list
                    merged_data = [original_data, merge_data]
                
                output_filename = filename.replace('.json', '_merged.json')
                with open(output_filename, 'w', encoding='utf-8') as f:
                    json.dump(merged_data, f, indent=2, ensure_ascii=False)
                
                return {
                    "result": f"Merged data and saved to {output_filename}",
                    "operation": "merge",
                    "filename": filename,
                    "output_filename": output_filename,
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
                "error": f"JSON processing error: {str(e)}",
                "success": False
            }

# =============================================================================
# TESTING FUNCTIONS
# =============================================================================

def test_csv_processing(tu):
    """Test CSV processing functionality."""
    
    print("🧪 Testing CSV Processing")
    print("=" * 30)
    
    # Create test CSV data
    test_data = [
        {"name": "Alice", "age": 25, "city": "New York"},
        {"name": "Bob", "age": 30, "city": "London"},
        {"name": "Charlie", "age": 35, "city": "Paris"},
        {"name": "Diana", "age": 28, "city": "Tokyo"}
    ]
    
    test_filename = "test_data.csv"
    
    try:
        # Test write operation
        print("\n1. Testing CSV write:")
        result = tu.run({
            "name": "csv_processor_tool",
            "arguments": {
                "operation": "write",
                "filename": test_filename,
                "data": test_data
            }
        })
        print(f"   Write result: {result}")
        
        # Test read operation
        print("\n2. Testing CSV read:")
        result = tu.run({
            "name": "csv_processor_tool",
            "arguments": {
                "operation": "read",
                "filename": test_filename
            }
        })
        print(f"   Read result: {result}")
        
        # Test analyze operation
        print("\n3. Testing CSV analyze:")
        result = tu.run({
            "name": "csv_processor_tool",
            "arguments": {
                "operation": "analyze",
                "filename": test_filename
            }
        })
        print(f"   Analyze result: {result}")
        
        # Test filter operation
        print("\n4. Testing CSV filter:")
        result = tu.run({
            "name": "csv_processor_tool",
            "arguments": {
                "operation": "filter",
                "filename": test_filename,
                "filter_column": "age",
                "filter_value": "30"
            }
        })
        print(f"   Filter result: {result}")
        
        # Test transform operation
        print("\n5. Testing CSV transform:")
        result = tu.run({
            "name": "csv_processor_tool",
            "arguments": {
                "operation": "transform",
                "filename": test_filename,
                "transform_operation": "add_prefix",
                "transform_column": "name",
                "transform_value": "Mr./Ms. "
            }
        })
        print(f"   Transform result: {result}")
        
        print("   ✅ CSV processing tests completed")
        
    except Exception as e:
        print(f"   ❌ CSV processing error: {e}")
    finally:
        # Clean up
        for file in [test_filename, "test_data_transformed.csv"]:
            if os.path.exists(file):
                os.remove(file)
                print(f"   🧹 Cleaned up {file}")

def test_json_processing(tu):
    """Test JSON processing functionality."""
    
    print("\n🧪 Testing JSON Processing")
    print("=" * 30)
    
    # Create test JSON data
    test_data = {
        "users": [
            {"id": 1, "name": "Alice", "email": "alice@example.com"},
            {"id": 2, "name": "Bob", "email": "bob@example.com"}
        ],
        "settings": {
            "theme": "dark",
            "language": "en"
        }
    }
    
    test_filename = "test_data.json"
    
    try:
        # Test write operation
        print("\n1. Testing JSON write:")
        result = tu.run({
            "name": "json_processor_tool",
            "arguments": {
                "operation": "write",
                "filename": test_filename,
                "data": test_data
            }
        })
        print(f"   Write result: {result}")
        
        # Test read operation
        print("\n2. Testing JSON read:")
        result = tu.run({
            "name": "json_processor_tool",
            "arguments": {
                "operation": "read",
                "filename": test_filename
            }
        })
        print(f"   Read result: {result}")
        
        # Test validate operation
        print("\n3. Testing JSON validate:")
        result = tu.run({
            "name": "json_processor_tool",
            "arguments": {
                "operation": "validate",
                "filename": test_filename
            }
        })
        print(f"   Validate result: {result}")
        
        # Test extract operation
        print("\n4. Testing JSON extract:")
        result = tu.run({
            "name": "json_processor_tool",
            "arguments": {
                "operation": "extract",
                "filename": test_filename,
                "extract_path": "users[0].name"
            }
        })
        print(f"   Extract result: {result}")
        
        # Test merge operation
        print("\n5. Testing JSON merge:")
        merge_data = {"version": "1.0", "author": "ToolUniverse"}
        result = tu.run({
            "name": "json_processor_tool",
            "arguments": {
                "operation": "merge",
                "filename": test_filename,
                "merge_data": merge_data
            }
        })
        print(f"   Merge result: {result}")
        
        print("   ✅ JSON processing tests completed")
        
    except Exception as e:
        print(f"   ❌ JSON processing error: {e}")
    finally:
        # Clean up
        for file in [test_filename, "test_data_merged.json"]:
            if os.path.exists(file):
                os.remove(file)
                print(f"   🧹 Cleaned up {file}")

def test_direct_access(tu):
    """Test direct tool access."""
    
    print("\n🔧 Testing Direct Access")
    print("=" * 25)
    
    try:
        # Test direct access
        result = tu.tools.csv_processor_tool(
            operation="analyze",
            filename="nonexistent.csv"
        )
        print(f"Direct csv_processor_tool(): {result}")
        
        result = tu.tools.json_processor_tool(
            operation="validate",
            filename="nonexistent.json"
        )
        print(f"Direct json_processor_tool(): {result}")
        
        print("✅ Direct access works")
        
    except Exception as e:
        print(f"❌ Direct access failed: {e}")

# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """Main function to demonstrate data processing tools."""
    
    print("🚀 Data Processing Tools Example")
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
        expected_tools = ["csv_processor_tool", "json_processor_tool"]
        available_tools = list(tu.all_tool_dict.keys())
        
        print(f"\n📋 Available tools: {available_tools}")
        
        for tool_name in expected_tools:
            if tool_name in available_tools:
                print(f"✅ {tool_name} is available")
            else:
                print(f"❌ {tool_name} not found")
        
        # Run tests
        test_csv_processing(tu)
        test_json_processing(tu)
        test_direct_access(tu)
        
        print("\n🎉 Data processing tools example completed!")
        
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
