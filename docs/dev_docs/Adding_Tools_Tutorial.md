# Adding Tools to ToolUniverse - Complete Tutorial

This tutorial covers everything you need to know about adding custom tools to ToolUniverse using the decorator-based auto-registration system.

## Table of Contents
1. :ref:`overview`
2. :ref:`development-environment-setup`
3. :ref:`quick-start`
4. :ref:`method-1-decorator-registration-recommended`
5. :ref:`method-2-manual-registration`
6. :ref:`tool-configuration`
7. :ref:`parameter-validation-and-error-handling`
8. :ref:`real-world-examples`
9. :ref:`best-practices`
10. :ref:`troubleshooting`

.. _overview:

## Overview

ToolUniverse supports **automatic tool discovery** through decorators. When you add a new tool, it's automatically registered and available without needing to manually edit core files.

### What You Can Add
- Custom API wrappers
- Data processing tools
- File manipulation utilities
- External service integrations
- Analysis and computation tools

### What Changed
- ❌ **Before**: Manual imports and mappings in `execute_function.py`
- ✅ **Now**: Simple decorator registration with auto-discovery

.. _development-environment-setup:

## Development Environment Setup

Before adding tools, ensure you have the proper development environment set up:

### 1. Clone and Install ToolUniverse

```bash
# Clone the repository
git clone https://github.com/mims-harvard/ToolUniverse.git
cd ToolUniverse

# Install in development mode
pip install -e ".[dev]"
```

### 2. Set Up Pre-commit Hooks (Recommended)

**Automatic Setup:**
```bash
# Auto-install pre-commit hooks
./setup_precommit.sh
```

**Manual Setup:**
```bash
# Install pre-commit if not already installed
pip install pre-commit

# Install hooks
pre-commit install

# Update to latest versions
pre-commit autoupdate
```

**Pre-commit Benefits:**
- ✅ **Automatic code formatting** with Black
- ✅ **Code linting** with flake8 and ruff
- ✅ **Import cleanup** with autoflake
- ✅ **File validation** (YAML, TOML, AST checks)
- ✅ **Runs on every commit** to ensure code quality

### 3. Verify Installation

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools()
print(f"✅ Loaded {len(tu.all_tools)} tools!")
```

.. _quick-start:

## Quick Start

Here's the fastest way to add a new tool:

```python
# my_custom_tool.py
from tooluniverse.tool_registry import register_tool

@register_tool('MyAwesomeTool', config={
    "name": "my_awesome_tool",
    "type": "MyAwesomeTool",
    "description": "A simple example tool",
    "parameter": {
        "type": "object",
        "properties": {
            "message": {"type": "string", "description": "Message to process"}
        },
        "required": ["message"]
    }
})
class MyAwesomeTool:
    def __init__(self, tool_config=None):
        self.tool_config = tool_config

    def run(self, arguments):
        message = arguments.get('message', '')
        return {
            'processed_message': f"Hello! You said: '{message}'",
            'original': message,
            'tool_name': 'MyAwesomeTool'
        }

# Usage
from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools()  # Auto-discovers and loads your tool

result = tu.run_one_function({
    "name": "my_awesome_tool",
    "arguments": {"message": "This is a test"}
})
print(result)
```

That's it! Your tool is automatically discovered and ready to use.

.. _method-1-decorator-registration-recommended:

## Method 1: Decorator Registration (Recommended)

The decorator approach is the simplest and most powerful way to add tools.

### Basic Structure

```python
from tooluniverse.tool_registry import register_tool

@register_tool('YourToolType', config={...})
class YourTool:
    def __init__(self, tool_config=None):
        # Initialize your tool
        pass

    def run(self, arguments):
        # Process arguments and return results
        return {...}
```

### Step-by-Step Tutorial

#### 1. Create Your Tool File
Create a new Python file ending with `_tool.py` (e.g., `weather_tool.py`):

```python
# weather_tool.py
import requests
from tooluniverse.tool_registry import register_tool

