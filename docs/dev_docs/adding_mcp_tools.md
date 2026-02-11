# 在 ToolUniverse 中添加 MCP 工具

本教程将指导你如何在 ToolUniverse 中集成 Model Context Protocol (MCP) 工具。ToolUniverse 提供了多种方式来连接和使用 MCP 服务器的工具。

## 目录

1. [MCP 工具类型概述](#mcp-工具类型概述)
2. [配置 MCP 客户端工具](#配置-mcp-客户端工具)
3. [使用自动加载器](#使用自动加载器)
4. [智能体工具配置](#智能体工具配置)
5. [高级配置选项](#高级配置选项)
6. [故障排除](#故障排除)

## MCP 工具类型概述

ToolUniverse 支持三种主要的 MCP 工具类型：

### 1. MCPClientTool
- **用途**: 通用的 MCP 客户端，支持所有 MCP 操作
- **特点**: 手动配置，精确控制
- **适用场景**: 需要访问多种 MCP 功能（工具、资源、提示）

### 2. MCPAutoLoaderTool
- **用途**: 自动发现并加载 MCP 服务器上的所有工具
- **特点**: 自动化配置，批量加载
- **适用场景**: 快速集成整个 MCP 服务器的工具集

### 3. MCPProxyTool
- **用途**: 为特定的 MCP 工具创建直接智能体
- **特点**: 一对一映射，透明转发
- **适用场景**: 将单个 MCP 工具集成为 ToolUniverse 工具

## 配置 MCP 客户端工具

### 基本配置

创建一个通用的 MCP 客户端工具配置：

```json
{
    "name": "my_mcp_client",
    "description": "连接到我的 MCP 服务器的客户端",
    "type": "MCPClientTool",
    "server_url": "http://localhost:8000",
    "transport": "http",
    "timeout": 600,
    "parameter": {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["list_tools", "call_tool", "list_resources", "read_resource", "list_prompts", "get_prompt"],
                "description": "要执行的 MCP 操作"
            },
            "tool_name": {
                "type": "string",
                "description": "要调用的工具名称（call_tool 操作必需）"
            },
            "tool_arguments": {
                "type": "object",
                "description": "传递给工具的参数（call_tool 操作使用）"
            },
            "uri": {
                "type": "string",
                "description": "资源 URI（read_resource 操作必需）"
            },
            "prompt_name": {
                "type": "string",
                "description": "提示名称（get_prompt 操作必需）"
            },
            "prompt_arguments": {
                "type": "object",
                "description": "传递给提示的参数（get_prompt 操作使用）"
            }
        },
        "required": ["operation"]
    }
}
```

### 使用示例

```python
from tooluniverse import ToolUniverse

# 初始化 ToolUniverse
tu = ToolUniverse()

# 调用 MCP 工具
result = tu.tools.my_mcp_client(
    operation="call_tool",
    tool_name="calculator",
    tool_arguments={"expression": "2 + 2"}
)

# 列出可用工具
tools = tu.tools.my_mcp_client(operation="list_tools")
```

## 使用自动加载器

### 基本自动加载器配置

```json
{
    "name": "mcp_auto_loader",
    "description": "自动加载 MCP 服务器工具",
    "type": "MCPAutoLoaderTool",
    "server_url": "http://localhost:8000",
    "transport": "http",
    "auto_register": true,
    "tool_prefix": "mcp_",
    "timeout": 30
}
```

### 高级自动加载器配置

```json
{
    "name": "expert_tool_loader",
    "description": "加载专家咨询工具",
    "type": "MCPAutoLoaderTool",
    "server_url": "http://localhost:7001/mcp",
    "transport": "http",
    "auto_register": true,
    "tool_prefix": "expert_",
    "selected_tools": ["consult_expert", "get_expert_response"],
    "timeout": 60
}
```

### 配置选项说明

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `server_url` | string | - | MCP 服务器 URL |
| `transport` | string | "http" | 传输协议（http/websocket）|
| `auto_register` | boolean | true | 是否自动注册发现的工具 |
| `tool_prefix` | string | "mcp_" | 工具名称前缀 |
| `selected_tools` | array | null | 要加载的特定工具列表 |
| `timeout` | integer | 30 | 请求超时时间（秒）|

### 使用自动加载器进行工具发现

```python
# 发现工具
discovered = tu.tools.mcp_auto_loader(operation="discover")

# 生成智能体工具配置
configs = tu.tools.mcp_auto_loader(operation="generate_configs")

# 直接调用 MCP 工具
result = tu.tools.mcp_auto_loader(
    operation="call_tool",
    tool_name="calculator",
    tool_arguments={"expression": "10 * 5"}
)
```

## 智能体工具配置

### 手动创建智能体工具

```json
{
    "name": "mcp_calculator",
    "description": "MCP 服务器上的计算器工具",
    "type": "MCPProxyTool",
    "server_url": "http://localhost:8000",
    "transport": "http",
    "target_tool_name": "calculator",
    "parameter": {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "要计算的数学表达式"
            }
        },
        "required": ["expression"]
    }
}
```

### 批量创建智能体工具

使用 `MCPServerDiscovery` 类批量发现和创建智能体工具：

```python
from tooluniverse.mcp_client_tool import MCPServerDiscovery
import asyncio

async def create_proxy_tools():
    # 发现服务器工具
    tool_configs = await MCPServerDiscovery.discover_server_tools(
        server_url="http://localhost:8000",
        transport="http"
    )

    # 保存配置到 JSON 文件
    import json
    with open("discovered_mcp_tools.json", "w") as f:
        json.dump(tool_configs, f, indent=2)

# 运行发现过程
asyncio.run(create_proxy_tools())
```

## 高级配置选项

### 支持的传输协议

#### HTTP 传输
```json
{
    "transport": "http",
    "server_url": "http://localhost:8000"
}
```

#### WebSocket 传输
```json
{
    "transport": "websocket",
    "server_url": "ws://localhost:8000"
}
```

### 环境变量支持

配置中可以使用环境变量：

```json
{
    "server_url": "${MCP_SERVER_URL}",
    "timeout": "${MCP_TIMEOUT:30}"
}
```

### 错误处理和重试

```json
{
    "name": "robust_mcp_client",
    "type": "MCPClientTool",
    "server_url": "http://localhost:8000",
    "timeout": 120,
    "retry_attempts": 3,
    "retry_delay": 5
}
```

## 配置文件组织

### 推荐的目录结构

```
src/tooluniverse/data/
├── mcp_client_tools.json          # 基础 MCP 客户端工具
├── expert_feedback_tools.json     # 专家反馈工具
├── analysis_tools.json            # 分析工具
└── custom_mcp_tools.json          # 自定义 MCP 工具
```

### 模块化配置示例

`expert_feedback_tools.json`:
```json
[
    {
        "name": "mcp_auto_loader_expert",
        "description": "自动发现和加载专家咨询工具",
        "type": "MCPAutoLoaderTool",
        "server_url": "http://localhost:7001/mcp",
        "tool_prefix": "expert_"
    },
    {
        "name": "consult_human_expert",
        "description": "咨询人类医疗专家",
        "type": "MCPClientTool",
        "server_url": "http://localhost:7001",
        "transport": "http",
        "mcp_tool_name": "consult_human_expert",
        "parameter": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "需要专家咨询的医疗问题"
                },
                "specialty": {
                    "type": "string",
                    "description": "需要的专业领域",
                    "default": "general"
                },
                "priority": {
                    "type": "string",
                    "enum": ["low", "normal", "high", "urgent"],
                    "default": "normal"
                }
            },
            "required": ["question"]
        }
    }
]
```

## 实际应用示例

### 示例 1: 医疗专家咨询系统

```python
# 配置专家咨询工具
expert_config = {
    "name": "medical_expert",
    "type": "MCPClientTool",
    "server_url": "https://expert-api.medical.com",
    "mcp_tool_name": "consult_expert"
}

# 使用专家工具
consultation = tu.tools.medical_expert(
    operation="call_tool",
    tool_name="consult_expert",
    tool_arguments={
        "question": "患者出现胸痛和呼吸困难，如何诊断？",
        "specialty": "cardiology",
        "priority": "high"
    }
})
```

### 示例 2: 数据分析工具集

```python
# 自动加载分析工具
analysis_loader = {
    "name": "analysis_tools_loader",
    "type": "MCPAutoLoaderTool",
    "server_url": "http://analysis-server:8080",
    "tool_prefix": "analysis_",
    "selected_tools": [
        "statistical_analysis",
        "data_visualization",
        "correlation_analysis"
    ]
}

# 运行统计分析
stats_result = tu.tools.analysis_statistical_analysis(
    data=[1, 2, 3, 4, 5],
    test_type="t_test"
)
```

## 故障排除

### 常见问题和解决方案

#### 1. 连接超时
```
错误: MCP request failed with status 408: Request Timeout
```

**解决方案**:
- 增加 `timeout` 值
- 检查网络连接
- 验证服务器 URL

#### 2. 传输协议不匹配
```
错误: Invalid transport 'invalid'. Supported: ['http', 'websocket']
```

**解决方案**:
- 确保 `transport` 设置为 "http" 或 "websocket"
- 检查服务器支持的协议

#### 3. 工具未找到
```
错误: Tool 'unknown_tool' not found on MCP server
```

**解决方案**:
- 使用 `list_tools` 操作查看可用工具
- 检查工具名称拼写
- 确认服务器已启动并运行

#### 4. 参数验证失败
```
错误: Required parameter 'question' missing
```

**解决方案**:
- 检查工具的参数 schema
- 确保提供所有必需参数
- 验证参数数据类型

### 调试技巧

#### 启用详细日志
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# 运行工具时会显示详细的请求/响应信息
```

#### 测试连接
```python
# 测试基本连接
connection_test = tu.tools.my_mcp_client(operation="list_tools")

if "error" in connection_test:
    print("连接失败:", connection_test["error"])
else:
    print("连接成功，可用工具:", len(connection_test["tools"]))
```

#### 验证工具配置
```python
# 验证自动加载器发现的工具
discovery_result = tu.tools.mcp_auto_loader(operation="discover")

print("发现的工具数量:", discovery_result["discovered_count"])
print("工具列表:", discovery_result["tools"])
```

## 最佳实践

### 1. 安全考虑
- 使用 HTTPS 连接生产环境的 MCP 服务器
- 配置适当的超时值避免长时间等待
- 验证所有输入参数

### 2. 性能优化
- 为频繁使用的工具启用缓存
- 合理设置 `timeout` 值
- 使用 `selected_tools` 只加载需要的工具

### 3. 错误处理
- 始终检查返回结果中的 `error` 字段
- 实现重试机制处理临时网络问题
- 记录详细的错误信息便于调试

### 4. 配置管理
- 使用环境变量管理敏感配置
- 将配置文件按功能模块组织
- 定期更新和验证配置

## 总结

通过本教程，你已经学会了：

1. ✅ 理解三种 MCP 工具类型的用途和特点
2. ✅ 配置和使用 MCPClientTool 进行通用 MCP 操作
3. ✅ 使用 MCPAutoLoaderTool 自动发现和加载工具
4. ✅ 创建 MCPProxyTool 进行直接工具智能体
5. ✅ 处理常见问题和故障排除
6. ✅ 应用最佳实践确保安全和性能

现在你可以将任何 MCP 服务器的工具集成到 ToolUniverse 中，扩展你的工具生态系统！

## 参考资源

- [MCP 协议规范](https://spec.modelcontextprotocol.io/)
- [ToolUniverse 官方文档](../README.md)
- [MCP 工具配置示例](../../data/mcp_client_tools.json)
- [API 参考文档](../../api/mcp_tools.rst)
