# Tool Description Optimizer - Quick Start Tutorial

## 🚀 Quick Start

Want to improve your tool descriptions in minutes? Here's how:

### 1. Basic Usage

```python
from tooluniverse import ToolUniverse

# Initialize and load tools
tu = ToolUniverse()
tu.load_tools()

# Optimize any tool
tool_name = "your_tool_name"  # Replace with actual tool name
tool_config = tu.get_tool_description(tool_name)

result = tu.run({
    "name": "ToolDescriptionOptimizer",
    "arguments": {"tool_config": tool_config}
})

print(f"Done! {result['total_iterations']} rounds, score: {result['final_quality_score']}/10")
```

### 2. Real Example

```python
# Optimize the FDA drug ingredient tool
tool_config = tu.get_tool_description("FDA_get_active_ingredient_info_by_drug_name")

result = tu.run({
    "name": "ToolDescriptionOptimizer",
    "arguments": {
        "tool_config": tool_config,
        "max_iterations": 3,
        "satisfaction_threshold": 8.0
    }
})
```

### 3. What You Get

- ✅ **Improved Descriptions**: More accurate and clear tool documentation
- ✅ **Quality Scores**: Objective metrics for description quality (1-10 scale)
- ✅ **Detailed Report**: Complete optimization history saved to file
- ✅ **Test Results**: Real tool execution data used for optimization

### 4. Key Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_iterations` | 3 | Number of optimization rounds |
| `satisfaction_threshold` | 8.0 | Quality score target (1-10) |
| `output_file` | auto | Where to save the report |

### 5. Example Results

**Before Optimization:**
```
"Fetch a list of active ingredients in a specific drug product."
```

**After Optimization:**
```
"Provides detailed information about the active ingredients in drug products,
including their properties and quantities, as found in various formulations and brands."
```

## 📊 What Gets Optimized

The optimizer improves:
- **Tool Description**: Overall purpose and functionality
- **Parameter Descriptions**: Input requirements and constraints
- **Clarity**: Easy to understand language
- **Accuracy**: Matches actual tool behavior
- **Conciseness**: Removes redundancy and filler

## 🔧 Common Use Cases

```python
# Quick improvement (2-3 rounds)
result = tu.run({
    "name": "ToolDescriptionOptimizer",
    "arguments": {
        "tool_config": tool_config,
        "max_iterations": 2,
        "satisfaction_threshold": 7.5
    }
})

# Thorough optimization (up to 5 rounds)
result = tu.run({
    "name": "ToolDescriptionOptimizer",
    "arguments": {
        "tool_config": tool_config,
        "max_iterations": 5,
        "satisfaction_threshold": 8.5
    }
})
```

## 📋 Complete Example Script

```python
#!/usr/bin/env python3
"""Quick Tool Optimization Script"""

from tooluniverse import ToolUniverse

def quick_optimize(tool_name):
    tu = ToolUniverse()
    tu.load_tools()

    tool_config = tu.get_tool_description(tool_name)

    result = tu.run({
        "name": "ToolDescriptionOptimizer",
        "arguments": {"tool_config": tool_config}
    })

    print(f"✅ {tool_name} optimized!")
    print(f"Score: {result['final_quality_score']}/10")
    return result

# Usage
quick_optimize("FDA_get_active_ingredient_info_by_drug_name")
```

That's it! For detailed documentation, see the [full tutorial](Tool_Description_Optimizer_Tutorial.md).