@register_tool('WeatherTool', config={
    "name": "get_weather",
    "type": "WeatherTool",
    "description": "Get current weather for a city",
    "parameter": {
        "type": "object",
        "properties": {
            "city": {
                "type": "string",
                "description": "City name to get weather for"
            },
            "units": {
                "type": "string",
                "description": "Temperature units (metric/imperial)",
                "default": "metric"
            }
        },
        "required": ["city"]
    }
})
class WeatherTool:
    def __init__(self, tool_config=None):
        self.tool_config = tool_config
        self.api_key = "your_api_key_here"  # In practice, use env vars

    def run(self, arguments):
        city = arguments.get('city')
        units = arguments.get('units', 'metric')

        # Mock API call (replace with real API)
        url = f"http://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": city,
            "appid": self.api_key,
            "units": units
        }

        try:
            response = requests.get(url, params=params)
            data = response.json()

            return {
                "city": city,
                "temperature": data["main"]["temp"],
                "description": data["weather"][0]["description"],
                "units": units,
                "success": True
            }
        except Exception as e:
            return {
                "error": f"Failed to get weather: {str(e)}",
                "success": False
            }
```

#### 2. Place in ToolUniverse Package
Move your file to the ToolUniverse source directory:
```bash
cp weather_tool.py /path/to/ToolUniverse/src/tooluniverse/
```

#### 3. Use Your Tool
Your tool is automatically discovered:

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools()

# Your tool is now available!
result = tu.run_one_function({
    "name": "get_weather",
    "arguments": {"city": "San Francisco", "units": "metric"}
})

print(result)
```

### Configuration Options

The `config` parameter in the decorator supports all standard ToolUniverse configuration:

```python
@register_tool('AdvancedTool', config={
    "name": "advanced_tool",
    "type": "AdvancedTool",
    "description": "An advanced tool with complex parameters",
    "parameter": {
        "type": "object",
        "properties": {
            "input_data": {
                "type": "object",
                "description": "Complex input data",
                "properties": {
                    "values": {"type": "array", "items": {"type": "number"}},
                    "operation": {"type": "string", "enum": ["sum", "avg", "max"]}
                }
            },
            "options": {
                "type": "object",
                "description": "Optional settings",
                "properties": {
                    "precision": {"type": "integer", "default": 2},
                    "format": {"type": "string", "default": "json"}
                }
            }
        },
        "required": ["input_data"]
    },
    "settings": {
        "timeout": 30,
        "max_retries": 3,
        "custom_field": "value"
    }
})
```

.. _method-2-manual-registration:

## Method 2: Manual Registration

For dynamic tools or special cases, you can register tools at runtime:

```python
from tooluniverse import ToolUniverse

class DynamicTool:
    def __init__(self, tool_config=None):
        self.tool_config = tool_config
        self.dynamic_data = self._load_dynamic_data()

    def run(self, arguments):
        return {"result": f"Processed {arguments}"}

    def _load_dynamic_data(self):
        # Load configuration from database, API, etc.
        return {}

# Create ToolUniverse instance
tu = ToolUniverse()
tu.load_tools()

# Manual registration
tool_config = {
    "name": "dynamic_tool",
    "type": "DynamicTool",
    "description": "A dynamically configured tool",
    "parameter": {
        "type": "object",
        "properties": {
            "input": {"type": "string", "description": "Input data"}
        },
        "required": ["input"]
    }
}

tu.register_custom_tool(DynamicTool, 'DynamicTool', tool_config)

# Use the manually registered tool
result = tu.run_one_function({
    "name": "dynamic_tool",
    "arguments": {"input": "test"}
})
```

.. _tool-configuration:

## Tool Configuration

### Required Fields
- `name`: Unique identifier for your tool
- `type`: Class name (must match decorator parameter)
- `description`: Human-readable description
- `parameter`: JSON Schema defining input parameters

### Optional Fields
- `settings`: Tool-specific configuration
- `version`: Tool version
- `tags`: Categorization tags
- `examples`: Usage examples

### Parameter Schema Examples

#### Simple Parameters
```json
{
    "type": "object",
    "properties": {
        "text": {"type": "string", "description": "Input text"},
        "count": {"type": "integer", "minimum": 1, "maximum": 100}
    },
    "required": ["text"]
}
```

#### Complex Parameters
```json
{
    "type": "object",
    "properties": {
        "data": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "value": {"type": "number"}
                }
            }
        },
        "options": {
            "type": "object",
            "properties": {
                "format": {"type": "string", "enum": ["json", "csv", "xml"]},
                "include_metadata": {"type": "boolean", "default": false}
            }
        }
    },
    "required": ["data"]
}
```

