# MyNewTool Examples

This directory contains two examples demonstrating how to add a local tool to ToolUniverse:

## 1. Single File Example (`single_file_example.py`)

**Use case**: Quick local development, no modifications to core files needed.

- All code in one file (tool definition + config + usage)
- Config is in the `@register_tool` decorator
- No separate JSON file needed
- No modifications to `__init__.py`, `default_config.py`, or `data/` directory

**Best for**: Local testing, prototyping, personal projects

## 2. Multi-File Example (Documentation Pattern)

**Use case**: Contributing a tool to the ToolUniverse repository.

Files:
- `my_new_tool.py`: Tool class definition (no config in decorator)
- `my_new_tool_tools.json`: Tool configuration file
- `my_new_tool_example.py`: Example usage code

This matches the structure shown in:
`docs/expand_tooluniverse/contributing/local_tools.rst`

**Note**: In a real contribution, these files would be placed in:
- `src/tooluniverse/my_new_tool.py`
- `src/tooluniverse/data/my_new_tool_tools.json`
- `examples/my_new_tool_example.py`

And you would need to modify `__init__.py` in 4 locations as described in the documentation.

**Best for**: Contributing tools to the repository

## Running the Examples

### Single File Example:
```bash
cd examples/my_new_tool
python single_file_example.py
```

### Multi-File Example:
```bash
cd examples/my_new_tool
python my_new_tool_example.py
```

