"""
MCP Tool Registration System for ToolUniverse

This module provides functionality to register local tools as MCP tools and
enables automatic loading of these tools on remote servers via ToolUniverse
integration.

Usage
-----

Server Side (Tool Provider):
.. code-block:: python

    from tooluniverse.mcp_tool_registry import (
        register_mcp_tool, start_mcp_server
    )

    @register_mcp_tool(
        tool_type_name="my_analysis_tool",
        config={
            "description": "Performs custom data analysis"
        },
        mcp_config={
            "server_name": "Custom Analysis Server",
        "host": "0.0.0.0",
        "port": 8001
    }
)
class MyAnalysisTool:
    def run(self, arguments):
        return {"result": "analysis complete"}

# Start MCP server with registered tools
start_mcp_server()
```

Client Side (Tool Consumer):
```python
from tooluniverse import ToolUniverse

# Auto-discover and load MCP tools from remote servers
tu = ToolUniverse()
tu.load_mcp_tools(server_urls=["http://localhost:8001"])

# Use the remote tool
result = tu.run_tool("my_analysis_tool", {"data": "input"})
```
"""

import asyncio
from typing import Dict, Any, List, Optional

from .tool_registry import register_tool


# Import SMCP and ToolUniverse dynamically to avoid circular imports
def _get_smcp():
    """Get SMCP class with delayed import to avoid circular import"""
    from tooluniverse import SMCP

    return SMCP


def _get_tooluniverse():
    """Get ToolUniverse class with delayed import to avoid circular import"""
    from tooluniverse import ToolUniverse

    return ToolUniverse


# Global MCP tool registry
_mcp_tool_registry: Dict[str, Any] = {}
_mcp_server_configs: Dict[int, Dict[str, Any]] = {}
_mcp_server_instances: Dict[int, Any] = {}
_mcp_tool_configs: List[Dict[str, Any]] = []  # Store tool configs


def register_mcp_tool(tool_type_name=None, config=None, mcp_config=None):
    """
    Decorator to register a tool class for MCP server exposure.

    This decorator registers tools both globally (via register_tool) and for
    MCP server management. The global registration allows ToolUniverse to
    properly instantiate tools, while MCP registration controls server
    exposure. The parameters and behavior are identical to register_tool,
    with an optional mcp_config parameter for server configuration.

    Parameters
    ----------
    tool_type_name : str, optional
        Custom name for the tool type. Same as register_tool.

    config : dict, optional
        Tool configuration dictionary. Same as register_tool.

    mcp_config : dict, optional
        Additional MCP server configuration. Can include:
        - server_name: Name of the MCP server
        - host: Server host (default: "localhost")
        - port: Server port (default: 8000)
        - transport: "http" or "stdio" (default: "http")
        - auto_start: Whether to auto-start server when tool is registered

    Returns
    -------
    function
        Decorator function that registers the tool class for MCP server only.

    Examples
    --------

    MCP tool registration:
    ```python
    @register_mcp_tool('CustomToolName', config={...},
                       mcp_config={"port": 8001})
    class MyTool:
        pass

    @register_mcp_tool()  # Uses class name, default MCP config
    class AnotherTool:
        pass
    ```
    """

    def decorator(cls):
        # Step 1: Register tool class to global registry
        # This allows ToolUniverse to properly instantiate and manage the tool
        # Note: Registration doesn't mean auto-loading. The lightweight
        # ToolUniverse with keep_default_tools=False remains isolated.
        registered_cls = register_tool(tool_type_name, config)(cls)

        # Step 2: Additionally register for MCP server management
        tool_name = tool_type_name or cls.__name__
        tool_config = config or {}
        tool_description = (
            tool_config.get("description")
            or (cls.__doc__ or f"Tool: {tool_name}").strip()
        )

        # Create default parameter schema if not provided
        tool_schema = tool_config.get("parameter_schema") or {
            "type": "object",
            "properties": {
                "arguments": {"type": "object", "description": "Tool arguments"}
            },
        }

        # Default MCP server configuration
        default_mcp_config = {
            "server_name": f"MCP Server for {tool_name}",
            "host": "localhost",
            "port": 8000,
            "transport": "http",
            "auto_start": False,
            "max_workers": 5,
        }

        # Merge with provided mcp_config
        server_config = {**default_mcp_config, **(mcp_config or {})}

        # Register for MCP exposure
        tool_info = {
            "name": tool_name,
            "type": tool_type_name or cls.__name__,  # 新增：保存工具类型
            "class": registered_cls,  # Use registered class
            "description": tool_description,
            "parameter_schema": tool_schema,
            "server_config": server_config,
            "tool_config": tool_config,
        }

        _mcp_tool_registry[tool_name] = tool_info

        # Register server config by port to group tools on same server
        port = server_config["port"]
        if port not in _mcp_server_configs:
            _mcp_server_configs[port] = {"config": server_config, "tools": []}
        _mcp_server_configs[port]["tools"].append(tool_info)

        # Note: Removed _mcp_tool_configs append since we're not using global
        # registry

        print(f"✅ Registered MCP tool: {tool_name} (server port: {port})")

        # Auto-start server if requested
        auto_start = server_config.get("auto_start", False)
        if auto_start:
            start_mcp_server_for_tool(tool_name)

        return registered_cls  # Return registered class

    return decorator


