"""
ToolUniverse MCP Integration Extensions

This module extends ToolUniverse with methods to automatically discover and load
MCP tools from remote servers, providing seamless integration between local tools
and remote MCP services.
"""

from typing import List, Dict, Any


def load_mcp_tools(self, server_urls: List[str] = None, **kwargs):
    """
    Load MCP tools from remote servers into this ToolUniverse instance.

    This method automatically discovers tools from MCP servers and registers them
    as ToolUniverse tools, enabling seamless usage of remote capabilities.

    Parameters
    ----------
    server_urls : list of str, optional
        List of MCP server URLs to load tools from. Examples:

        - ["http://localhost:8001", "http://analysis-server:8002"]
        - ["ws://localhost:9000"]  # WebSocket MCP servers

        If None, attempts to discover from local MCP tool registry.

    **kwargs
        Additional configuration options:

        - tool_prefix (str): Prefix for loaded tool names (default: "mcp_")
        - timeout (int): Connection timeout in seconds (default: 30)
        - auto_register (bool): Whether to auto-register discovered tools (default: True)
        - selected_tools (list): Specific tools to load from each server
        - categories (list): Tool categories to filter by

    Returns
    -------
    dict
        Summary of loaded tools with counts and any errors encountered.

    Examples
    --------

    Load from specific servers:

    .. code-block:: python

        tu = ToolUniverse()

        # Load tools from multiple MCP servers
        result = tu.load_mcp_tools([
            "http://localhost:8001",  # Local analysis server
            "http://ml-server:8002",  # Remote ML server
            "ws://realtime:9000"      # WebSocket server
        ])

        print(f"Loaded {result['total_tools']} tools from {result['servers_connected']} servers")

    Load with custom configuration:

    .. code-block:: python

        tu.load_mcp_tools(
        server_urls=["http://localhost:8001"],
        tool_prefix="analysis\\_",
        timeout=60,
        selected_tools=["protein_analysis", "drug_interaction"]
    )
    ```

    Auto-discovery from local registry:
    ```python
    # If you have registered MCP tools locally, auto-discover their servers
    tu.load_mcp_tools()  # Uses servers from mcp_tool_registry
    ```
    """
    # Default configuration
    config = {
        "tool_prefix": "mcp_",
        "timeout": 30,
        "auto_register": True,
        "selected_tools": None,
        "categories": None,
        **kwargs,
    }

    # Get server URLs
    if server_urls is None:
        try:
            from .mcp_tool_registry import get_mcp_tool_urls

            server_urls = get_mcp_tool_urls()
        except ImportError:
            server_urls = []

    if not server_urls:
        print("📭 No MCP servers specified or discovered")
        return {"total_tools": 0, "servers_connected": 0, "errors": []}

    print(f"🔄 Loading MCP tools from {len(server_urls)} servers...")

    results = {"total_tools": 0, "servers_connected": 0, "servers": {}, "errors": []}

    for url in server_urls:
        try:
            result = self._load_tools_from_mcp_server(url, config)
            results["servers"][url] = result
            results["total_tools"] += result.get("tools_loaded", 0)
            if result.get("success", False):
                results["servers_connected"] += 1
        except Exception as e:
            error_msg = f"Failed to load from {url}: {str(e)}"
            print(f"❌ {error_msg}")
            results["errors"].append(error_msg)

    print(
        f"✅ Loaded {results['total_tools']} tools from {results['servers_connected']} servers"
    )
    return results


