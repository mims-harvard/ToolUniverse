# ToolUniverse Quick Reference - Adding Tools

## 🚀 Quick Start (30 seconds)

```python
# my_tool.py - Place in src/tooluniverse/
from tooluniverse.tool_registry import register_tool

@register_tool('MyTool', config={
    "name": "my_tool",
    "type": "MyTool",
    "description": "Does something useful",
    "parameter": {
        "type": "object",
        "properties": {
            "input": {"type": "string", "description": "Your input"}
        },
        "required": ["input"]
    }
})
class MyTool:
    def __init__(self, tool_config=None):
        self.tool_config = tool_config

    def run(self, arguments):
        return {"result": f"Processed: {arguments['input']}", "success": True}

# Usage
from tooluniverse import ToolUniverse
tu = ToolUniverse()
tu.load_tools()
result = tu.run_one_function({"name": "my_tool", "arguments": {"input": "test"}})
```

## 📋 Common Patterns

### API Wrapper Tool
```python
@register_tool('APITool', config={...})
class APITool:
    def run(self, arguments):
        try:
            response = requests.get(arguments['url'])
            return {"data": response.json(), "success": True}
        except Exception as e:
            return {"error": str(e), "success": False}
```

### File Processor Tool
```python
@register_tool('FileProcessor', config={...})
class FileProcessor:
    def run(self, arguments):
        with open(arguments['file_path'], 'r') as f:
            content = f.read()
        # Process content...
        return {"processed_content": content, "success": True}
```

### Database Tool
```python
@register_tool('DatabaseTool', config={...})
class DatabaseTool:
    def __init__(self, tool_config=None):
        self.db_config = tool_config.get("settings", {})

    def run(self, arguments):
        # Execute query...
        return {"results": [], "count": 0, "success": True}
```

## 🔧 Configuration Templates

### Simple Tool Config
```python
config={
    "name": "tool_name",
    "type": "ToolClass",
    "description": "What it does",
    "parameter": {
        "type": "object",
        "properties": {
            "param1": {"type": "string", "description": "Description"}
        },
        "required": ["param1"]
    }
}
```

### Advanced Tool Config
```python
config={
    "name": "advanced_tool",
    "type": "AdvancedTool",
    "description": "Complex tool with settings",
    "parameter": {
        "type": "object",
        "properties": {
            "data": {"type": "array", "items": {"type": "object"}},
            "options": {"type": "object", "default": {}}
        },
        "required": ["data"]
    },
    "settings": {
        "api_key": "env:API_KEY",
        "timeout": 30,
        "retries": 3
    }
}
```

## ❌ Common Mistakes

### ❌ Wrong: Missing required methods
```python
class BadTool:
    def process(self, data):  # Wrong method name
        return data
```

### ✅ Correct: Proper structure
```python
class GoodTool:
    def __init__(self, tool_config=None):  # Required
        self.tool_config = tool_config

    def run(self, arguments):  # Required method name
        return {"result": "success", "success": True}
```

### ❌ Wrong: No error handling
```python
def run(self, arguments):
    result = risky_operation(arguments['data'])  # Can crash
    return {"result": result}
```

### ✅ Correct: With error handling
```python
def run(self, arguments):
    try:
        result = risky_operation(arguments['data'])
        return {"result": result, "success": True}
    except Exception as e:
        return {"error": str(e), "success": False}
```

## 🧪 Testing Checklist

- [ ] File ends with `_tool.py`
- [ ] Placed in `src/tooluniverse/`
- [ ] Class has `__init__(self, tool_config=None)`
- [ ] Class has `run(self, arguments)` method
- [ ] Config has all required fields (`name`, `type`, `description`, `parameter`)
- [ ] Returns consistent format (`success: True/False`)
- [ ] Error handling implemented
- [ ] Test script works:

```python
from tooluniverse import ToolUniverse
tu = ToolUniverse()
tu.load_tools()
print(tu.run_one_function({"name": "your_tool", "arguments": {...}}))
```

## 🆘 Troubleshooting

| Problem | Solution |
|---------|----------|
| Tool not found | Check file name ends with `_tool.py` |
| Import error | Test: `python -c "from tooluniverse.your_tool import YourTool"` |
| Config error | Validate JSON: `json.loads(json.dumps(config))` |
| Runtime error | Add try/catch, return `{"error": str(e), "success": False}` |
| Wrong parameters | Check parameter schema matches your `run()` method |

## 📚 Full Documentation

For complete examples and advanced usage, see [Adding_Tools_Tutorial.md](Adding_Tools_Tutorial.md)
