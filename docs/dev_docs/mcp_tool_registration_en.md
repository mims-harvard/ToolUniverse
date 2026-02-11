# MCP Tool Registration Tutorial - Register Local Tools as MCP Tools

This tutorial demonstrates how to use ToolUniverse's new functionality to register local tools as MCP tools and automatically load them on other servers.

## 🚀 Quick Reference (60 seconds)

### Server Side - Expose Your Tool
```python
# my_mcp_server.py
from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server

@register_mcp_tool(
    tool_type_name="my_analyzer",
    config={
        "description": "Analyzes data and returns results",
        "parameter_schema": {
            "type": "object",
            "properties": {
                "data": {"type": "string", "description": "Data to analyze"}
            },
            "required": ["data"]
        }
    },
    mcp_config={
        "server_name": "My Analysis Server",
        "port": 8001,
        "host": "0.0.0.0"
    }
)
class MyAnalyzer:
    def run(self, arguments):
        data = arguments.get('data', '')
        return {"result": f"Analyzed: {data}", "success": True}

# Start server
if __name__ == "__main__":
    start_mcp_server()
```

### Client Side - Use Remote Tool
```python
# my_mcp_client.py
from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_mcp_tools(["http://localhost:8001"])

result = tu.tools.mcp_my_analyzer(
    operation="call_tool",
    tool_name="my_analyzer",
    tool_arguments={"data": "test data"}
})
print(result)
```

## 📋 Common MCP Tool Patterns

### API Service Tool
```python
@register_mcp_tool(
    tool_type_name="api_service",
    config={"description": "External API wrapper"},
    mcp_config={"port": 8001}
)
class APIService:
    def run(self, arguments):
        import requests
        try:
            response = requests.get(arguments['url'])
            return {"data": response.json(), "success": True}
        except Exception as e:
            return {"error": str(e), "success": False}
```

### Data Processor Tool
```python
@register_mcp_tool(
    tool_type_name="data_processor",
    config={
        "description": "Process and transform data",
        "parameter_schema": {
            "type": "object",
            "properties": {
                "data": {"type": "array"},
                "operation": {"type": "string", "enum": ["sum", "avg", "max"]}
            }
        }
    },
    mcp_config={"port": 8002}
)
class DataProcessor:
    def run(self, arguments):
        data = arguments['data']
        op = arguments['operation']

        if op == "sum": result = sum(data)
        elif op == "avg": result = sum(data) / len(data)
        elif op == "max": result = max(data)

        return {"result": result, "success": True}
```

## 🔧 Configuration Templates

### Simple MCP Tool
```python
@register_mcp_tool(
    tool_type_name="tool_name",
    config={
        "description": "What the tool does",
        "parameter_schema": {
            "type": "object",
            "properties": {
                "param": {"type": "string", "description": "Parameter description"}
            },
            "required": ["param"]
        }
    },
    mcp_config={"port": 8001}
)
```

### Multi-Server Setup
```python
# Text tools on port 8001
@register_mcp_tool(..., mcp_config={"port": 8001})

# Data tools on port 8002
@register_mcp_tool(..., mcp_config={"port": 8002})

# File tools on port 8003
@register_mcp_tool(..., mcp_config={"port": 8003})
```

## ❌ Common Mistakes

### ❌ Wrong: Old parameter format
```python
@register_mcp_tool(
    name="tool_name",  # Wrong!
    description="Tool description",  # Wrong!
    mcp_config={"port": 8001}
)
```

### ✅ Correct: New parameter format
```python
@register_mcp_tool(
    tool_type_name="tool_name",  # Correct!
    config={
        "description": "Tool description",  # Correct!
        "parameter_schema": {...}
    },
    mcp_config={"port": 8001}
)
```

### ❌ Wrong: Missing run method
```python
class BadTool:
    def process(self, data):  # Wrong method name
        return data
```

### ✅ Correct: Proper run method
```python
class GoodTool:
    def run(self, arguments):  # Correct method name
        return {"result": "success", "success": True}
```

## 🧪 Testing Your MCP Tools

### 1. Test Server Start
```bash
python my_mcp_server.py
# Should show: "✅ Server running on http://localhost:8001"
```