.. _parameter-validation-and-error-handling:

## Parameter Validation and Error Handling

ToolUniverse provides built-in support for parameter validation and structured error handling to help you create robust tools.

### Parameter Validation

You can implement custom parameter validation by overriding the `validate_parameters()` method:

```python
from tooluniverse.exceptions import ToolValidationError

class MyTool:
    def validate_parameters(self, arguments):
        # First run base validation
        base_error = super().validate_parameters(arguments)
        if base_error:
            return base_error
        
        # Add custom validation
        if "email" in arguments:
            email = arguments["email"]
            if "@" not in email:
                return ToolValidationError(
                    "Invalid email format",
                    next_steps=["Provide a valid email address"],
                    details={"field": "email", "value": email}
                )
        
        return None  # Validation passed
```

### Error Handling

Override `handle_error()` to provide tool-specific error classification:

```python
from tooluniverse.exceptions import ToolAuthError, ToolRateLimitError

class APITool:
    def handle_error(self, exception):
        error_str = str(exception).lower()
        
        if "api key" in error_str:
            return ToolAuthError(
                "API authentication failed",
                next_steps=["Check API key", "Verify environment variables"]
            )
        elif "rate limit" in error_str:
            return ToolRateLimitError(
                "API rate limit exceeded",
                next_steps=["Wait and retry", "Check quota limits"]
            )
        
        # Fall back to base error handling
        return super().handle_error(exception)
```

### Exception System Migration

If you're using older exception classes, migrate to the new structured system:

```python
# Old way (deprecated)
from tooluniverse.base_tool import ValidationError
raise ValidationError("Invalid input")

# New way (recommended)
from tooluniverse.exceptions import ToolValidationError
raise ToolValidationError(
    "Invalid input",
    next_steps=["Check parameter format"],
    details={"field": "email"}
)
```

For more information about the exception system, see the [API documentation](../api/tooluniverse.exceptions.rst).

.. _real-world-examples:

## Real-World Examples

### Example 1: Database Query Tool

```python
# database_tool.py
import sqlite3
from typing import Dict, Any, List
from tooluniverse.tool_registry import register_tool

@register_tool('DatabaseQueryTool', config={
    "name": "query_database",
    "type": "DatabaseQueryTool",
    "description": "Execute SQL queries on a database",
    "parameter": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "SQL query to execute"},
            "database": {"type": "string", "description": "Database name"},
            "limit": {"type": "integer", "default": 100, "maximum": 1000}
        },
        "required": ["query", "database"]
    },
    "settings": {
        "db_path": "/path/to/databases/",
        "readonly": true
    }
})
class DatabaseQueryTool:
    def __init__(self, tool_config: Dict[str, Any]):
        self.tool_config = tool_config
        self.db_path = tool_config.get("settings", {}).get("db_path", ".")
        self.readonly = tool_config.get("settings", {}).get("readonly", True)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        query = arguments.get('query')
        database = arguments.get('database')
        limit = arguments.get('limit', 100)

        try:
            db_file = f"{self.db_path}/{database}.db"
            conn = sqlite3.connect(db_file)
            conn.row_factory = sqlite3.Row  # Enable column access by name

            cursor = conn.cursor()

            # Add LIMIT if not present in query
            if 'LIMIT' not in query.upper():
                query += f" LIMIT {limit}"

            cursor.execute(query)
            rows = cursor.fetchall()

            # Convert to list of dictionaries
            results = [dict(row) for row in rows]

            conn.close()

            return {
                "results": results,
                "count": len(results),
                "query": query,
                "database": database,
                "success": True
            }

        except Exception as e:
            return {
                "error": str(e),
                "query": query,
                "database": database,
                "success": False
            }
```

### Example 2: File Processing Tool