def register_mcp_tool_from_config(tool_class: type, config: Dict[str, Any]):
    """
    Register an existing tool class as MCP tool using configuration.

    This function provides a programmatic way to register tools as MCP tools
    without using decorators, useful for dynamic tool registration.
    Just like register_mcp_tool decorator, this registers tools for MCP
    exposure only.

    Parameters
    ----------
    tool_class : type
        The tool class to register
    config : dict
        Configuration containing:
        - name: Tool name (required)
        - description: Tool description
        - parameter_schema: JSON schema for parameters
        - mcp_config: MCP server configuration

    Examples
    --------
    ```python
    class ExistingTool:
        def run(self, arguments):
            return {"status": "processed"}

    register_mcp_tool_from_config(ExistingTool, {
        "name": "existing_tool",
        "description": "An existing tool exposed via MCP",
        "mcp_config": {"port": 8002}
    })
    ```
    """
    name = config.get("name") or tool_class.__name__
    tool_config = {k: v for k, v in config.items() if k != "mcp_config"}
    mcp_config = config.get("mcp_config", {})

    # Use the decorator to register for MCP only
    register_mcp_tool(tool_type_name=name, config=tool_config, mcp_config=mcp_config)(
        tool_class
    )


def get_mcp_tool_configs() -> List[Dict[str, Any]]:
    """Get the MCP tool configurations for ToolUniverse."""
    return _mcp_tool_configs.copy()


def get_mcp_tool_registry() -> Dict[str, Any]:
    """Get the current MCP tool registry."""
    return _mcp_tool_registry.copy()


def get_registered_tools() -> List[Dict[str, Any]]:
    """
    Get a list of all registered MCP tools with their information.

    Returns
        List of dictionaries containing tool information including name,
        description, and port.
    """
    tools = []
    for tool_name, tool_info in _mcp_tool_registry.items():
        tools.append(
            {
                "name": tool_name,
                "description": tool_info["description"],
                "port": tool_info["server_config"]["port"],
                "class": tool_info["class"].__name__,
            }
        )
    return tools


def get_mcp_server_configs() -> Dict[int, Dict[str, Any]]:
    """Get the current MCP server configurations grouped by port."""
    return _mcp_server_configs.copy()