### 2. Test Tool Discovery
```python
from tooluniverse import ToolUniverse
tu = ToolUniverse()
discovery = tu.discover_mcp_tools(["http://localhost:8001"])
print(f"Found {discovery['total_tools']} tools")
```

### 3. Test Tool Execution
```python
tu.load_mcp_tools(["http://localhost:8001"])
result = tu.tools.mcp_my_tool(
    operation="call_tool",
    tool_name="my_tool",
    tool_arguments={"param": "test"}
})
print(result)
```

## 🆘 Troubleshooting

| Problem | Solution |
|---------|----------|
| Server won't start | Check if port is already in use: `lsof -i :8001` |
| Tool not discoverable | Verify `@register_mcp_tool` decorator is correct |
| Connection timeout | Increase timeout: `tu.load_mcp_tools([...], timeout=60)` |
| Wrong tool name | MCP tools are prefixed with `mcp_`: use `mcp_my_tool` |
| Parameter errors | Check `parameter_schema` matches your `run()` method |

## 📚 Full Documentation

For complete examples and advanced usage, see the sections below.

## Core Concepts

### The Problem
- You have a useful local tool
- Want to expose it for use by other ToolUniverse instances
- Need remote access through MCP protocol

### The Solution
1. Use the `@register_mcp_tool` decorator to register local tools
2. Start MCP servers to expose these tools
3. Use `load_mcp_tools()` in other ToolUniverse instances to auto-load

## Quick Start

### 1. Server Side - Register and Expose Tools

```python
# my_analysis_server.py
from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server

@register_mcp_tool(
    tool_type_name="protein_analyzer",
    config={
        "description": "Analyze protein sequences and return detailed information",
        "parameter_schema": {
            "type": "object",
            "properties": {
                "sequence": {"type": "string", "description": "Protein sequence"},
                "analysis_type": {"type": "string", "enum": ["basic", "detailed"], "default": "basic"}
            },
            "required": ["sequence"]
        }
    },
    mcp_config={
        "server_name": "Protein Analysis Server",
        "port": 8001,
        "host": "0.0.0.0"  # Allow remote access
    }
)
class ProteinAnalyzer:
    def __init__(self, tool_config=None):
        self.tool_config = tool_config

    def run(self, arguments):
        sequence = arguments.get('sequence', '')
        analysis_type = arguments.get('analysis_type', 'basic')

        # Protein analysis logic
        result = {
            "sequence_length": len(sequence),
            "molecular_weight": len(sequence) * 110,  # Simplified calculation
            "analysis_type": analysis_type,
            "success": True
        }

        if analysis_type == "detailed":
            result.update({
                "amino_acid_composition": self._analyze_composition(sequence),
                "hydrophobicity": self._calculate_hydrophobicity(sequence)
            })

        return result

    def _analyze_composition(self, sequence):
        # Amino acid composition analysis
        composition = {}
        for aa in sequence:
            composition[aa] = composition.get(aa, 0) + 1
        return composition

    def _calculate_hydrophobicity(self, sequence):
        # Hydrophobicity calculation (simplified)
        hydrophobic = 'AILMFWYV'
        hydrophobic_count = sum(1 for aa in sequence if aa in hydrophobic)
        return hydrophobic_count / len(sequence) if sequence else 0

# Start MCP server
if __name__ == "__main__":
    print("🚀 Starting Protein Analysis MCP Server...")
    start_mcp_server()  # Start servers for all registered tools
    print("✅ Server running on http://localhost:8001")
```

### 2. Client Side - Auto-load and Use Remote Tools