```python
# file_processor_tool.py
import os
import json
import csv
from pathlib import Path
from tooluniverse.tool_registry import register_tool

@register_tool('FileProcessorTool', config={
    "name": "process_file",
    "type": "FileProcessorTool",
    "description": "Process and transform files between different formats",
    "parameter": {
        "type": "object",
        "properties": {
            "input_file": {"type": "string", "description": "Path to input file"},
            "output_format": {"type": "string", "enum": ["json", "csv", "txt"]},
            "operation": {"type": "string", "enum": ["convert", "analyze", "validate"]}
        },
        "required": ["input_file", "operation"]
    }
})
class FileProcessorTool:
    def __init__(self, tool_config=None):
        self.tool_config = tool_config
        self.supported_formats = ['.json', '.csv', '.txt', '.xml']

    def run(self, arguments):
        input_file = arguments.get('input_file')
        operation = arguments.get('operation')
        output_format = arguments.get('output_format')

        if not os.path.exists(input_file):
            return {"error": f"File not found: {input_file}", "success": False}

        try:
            if operation == "analyze":
                return self._analyze_file(input_file)
            elif operation == "convert":
                return self._convert_file(input_file, output_format)
            elif operation == "validate":
                return self._validate_file(input_file)
            else:
                return {"error": f"Unknown operation: {operation}", "success": False}

        except Exception as e:
            return {"error": str(e), "success": False}

    def _analyze_file(self, file_path):
        file_stats = os.stat(file_path)
        file_ext = Path(file_path).suffix.lower()

        analysis = {
            "file_path": file_path,
            "size_bytes": file_stats.st_size,
            "extension": file_ext,
            "readable": os.access(file_path, os.R_OK),
            "success": True
        }

        # Format-specific analysis
        if file_ext == '.json':
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                analysis["json_valid"] = True
                analysis["json_type"] = type(data).__name__
                if isinstance(data, list):
                    analysis["items_count"] = len(data)
                elif isinstance(data, dict):
                    analysis["keys_count"] = len(data.keys())
            except:
                analysis["json_valid"] = False

        return analysis

    def _convert_file(self, input_file, output_format):
        # Implementation for file conversion
        return {
            "message": f"Would convert {input_file} to {output_format}",
            "input_file": input_file,
            "output_format": output_format,
            "success": True
        }

    def _validate_file(self, file_path):
        # Implementation for file validation
        return {
            "file_path": file_path,
            "valid": True,
            "issues": [],
            "success": True
        }
```

### Example 3: API Integration Tool

```python
# api_client_tool.py
import requests
from typing import Dict, Any, Optional
from tooluniverse.tool_registry import register_tool

@register_tool('APIClientTool', config={
    "name": "call_api",
    "type": "APIClientTool",
    "description": "Make HTTP API calls with built-in error handling",
    "parameter": {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "API endpoint URL"},
            "method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE"], "default": "GET"},
            "headers": {"type": "object", "description": "HTTP headers"},
            "data": {"type": "object", "description": "Request body data"},
            "timeout": {"type": "integer", "default": 30, "minimum": 1, "maximum": 300}
        },
        "required": ["url"]
    },
    "settings": {
        "max_retries": 3,
        "default_headers": {
            "User-Agent": "ToolUniverse-APIClient/1.0"
        }
    }
})
class APIClientTool:
    def __init__(self, tool_config: Dict[str, Any]):
        self.tool_config = tool_config
        self.max_retries = tool_config.get("settings", {}).get("max_retries", 3)
        self.default_headers = tool_config.get("settings", {}).get("default_headers", {})

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        url = arguments.get('url')
        method = arguments.get('method', 'GET').upper()
        headers = {**self.default_headers, **arguments.get('headers', {})}
        data = arguments.get('data')
        timeout = arguments.get('timeout', 30)

        for attempt in range(self.max_retries + 1):
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=data if data else None,
                    timeout=timeout
                )

                result = {
                    "status_code": response.status_code,
                    "url": url,
                    "method": method,
                    "success": response.status_code < 400,
                    "attempt": attempt + 1
                }

                # Try to parse JSON response
                try:
                    result["data"] = response.json()
                except:
                    result["data"] = response.text

                if response.status_code < 400:
                    return result
                else:
                    result["error"] = f"HTTP {response.status_code}"
                    if attempt == self.max_retries:
                        return result

            except Exception as e:
                if attempt == self.max_retries:
                    return {
                        "error": str(e),
                        "url": url,
                        "method": method,
                        "success": False,
                        "attempt": attempt + 1
                    }

        return {"error": "Max retries exceeded", "success": False}
```

.. _best-practices:

## Best Practices