def start_mcp_server(port: Optional[int] = None, **kwargs):
    """
    Start MCP server(s) for registered tools.

    Parameters
    ----------
    port : int, optional
        Specific port to start server for. If None, starts servers for all
        registered tools.
    **kwargs
        Additional arguments passed to SMCP server

    Examples
    --------
    ```python
    # Start server for specific port
    start_mcp_server(port=8001)

    # Start all servers
    start_mcp_server()

    # Start with custom configuration
    start_mcp_server(max_workers=20, debug=True)
    ```
    """

    try:
        # Test if SMCP is available
        _get_smcp()
    except ImportError:
        print("❌ SMCP not available. Cannot start MCP server.")
        return

    if port is not None:
        # Start server for specific port
        if port in _mcp_server_configs:
            print("🎯 MCP server(s) starting. Press Ctrl+C to stop.")
            _start_server_for_port(port, **kwargs)
        else:
            print(f"❌ No tools registered for port {port}")
    else:
        # Start servers for all registered ports
        ports = list(_mcp_server_configs.keys())
        if len(ports) > 1:
            print(
                f"⚠️  Multiple ports registered ({len(ports)}), starting server for port {ports[0]} only"
            )
            print(f"   Other ports: {ports[1:]}")
            port_to_start = ports[0]
        else:
            port_to_start = ports[0]

        print("🎯 MCP server(s) starting. Press Ctrl+C to stop.")
        _start_server_for_port(port_to_start, **kwargs)

    # Note: No need for while True loop - run_simple() is blocking
    # Server will run until interrupted


def _start_server_for_port(port: int, **kwargs):
    """Start SMCP server for tools on a specific port."""
    if port in _mcp_server_instances:
        print(f"🔄 MCP server already running on port {port}")
        return

    server_info = _mcp_server_configs[port]
    config = server_info["config"]
    tools = server_info["tools"]

    print(f"🚀 Starting MCP server on port {port} with {len(tools)} tools...")

    # Create a lightweight ToolUniverse instance WITHOUT default tools
    # This ensures only registered MCP tools are loaded
    ToolUniverse = _get_tooluniverse()
    tu = ToolUniverse(
        tool_files={},  # Empty tool files - no default categories
        keep_default_tools=False,  # Don't load any default tools
    )

    # Register MCP tools using the public API
    for tool_info in tools:
        tool_config = {
            "name": tool_info["name"],
            "type": tool_info["type"],  # 使用正确的type字段
            "description": tool_info["description"],
            "parameter": tool_info["parameter_schema"],
            "category": "mcp_tools",
        }

        try:
            tu.register_custom_tool(
                tool_class=tool_info["class"],
                tool_name=tool_info["type"],
                tool_config=tool_config,
                instantiate=True,  # 立即实例化并缓存
            )
        except Exception as e:
            print(f"❌ Failed to register tool {tool_info['name']}: {e}")
            continue

    print(f"✅ Registered {len(tools)} MCP tool(s) using ToolUniverse API")
    tool_names = ", ".join([t["name"] for t in tools])
    print(f"   Tools: {tool_names}")

    # Create SMCP server with pre-configured lightweight ToolUniverse
    server = _get_smcp()(
        name=config["server_name"],
        tooluniverse_config=tu,  # Pass pre-configured ToolUniverse
        auto_expose_tools=True,  # Auto-expose since tools are in ToolUniverse
        search_enabled=False,  # Disable search for remote tool servers
        max_workers=config.get("max_workers", 5),
        **kwargs,
    )

    # Store server instance
    _mcp_server_instances[port] = server

    # Start server (blocking call)
    host = config["host"]
    print(f"✅ MCP server starting on {host}:{port}")
    print(f"   Server URL: http://{host}:{port}/mcp")

    try:
        # Enable stateless mode for MCPAutoLoaderTool compatibility
        server.run_simple(
            transport=config["transport"],
            host=config["host"],
            port=port,
            stateless_http=True,
        )
    except Exception as e:
        print(f"❌ Error running MCP server on port {port}: {e}")
        raise


# Note: Removed 438 lines of dead code:
# - _add_tool_to_smcp_server (lines 410-457)
# - _create_mcp_tool_from_tooluniverse_with_instance (lines 459-700)
# - _build_fastmcp_tool_function (lines 702-848)
# These functions were never called and have been replaced by SMCP's
# built-in tool exposure mechanism.