def _load_tools_from_mcp_server(
    self, server_url: str, config: Dict[str, Any]
) -> Dict[str, Any]:
    """Load tools from a specific MCP server."""
    try:
        # Create MCPAutoLoaderTool configuration
        loader_name = f"mcp_loader_{server_url.replace('://', '_').replace(':', '_').replace('/', '_')}"

        loader_config = {
            "name": loader_name,
            "type": "MCPAutoLoaderTool",
            "server_url": server_url,
            "auto_register": config["auto_register"],
            "tool_prefix": config["tool_prefix"],
            "timeout": config["timeout"],
        }

        # Add selected tools filter if specified
        if config["selected_tools"]:
            loader_config["selected_tools"] = config["selected_tools"]

        # Add the auto-loader configuration directly to the tools list
        self.all_tools.append(loader_config)
        self.all_tool_dict[loader_name] = loader_config

        print(f"✅ Created MCP auto-loader for {server_url}")

        # Try to discover tools immediately to get count (mimic _process_mcp_auto_loaders)
        try:
            # Import the tool registry to get the class
            from .execute_function import tool_type_mappings

            # Create auto loader instance (same as _process_mcp_auto_loaders)
            auto_loader = tool_type_mappings["MCPAutoLoaderTool"](loader_config)

            # Run auto-load process (same as _process_mcp_auto_loaders)
            import asyncio
            import warnings

            async def _run_auto_load():
                """Run auto-load with proper cleanup"""
                try:
                    result = await auto_loader.auto_load_and_register(self)
                    return result
                finally:
                    # Ensure session cleanup
                    await auto_loader._close_session()

            # Check if we're already in an event loop
            try:
                asyncio.get_running_loop()
                in_event_loop = True
            except RuntimeError:
                in_event_loop = False

            if in_event_loop:
                # In event loop - create task for later processing
                tools_count = 0
                discovery_error = (
                    "Cannot process in event loop - will be processed later"
                )
            else:
                # No event loop, safe to create one (same as _process_mcp_auto_loaders)
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", ResourceWarning)

                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        result = loop.run_until_complete(_run_auto_load())
                        tools_count = result.get("registered_count", 0)
                        discovery_error = None
                    finally:
                        loop.close()
                        asyncio.set_event_loop(None)

            return {
                "success": True,
                "tools_loaded": tools_count,
                "loader_name": loader_name,
                "server_url": server_url,
                "discovery_error": discovery_error,
            }
        except Exception as e:
            # Auto-loader created but discovery failed
            return {
                "success": True,
                "tools_loaded": 0,
                "loader_name": loader_name,
                "server_url": server_url,
                "discovery_error": str(e),
            }

    except Exception as e:
        return {"success": False, "error": str(e), "server_url": server_url}


def discover_mcp_tools(self, server_urls: List[str] = None, **kwargs) -> Dict[str, Any]:
    """
    Discover available tools from MCP servers without loading them.

    This method connects to MCP servers to discover what tools are available
    without actually registering them in ToolUniverse. Useful for exploration
    and selective tool loading.

    Parameters
    ----------
    server_urls : list of str, optional
        List of MCP server URLs to discover from
    **kwargs
        Additional options:
        - timeout (int): Connection timeout (default: 30)
        - include_schemas (bool): Include tool parameter schemas (default: True)

    Returns
    -------
    dict
        Discovery results with tools organized by server

    Examples
    --------
    .. code-block:: python

        tu = ToolUniverse()

        # Discover what's available
        discovery = tu.discover_mcp_tools([
            "http://localhost:8001",
            "http://ml-server:8002"
        ])

        # Show available tools
        for server, info in discovery["servers"].items():
            print(f"\\n{server}:")
            for tool in info.get("tools", []):
                print(f"  - {tool['name']}: {tool['description']}")
    """
    if server_urls is None:
        try:
            from .mcp_tool_registry import get_mcp_tool_urls

            server_urls = get_mcp_tool_urls()
        except ImportError:
            server_urls = []

    if not server_urls:
        return {"servers": {}, "total_tools": 0, "errors": []}

    config = {"timeout": 30, "include_schemas": True, **kwargs}

    print(f"🔍 Discovering tools from {len(server_urls)} MCP servers...")

    results = {"servers": {}, "total_tools": 0, "errors": []}

    for url in server_urls:
        try:
            # Detect transport from URL
            if url.startswith("stdio://"):
                transport = "stdio"
            elif url.startswith("ws://") or url.startswith("wss://"):
                transport = "websocket"
            else:
                transport = "http"

            # Create temporary discovery client
            discovery_config = {
                "name": f"temp_discovery_{hash(url)}",
                "description": f"Temporary MCP client for discovery from {url}",
                "type": "MCPClientTool",
                "server_url": url,
                "transport": transport,
                "timeout": config["timeout"],
                "parameter": {
                    "type": "object",
                    "properties": {
                        "operation": {
                            "type": "string",
                            "enum": [
                                "list_tools",
                                "call_tool",
                                "list_resources",
                                "read_resource",
                                "list_prompts",
                                "get_prompt",
                            ],
                        }
                    },
                    "required": ["operation"],
                },
            }

            # Use lazy loading to get the MCPClientTool class
            from .tool_registry import get_tool_class_lazy

            mcp_client_tool_class = get_tool_class_lazy("MCPClientTool")

            if mcp_client_tool_class is None:
                raise ValueError("MCPClientTool class not found in tool registry")

            # Register temporary tool for discovery
            # Use the unique name from config, not the class name
            self.register_custom_tool(
                tool_class=mcp_client_tool_class,
                tool_name=discovery_config["name"],  # Use the unique hashed name
                tool_config=discovery_config,
            )

            # Discover tools using the tools namespace
            tool_callable = getattr(self.tools, discovery_config["name"])
            discovery_result = tool_callable(operation="list_tools")

            # Check for error first
            if "error" in discovery_result:
                error_msg = discovery_result["error"]
                results["servers"][url] = {
                    "tools": [],
                    "count": 0,
                    "status": "error",
                    "error": error_msg,
                }
                print(f"❌ {url}: {error_msg}")
            elif "tools" in discovery_result:
                # Success - got tools
                tools = discovery_result["tools"]
                results["servers"][url] = {
                    "tools": tools,
                    "count": len(tools),
                    "status": "success",
                }
                results["total_tools"] += len(tools)
                print(f"✅ {url}: {len(tools)} tools discovered")
            else:
                # Unexpected response format
                error_msg = f"Unexpected response format: {discovery_result}"
                results["servers"][url] = {
                    "tools": [],
                    "count": 0,
                    "status": "error",
                    "error": error_msg,
                }
                print(f"❌ {url}: {error_msg}")

            # Clean up temporary tool
            if hasattr(self, "_remove_tool"):
                self._remove_tool(discovery_config["name"])

        except Exception as e:
            error_msg = f"Discovery failed for {url}: {str(e)}"
            results["errors"].append(error_msg)
            results["servers"][url] = {
                "tools": [],
                "count": 0,
                "status": "error",
                "error": str(e),
            }
            print(f"❌ {error_msg}")

    print(f"🔍 Discovery complete: {results['total_tools']} total tools found")
    return results