```python
# my_analysis_client.py
from tooluniverse import ToolUniverse

# Create ToolUniverse instance
tu = ToolUniverse()

# Auto-discover and load MCP tools
print("🔄 Loading MCP tools from remote server...")
result = tu.load_mcp_tools(["http://localhost:8001"])

print(f"✅ Loaded {result['total_tools']} tools from {result['servers_connected']} servers")

# Use remote protein analysis tool
protein_result = tu.tools.mcp_protein_analyzer(
    operation="call_tool",
    tool_name="protein_analyzer",
    tool_arguments={
        "sequence": "MKWVTFISLLFLFSSAYSRGVFRRDAHKSEVAHRFKDLGEENFKALVLIAFAQYLQQCPFEDHVKLVNEVTEFAKTCVADESAENCDKSLHTLFGDKLCTVATLRETYGEMADCCAKQEPERNECFLQHKDDNPNLPRLVRPEVDVMCTAFHDNEETFLKKYLYEIARRHPYFYAPELLFFAKRYKAAFTECCQAADKAACLLPKLDELRDEGKASSAKQRLKCASLQKFGERAFKAWAVARLSQRFPKAEFAEVSKLVTDLTKVHTECCHGDLLECADDRADLAKYICENQDSISSKLKECCEKPLLEKSHCIAEVENDEMPADLPSLAADFVESKDVCKNYAEAKDVFLGMFLYEYARRHPDYSVVLLLRLAKTYETTLEKCCAAADPHECYAKVFDEFKPLVEEPQNLIKQNCELFEQLGEYKFQNALLVRYTKKVPQVSTPTLVEVSRNLGKVGSKCCKHPEAKRMPCAEDYLSVVLNQLCVLHEKTPVSDRVTKCCTESLVNRRPCFSALEVDETYVPKEFNAETFTFHADICTLSEKERQIKKQTALVELVKHKPKATKEQLKAVMDDFAAFVEKCCKADDKETCFAEEGKKLVAASQAALGL",
        "analysis_type": "detailed"
    }
})

print("🧬 Protein Analysis Result:")
print(protein_result)

# List current MCP connections
connections = tu.list_mcp_connections()
print(f"\n🔗 Active MCP connections: {connections['total_mcp_tools']} tools")
print(f"📡 Connected servers: {connections['servers']}")
```

## Complete Usage Examples

### 1. Multi-Tool Server

```python
# multi_tool_server.py
from tooluniverse import register_mcp_tool, start_mcp_server

# Text sentiment analysis tool
@register_mcp_tool(
    name="text_sentiment",
    description="Analyze text sentiment",
    mcp_config={"port": 8001}
)
class TextSentimentTool:
    def run(self, arguments):
        text = arguments.get('text', '')

        # Simple sentiment analysis
        positive_words = ['good', 'great', 'excellent', 'amazing', 'wonderful', 'fantastic']
        negative_words = ['bad', 'terrible', 'awful', 'horrible', 'poor', 'worst']

        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)

        if positive_count > negative_count:
            sentiment = "positive"
        elif negative_count > positive_count:
            sentiment = "negative"
        else:
            sentiment = "neutral"

        return {
            "sentiment": sentiment,
            "confidence": abs(positive_count - negative_count) / max(1, positive_count + negative_count),
            "positive_indicators": positive_count,
            "negative_indicators": negative_count,
            "success": True
        }

# Data statistics tool
@register_mcp_tool(
    name="data_stats",
    description="Calculate data statistics",
    mcp_config={"port": 8001}  # Same port, same server
)
class DataStatsTool:
    def run(self, arguments):
        data = arguments.get('data', [])
        if not data:
            return {"error": "Data cannot be empty", "success": False}

        return {
            "count": len(data),
            "sum": sum(data),
            "average": sum(data) / len(data),
            "min": min(data),
            "max": max(data),
            "range": max(data) - min(data),
            "success": True
        }

# File information tool
@register_mcp_tool(
    name="file_analyzer",
    description="Analyze file information",
    mcp_config={"port": 8002}  # Different port, separate server
)
class FileAnalyzerTool:
    def run(self, arguments):
        import os
        from pathlib import Path

        filepath = arguments.get('filepath', '')
        if not filepath or not os.path.exists(filepath):
            return {"error": "File does not exist", "success": False}

        path = Path(filepath)
        stat = path.stat()

        return {
            "filename": path.name,
            "size_bytes": stat.st_size,
            "size_kb": round(stat.st_size / 1024, 2),
            "extension": path.suffix,
            "is_file": path.is_file(),
            "is_directory": path.is_dir(),
            "absolute_path": str(path.absolute()),
            "success": True
        }

if __name__ == "__main__":
    print("🚀 Starting Multi-Tool MCP Server...")

    # List registered tools
    from tooluniverse import list_mcp_tools
    list_mcp_tools()

    # Start all servers
    start_mcp_server()
    print("✅ Servers started!")
    print("   - Text & Data tools: http://localhost:8001")
    print("   - File tools: http://localhost:8002")
```