def start_mcp_server_for_tool(tool_name: str):
    """Start MCP server for a specific tool."""
    if tool_name not in _mcp_tool_registry:
        print(f"❌ Tool '{tool_name}' not found in MCP registry")
        return

    tool_info = _mcp_tool_registry[tool_name]
    port = tool_info["server_config"]["port"]
    start_mcp_server(port=port)


def stop_mcp_server(port: Optional[int] = None):
    """
    Stop MCP server(s).

    Parameters
    ----------
    port : int, optional
        Specific port to stop server for. If None, stops all servers.
    """
    if port is not None:
        if port in _mcp_server_instances:
            server = _mcp_server_instances[port]
            asyncio.create_task(server.close())
            del _mcp_server_instances[port]
            print(f"🛑 Stopped MCP server on port {port}")
        else:
            print(f"❌ No server running on port {port}")
    else:
        # Stop all servers
        for port in list(_mcp_server_instances.keys()):
            stop_mcp_server(port)


def list_mcp_tools():
    """List all registered MCP tools with their configurations."""
    if not _mcp_tool_registry:
        print("📭 No MCP tools registered")
        return

    print("📋 Registered MCP Tools:")
    print("=" * 50)

    for name, tool_info in _mcp_tool_registry.items():
        config = tool_info["server_config"]
        print(f"🔧 {name}")
        print(f"   Description: {tool_info['description']}")
        print(f"   Class: {tool_info['class'].__name__}")
        print(f"   Server: {config['host']}:{config['port']}")
        print(f"   Transport: {config['transport']}")
        print()


def get_mcp_tool_urls() -> List[str]:
    """Get list of MCP server URLs for all registered tools."""
    urls = []
    for port, server_info in _mcp_server_configs.items():
        config = server_info["config"]
        if config["transport"] == "http":
            url = f"http://{config['host']}:{port}"
            urls.append(url)
    return urls


# Convenience functions for ToolUniverse integration
def load_mcp_tools_to_tooluniverse(tu, server_urls: Optional[List[str]] = None):
    """
    Load MCP tools from servers into a ToolUniverse instance.

    Parameters
    ----------
    tu : ToolUniverse
        ToolUniverse instance to load tools into
    server_urls : list of str, optional
        List of MCP server URLs. If None, uses all registered local servers.

    Examples
    --------
    ```python
    from tooluniverse import ToolUniverse
    from tooluniverse.mcp_tool_registry import load_mcp_tools_to_tooluniverse

    tu = ToolUniverse()

    # Load from specific servers
    load_mcp_tools_to_tooluniverse(tu, [
        "http://localhost:8001",
        "http://analysis-server:8002"
    ])

    # Load from all local registered servers
    load_mcp_tools_to_tooluniverse(tu)
    ```
    """
    if server_urls is None:
        server_urls = get_mcp_tool_urls()

    if not server_urls:
        print("📭 No MCP servers available to load tools from")
        return

    print(f"🔄 Loading MCP tools from {len(server_urls)} servers...")

    for url in server_urls:
        try:
            # Create auto-loader for this server
            url_clean = url.replace(":", "_").replace("/", "_")
            loader_name = f"mcp_auto_loader_{url_clean}"
            loader_config = {
                "name": loader_name,
                "type": "MCPAutoLoaderTool",
                "server_url": url,
                "auto_register": True,
                "tool_prefix": "mcp_",
                "timeout": 30,
            }

            # Add auto-loader to ToolUniverse
            # Use lazy loading to get the MCPAutoLoaderTool class
            from .tool_registry import get_tool_class_lazy

            mcp_auto_loader_class = get_tool_class_lazy("MCPAutoLoaderTool")

            if mcp_auto_loader_class is None:
                raise ValueError("MCPAutoLoaderTool class not found in tool registry")

            tu.register_custom_tool(
                tool_class=mcp_auto_loader_class,
                tool_name="MCPAutoLoaderTool",
                tool_config=loader_config,
            )

            print(f"✅ Added MCP auto-loader for {url}")

        except Exception as e:
            print(f"❌ Failed to load tools from {url}: {e}")

    print("🎉 MCP tools loading complete!")
