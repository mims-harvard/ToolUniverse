# Python Code Executor Tools

This directory contains examples and documentation for ToolUniverse's Python code execution tools.

## Overview

The Python Code Executor Tools provide secure execution of Python code snippets and script files within the ToolUniverse framework. These tools are designed with security in mind, featuring sandboxed execution environments and controlled access to system resources.

## Tools

### 1. python_code_executor
Executes Python code snippets safely in a sandboxed environment.

**Features:**
- Secure code execution with AST safety checks
- Variable passing and result extraction
- Timeout and memory limits
- Controlled module imports
- Detailed error reporting

**Example:**
```python
result = tu.run({
    "name": "python_code_executor",
    "arguments": {
        "code": "result = 10 + 20 * 3",
        "timeout": 10
    }
})
```

### 2. python_script_runner
Runs Python script files in an isolated subprocess with enhanced dependency management.

**Features:**
- Isolated subprocess execution
- Command-line argument support
- Environment variable passing
- Working directory control
- Output capture
- **NEW**: Automatic dependency checking and installation
- **NEW**: User confirmation for package installation
- **NEW**: Multiple import strategies for package name variations

**Basic Example:**
```python
result = tu.run({
    "name": "python_script_runner",
    "arguments": {
        "script_path": "my_script.py",
        "script_args": ["--input", "data.csv"],
        "timeout": 30
    }
})
```

**Dependency Management Example:**
```python
result = tu.run({
    "name": "python_script_runner",
    "arguments": {
        "script_path": "my_script.py",
        "dependencies": ["requests", "pandas"],
        "auto_install_dependencies": False,  # Require user confirmation
        "require_confirmation": True,
        "timeout": 30
    }
})

# Handle dependency confirmation
if result.get("requires_confirmation"):
    print(f"Missing packages: {result['missing_packages']}")
    print(f"Install command: {result['install_command']}")
    # User can then run the install command or set auto_install_dependencies=True
```

## Security Features

- **AST Safety Checks**: Static analysis to detect dangerous operations
- **Restricted Builtins**: Whitelist of safe built-in functions
- **Controlled Imports**: Only pre-approved modules can be imported
- **Resource Limits**: Timeout and memory restrictions
- **Isolated Execution**: Clean namespace and environment

## Allowed Modules

By default, the following modules are allowed:
- `math`, `json`, `datetime`, `collections`
- `itertools`, `re`, `typing`, `dataclasses`
- `decimal`, `fractions`, `statistics`, `random`

## Examples

### Quick Start
```bash
python quick_start.py
```

### Basic Usage
```bash
python basic_usage.py
```

### Dependency Management
```bash
python dependency_management_example.py
```

### Simple Dependency Demo
```bash
python simple_dependency_demo.py
```

The dependency management examples demonstrate:
- User confirmation for package installation
- Multiple import strategies for package name variations
- Safe error handling for invalid packages
- Auto-install options (with user control)
- Clean execution for scripts without dependencies

The simple demo shows:
- Automatic detection of missing packages
- User confirmation prompts
- Installation command suggestions

## Configuration

### python_code_executor Parameters
- `timeout`: Execution timeout in seconds (default: 30)
- `memory_limit_mb`: Memory limit in MB (default: 512)
- `arguments`: Variables to pass to the execution environment
- `enable_ast_check`: Enable AST safety checks (default: true)
- `return_variable`: Variable name to extract as result (default: "result")
- `allowed_imports`: Additional allowed modules beyond the default set

### python_script_runner Parameters
- `script_path`: Path to Python script file (.py) to execute
- `script_args`: Command-line arguments to pass to the script
- `timeout`: Execution timeout in seconds (default: 60)
- `working_directory`: Working directory for script execution
- `env_vars`: Environment variables to set for script execution
- **NEW**: `dependencies`: List of Python packages that the script depends on
- **NEW**: `auto_install_dependencies`: Whether to automatically install missing dependencies (default: false)
- **NEW**: `require_confirmation`: Whether to require user confirmation before installing packages (default: true)

## Error Handling

The tools provide detailed error information including:
- Error type and message
- Stack trace
- Execution metadata
- Security warnings

## Best Practices

1. **Always set timeouts** to prevent infinite loops
2. **Use specific return variables** to extract results
3. **Handle errors gracefully** by checking the success flag
4. **Test with simple examples** before running complex code
5. **Be aware of security restrictions** when importing modules

## Troubleshooting

### Common Issues

1. **ImportError**: Module not in allowed list
   - Solution: Add module to allowed_imports or use pre-imported modules

2. **TimeoutError**: Code execution took too long
   - Solution: Increase timeout or optimize code

3. **SecurityError**: Forbidden operation detected
   - Solution: Use allowed functions and modules only

4. **MissingResultError**: Return variable not found
   - Solution: Ensure code sets the specified return variable

### Getting Help

- Check the error message and error_type
- Review the traceback for detailed information
- Consult the tool documentation for parameter details
- Test with simpler examples to isolate issues

## License

This project is part of ToolUniverse. Please refer to the main project license for details.