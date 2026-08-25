"""
MCP Client Tool for ToolUniverse

This module provides a tool that acts as a client to connect to an existing MCP server,
supporting all MCP functionality including tools, resources, and prompts.
"""

import json
import asyncio
import copy
import hashlib
import re
import websockets
from typing import Dict, List, Any, Optional
from urllib.parse import urljoin
import warnings
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from .base_tool import BaseTool
from .tool_registry import register_tool
from .logging_config import get_logger
import os

logger = get_logger(__name__)


def _unwrap_mcp_tool_result(result: Any) -> Any:
    """Return the value of a standard MCP tools/call response when unambiguous."""
    if not isinstance(result, dict):
        return result

    content = result.get("content")
    if result.get("isError"):
        error_parts = [
            str(item.get("text"))
            for item in content or []
            if isinstance(item, dict)
            and item.get("type") == "text"
            and item.get("text") is not None
        ]
        detail: Any = "\n".join(error_parts) or result.get("structuredContent")
        return {"status": "error", "error": detail or "remote MCP tool failed"}

    structured = result.get("structuredContent")
    if structured is not None:
        return structured

    if not isinstance(content, list) or len(content) != 1:
        return result
    item = content[0]
    if not isinstance(item, dict) or item.get("type") != "text":
        return result
    text = item.get("text")
    if not isinstance(text, str):
        return result
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return text