### 2. Smart Client Usage

```python
# smart_client.py
from tooluniverse import ToolUniverse

def main():
    tu = ToolUniverse()

    # 1. First discover available tools
    print("🔍 Discovering available MCP tools...")
    discovery = tu.discover_mcp_tools([
        "http://localhost:8001",
        "http://localhost:8002"
    ])

    print(f"Found {discovery['total_tools']} tools across {len(discovery['servers'])} servers:")
    for server, info in discovery['servers'].items():
        print(f"  📡 {server}: {info['count']} tools")
        for tool in info.get('tools', []):
            print(f"    - {tool['name']}: {tool['description']}")

    # 2. Load all tools
    print("\n🔄 Loading MCP tools...")
    load_result = tu.load_mcp_tools([
        "http://localhost:8001",
        "http://localhost:8002"
    ])

    print(f"✅ Loaded {load_result['total_tools']} tools")

    # 3. Use tools for analysis
    print("\n🧪 Testing tools...")

    # Text sentiment analysis
    sentiment_result = tu.tools.mcp_text_sentiment(
        operation="call_tool",
        tool_name="text_sentiment",
        tool_arguments={
            "text": "This tool is amazing! The functionality is excellent and I think it's wonderful."
        }
    })
    print(f"📝 Sentiment Analysis: {sentiment_result}")

    # Data statistics
    stats_result = tu.tools.mcp_data_stats(
        operation="call_tool",
        tool_name="data_stats",
        tool_arguments={
            "data": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        }
    })
    print(f"📊 Data Statistics: {stats_result}")

    # File analysis
    file_result = tu.tools.mcp_file_analyzer(
        operation="call_tool",
        tool_name="file_analyzer",
        tool_arguments={
            "filepath": __file__  # Analyze current file
        }
    })
    print(f"📁 File Analysis: {file_result}")

    # 4. Show connection status
    print("\n🔗 Connection Status:")
    connections = tu.list_mcp_connections()
    print(f"Total MCP tools loaded: {connections['total_mcp_tools']}")
    print(f"Active servers: {len(connections['servers'])}")
    for server in connections['servers']:
        print(f"  - {server}")

if __name__ == "__main__":
    main()
```

## Advanced Configuration

### 1. Custom Parameter Schema

```python
@register_mcp_tool(
    name="advanced_analyzer",
    description="Advanced data analysis tool",
    parameter_schema={
        "type": "object",
        "properties": {
            "data": {
                "type": "array",
                "items": {"type": "number"},
                "description": "Numerical data array"
            },
            "analysis_config": {
                "type": "object",
                "properties": {
                    "method": {"type": "string", "enum": ["linear", "polynomial", "exponential"]},
                    "confidence_level": {"type": "number", "minimum": 0.8, "maximum": 0.99},
                    "include_plots": {"type": "boolean", "default": False}
                },
                "required": ["method"]
            },
            "output_format": {
                "type": "string",
                "enum": ["json", "csv", "xml"],
                "default": "json"
            }
        },
        "required": ["data", "analysis_config"]
    },
    mcp_config={
        "server_name": "Advanced Analytics Server",
        "port": 9000,
        "max_workers": 10  # Support more concurrency
    }
)
class AdvancedAnalyzer:
    def run(self, arguments):
        # Complex analysis logic
        pass
```

### 2. Production Environment Configuration