def list_mcp_connections(self) -> Dict[str, Any]:
    """
    List all active MCP connections and loaded tools.

    Returns
    -------
    dict
        Information about MCP connections, auto-loaders, and loaded tools

    Examples
    --------
    .. code-block:: python

        tu = ToolUniverse()
        tu.load_mcp_tools(["http://localhost:8001"])

        connections = tu.list_mcp_connections()
        print(f"Active MCP connections: {len(connections['connections'])}")
    """
    mcp_tools = {}
    mcp_loaders = {}

    # Find MCP-related tools in the current tool configuration
    for tool_name, tool_config in getattr(self, "tool_configs", {}).items():
        tool_type = tool_config.get("type", "")

        if tool_type == "MCPAutoLoaderTool":
            server_url = tool_config.get("server_url", "")
            mcp_loaders[tool_name] = {
                "server_url": server_url,
                "tool_prefix": tool_config.get("tool_prefix", "mcp_"),
                "auto_register": tool_config.get("auto_register", True),
                "config": tool_config,
            }
        elif tool_type in ["MCPClientTool", "MCPProxyTool"]:
            server_url = tool_config.get("server_url", "")
            mcp_tools[tool_name] = {
                "type": tool_type,
                "server_url": server_url,
                "config": tool_config,
            }

    return {
        "connections": {"auto_loaders": mcp_loaders, "direct_tools": mcp_tools},
        "total_mcp_tools": len(mcp_tools) + len(mcp_loaders),
        "servers": list(
            set(
                [config["server_url"] for config in mcp_loaders.values()]
                + [config["server_url"] for config in mcp_tools.values()]
            )
        ),
    }


# Monkey patch methods into ToolUniverse
def _patch_tooluniverse(tool_universe_cls):
    """
    Add MCP integration methods to ToolUniverse class.

    Args:
        tool_universe_cls: The ToolUniverse class to patch (passed purely to avoid circular imports)
    """
    try:
        # Add methods to ToolUniverse if they don't exist
        if not hasattr(tool_universe_cls, "load_mcp_tools"):
            tool_universe_cls.load_mcp_tools = load_mcp_tools

        if not hasattr(tool_universe_cls, "discover_mcp_tools"):
            tool_universe_cls.discover_mcp_tools = discover_mcp_tools

        if not hasattr(tool_universe_cls, "list_mcp_connections"):
            tool_universe_cls.list_mcp_connections = list_mcp_connections

        if not hasattr(tool_universe_cls, "_load_tools_from_mcp_server"):
            tool_universe_cls._load_tools_from_mcp_server = _load_tools_from_mcp_server

        # print("✅ ToolUniverse MCP integration methods added")

    except Exception as e:
        print(f"⚠️ Could not patch ToolUniverse: {e}")