class BaseMCPClient:
    """
    Base MCP client with common functionality shared between MCPClientTool and MCPAutoLoaderTool.
    Provides session management, request handling, and async cleanup patterns.
    """

    def __init__(
        self,
        server_url: str,
        transport: str = "http",
        timeout: int = 30,
        headers: Optional[Dict[str, str]] = None,
        auth_env: str = "",
        http_headers_from_env: Optional[Dict[str, Any]] = None,
    ):
        self.server_url = os.path.expandvars(server_url)
        # Normalize transport for backward compatibility: treat 'stdio' as HTTP
        normalized_transport = (
            transport.lower() if isinstance(transport, str) else "http"
        )
        if normalized_transport == "stdio":
            normalized_transport = "http"
        self.transport = normalized_transport
        self.timeout = timeout
        self.http_headers_from_env = http_headers_from_env or {}
        self.session = None
        self.header_templates = dict(headers or {})
        self.auth_env = auth_env
        self.headers = {}
        for name, value in self.header_templates.items():
            expanded_name = str(name).strip()
            expanded_value = os.path.expandvars(str(value)).strip()
            if not expanded_name or "\r" in expanded_name or "\n" in expanded_name:
                raise ValueError("Invalid MCP header name")
            if "\r" in expanded_value or "\n" in expanded_value:
                raise ValueError("Invalid MCP header value")
            self.headers[expanded_name] = expanded_value
        if auth_env:
            token = os.getenv(auth_env, "").strip()
            if token:
                self.headers["Authorization"] = f"Bearer {token}"

        # Validate transport (accept 'stdio' via normalization above)
        supported_transports = ["http", "websocket"]
        if self.transport not in supported_transports:
            # Keep message concise to satisfy line length rules
            raise ValueError("Invalid transport")

        if not isinstance(self.http_headers_from_env, dict):
            raise ValueError("http_headers_from_env must be an object")

    def _resolve_http_headers(self) -> Dict[str, str]:
        """Resolve configured HTTP headers without storing secrets in tool configs."""
        headers = {}
        for header_name, header_config in self.http_headers_from_env.items():
            if (
                not isinstance(header_name, str)
                or not header_name
                or any(char in header_name for char in "\r\n:")
            ):
                raise ValueError("Invalid HTTP header name")

            if isinstance(header_config, str):
                env_name = header_config
                prefix = ""
            elif isinstance(header_config, dict):
                env_name = header_config.get("env")
                prefix = header_config.get("prefix", "")
            else:
                raise ValueError(
                    f"Invalid environment mapping for HTTP header {header_name}"
                )

            if not isinstance(env_name, str) or not re.fullmatch(
                r"[A-Za-z_][A-Za-z0-9_]*", env_name
            ):
                raise ValueError(
                    f"Invalid environment variable for HTTP header {header_name}"
                )
            if not isinstance(prefix, str) or any(char in prefix for char in "\r\n"):
                raise ValueError(f"Invalid prefix for HTTP header {header_name}")

            value = os.environ.get(env_name)
            if value:
                if any(char in value for char in "\r\n"):
                    raise ValueError(f"Invalid value for HTTP header {header_name}")
                headers[header_name] = f"{prefix}{value}"
        return headers

    async def _close_session(self):
        """Placeholder for compatibility; HTTP client calls are scoped per request."""
        return

    def _get_mcp_endpoint(self, path: str) -> str:
        """Get the full MCP endpoint URL"""
        if self.transport == "http":
            base_url = self.server_url
            if not base_url.rstrip("/").endswith("/mcp"):
                # Preserve the legacy generated endpoint for bare server URLs,
                # but keep an explicitly configured /mcp slash shape exact.
                base_url = base_url.rstrip("/") + "/mcp/"
            if not path:
                return base_url
            return urljoin(base_url.rstrip("/") + "/", path)
        return self.server_url

    async def _make_mcp_request(
        self, method: str, params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make an MCP JSON-RPC request"""
        if self.transport == "http":
            endpoint = self._get_mcp_endpoint("")
            headers = dict(self.headers)
            headers.update(self._resolve_http_headers())
            async with streamablehttp_client(
                endpoint,
                headers=headers or None,
                timeout=self.timeout,
            ) as (
                read_stream,
                write_stream,
                _,
            ):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()

                    if method == "tools/list":
                        result = await session.list_tools()
                    elif method == "tools/call":
                        if not params or "name" not in params:
                            raise ValueError("Missing tool name for tools/call")
                        result = await session.call_tool(
                            params["name"], params.get("arguments") or {}
                        )
                    elif method == "resources/list":
                        result = await session.list_resources()
                    elif method == "resources/read":
                        if not params or "uri" not in params:
                            raise ValueError("Missing uri for resources/read")
                        result = await session.read_resource(params["uri"])
                    elif method == "prompts/list":
                        result = await session.list_prompts()
                    elif method == "prompts/get":
                        if not params or "name" not in params:
                            raise ValueError("Missing prompt name for prompts/get")
                        result = await session.get_prompt(
                            params["name"], params.get("arguments")
                        )
                    else:
                        raise ValueError(f"Unsupported MCP method: {method}")

                    if hasattr(result, "model_dump"):
                        return result.model_dump(mode="json")
                    return result

        elif self.transport == "websocket":
            async with websockets.connect(self.server_url) as websocket:
                request_id = "1"
                payload = {"jsonrpc": "2.0", "id": request_id, "method": method}
                if params:
                    payload["params"] = params
                await websocket.send(json.dumps(payload))
                response = await websocket.recv()
                result = json.loads(response)

                if "error" in result:
                    raise Exception(f"MCP error: {result['error']}")

                return result.get("result", {})

        else:
            raise ValueError(f"Unsupported transport: {self.transport}")

    def _run_with_cleanup(self, async_func):
        """Common async execution pattern with proper cleanup"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(async_func())
        finally:
            try:
                pending = asyncio.all_tasks(loop)
                for task in pending:
                    task.cancel()
                if pending:
                    loop.run_until_complete(
                        asyncio.gather(*pending, return_exceptions=True)
                    )
                loop.close()
            except Exception:
                pass


@register_tool("MCPClientTool")
class MCPClientTool(BaseTool, BaseMCPClient):
    """
    A tool that acts as an MCP client to connect to existing MCP servers.
    Supports both HTTP and WebSocket transports.
    """

    def __init__(self, tool_config):
        BaseTool.__init__(self, tool_config)
        BaseMCPClient.__init__(
            self,
            server_url=tool_config.get("server_url", "http://localhost:8000"),
            transport=tool_config.get("transport", "http"),
            timeout=tool_config.get("timeout", 600),
            headers=tool_config.get("headers"),
            auth_env=tool_config.get("auth_env", ""),
            http_headers_from_env=tool_config.get("http_headers_from_env"),
        )

        # Debug logging for transport configuration
        tool_name = tool_config.get("name", "Unknown")
        logger.debug(
            f"MCP Tool Init: {tool_name} -> transport={self.transport}, server={self.server_url}"
        )

        self._tools_cache = None
        self._resources_cache = None
        self._prompts_cache = None

    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools from the MCP server"""
        if self._tools_cache is None:
            result = await self._make_mcp_request("tools/list")
            self._tools_cache = result.get("tools", [])
        return self._tools_cache

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on the MCP server"""
        params = {"name": name, "arguments": arguments}

        result = await self._make_mcp_request("tools/call", params)
        return result

    async def list_resources(self) -> List[Dict[str, Any]]:
        """List available resources from the MCP server"""
        if self._resources_cache is None:
            try:
                result = await self._make_mcp_request("resources/list")
                self._resources_cache = result.get("resources", [])
            except Exception:
                # Some servers might not support resources
                self._resources_cache = []
        return self._resources_cache

    async def read_resource(self, uri: str) -> Dict[str, Any]:
        """Read a resource from the MCP server"""
        params = {"uri": uri}
        result = await self._make_mcp_request("resources/read", params)
        return result

    async def list_prompts(self) -> List[Dict[str, Any]]:
        """List available prompts from the MCP server"""
        if self._prompts_cache is None:
            try:
                result = await self._make_mcp_request("prompts/list")
                self._prompts_cache = result.get("prompts", [])
            except Exception:
                # Some servers might not support prompts
                self._prompts_cache = []
        return self._prompts_cache

    async def get_prompt(
        self, name: str, arguments: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Get a prompt from the MCP server"""
        params = {"name": name}
        if arguments:
            params["arguments"] = arguments

        result = await self._make_mcp_request("prompts/get", params)
        return result

    def run(self, arguments):
        """
        Main run method for the tool.
        Supports different operations based on the 'operation' argument.
        """
        operation = arguments.get("operation", "call_tool")

        async def _run_async():
            try:
                if operation == "list_tools":
                    return await self._run_list_tools()
                elif operation == "call_tool":
                    return await self._run_call_tool(arguments)
                elif operation == "list_resources":
                    return await self._run_list_resources()
                elif operation == "read_resource":
                    return await self._run_read_resource(arguments)
                elif operation == "list_prompts":
                    return await self._run_list_prompts()
                elif operation == "get_prompt":
                    return await self._run_get_prompt(arguments)
                else:
                    return {
                        "status": "error",
                        "error": f"Unknown operation: {operation}",
                    }
            except Exception as e:
                return {"status": "error", "error": str(e)}
            finally:
                # Always clean up session
                await self._close_session()

        return self._run_with_cleanup(_run_async)

    async def _run_list_tools(self):
        """Run list_tools operation"""
        tools = await self.list_tools()
        return {"tools": tools}

    async def _run_call_tool(self, arguments):
        """Run call_tool operation"""
        tool_name = arguments.get("tool_name")
        tool_arguments = arguments.get("tool_arguments", {})

        if not tool_name:
            return {
                "status": "error",
                "error": "tool_name is required for call_tool operation",
            }

        result = await self.call_tool(tool_name, tool_arguments)
        return result

    async def _run_list_resources(self):
        """Run list_resources operation"""
        resources = await self.list_resources()
        return {"resources": resources}

    async def _run_read_resource(self, arguments):
        """Run read_resource operation"""
        uri = arguments.get("uri")

        if not uri:
            return {
                "status": "error",
                "error": "uri is required for read_resource operation",
            }

        result = await self.read_resource(uri)
        return result

    async def _run_list_prompts(self):
        """Run list_prompts operation"""
        prompts = await self.list_prompts()
        return {"prompts": prompts}

    async def _run_get_prompt(self, arguments):
        """Run get_prompt operation"""
        prompt_name = arguments.get("prompt_name")
        prompt_arguments = arguments.get("prompt_arguments", {})

        if not prompt_name:
            return {
                "status": "error",
                "error": "prompt_name is required for get_prompt operation",
            }

        result = await self.get_prompt(prompt_name, prompt_arguments)
        return result


@register_tool("MCPProxyTool")
class MCPProxyTool(MCPClientTool):
    """
    A proxy tool that automatically forwards tool calls to an MCP server.
    This creates individual tools for each tool available on the MCP server.
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.target_tool_name = tool_config.get("target_tool_name")
        if not self.target_tool_name:
            raise ValueError("MCPProxyTool requires 'target_tool_name' in tool_config")
        self.normalize_mcp_result = tool_config.get("normalize_mcp_result", False)
        self.require_structured_content = tool_config.get(
            "require_structured_content", False
        )
        self.output_schema = tool_config.get("return_schema")
        self.contract_sha256 = tool_config.get("mcp_contract_sha256")
        self.structured_error_field = tool_config.get("mcp_structured_error_field")

    @staticmethod
    def _error_text(result: Dict[str, Any]) -> str:
        for item in result.get("content", []):
            if isinstance(item, dict) and item.get("type") == "text":
                text = item.get("text")
                if isinstance(text, str) and text:
                    return text
        return "Remote MCP tool reported an error"

    def _normalize_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        if result.get("isError"):
            return {"status": "error", "error": self._error_text(result)}

        structured_content = result.get("structuredContent")
        if structured_content is None:
            if self.require_structured_content:
                return {
                    "status": "error",
                    "error": (
                        f"MCP tool '{self.target_tool_name}' did not return "
                        "required structuredContent"
                    ),
                }
            return result

        structured_error = None
        if self.structured_error_field and isinstance(structured_content, dict):
            structured_error = structured_content.get(self.structured_error_field)
        if structured_error is not None:
            if isinstance(structured_error, dict):
                error_message = structured_error.get("message")
                if not error_message:
                    error_message = json.dumps(structured_error, sort_keys=True)
            else:
                error_message = str(structured_error)
            return {
                "status": "error",
                "error": error_message,
                "error_details": structured_error,
            }

        if self.output_schema:
            try:
                import jsonschema

                jsonschema.validate(structured_content, self.output_schema)
            except jsonschema.ValidationError as exc:
                return {
                    "status": "error",
                    "error": (
                        f"MCP tool '{self.target_tool_name}' returned invalid "
                        f"structuredContent: {exc.message}"
                    ),
                }

        provenance = {"protocol": "mcp", "tool": self.target_tool_name}
        if self.contract_sha256:
            provenance["contract_sha256"] = self.contract_sha256
        return {
            "status": "success",
            "data": structured_content,
            "provenance": provenance,
        }

    def run(self, arguments):
        """Forward the call directly to the target tool on the MCP server"""

        async def _run_async():
            try:
                result = await self.call_tool(self.target_tool_name, arguments)
                if self.normalize_mcp_result:
                    return self._normalize_result(result)
                return _unwrap_mcp_tool_result(result)
            except Exception as e:
                return {"status": "error", "error": str(e)}
            finally:
                # Always clean up session
                await self._close_session()

        return self._run_with_cleanup(_run_async)


@register_tool("MCPServerDiscovery")
class MCPServerDiscovery:
    """
    Helper class to discover and create tool configurations for MCP servers.
    """

    @staticmethod
    async def discover_server_tools(
        server_url: str, transport: str = "http"
    ) -> List[Dict[str, Any]]:
        """
        Discover all tools available on an MCP server and return tool configurations.
        """
        # Create a temporary client to discover tools
        temp_config = {
            "server_url": server_url,
            "transport": transport,
            "name": "temp_discovery",
            "description": "Temporary tool for discovery",
        }

        client = MCPClientTool(temp_config)

        try:
            # Get available tools
            tools = await client.list_tools()

            # Create tool configurations for each discovered tool
            tool_configs = []

            for tool in tools:
                tool_name = tool.get("name", "unknown_tool")
                tool_description = tool.get(
                    "description", f"Tool {tool_name} from MCP server"
                )

                # Create a configuration for this specific tool
                config = {
                    "name": f"mcp_{tool_name}",
                    "description": tool_description,
                    "type": "MCPProxyTool",
                    "server_url": server_url,
                    "transport": transport,
                    "target_tool_name": tool_name,
                    "parameter": {
                        "type": "object",
                        "properties": tool.get("inputSchema", {}).get("properties", {}),
                        "required": tool.get("inputSchema", {}).get("required", []),
                    },
                }
                output_schema = tool.get("outputSchema")
                if isinstance(output_schema, dict):
                    config["return_schema"] = output_schema

                tool_configs.append(config)

            return tool_configs

        except Exception as e:
            logger.error(f"Error discovering tools from MCP server {server_url}: {e}")
            return []
        finally:
            await client._close_session()

    @staticmethod
    def create_mcp_tools_config(
        server_configs: List[Dict[str, str]],
    ) -> List[Dict[str, Any]]:
        """
        Create tool configurations for multiple MCP servers.

        Args:
            server_configs: List of server configurations, each containing:
                - server_url: URL of the MCP server
                - transport: 'http' or 'websocket' (optional, defaults to 'http')
                - server_name: Name prefix for tools (optional)

        Returns:
            List of tool configurations that can be loaded into ToolUniverse
        """
        all_configs = []

        for server_config in server_configs:
            server_url = server_config["server_url"]
            transport = server_config.get("transport", "http")
            server_name = server_config.get("server_name", "mcp_server")

            # Create a generic MCP client tool for this server
            client_config = {
                "name": f"{server_name}_client",
                "description": f"MCP client for server at {server_url}",
                "type": "MCPClientTool",
                "server_url": server_url,
                "transport": transport,
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
                            "description": "The MCP operation to perform",
                        },
                        "tool_name": {
                            "type": "string",
                            "description": "Name of the tool to call (required for call_tool operation)",
                        },
                        "tool_arguments": {
                            "type": "object",
                            "description": "Arguments to pass to the tool (for call_tool operation)",
                        },
                        "uri": {
                            "type": "string",
                            "description": "Resource URI (required for read_resource operation)",
                        },
                        "prompt_name": {
                            "type": "string",
                            "description": "Name of the prompt to get (required for get_prompt operation)",
                        },
                        "prompt_arguments": {
                            "type": "object",
                            "description": "Arguments to pass to the prompt (for get_prompt operation)",
                        },
                    },
                    "required": ["operation"],
                },
            }

            all_configs.append(client_config)

        return all_configs