```python
# production_server.py
@register_mcp_tool(
    name="production_tool",
    description="Production environment tool",
    mcp_config={
        "server_name": "Production Analysis Service",
        "host": "0.0.0.0",  # Listen on all interfaces
        "port": 8080,
        "transport": "http",
        "max_workers": 20,  # High concurrency support
        "timeout": 300      # 5 minute timeout
    }
)
class ProductionTool:
    def __init__(self, tool_config=None):
        # Production environment initialization
        self.setup_logging()
        self.validate_environment()

    def run(self, arguments):
        # Production-grade error handling
        try:
            result = self.process_data(arguments)
            self.log_success(result)
            return result
        except Exception as e:
            self.log_error(e)
            return {"error": str(e), "success": False}
```

### 3. Batch Registration of Existing Tools

```python
# batch_registration.py
from tooluniverse import register_mcp_tool_from_config

# Existing tool classes
class ExistingAnalysisTool:
    def run(self, arguments):
        return {"analysis": "completed"}

class ExistingProcessorTool:
    def run(self, arguments):
        return {"processing": "done"}

# Batch register as MCP tools
tools_to_register = [
    {
        "class": ExistingAnalysisTool,
        "config": {
            "name": "analysis_tool",
            "description": "Existing analysis tool",
            "mcp_config": {"port": 8001}
        }
    },
    {
        "class": ExistingProcessorTool,
        "config": {
            "name": "processor_tool",
            "description": "Existing processing tool",
            "mcp_config": {"port": 8001}
        }
    }
]

for tool_info in tools_to_register:
    register_mcp_tool_from_config(tool_info["class"], tool_info["config"])

# Start servers
from tooluniverse import start_mcp_server
start_mcp_server()
```

## Best Practices

### 1. Error Handling
```python
def run(self, arguments):
    try:
        # Validate input
        if not self.validate_input(arguments):
            return {"error": "Input validation failed", "success": False}

        # Execute logic
        result = self.process(arguments)

        # Return structured result
        return {"result": result, "success": True}

    except ValueError as e:
        return {"error": f"Parameter error: {str(e)}", "success": False}
    except Exception as e:
        return {"error": f"Processing failed: {str(e)}", "success": False}
```

### 2. Performance Optimization
```python
# Use connection pools and caching
@register_mcp_tool(
    name="optimized_tool",
    mcp_config={
        "max_workers": 10,  # Concurrent processing
        "timeout": 60       # Reasonable timeout
    }
)
class OptimizedTool:
    def __init__(self, tool_config=None):
        self.cache = {}
        self.connection_pool = self.setup_pool()

    def run(self, arguments):
        # Cache check
        cache_key = self.get_cache_key(arguments)
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Process and cache
        result = self.process(arguments)
        self.cache[cache_key] = result
        return result
```

### 3. Security Considerations
```python
@register_mcp_tool(
    name="secure_tool",
    mcp_config={
        "host": "127.0.0.1",  # Local access only
        "port": 8001
    }
)
class SecureTool:
    def run(self, arguments):
        # Input sanitization and validation
        clean_input = self.sanitize_input(arguments)

        # Permission check
        if not self.check_permissions(clean_input):
            return {"error": "Insufficient permissions", "success": False}

        # Secure processing
        return self.secure_process(clean_input)
```

## Troubleshooting

### Common Issues

1. **Server Start Failure**
   ```python
   # Check port usage
   import socket
   sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
   result = sock.connect_ex(('localhost', 8001))
   if result == 0:
       print("Port 8001 is already in use")
   ```

2. **Tools Not Discoverable**
   ```python
   # Check tool registration
   from tooluniverse import get_mcp_tool_registry
   registry = get_mcp_tool_registry()
   print("Registered MCP tools:", list(registry.keys()))
   ```

3. **Connection Timeout**
   ```python
   # Increase timeout
   tu.load_mcp_tools(["http://localhost:8001"], timeout=60)
   ```

## Summary

With this MCP tool registration system, you can:

1. ✅ **Simple Registration** - Use `@register_mcp_tool` decorator
2. ✅ **Auto Exposure** - One-click MCP server startup
3. ✅ **Seamless Integration** - Other ToolUniverse instances auto-discover and load
4. ✅ **Reuse SMCP** - Fully based on existing SMCP architecture
5. ✅ **Production Ready** - Support for concurrency, error handling, configuration management

This makes it easy to share useful local tools with team members or reuse tool functionality across different servers!
