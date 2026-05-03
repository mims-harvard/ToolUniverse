# Tool Discover Examples

## 最简单的例子

```bash
cd examples
python use_tool_discover.py
```

这个例子展示如何像使用其他工具一样使用 `ToolDiscover` 工具：

1. 初始化 ToolUniverse
2. 使用 `tu.run()` 调用 ToolDiscover
3. 得到生成的工具文件

## 正确的调用方式

```python
from src.tooluniverse import ToolUniverse

# 初始化
tu = ToolUniverse()
tu.load_tools()

# 调用 ToolDiscover
result = tu.run({
    "name": "ToolDiscover",
    "arguments": {
        "tool_description": "A simple calculator for basic math operations",
        "max_iterations": 1,
        "save_to_file": True,
        "output_file": "generated_calculator_tool"
    }
})
```

## 关键点

- ✅ 使用 `tu.run()` 而不是直接调用 `compose()`
- ✅ 传递正确的参数格式
- ✅ 包含所有必需参数（如 `output_file`）

这就是标准的工具调用方式！