@register_tool("MCPAutoLoaderTool")
class MCPAutoLoaderTool(BaseTool, BaseMCPClient):
    """
    An advanced MCP tool that automatically discovers and loads all tools from an MCP server.
    It can register discovered tools as individual ToolUniverse tools for seamless usage.
    """

    def __init__(self, tool_config):
        BaseTool.__init__(self, tool_config)
        BaseMCPClient.__init__(
            self,
            server_url=tool_config.get("server_url", "http://localhost:8000"),
            transport=tool_config.get("transport", "http"),
            timeout=tool_config.get("timeout", 5),
            headers=tool_config.get("headers"),
            auth_env=tool_config.get("auth_env", ""),
            http_headers_from_env=tool_config.get("http_headers_from_env"),
        )

        self.auto_register = tool_config.get("auto_register", True)
        self.tool_prefix = tool_config.get("tool_prefix", "mcp_")
        self.selected_tools = tool_config.get(
            "selected_tools", None
        )  # None means load all
        contracts = tool_config.get("tool_contracts", [])
        if not isinstance(contracts, list):
            raise ValueError("tool_contracts must be a list")
        self.tool_contracts = {
            contract.get("name"): contract
            for contract in contracts
            if isinstance(contract, dict) and contract.get("name")
        }
        self.strict_tool_contracts = tool_config.get("strict_tool_contracts", False)
        self.normalize_mcp_result = tool_config.get("normalize_mcp_result", False)
        self.require_structured_content = tool_config.get(
            "require_structured_content", False
        )
        self.structured_error_field = tool_config.get("mcp_structured_error_field")
        if self.strict_tool_contracts and not self.tool_contracts:
            raise ValueError("strict_tool_contracts requires reviewed tool_contracts")

        # Debug logging
        logger.debug(
            f"MCPAutoLoaderTool '{tool_config.get('name', 'Unknown')}' initialized with:"
        )
        logger.debug(f"  - server_url: {self.server_url}")
        logger.debug(f"  - transport: {self.transport}")
        logger.debug(f"  - auto_register: {self.auto_register}")
        logger.debug(f"  - tool_prefix: {self.tool_prefix}")
        logger.debug(f"  - selected_tools: {self.selected_tools}")
        logger.debug(f"  - timeout: {self.timeout}")

        self._discovered_tools = {}
        self._registered_tools = {}

    @staticmethod
    def _contract_sha256(tool_info: Dict[str, Any]) -> str:
        reviewed_contract = {
            "name": tool_info.get("name"),
            "inputSchema": tool_info.get("inputSchema"),
            "outputSchema": tool_info.get("outputSchema"),
        }
        encoded = json.dumps(
            reviewed_contract,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def _verify_and_pin_contracts(
        self, remote_tools: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        expected_names = self.selected_tools or list(self.tool_contracts)
        missing_remote = [name for name in expected_names if name not in remote_tools]
        if missing_remote:
            raise ValueError(
                "Reviewed MCP tools missing from server: "
                + ", ".join(sorted(missing_remote))
            )

        pinned_tools = {}
        for name in expected_names:
            reviewed = self.tool_contracts.get(name)
            if reviewed is None:
                raise ValueError(f"No reviewed MCP contract for tool: {name}")
            reviewed_hash = reviewed.get("contract_sha256")
            if not reviewed_hash:
                reviewed_hash = self._contract_sha256(reviewed)
            remote_hash = self._contract_sha256(remote_tools[name])
            if reviewed_hash != remote_hash:
                raise ValueError(f"MCP contract changed for reviewed tool: {name}")
            pinned_tool = copy.deepcopy(remote_tools[name])
            for local_field in ("description", "title", "annotations"):
                if local_field in reviewed:
                    pinned_tool[local_field] = copy.deepcopy(reviewed[local_field])
            pinned_tools[name] = pinned_tool
        return pinned_tools

    async def discover_tools(self) -> Dict[str, Any]:
        """Discover all available tools from the MCP server"""
        try:
            tools_response = await self._make_mcp_request("tools/list")
            tools = tools_response.get("tools", [])

            remote_tools = {}
            for tool in tools:
                tool_name = tool.get("name")
                if tool_name:
                    remote_tools[tool_name] = tool

            if self.strict_tool_contracts:
                self._discovered_tools = self._verify_and_pin_contracts(remote_tools)
            else:
                self._discovered_tools = remote_tools

            return self._discovered_tools
        except Exception as e:
            raise Exception(f"Failed to discover tools: {str(e)}")

    async def call_tool(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Directly call an MCP tool by name"""
        try:
            params = {"name": tool_name, "arguments": arguments}

            result = await self._make_mcp_request("tools/call", params)
            return result
        except Exception as e:
            raise Exception(f"Failed to call tool {tool_name}: {str(e)}")

    def generate_proxy_tool_configs(self) -> List[Dict[str, Any]]:
        """Generate proxy tool configurations for discovered tools"""
        configs = []

        for tool_name, tool_info in self._discovered_tools.items():
            # Skip if selected_tools is specified and this tool is not in it
            if self.selected_tools and tool_name not in self.selected_tools:
                continue

            proxy_name = f"{self.tool_prefix}{tool_name}"

            config = {
                "name": proxy_name,
                "description": tool_info.get(
                    "description", f"Auto-loaded MCP tool: {tool_name}"
                ),
                "type": "MCPProxyTool",
                "server_url": self.server_url,
                "transport": self.transport,
                "timeout": self.timeout,
                "target_tool_name": tool_name,
                "parameter": tool_info.get(
                    "inputSchema", {"type": "object", "properties": {}, "required": []}
                ),
            }
            output_schema = tool_info.get("outputSchema")
            if isinstance(output_schema, dict):
                config["return_schema"] = output_schema
            if self.http_headers_from_env:
                config["http_headers_from_env"] = copy.deepcopy(
                    self.http_headers_from_env
                )
            if self.normalize_mcp_result:
                config["normalize_mcp_result"] = True
            if self.require_structured_content:
                config["require_structured_content"] = True
            if self.structured_error_field:
                config["mcp_structured_error_field"] = self.structured_error_field
            if self.strict_tool_contracts:
                config["mcp_contract_sha256"] = self._contract_sha256(tool_info)
            if isinstance(tool_info.get("annotations"), dict):
                config["annotations"] = copy.deepcopy(tool_info["annotations"])

            if self.header_templates:
                config["headers"] = dict(self.header_templates)
            if self.auth_env:
                config["auth_env"] = self.auth_env

            configs.append(config)

        return configs

    def register_tools_in_engine(self, engine):
        """Register discovered tools using ToolUniverse public API"""
        try:
            configs = self.generate_proxy_tool_configs()

            for config in configs:
                config["type"]
                tool_name = config["name"]

                # Use public API to register tool
                engine.register_custom_tool(
                    tool_class=MCPProxyTool,
                    tool_name=tool_name,
                    tool_config=config,
                    instantiate=True,  # Immediately instantiate and cache
                )

                # Keep reference for tracking
                # Use the actual key that register_custom_tool uses
                actual_key = config.get("name", tool_name)
                self._registered_tools[tool_name] = engine.callable_functions[
                    actual_key
                ]

            return len(configs)
        except Exception as e:
            raise Exception(f"Failed to register tools: {str(e)}")

    async def auto_load_and_register(self, engine) -> Dict[str, Any]:
        """Automatically discover, load and register all MCP tools"""
        try:
            # Discover tools
            discovered = await self.discover_tools()

            logger.info(
                f"🔍 MCPAutoLoaderTool discovered {len(discovered)} tools from MCP server:"
            )
            for tool_name, tool_info in discovered.items():
                logger.info(
                    f"  📋 {tool_name}: {tool_info.get('description', 'No description')}"
                )

            # Register tools if auto_register is enabled
            if self.auto_register:
                registered_count = self.register_tools_in_engine(engine)

                logger.info(
                    f"✅ MCPAutoLoaderTool registered {registered_count} tools with prefix '{self.tool_prefix}':"
                )
                for registered_name in self._registered_tools.keys():
                    logger.info(f"  🔧 {registered_name}")

                return {
                    "discovered_count": len(discovered),
                    "registered_count": registered_count,
                    "tools": list(discovered.keys()),
                    "registered_tools": list(self._registered_tools.keys()),
                }
            else:
                logger.info(
                    "ℹ️  MCPAutoLoaderTool auto_register is disabled. Tools not registered automatically."
                )
                return {
                    "discovered_count": len(discovered),
                    "tools": list(discovered.keys()),
                    "configs": self.generate_proxy_tool_configs(),
                }
        except Exception as e:
            # The engine emits one concise, actionable availability message.
            # Keep the full exception chain at debug level for diagnostics instead
            # of printing a second, vague failure to ordinary SDK users.
            logger.debug("MCPAutoLoaderTool auto-load failed", exc_info=True)
            raise Exception(f"Auto-load failed: {str(e)}")

    def run(self, arguments):
        """Main run method for the auto-loader tool"""
        operation = arguments.get("operation")

        async def _run_async():
            try:
                if operation == "discover":
                    # Discover available tools
                    discovered = await self.discover_tools()
                    return {
                        "discovered_count": len(discovered),
                        "tools": list(discovered.keys()),
                        "tool_details": discovered,
                    }

                elif operation == "generate_configs":
                    # Generate proxy tool configurations
                    if not self._discovered_tools:
                        # Need to discover first
                        await self.discover_tools()

                    configs = self.generate_proxy_tool_configs()
                    return {"configs": configs, "count": len(configs)}

                elif operation == "call_tool":
                    # Directly call an MCP tool
                    tool_name = arguments.get("tool_name")
                    tool_arguments = arguments.get("tool_arguments", {})

                    if not tool_name:
                        raise ValueError(
                            "tool_name is required for call_tool operation"
                        )

                    result = await self.call_tool(tool_name, tool_arguments)
                    return result

                else:
                    raise ValueError(f"Unsupported operation: {operation}")
            finally:
                # Always clean up session
                await self._close_session()

        return self._run_with_cleanup(_run_async)

    def __del__(self):
        """Cleanup when object is destroyed"""
        if (
            hasattr(self, "session")
            and self.session
            and hasattr(self.session, "_connector")
        ):
            # Suppress ResourceWarnings during cleanup
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", ResourceWarning)
                try:
                    # Try to get the current loop
                    try:
                        loop = asyncio.get_running_loop()
                        # Schedule cleanup in the current loop
                        loop.create_task(self._close_session())
                    except RuntimeError:
                        # No running loop, create a new one for cleanup
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            loop.run_until_complete(self._close_session())
                        finally:
                            loop.close()
                except Exception:
                    # If all else fails, just set session to None
                    self.session = None