### 1. File Naming
- Name your tool files with `_tool.py` suffix
- Use descriptive names: `weather_tool.py`, `database_tool.py`

### 2. Class Design
```python
class MyTool:
    def __init__(self, tool_config=None):
        """Always accept tool_config parameter"""
        self.tool_config = tool_config or {}
        # Initialize from config
        self.setting_value = tool_config.get("settings", {}).get("key", "default")

    def run(self, arguments):
        """Main entry point - always called 'run'"""
        # Validate inputs
        required_param = arguments.get('required_param')
        if not required_param:
            return {"error": "required_param is missing", "success": False}

        # Process and return results
        return {"result": "success", "success": True}
```

### 3. Error Handling
```python
def run(self, arguments):
    try:
        # Your logic here
        result = self.process_data(arguments)
        return {"result": result, "success": True}

    except ValueError as e:
        return {"error": f"Invalid input: {str(e)}", "success": False}

    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}", "success": False}
```

### 4. Configuration Management
```python
@register_tool('ConfigurableTool', config={
    "name": "my_tool",
    "type": "ConfigurableTool",
    "description": "A tool that uses configuration",
    "parameter": {...},
    "settings": {
        "api_endpoint": "https://api.example.com",
        "timeout": 30,
        "retries": 3
    }
})
class ConfigurableTool:
    def __init__(self, tool_config=None):
        settings = tool_config.get("settings", {})
        self.api_endpoint = settings.get("api_endpoint")
        self.timeout = settings.get("timeout", 30)
        self.retries = settings.get("retries", 3)
```

### 5. Return Format Consistency
Always return dictionaries with consistent structure:
```python
# Success
return {
    "result": actual_result,
    "success": True,
    "metadata": {...}  # optional
}

# Error
return {
    "error": "Description of what went wrong",
    "success": False,
    "details": {...}  # optional error details
}
```

.. _troubleshooting:

## Troubleshooting

### Tool Not Found
**Problem**: Your tool isn't being discovered
**Solutions**:
1. Ensure file ends with `_tool.py`
2. Check file is in the correct directory
3. Verify the import doesn't fail:
   ```python
   python -c "from your_tool_module import YourTool"
   ```

### Import Errors
**Problem**: Module import fails during auto-discovery
**Solutions**:
1. Check all dependencies are installed
2. Ensure relative imports use proper syntax
3. Test import manually:
   ```python
   import sys
   sys.path.append('/path/to/tooluniverse/src')
   from tooluniverse.your_tool import YourTool
   ```

### Configuration Issues
**Problem**: Tool config not loading properly
**Solutions**:
1. Validate JSON syntax in config
2. Check required fields are present
3. Test config separately:
   ```python
   import json
   config = {...}  # your config
   print(json.dumps(config, indent=2))  # Should not error
   ```

### Runtime Errors
**Problem**: Tool fails during execution
**Solutions**:
1. Add comprehensive error handling
2. Validate all inputs in `run()` method
3. Return error details:
   ```python
   except Exception as e:
       return {
           "error": str(e),
           "traceback": traceback.format_exc(),  # For debugging
           "success": False
       }
   ```

### Testing Your Tool
Create a simple test script:
```python
# test_my_tool.py
from tooluniverse import ToolUniverse

def test_my_tool():
    tu = ToolUniverse()
    tu.load_tools()

    # Test your tool
    result = tu.run_one_function({
        "name": "your_tool_name",
        "arguments": {"test_param": "test_value"}
    })

    print("Result:", result)
    assert result.get("success") is True, f"Tool failed: {result}"
    print("✅ Tool test passed!")

if __name__ == "__main__":
    test_my_tool()
```

## Next Steps

1. **Start Simple**: Begin with a basic tool using the quick start example
2. **Add Complexity**: Gradually add more features and configuration
3. **Test Thoroughly**: Create test cases for different scenarios
4. **Document**: Add clear descriptions and examples
5. **Share**: Consider contributing useful tools back to the community

## Need Help?

- Check existing tools in the ToolUniverse codebase for examples
- Review the configuration schemas of similar tools
- Test incrementally - start with basic functionality
- Use the troubleshooting section for common issues

The decorator-based system makes adding tools straightforward while maintaining all the power and flexibility of ToolUniverse. Happy tool building! 🛠️