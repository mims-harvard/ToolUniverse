"""
Scientific Model Context Protocol (SMCP) - Enhanced MCP Server with ToolUniverse Integration

SMCP is a sophisticated MCP (Model Context Protocol) server that bridges the gap between
AI agents and scientific tools. It seamlessly integrates ToolUniverse's extensive
collection of 350+ scientific tools with the MCP protocol, enabling AI systems to
access scientific databases, perform complex analyses, and execute scientific workflows.

The SMCP module provides a complete solution for exposing scientific computational
resources through the standardized MCP protocol, making it easy for AI agents to
discover, understand, and execute scientific tools in a unified manner.

Usage Patterns
--------------

Quick Start:

```python
# High-performance server with custom configuration
server = SMCP(
    name="Production Scientific API",
    tool_categories=["uniprot", "ChEMBL", "opentarget", "hpa"],
    max_workers=20,
    search_enabled=True
)
server.run_simple(
    transport="http",
    host="0.0.0.0",
    port=7000
)
```

Client Integration:
```python
# Using MCP client to discover and use tools
import json

# Discover protein analysis tools
response = await client.call_tool("find_tools", {
    "query": "protein structure analysis",
    "limit": 5
})

# Use discovered tool
result = await client.call_tool("UniProt_get_entry_by_accession", {
    "arguments": json.dumps({"accession": "P05067"})
})
```

Architecture
------------

┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   MCP Client    │◄──►│      SMCP        │◄──►│  ToolUniverse   │
│  (AI Agent)     │    │     Server       │    │   (350+ Tools)  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌──────────────────┐
                       │  Scientific      │
                       │  Databases &     │
                       │  Services        │
                       └──────────────────┘

The SMCP server acts as an intelligent middleware layer that:
1. Receives MCP requests from AI agents/clients
2. Translates requests to ToolUniverse tool calls
3. Executes tools against scientific databases/services
4. Returns formatted results via MCP protocol
5. Provides intelligent tool discovery and recommendation

Integration Points
------------------

MCP Protocol Layer:
    - Standard MCP methods (tools/list, tools/call, etc.)
    - Custom scientific methods (tools/find, tools/search)
    - Transport-agnostic communication (stdio, HTTP, SSE)
    - Proper error codes and JSON-RPC 2.0 compliance

ToolUniverse Integration:
    - Dynamic tool loading and configuration
    - Schema transformation and validation
    - Execution wrapper with error handling
    - Category-based tool organization

AI Agent Interface:
    - Natural language tool discovery
    - Contextual tool recommendations
    - Structured parameter schemas
    - Comprehensive tool documentation
"""

import asyncio
import functools
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional, Union, Callable, Literal

from fastmcp import FastMCP

FASTMCP_AVAILABLE = True

from .execute_function import ToolUniverse
from .logging_config import (
    get_logger,
)


class SMCP(FastMCP):
    """
    Scientific Model Context Protocol (SMCP) Server

    SMCP is an enhanced MCP (Model Context Protocol) server that seamlessly integrates
    ToolUniverse's extensive collection of scientific and scientific tools with the
    FastMCP framework. It provides a unified, AI-accessible interface for scientific
    computing, data analysis, and research workflows.

    The SMCP server extends standard MCP capabilities with scientific domain expertise,
    intelligent tool discovery, and optimized configurations for research applications.
    It automatically handles the complex task of exposing hundreds of specialized tools
    through a consistent, well-documented interface.

    Key Features:
    ============
    🔬 **Scientific Tool Integration**: Native access to 350+ specialized tools covering
       scientific databases, literature search, clinical data, genomics, proteomics,
       chemical informatics, and AI-powered analysis capabilities.

    🧠 **AI-Powered Tool Discovery**: Multi-tiered intelligent search system using:
       - ToolFinderLLM: Cost-optimized LLM-based semantic understanding with pre-filtering
       - Tool_RAG: Embedding-based similarity search
       - Keyword Search: Simple text matching as reliable fallback

    📡 **Full MCP Protocol Support**: Complete implementation of MCP specification with:
       - Standard methods (tools/list, tools/call, resources/*, prompts/*)
       - Custom scientific methods (tools/find, tools/search)
       - Multi-transport support (stdio, HTTP, SSE)
       - JSON-RPC 2.0 compliance with proper error handling

    ⚡ **High-Performance Architecture**: Production-ready features including:
       - Configurable thread pools for concurrent tool execution
       - Intelligent tool loading and caching
       - Resource management and graceful degradation
       - Comprehensive error handling and recovery

    🔧 **Developer-Friendly**: Simplified configuration and deployment with:
       - Sensible defaults for scientific computing
       - Flexible customization options
       - Comprehensive documentation and examples
       - Built-in diagnostic and monitoring tools

    Custom MCP Methods:
    ==================
    tools/find:
        AI-powered tool discovery using natural language queries. Supports semantic
        search, category filtering, and flexible response formats.

    tools/search:
        Alternative endpoint for tool discovery with identical functionality to
        tools/find, provided for compatibility and convenience.

    Parameters:
    ===========
    name : str, optional
        Human-readable server name used in logs and identification.
        Default: "SMCP Server"
        Examples: "Scientific Research API", "Drug Discovery Server"

    tooluniverse_config : ToolUniverse or dict, optional
        Either a pre-configured ToolUniverse instance or configuration dict.
        If None, creates a new ToolUniverse with default settings.
        Allows reuse of existing tool configurations and customizations.

    tool_categories : list of str, optional
        Specific ToolUniverse categories to load. If None and auto_expose_tools=True,
        loads all available tools. Common combinations:
        - Scientific: ["ChEMBL", "uniprot", "opentarget", "pubchem", "hpa"]
        - Literature: ["EuropePMC", "semantic_scholar", "pubtator", "agents"]
        - Clinical: ["fda_drug_label", "clinical_trials", "adverse_events"]

    exclude_tools : list of str, optional
        Specific tool names to exclude from loading. These tools will not be
        exposed via the MCP interface even if they are in the loaded categories.
        Useful for removing specific problematic or unwanted tools.

    exclude_categories : list of str, optional
        Tool categories to exclude from loading. These entire categories will
        be skipped during tool loading. Can be combined with tool_categories
        to first select categories and then exclude specific ones.

    include_tools : list of str, optional
        Specific tool names to include. If provided, only these tools will be
        loaded regardless of categories. Overrides category-based selection.

    tools_file : str, optional
        Path to a text file containing tool names to include (one per line).
        Alternative to include_tools parameter. Comments (lines starting with #)
        and empty lines are ignored.

    tool_config_files : dict of str, optional
        Additional tool configuration files to load. Format:
        {"category_name": "/path/to/config.json"}. These files will be loaded
        in addition to the default tool files.

    include_tool_types : list of str, optional
        Specific tool types to include. If provided, only tools of these types
        will be loaded. Available types include: 'OpenTarget', 'ToolFinderEmbedding',
        'ToolFinderKeyword', 'ToolFinderLLM', etc.

    exclude_tool_types : list of str, optional
        Tool types to exclude from loading. These tool types will be skipped
        during tool loading. Useful for excluding entire categories of tools
        (e.g., all ToolFinder types or all OpenTarget tools).

    space : str or list of str, optional
        Space configuration URI(s) to load. Can be a single URI string or a list
        of URIs for loading multiple Space configurations. Supported formats:
        - Local file: "./config.yaml" or "/path/to/config.yaml"
        - HuggingFace: "hf:username/repo" or "hf:username/repo/file.yaml"
        - HTTP URL: "https://example.com/config.yaml"

        When provided, Space configurations are loaded after tool initialization,
        applying LLM settings, hooks, and tool selections from the configuration files.
        Multiple spaces can be loaded sequentially, with later configurations
        potentially overriding earlier ones.

        Example: space="./my-workspace.yaml"
        Example: space=["hf:community/bio-tools", "./custom-tools.yaml"]

    auto_expose_tools : bool, default True
        Whether to automatically expose ToolUniverse tools as MCP tools.
        When True, all loaded tools become available via the MCP interface
        with automatic schema conversion and execution wrapping.

    search_enabled : bool, default True
        Enable AI-powered tool search functionality via tools/find method.
        Includes ToolFinderLLM (cost-optimized LLM-based), Tool_RAG (embedding-based),
        and simple keyword search capabilities with intelligent fallback.

    max_workers : int, default 5
        Maximum number of concurrent worker threads for tool execution.
        Higher values allow more parallel tool calls but use more resources.
        Recommended: 5-20 depending on server capacity and expected load.

    hooks_enabled : bool, default False
        Whether to enable output processing hooks for intelligent post-processing
        of tool outputs. When True, hooks can automatically summarize long outputs,
        save results to files, or apply other transformations.

    hook_config : dict, optional
        Custom hook configuration dictionary. If provided, overrides default
        hook settings. Should contain 'hooks' list with hook definitions.
        Example: {"hooks": [{"name": "summarization_hook", "type": "SummarizationHook", ...}]}

    hook_type : str, optional
        Simple hook type selection. Can be 'SummarizationHook', 'FileSaveHook',
        or a list of both. Provides an easy way to enable hooks without full configuration.
        Takes precedence over hooks_enabled when specified.

    compact_mode : bool, default False
        Enable compact mode that only exposes core tools to prevent context window overflow.
        When True:
        - Only exposes search tools (find_tools), execute tool (execute_tool),
          and tool discovery tools (list_tools, grep_tools, get_tool_info)
        - All tools are still loaded in background for execute_tool to work
        - Prevents automatic exposure of all tools, reducing context window usage
        - Maintains full functionality through search and execute capabilities
        - Tool discovery tools enable progressive disclosure: start with minimal info, request details when needed
        - Agent-friendly features: simple text search (no regex required), natural language task discovery,
          combined search+detail tools to reduce tool call overhead

    **kwargs**
        Additional arguments passed to the underlying FastMCP server instance.
        Supports all FastMCP configuration options for advanced customization.

    Raises:
    =======
    ImportError
        If FastMCP is not installed. FastMCP is a required dependency for SMCP.
        Install with: pip install fastmcp

    Notes:
    ======
    - SMCP automatically handles ToolUniverse tool loading and MCP conversion
    - Tool search uses ToolFinderLLM (optimized for cost) when available, gracefully falls back to simpler methods
    - All tools support JSON argument passing for maximum flexibility
    - Server supports graceful shutdown and comprehensive resource cleanup
    - Thread pool execution ensures non-blocking operation for concurrent requests
    - Built-in error handling provides informative debugging information
    """

    def __init__(
        self,
        name: Optional[str] = None,
        tooluniverse_config: Optional[Union[ToolUniverse, Dict[str, Any]]] = None,
        tool_categories: Optional[List[str]] = None,
        exclude_tools: Optional[List[str]] = None,
        exclude_categories: Optional[List[str]] = None,
        include_tools: Optional[List[str]] = None,
        tools_file: Optional[str] = None,
        tool_config_files: Optional[Dict[str, str]] = None,
        include_tool_types: Optional[List[str]] = None,
        exclude_tool_types: Optional[List[str]] = None,
        space: Optional[Union[str, List[str]]] = None,
        auto_expose_tools: bool = True,
        search_enabled: bool = True,
        max_workers: int = 5,
        hooks_enabled: bool = False,
        hook_config: Optional[Dict[str, Any]] = None,
        hook_type: Optional[str] = None,
        compact_mode: bool = False,
        **kwargs,
    ):
        if not FASTMCP_AVAILABLE:
            raise ImportError(
                "FastMCP is required for SMCP. Install it with: pip install fastmcp"
            )

        # Filter out SMCP-specific kwargs before passing to FastMCP
        fastmcp_kwargs = kwargs.copy()
        fastmcp_kwargs.pop("tooluniverse", None)  # Remove if accidentally passed

        # Initialize FastMCP with default settings optimized for scientific use
        super().__init__(name=name or "SMCP Server", **fastmcp_kwargs)

        # Get logger for this class
        self.logger = get_logger("SMCP")

        # Initialize ToolUniverse with hook support
        if isinstance(tooluniverse_config, ToolUniverse):
            self.tooluniverse = tooluniverse_config
        else:
            self.tooluniverse = ToolUniverse(
                tool_files=tooluniverse_config,
                keep_default_tools=True,
                hooks_enabled=hooks_enabled,
                hook_config=hook_config,
                hook_type=hook_type,
                enable_name_shortening=True,
            )

        # Configuration
        self.tool_categories = tool_categories
        self.exclude_tools = exclude_tools or []
        self.exclude_categories = exclude_categories or []
        self.include_tools = include_tools or []
        self.tools_file = tools_file
        self.tool_config_files = tool_config_files or {}
        self.include_tool_types = include_tool_types or []
        self.exclude_tool_types = exclude_tool_types or []
        self.space = space
        self.compact_mode = compact_mode
        # In compact mode, don't auto-expose all tools
        self.auto_expose_tools = False if compact_mode else auto_expose_tools
        self.search_enabled = search_enabled
        self.max_workers = max_workers
        self.hooks_enabled = hooks_enabled
        self.hook_config = hook_config
        self.hook_type = hook_type

        # Space configuration storage
        self.space_llm_config = None
        self.space_metadata = None

        # Thread pool for concurrent tool execution
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

        # Track exposed tools to avoid duplicates
        self._exposed_tools = set()

        # Initialize TaskManager for MCP Tasks support
        from .task_manager import TaskManager

        self.task_manager = TaskManager(tool_universe=self.tooluniverse)
        self._task_manager_started = False

        # Load Space configurations first if provided
        if space:
            self._load_space_configs(space)

        # Initialize SMCP-specific features (after Space is loaded)
        self._setup_smcp_tools()

        # Register custom MCP methods
        self._register_custom_mcp_methods()

    def _load_space_configs(self, space: Union[str, List[str]]):
        """
        Load Space configurations.

        This method loads Space configuration(s) and retrieves the LLM config
        and metadata from ToolUniverse. It completely reuses ToolUniverse's
        load_space functionality without reimplementing any logic.

        Args:
            space: Space URI or list of URIs (e.g., "./config.yaml",
                      "hf:user/repo", or ["config1.yaml", "config2.yaml"])
        """
        space_list = [space] if isinstance(space, str) else space

        for uri in space_list:
            self.logger.info("📦 Loading Space: %s", uri)

            # Pass filtering parameters from SMCP to load_space
            config = self.tooluniverse.load_space(
                uri,
                exclude_tools=self.exclude_tools,
                exclude_categories=self.exclude_categories,
                include_tools=self.include_tools,
                tools_file=self.tools_file,  # KEY FIX: Pass tools_file filter
                include_tool_types=self.include_tool_types,
                exclude_tool_types=self.exclude_tool_types,
            )

            # Get configurations from ToolUniverse (complete reuse)
            self.space_metadata = self.tooluniverse.get_space_metadata()
            self.space_llm_config = self.tooluniverse.get_space_llm_config()

            self.logger.info("✅ Space loaded: %s", config.get("name", "Unknown"))

    def get_llm_config(self) -> Optional[Dict[str, Any]]:
        """
        Get the current Space LLM configuration.

        Returns:
            LLM configuration dictionary or None if not set
        """
        return self.space_llm_config

    def _register_custom_mcp_methods(self):
        """
        Register custom MCP protocol methods for enhanced functionality.

        This method extends the standard MCP protocol by registering custom handlers
        for scientific tool discovery and search operations, as well as MCP Tasks
        support for long-running operations.

        Custom Methods Registered:
        =========================
        - tools/find: AI-powered tool discovery using natural language queries
        - tools/search: Alternative endpoint for tool search (alias for tools/find)
        - tasks/get: Get current task status
        - tasks/list: List all tasks
        - tasks/cancel: Cancel a running task
        - tasks/result: Wait for task completion and get result

        Implementation Details:
        ======================
        - Uses FastMCP's middleware system instead of request handler patching
        - Implements custom middleware methods for tools/find and tools/search
        - Adds MCP Tasks protocol support for long-running tool operations
        - Standard MCP methods (tools/list, tools/call) are handled by FastMCP
        - Implements proper error handling and JSON-RPC 2.0 compliance

        Notes:
        ======
        This method is called automatically during SMCP initialization and should
        not be called manually.
        """
        try:
            # Temporarily disabled for Codex compatibility
            # Add custom middleware for tools/find and tools/search
            # self.add_middleware(self._tools_find_middleware)

            # Register MCP Tasks handlers
            # Note: FastMCP should handle these via its built-in MCP Tasks support
            # but we provide our own handlers for compatibility
            self.logger.info(
                "✅ Custom MCP methods registration skipped for Codex compatibility"
            )
            self.logger.info("✅ MCP Tasks support initialized")

        except Exception as e:
            self.logger.error(f"Error registering custom MCP methods: {e}")

    def _get_valid_categories(self):
        """Get valid tool categories from ToolUniverse."""
        try:
            if hasattr(self.tooluniverse, "get_tool_types"):
                return set(self.tooluniverse.get_tool_types())
            temp_tu = ToolUniverse()
            return set(temp_tu.get_tool_types())
        except Exception as e:
            self.logger.error(f"Error getting valid categories: {e}")
            return set()

    def _load_tools_with_filters(self, tool_type=None):
        """Load tools with the common set of filter parameters.

        Centralizes the repeated pattern of calling load_tools with the same
        exclude/include/tools_file/config kwargs used across _setup_smcp_tools.
        """
        self.tooluniverse.load_tools(
            tool_type=tool_type,
            exclude_tools=self.exclude_tools,
            exclude_categories=self.exclude_categories,
            include_tools=self.include_tools,
            tools_file=self.tools_file,
            tool_config_files=self.tool_config_files,
            include_tool_types=self.include_tool_types,
            exclude_tool_types=self.exclude_tool_types,
        )

    def _ensure_compact_mode_categories(self):
        """Load tool discovery categories required for compact mode."""
        if not self.compact_mode:
            return
        for category in ("tool_finder", "compact_mode"):
            try:
                self.tooluniverse.load_tools(tool_type=[category])
            except Exception as e:
                self.logger.debug(f"Could not load category {category}: {e}")

    def _load_by_categories(self):
        """Load tools for the requested categories with validation and fallback."""
        try:
            valid_categories = self._get_valid_categories()
            invalid = [c for c in self.tool_categories if c not in valid_categories]

            if invalid:
                self.logger.warning(
                    f"Invalid categories {invalid}. Available: {list(valid_categories)}"
                )
                valid_only = [c for c in self.tool_categories if c in valid_categories]
                if valid_only:
                    self.logger.info(f"Loading valid categories: {valid_only}")
                    self._load_tools_with_filters(tool_type=valid_only)
                else:
                    self.logger.warning(
                        "No valid categories found, loading all tools instead"
                    )
                    self._load_tools_with_filters()
            else:
                self._load_tools_with_filters(tool_type=self.tool_categories)

            self._ensure_compact_mode_categories()

        except Exception as e:
            self.logger.error(f"Error loading specified categories: {e}")
            self.logger.info("Falling back to loading all tools")
            self._load_tools_with_filters()
            self._ensure_compact_mode_categories()

    async def _tools_find_middleware(self, context, call_next):
        """
        Middleware for handling tools/find and tools/search requests.

        This middleware intercepts tools/find and tools/search requests and
        provides AI-powered tool discovery functionality.
        """
        # Check if this is a tools/find or tools/search request
        if hasattr(context, "method") and context.method in [
            "tools/find",
            "tools/search",
        ]:
            try:
                # Handle the custom method
                result = await self._handle_tools_find(context.id, context.params)
                return result
            except Exception as e:
                self.logger.error(f"Error in tools/find middleware: {e}")
                return {
                    "jsonrpc": "2.0",
                    "id": context.id,
                    "error": {"code": -32603, "message": f"Internal error: {str(e)}"},
                }

        # For all other methods, call the next middleware/handler
        return await call_next(context)

    async def _handle_tools_find(
        self, request_id: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle the custom tools/find MCP method.

        Searches for tools by natural language query and returns a JSON-RPC 2.0
        response in either ``detailed`` (default) or ``mcp_standard`` format.
        """
        try:
            # Extract parameters
            query = params.get("query", "")
            categories = params.get("categories")
            limit = params.get("limit", 10)
            use_advanced_search = params.get("use_advanced_search", True)
            search_method = params.get(
                "search_method", "auto"
            )  # 'auto', 'llm', 'embedding', 'keyword'
            format_type = params.get(
                "format", "detailed"
            )  # 'detailed' or 'mcp_standard'

            if not query:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32602,
                        "message": "Invalid params: 'query' is required",
                    },
                }

            # Perform the search using existing search functionality
            search_result = await self._perform_tool_search(
                query=query,
                categories=categories,
                limit=limit,
                use_advanced_search=use_advanced_search,
                search_method=search_method,
            )

            # Parse the search result
            search_data = json.loads(search_result)

            # Handle different response formats
            if isinstance(search_data, list):
                # If search_data is a list, treat it as tools directly
                tools_list = search_data
                search_metadata = {
                    "search_query": query,
                    "search_method": "unknown",
                    "total_matches": len(tools_list),
                    "categories_filtered": categories,
                }
            elif isinstance(search_data, dict):
                # If search_data is a dict, extract tools and metadata
                tools_list = search_data.get("tools", [])
                search_metadata = {
                    "search_query": query,
                    "search_method": search_data.get("search_method", "unknown"),
                    "total_matches": search_data.get("total_matches", len(tools_list)),
                    "categories_filtered": categories,
                }
            else:
                # Fallback for unexpected format
                tools_list = []
                search_metadata = {
                    "search_query": query,
                    "search_method": "unknown",
                    "total_matches": 0,
                    "categories_filtered": categories,
                }

            # Format response based on requested format
            if format_type == "mcp_standard":
                # Format as standard MCP tools/list style response
                mcp_tools_list = []
                for tool in tools_list:
                    mcp_tool = {
                        "name": tool.get("name"),
                        "description": tool.get("description", ""),
                        "inputSchema": {
                            "type": "object",
                            "properties": tool.get("parameters", {}),
                            "required": tool.get("required", []),
                        },
                    }
                    mcp_tools_list.append(mcp_tool)

                result = {
                    "tools": mcp_tools_list,
                    "_meta": search_metadata,
                }
            else:
                # Return detailed format (default)
                result = search_data

            return {"jsonrpc": "2.0", "id": request_id, "result": result}

        except json.JSONDecodeError as e:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": f"Search result parsing error: {str(e)}",
                },
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": f"Internal error in tools/find: {str(e)}",
                },
            }

    # -- MCP Tasks Protocol Handlers --

    async def _ensure_task_manager(self) -> None:
        """Start the task manager if it has not been started yet."""
        if not self._task_manager_started:
            await self.task_manager.start()
            self._task_manager_started = True

    async def handle_tasks_get(
        self, task_id: str, auth_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get current task status."""
        await self._ensure_task_manager()
        return await self.task_manager.get_status(task_id, auth_context)

    async def handle_tasks_list(
        self, auth_context: Optional[str] = None, cursor: Optional[str] = None
    ) -> Dict[str, Any]:
        """List all tasks."""
        await self._ensure_task_manager()
        return await self.task_manager.list_tasks(auth_context, cursor)

    async def handle_tasks_cancel(
        self, task_id: str, auth_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Cancel a running task."""
        await self._ensure_task_manager()
        return await self.task_manager.cancel_task(task_id, auth_context)

    async def handle_tasks_result(
        self,
        task_id: str,
        auth_context: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Wait for task completion and return its result."""
        await self._ensure_task_manager()
        result = await self.task_manager.get_result(task_id, auth_context, timeout)
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(result, ensure_ascii=False),
                }
            ],
            "_meta": {
                "io.modelcontextprotocol/related-task": {
                    "taskId": task_id,
                },
            },
        }

    async def _perform_tool_search(
        self,
        query: str,
        categories: Optional[List[str]],
        limit: int,
        use_advanced_search: bool,
        search_method: str = "auto",
    ) -> str:
        """
        Execute tool search using the most appropriate search method available.

        Simplified unified interface that leverages the consistent tool interfaces.
        All search tools now return JSON format directly.

        Parameters:
        ===========
        query : str
            Natural language query describing the desired tool functionality
        categories : list of str, optional
            Tool categories to filter results by
        limit : int
            Maximum number of tools to return
        use_advanced_search : bool
            Whether to prefer AI-powered search when available
        search_method : str, default 'auto'
            Specific search method: 'auto', 'llm', 'embedding', 'keyword'

        Returns:
        ========
        str
            JSON string containing search results
        """
        try:
            # Determine which tool to use based on method and availability
            tool_name = self._select_search_tool(search_method, use_advanced_search)

            # Prepare unified function call - all search tools now use same interface
            function_call = {
                "name": tool_name,
                "arguments": {"description": query, "limit": limit},
            }

            # Add categories only if provided to avoid validation issues
            if categories is not None:
                function_call["arguments"]["categories"] = categories

            # Execute the search tool
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor, self.tooluniverse.run_one_function, function_call
            )

            # All search tools now return JSON format directly
            # Ensure result is properly serialized to JSON
            if isinstance(result, str):
                # Try to parse as JSON to validate, if fails wrap it
                try:
                    json.loads(result)
                    return result
                except (json.JSONDecodeError, ValueError):
                    # Not valid JSON, wrap it
                    return json.dumps(
                        {"tools": [], "result": result}, ensure_ascii=False
                    )
            elif isinstance(result, dict) or isinstance(result, list):
                return json.dumps(result, ensure_ascii=False, default=str)
            else:
                # For other types, convert to JSON
                return json.dumps(
                    {"tools": [], "result": str(result)}, ensure_ascii=False
                )

        except Exception as e:
            error_msg = f"Search error: {str(e)}"
            self.logger.error(
                f"_perform_tool_search failed: {error_msg}", exc_info=True
            )
            return json.dumps(
                {
                    "error": error_msg,
                    "error_type": type(e).__name__,
                    "query": query,
                    "tools": [],
                },
                ensure_ascii=False,
            )

    def _select_search_tool(self, search_method: str, use_advanced_search: bool) -> str:
        """
        Select the appropriate search tool based on method and availability.

        Returns:
            str: Tool name to use for search
        """
        # Get available tools
        all_tools = self.tooluniverse.return_all_loaded_tools()
        available_tool_names = [tool.get("name", "") for tool in all_tools]

        # Handle specific method requests
        if search_method == "keyword":
            return "Tool_Finder_Keyword"
        elif search_method == "llm" and "Tool_Finder_LLM" in available_tool_names:
            return "Tool_Finder_LLM"
        elif search_method == "embedding" and "Tool_Finder" in available_tool_names:
            return "Tool_Finder"
        elif search_method == "auto":
            # Auto-selection priority: Keyword > RAG > LLM
            if use_advanced_search:
                if "Tool_Finder_Keyword" in available_tool_names:
                    return "Tool_Finder_Keyword"
                if "Tool_Finder" in available_tool_names:
                    return "Tool_Finder"
                elif "Tool_Finder_LLM" in available_tool_names:
                    return "Tool_Finder_LLM"
        else:
            # Invalid method or method not available, fallback to keyword
            return "Tool_Finder_Keyword"

    def _setup_smcp_tools(self):
        """Initialize ToolUniverse tools, expose them as MCP tools, and set up search.

        Handles: pre-loaded tool detection, category validation and loading with
        fallback, compact mode discovery categories, tool exposure to MCP,
        search initialization, and utility tool registration.
        """
        # Determine if ToolUniverse already has tools loaded
        preloaded_tools = getattr(self.tooluniverse, "all_tools", [])
        preloaded_count = (
            len(preloaded_tools) if isinstance(preloaded_tools, list) else 0
        )
        space_loaded = (
            self.space
            and hasattr(self.tooluniverse, "_current_space_config")
            and preloaded_count > 0
        )

        if preloaded_count > 0:
            self.logger.info(
                f"ToolUniverse already pre-configured with {preloaded_count} tool(s); skipping automatic loading."
            )
            self._ensure_compact_mode_categories()

        if space_loaded:
            self.logger.info(
                f"Space configuration loaded {preloaded_count} tool(s), skipping additional loading"
            )
            self._ensure_compact_mode_categories()
        elif preloaded_count == 0 and self.tool_categories:
            self._load_by_categories()
        elif (self.auto_expose_tools or self.compact_mode) and not space_loaded:
            # Load all tools by default (unless Space already handled it)
            self._load_tools_with_filters()
            self._ensure_compact_mode_categories()
            if self.compact_mode:
                self.logger.info(
                    f"Compact mode: Loaded {len(self.tooluniverse.all_tools)} tools in background"
                )

        # Auto-expose ToolUniverse tools as MCP tools
        # In compact mode, _expose_tooluniverse_tools will call _expose_core_discovery_tools
        if self.auto_expose_tools or self.compact_mode:
            self._expose_tooluniverse_tools()

        # Add search functionality if enabled
        if self.search_enabled:
            self._add_search_tools()

        # Add utility tools
        self._add_utility_tools()

    def _expose_tooluniverse_tools(self):
        """Convert and register loaded ToolUniverse tools as MCP-compatible tools.

        Skips meta-tools (MCPAutoLoaderTool, MCPClientTool) and tracks already-exposed
        tools to prevent duplicates. Individual tool failures are logged but do not
        halt the process.
        """
        if not hasattr(self.tooluniverse, "all_tools"):
            self.logger.warning("No all_tools attribute in tooluniverse")
            return

        # Skip automatic tool exposure in compact mode
        if self.compact_mode:
            self.logger.info(
                "Compact mode: Skipping automatic tool exposure. "
                "Only core tools will be exposed."
            )
            # In compact mode, explicitly expose only core discovery tools
            self._expose_core_discovery_tools()
            return

        self.logger.info(
            f"Exposing {len(self.tooluniverse.all_tools)} tools from ToolUniverse"
        )

        # Define tool types that should not be exposed as MCP tools
        # These are internal/meta tools that are used for loading other tools
        skip_tool_types = {"MCPAutoLoaderTool", "MCPClientTool"}

        for i, tool_config in enumerate(self.tooluniverse.all_tools):
            try:
                # Debug: Check the type of tool_config
                if not isinstance(tool_config, dict):
                    self.logger.warning(
                        f"tool_config at index {i} is not a dict, it's {type(tool_config)}: {tool_config}"
                    )
                    continue

                tool_name = tool_config.get("name")
                tool_type = tool_config.get("type")

                # Skip internal/meta tools that are used for loading other tools
                if tool_type in skip_tool_types:
                    self.logger.debug(
                        f"Skipping exposure of meta tool: {tool_name} (type: {tool_type})"
                    )
                    continue

                if tool_name and tool_name not in self._exposed_tools:
                    # tool_name is already shortened (primary identifier)
                    self._create_mcp_tool_from_tooluniverse(tool_config, tool_name)
                    self._exposed_tools.add(tool_name)

            except Exception as e:
                self.logger.error(f"Error processing tool at index {i}: {e}")
                self.logger.debug(f"Tool config: {tool_config}")
                continue

        exposed_count = len(self._exposed_tools)
        self.logger.info(f"Successfully exposed {exposed_count} tools to MCP interface")

    def _expose_core_discovery_tools(self):
        """
        Expose only core tool discovery tools in compact mode.
        """
        core_tool_names = [
            "list_tools",
            "grep_tools",
            "get_tool_info",
            "execute_tool",
        ]

        exposed_count = 0
        for tool_config in self.tooluniverse.all_tools:
            if not isinstance(tool_config, dict):
                continue

            tool_name = tool_config.get("name")
            if tool_name in core_tool_names:
                try:
                    if tool_name not in self._exposed_tools:
                        self._create_mcp_tool_from_tooluniverse(tool_config)
                        self._exposed_tools.add(tool_name)
                        exposed_count += 1
                        self.logger.debug(f"Exposed core tool: {tool_name}")
                except Exception as e:
                    self.logger.warning(f"Failed to expose core tool {tool_name}: {e}")

        self.logger.info(f"Compact mode: Exposed {exposed_count} core discovery tools")

    def _add_search_tools(self):
        """Register the ``find_tools`` MCP tool for AI-powered tool discovery.

        Initializes the tool finder (ToolFinderLLM > Tool_RAG > keyword fallback)
        and registers a ``find_tools`` MCP tool that delegates to ``_perform_tool_search``.
        """

        # Initialize tool finder (prefer LLM-based if available, fallback to embedding-based)
        self._init_tool_finder()

        if "tool_finder" in (self.exclude_categories or []):
            self.logger.info(
                "🚫 Skipping 'find_tools' registration (tool_finder excluded)"
            )
            return

        from mcp.types import ToolAnnotations

        @self.tool(
            annotations=ToolAnnotations(
                readOnlyHint=True,  # Search tool is read-only
                destructiveHint=False,
            )
        )
        async def find_tools(
            query: str,
            categories: Optional[List[str]] = None,
            limit: int = 10,
            use_advanced_search: bool = True,
            search_method: str = "auto",
        ) -> str:
            """
            Find and search available ToolUniverse tools using AI-powered search.

            This tool provides the same functionality as the tools/find MCP method.

            Args:
                query: Search query describing the desired functionality
                categories: Optional list of categories to filter by
                limit: Maximum number of results to return (default: 10)
                use_advanced_search: Use AI-powered search if available (default: True)
                search_method: Specific search method - 'auto', 'llm', 'embedding', 'keyword' (default: 'auto')

            Returns:
                JSON string containing matching tools with detailed information
            """
            return await self._perform_tool_search(
                query, categories, limit, use_advanced_search, search_method
            )

        # # Keep the original search_tools as an alias for backward compatibility
        # @self.tool()
        # async def search_tools(
        #     query: str,
        #     categories: Optional[List[str]] = None,
        #     limit: int = 10,
        #     use_advanced_search: bool = True,
        #     search_method: str = 'auto'
        # ) -> str:
        #     """
        #     Search available ToolUniverse tools (alias for find_tools).

        #     Args:
        #         query: Search query string describing the desired functionality
        #         categories: Optional list of categories to filter by
        #         limit: Maximum number of results to return
        #         use_advanced_search: Whether to use AI-powered tool finder
        #         search_method: Specific search method - 'auto', 'llm', 'embedding', 'keyword' (default: 'auto')

        #     Returns:
        #         JSON string containing matching tools information
        #     """
        #     return await self._perform_tool_search(query, categories, limit, use_advanced_search, search_method)

    def _init_tool_finder(self):
        """Initialize the best available tool finder (LLM > RAG > keyword).

        Sets ``self.tool_finder_available`` and ``self.tool_finder_type``.
        Attempts to load the ``tool_finder`` category if no search tools
        are found among the already-loaded tools.
        """
        self.tool_finder_available = False
        self.tool_finder_type = None

        # Check if ToolFinderLLM is available in loaded tools
        try:
            all_tools = self.tooluniverse.return_all_loaded_tools()
            available_tool_names = [tool.get("name", "") for tool in all_tools]

            # Try ToolFinderLLM first (more advanced)
            if "Tool_Finder_LLM" in available_tool_names:
                self.tool_finder_available = True
                self.tool_finder_type = "Tool_Finder_LLM"
                self.logger.info("✅ Tool_Finder_LLM available for advanced search")
                return

            # Fallback to Tool_RAG (embedding-based)
            if "Tool_RAG" in available_tool_names:
                self.tool_finder_available = True
                self.tool_finder_type = "Tool_RAG"
                self.logger.info(
                    "✅ Tool_RAG (embedding-based) available for advanced search"
                )
                return

            # Check if ToolFinderKeyword is available for simple search
            if "Tool_Finder_Keyword" in available_tool_names:
                self.logger.info("✅ ToolFinderKeyword available for simple search")

            self.logger.warning("⚠️ No advanced tool finders available in loaded tools")
            self.logger.debug(
                f"Available tools: {available_tool_names[:5]}..."
            )  # Show first 5 tools
        except Exception as e:
            self.logger.warning(f"⚠️ Failed to check for tool finders: {e}")

        # Try to load tool finder tools if not already loaded
        try:
            # Respect exclude_categories - don't load if explicitly excluded
            if "tool_finder" in (self.exclude_categories or []):
                self.logger.debug("tool_finder category is excluded, skipping load")
            elif not self.tool_finder_available:
                # Only load if search tools aren't already available
                self.logger.info(
                    "Attempting to load tool_finder category for search functionality"
                )
                try:
                    self.tooluniverse.load_tools(tool_type=["tool_finder"])
                except Exception as e:
                    self.logger.debug(f"Could not load tool_finder category: {e}")

            # Re-check availability after potential loading
            all_tools = self.tooluniverse.return_all_loaded_tools()
            available_tool_names = [tool.get("name", "") for tool in all_tools]

            if "Tool_Finder_LLM" in available_tool_names:
                self.tool_finder_available = True
                self.tool_finder_type = "Tool_Finder_LLM"
                self.logger.info(
                    "✅ Successfully loaded Tool_Finder_LLM for advanced search"
                )
            elif "Tool_RAG" in available_tool_names:
                self.tool_finder_available = True
                self.tool_finder_type = "Tool_RAG"
                self.logger.info("✅ Successfully loaded Tool_RAG for advanced search")
            else:
                self.logger.warning("⚠️ Failed to load any advanced tool finder tools")

            # Check if ToolFinderKeyword is available for simple search
            if "Tool_Finder_Keyword" in available_tool_names:
                self.logger.info("✅ Tool_Finder_Keyword available for simple search")
            else:
                self.logger.warning(
                    "⚠️ ToolFinderKeyword not available, using fallback search"
                )

        except Exception as e:
            self.logger.warning(f"⚠️ Failed to load tool finder tools: {e}")
            self.logger.info(
                "📝 Advanced search will not be available, using simple keyword search only"
            )

    def _add_utility_tools(self):
        """Register utility tools (currently a no-op; execute_tool is a native ToolUniverse tool)."""

        # Note: execute_tool is now a ToolUniverse native tool
        # It is exposed via _expose_core_discovery_tools() in compact mode
        # or via _expose_tooluniverse_tools() in normal mode

    def add_custom_tool(
        self, name: str, function: Callable, description: Optional[str] = None, **kwargs
    ):
        """Add a custom Python function as an MCP tool.

        Args:
            name: Unique tool name for the MCP interface.
            function: Sync or async callable to register.
            description: If provided, overrides the function's docstring.
            **kwargs: Additional FastMCP tool configuration options.

        Returns:
            The decorated function registered with FastMCP.
        """
        if description:
            function.__doc__ = description

        # Use FastMCP's tool decorator
        decorated_function = self.tool(name=name, **kwargs)(function)
        return decorated_function

    def _get_tool_annotations(self, tool_config: Dict[str, Any]) -> Dict[str, bool]:
        """
        Get MCP tool annotations from tool config.

        Annotations should already be computed and stored in tool_config['mcp_annotations']
        during tool registration. This method simply retrieves them, with a fallback
        to compute them if they're missing (for backward compatibility).

        Parameters
        ----------
        tool_config : dict
            Tool configuration dictionary

        Returns
        -------
        dict
            Dictionary with readOnlyHint and destructiveHint boolean values
        """
        # Check if annotations are already in tool_config (preferred)
        if "mcp_annotations" in tool_config:
            return tool_config["mcp_annotations"]

        # Fallback: compute annotations if not present (backward compatibility)
        from .tool_defaults import get_annotations_for_tool

        return get_annotations_for_tool(tool_config=tool_config)

    async def close(self):
        """Gracefully shut down the SMCP server, stopping the task manager and thread pool."""
        try:
            # Stop TaskManager
            if self._task_manager_started:
                await self.task_manager.stop()
                self.logger.info("TaskManager stopped")
        except Exception as e:
            self.logger.error(f"Error stopping TaskManager: {e}")

        try:
            # Shutdown thread pool
            self.executor.shutdown(wait=True)
        except Exception:
            pass

    def _print_tooluniverse_banner(self):
        """Print ToolUniverse branding banner after FastMCP banner with dynamic information."""
        # Get transport info if available
        transport_display = getattr(self, "_transport_type", "Unknown")
        server_url = getattr(self, "_server_url", "N/A")
        tools_count = len(self._exposed_tools)

        # Map transport types to display names
        transport_map = {
            "stdio": "STDIO",
            "streamable-http": "Streamable-HTTP",
            "http": "HTTP",
            "sse": "SSE",
        }
        transport_name = transport_map.get(transport_display, transport_display)

        # Format lines with proper alignment (matching FastMCP style)
        # Each line should be exactly 75 characters (emoji takes 2 display widths but counts as 1 in len())
        transport_line = f"                 📦 Transport:       {transport_name}"
        server_line = f"                 🔗 Server URL:      {server_url}"
        tools_line = f"                 🧰 Loaded Tools:    {tools_count}"

        # Pad to exactly 75 characters (emoji counts as 1 in len() but displays as 2)
        transport_line = transport_line + " " * (75 - len(transport_line))
        server_line = server_line + " " * (75 - len(server_line))
        tools_line = tools_line + " " * (75 - len(tools_line))

        banner = f"""
╭────────────────────────────────────────────────────────────────────────────╮
│                                                                            │
│                         🧬 ToolUniverse SMCP Server 🧬                     │
│                                                                            │
│            Bridging AI Agents with Scientific Computing Tools              │
│                                                                            │
│{transport_line}│
│{server_line}│
│{tools_line}│
│                                                                            │
│                 🌐 Website:  https://aiscientist.tools/                    │
│                 💻 GitHub:   https://github.com/mims-harvard/ToolUniverse  │
│                                                                            │
╰────────────────────────────────────────────────────────────────────────────╯
"""
        # In stdio mode, ensure the banner goes to stderr to avoid polluting stdout
        # which must exclusively carry JSON-RPC messages.
        import sys as _sys

        if getattr(self, "_transport_type", None) == "stdio":
            print(banner, file=_sys.stderr)
        else:
            print(banner)

    def run(self, *args, **kwargs):
        """
        Override run method to display ToolUniverse banner after FastMCP banner.

        This method intercepts the parent's run() call to inject our custom banner
        immediately after FastMCP displays its startup banner.
        """
        # Save transport information for banner display
        transport = kwargs.get("transport", args[0] if args else "unknown")
        host = kwargs.get("host", "0.0.0.0")
        port = kwargs.get("port", 7000)

        self._transport_type = transport

        # Build server URL based on transport
        if transport == "streamable-http" or transport == "http":
            self._server_url = f"http://{host}:{port}/mcp"
        elif transport == "sse":
            self._server_url = f"http://{host}:{port}"
        else:
            self._server_url = "N/A (stdio mode)"

        # Use threading to print our banner shortly after FastMCP's banner
        import threading
        import time

        def delayed_banner():
            """Print ToolUniverse banner with a small delay to appear after FastMCP banner."""
            time.sleep(1.0)  # Delay to ensure FastMCP banner displays first
            self._print_tooluniverse_banner()

        # Start banner thread only on first run
        if not hasattr(self, "_tooluniverse_banner_shown"):
            self._tooluniverse_banner_shown = True
            banner_thread = threading.Thread(target=delayed_banner, daemon=True)
            banner_thread.start()

        # Call parent's run method (blocking call)
        return super().run(*args, **kwargs)

    def run_simple(
        self,
        transport: Literal["stdio", "http", "sse"] = "http",
        host: str = "0.0.0.0",
        port: int = 7000,
        **kwargs,
    ):
        """Start the SMCP server with the given transport.

        Args:
            transport: Communication protocol - "stdio", "http", or "sse".
            host: Bind address for HTTP/SSE transports.
            port: Port for HTTP/SSE transports.
            **kwargs: Additional arguments passed to FastMCP's run().
        """
        self.logger.info(f"🚀 Starting SMCP server '{self.name}'...")
        self.logger.info(
            f"📊 Loaded {len(self._exposed_tools)} tools from ToolUniverse"
        )
        self.logger.info(f"🔍 Search enabled: {self.search_enabled}")

        # Log hook configuration
        if self.hooks_enabled or self.hook_type:
            if self.hook_type:
                self.logger.info(f"🔗 Hooks enabled: {self.hook_type}")
            elif self.hook_config:
                hook_count = len(self.hook_config.get("hooks", []))
                self.logger.info(f"🔗 Hooks enabled: {hook_count} custom hooks")
            else:
                self.logger.info("🔗 Hooks enabled: default configuration")
        else:
            self.logger.info("🔗 Hooks disabled")

        # Configure logger for stdio mode to avoid stdout pollution
        if transport == "stdio":
            import logging
            import sys

            # Redirect all logger output to stderr for stdio mode
            for handler in self.logger.handlers[:]:
                self.logger.removeHandler(handler)

            stderr_handler = logging.StreamHandler(sys.stderr)
            stderr_handler.setLevel(logging.INFO)
            formatter = logging.Formatter("%(message)s")
            stderr_handler.setFormatter(formatter)
            self.logger.addHandler(stderr_handler)
            self.logger.setLevel(logging.INFO)

            # Also redirect root logger to stderr
            root_logger = logging.getLogger()
            for handler in root_logger.handlers[:]:
                root_logger.removeHandler(handler)
            root_logger.addHandler(stderr_handler)
            root_logger.setLevel(logging.INFO)

        try:
            if transport == "stdio":
                self.run(transport="stdio", **kwargs)
            elif transport == "http":
                self.run(transport="streamable-http", host=host, port=port, **kwargs)
            elif transport == "sse":
                self.run(transport="sse", host=host, port=port, **kwargs)
            else:
                raise ValueError(f"Unsupported transport: {transport}")

        except KeyboardInterrupt:
            self.logger.info("\n🛑 Server stopped by user")
        except Exception as e:
            self.logger.error(f"❌ Server error: {e}")
        finally:
            # Cleanup
            asyncio.run(self.close())

    # ------------------------------------------------------------------
    # JSON Schema -> Python type helpers for MCP tool construction
    # ------------------------------------------------------------------

    # Simple JSON Schema type -> Python type mapping (with lenient str coercion)
    _SIMPLE_TYPE_MAP = {
        "string": str,
        "integer": Union[int, str],
        "number": Union[float, str],
        "boolean": Union[bool, str],
        "array": list,
        "object": dict,
    }

    @staticmethod
    def _resolve_oneof_type(param_info: Dict[str, Any]) -> tuple:
        """Convert a JSON Schema oneOf spec to (python_type, field_kwargs_update).

        Returns:
            (python_type, extra_field_kwargs) where extra_field_kwargs may contain
            json_schema_extra with the oneOf schema.
        """
        one_of_types: List = []
        one_of_schemas: List = []
        for item in param_info["oneOf"]:
            item_type = item.get("type")
            if item_type == "string":
                one_of_types.append(str)
                one_of_schemas.append({"type": "string"})
            elif item_type == "array":
                items = item.get("items", {})
                if items.get("type") == "string":
                    one_of_types.append(list[str])
                    one_of_schemas.append(
                        {"type": "array", "items": {"type": "string"}}
                    )
                else:
                    one_of_types.append(list)
                    one_of_schemas.append({"type": "array", "items": items})
            elif item_type == "integer":
                one_of_types.append(int)
                one_of_schemas.append({"type": "integer"})
            elif item_type == "number":
                one_of_types.append(float)
                one_of_schemas.append({"type": "number"})
            elif item_type == "boolean":
                one_of_types.append(bool)
                one_of_schemas.append({"type": "boolean"})
            elif item_type == "object":
                one_of_types.append(dict)
                one_of_schemas.append(item)

        if len(one_of_types) == 0:
            python_type = str
        elif len(one_of_types) == 1:
            python_type = one_of_types[0]
        else:
            python_type = Union[tuple(one_of_types)]

        return python_type, {"json_schema_extra": {"oneOf": one_of_schemas}}

    @classmethod
    def _resolve_param_type(cls, param_info: Dict[str, Any]) -> tuple:
        """Map a single JSON Schema parameter to (python_type, extra_field_kwargs).

        Handles oneOf, simple types, array items cleanup, and nested object cleanup.
        """
        extra: Dict[str, Any] = {}

        # oneOf takes priority
        if "oneOf" in param_info:
            return cls._resolve_oneof_type(param_info)

        param_type = param_info.get("type", "string")

        # Handle nullable types like ["string", "null"]
        if isinstance(param_type, list):
            non_null = [t for t in param_type if t != "null"]
            is_nullable = "null" in param_type
            base_type = non_null[0] if non_null else "string"
            base_python_type = cls._SIMPLE_TYPE_MAP.get(base_type, str)
            python_type = (
                Optional[base_python_type] if is_nullable else base_python_type
            )
            param_type = base_type
        else:
            python_type = cls._SIMPLE_TYPE_MAP.get(param_type, str)

        if param_type == "array":
            items_info = param_info.get("items", {})
            cleaned_items = (
                {k: v for k, v in items_info.items() if k != "required"}
                if items_info
                else {"type": "string"}
            )
            extra["json_schema_extra"] = {"type": "array", "items": cleaned_items}

        elif param_type == "object":
            object_props = param_info.get("properties", {})
            if object_props:
                cleaned_props = {}
                nested_required = []
                for prop_name, prop_val in object_props.items():
                    cleaned = prop_val.copy()
                    if "required" in cleaned:
                        req_value = cleaned.pop("required")
                        if req_value in ["True", "true", True]:
                            nested_required.append(prop_name)
                    cleaned_props[prop_name] = cleaned
                schema = {"type": "object", "properties": cleaned_props}
                if nested_required:
                    schema["required"] = nested_required
                extra["json_schema_extra"] = schema

        elif param_type not in cls._SIMPLE_TYPE_MAP:
            extra["json_schema_extra"] = {"type": param_type}

        return python_type, extra

    def _create_mcp_tool_from_tooluniverse(
        self, tool_config: Dict[str, Any], mcp_name: Optional[str] = None
    ):
        """Create an MCP tool from a ToolUniverse tool configuration.

        This method creates a function with proper parameter signatures that match
        the ToolUniverse tool schema, enabling FastMCP's automatic parameter validation.

        Args:
            tool_config: ToolUniverse tool configuration dictionary
            mcp_name: Optional shortened name for MCP exposure (if None, uses original name)
        """
        try:
            # Debug: Ensure tool_config is a dictionary
            if not isinstance(tool_config, dict):
                raise ValueError(
                    f"tool_config must be a dictionary, got {type(tool_config)}: {tool_config}"
                )

            tool_name = tool_config["name"]
            # Use shortened MCP name if provided, otherwise use original
            exposed_name = mcp_name if mcp_name is not None else tool_name
            description = tool_config.get(
                "description", f"ToolUniverse tool: {tool_name}"
            )
            parameters = tool_config.get("parameter", {})

            # Extract parameter information from the schema
            # Handle case where properties might be None (like in Finish tool)
            properties = parameters.get("properties")
            if properties is None:
                properties = {}
            required_params = parameters.get("required", [])

            # Handle non-standard schema format where 'required' is set on individual properties
            # instead of at the object level (common in ToolUniverse schemas)
            if not required_params and properties:
                required_params = [
                    param_name
                    for param_name, param_info in properties.items()
                    if param_info.get("required", False)
                ]

            # Build function signature dynamically with Pydantic Field support
            import inspect
            from typing import Annotated
            from pydantic import Field

            # Create parameter signature for the function
            func_params = []
            param_annotations = {}

            # Process parameters in two phases: required first, then optional
            # This ensures Python function signature validity (no default args before non-default)
            for is_required_phase in [True, False]:
                for param_name, param_info in properties.items():
                    param_description = param_info.get(
                        "description", f"{param_name} parameter"
                    )
                    is_required = param_name in required_params

                    # Skip if not in current phase
                    if is_required != is_required_phase:
                        continue

                    # Resolve Python type and optional json_schema_extra
                    python_type, extra_kwargs = self._resolve_param_type(param_info)
                    field_kwargs = {"description": param_description, **extra_kwargs}
                    pydantic_field = Field(**field_kwargs)

                    if is_required:
                        # Required parameter with description and schema info
                        annotated_type = Annotated[python_type, pydantic_field]
                        param_annotations[param_name] = annotated_type
                        func_params.append(
                            inspect.Parameter(
                                param_name,
                                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                                annotation=annotated_type,
                            )
                        )
                    else:
                        # Optional parameter with description, schema info and default value
                        annotated_type = Annotated[
                            Union[python_type, type(None)], pydantic_field
                        ]
                        param_annotations[param_name] = annotated_type
                        func_params.append(
                            inspect.Parameter(
                                param_name,
                                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                                default=None,
                                annotation=annotated_type,
                            )
                        )

            # Add _tooluniverse_stream as an optional parameter for streaming support
            # This parameter is NOT exposed in the MCP schema (it's in kwargs but not in param_annotations)
            # Users can pass it to enable streaming, but it won't appear in the tool schema

            async def dynamic_tool_function(**kwargs) -> str:
                """Execute ToolUniverse tool with provided arguments."""
                import json

                stream_callback = None
                try:
                    # Remove ctx if present (legacy support)
                    ctx = kwargs.pop("ctx", None) if "ctx" in kwargs else None
                    # Extract streaming flag (users can optionally pass this)
                    stream_flag = bool(kwargs.pop("_tooluniverse_stream", False))
                    # Extract task metadata if present (for MCP Tasks)
                    task_request = (
                        kwargs.pop("_task", None) if "_task" in kwargs else None
                    )

                    # Filter out None values for optional parameters
                    # Note: _tooluniverse_stream was extracted and popped above
                    # so it won't be in args_dict, which is what we want
                    args_dict = {k: v for k, v in kwargs.items() if v is not None}

                    # Check if tool supports tasks
                    execution_config = tool_config.get("execution", {})
                    task_support = execution_config.get("taskSupport", "forbidden")

                    # Handle task request
                    if task_request and task_support != "forbidden":
                        # Create task instead of executing directly
                        if not self._task_manager_started:
                            await self.task_manager.start()
                            self._task_manager_started = True

                        ttl = task_request.get("ttl", 3600000)  # Default 1 hour
                        task_id = await self.task_manager.create_task(
                            tool_name=tool_name,
                            arguments=args_dict,
                            ttl=ttl,
                        )

                        # Return task creation response
                        return json.dumps(
                            {
                                "_meta": {
                                    "task": {
                                        "taskId": task_id,
                                        "status": "working",
                                        "statusMessage": f"Task {task_id} submitted",
                                        "pollInterval": 5000,
                                    }
                                }
                            },
                            ensure_ascii=False,
                        )

                    elif task_request and task_support == "forbidden":
                        return json.dumps(
                            {
                                "error": f"Tool {tool_name} does not support task execution"
                            },
                            ensure_ascii=False,
                        )

                    # Validate required parameters (check against args_dict, not filtered_args)
                    missing_required = [
                        param for param in required_params if param not in args_dict
                    ]
                    if missing_required:
                        return json.dumps(
                            {
                                "error": f"Missing required parameters: {missing_required}",
                                "required": required_params,
                                "provided": list(args_dict.keys()),
                            },
                            ensure_ascii=False,
                        )

                    function_call = {"name": tool_name, "arguments": args_dict}

                    try:
                        loop = asyncio.get_running_loop()
                    except RuntimeError:
                        loop = asyncio.get_event_loop()

                    if stream_flag and ctx is not None:

                        def _stream_callback(chunk: str) -> None:
                            if not chunk:
                                return
                            try:
                                future = asyncio.run_coroutine_threadsafe(
                                    ctx.info(chunk), loop
                                )

                                def _log_future_result(fut) -> None:
                                    exc = fut.exception()
                                    if exc:
                                        self.logger.debug(
                                            f"Streaming callback error for {tool_name}: {exc}"
                                        )

                                future.add_done_callback(_log_future_result)
                            except Exception as cb_error:  # noqa: BLE001
                                self.logger.debug(
                                    f"Failed to dispatch stream chunk for {tool_name}: {cb_error}"
                                )

                        # Assign the function to stream_callback
                        stream_callback = _stream_callback

                        # Note: _tooluniverse_stream was extracted from kwargs above
                        # and is not passed to the tool. The stream_callback is sufficient
                        # to enable streaming for downstream tools.

                    # In stdio mode, capture stdout to prevent pollution of JSON-RPC stream
                    is_stdio_mode = getattr(self, "_transport_type", None) == "stdio"

                    if is_stdio_mode:
                        # Wrap tool execution to capture stdout and redirect to stderr
                        def _run_with_stdout_capture():
                            import io

                            old_stdout = sys.stdout
                            try:
                                # Capture stdout during tool execution
                                stdout_capture = io.StringIO()
                                sys.stdout = stdout_capture

                                # Execute the tool
                                result = self.tooluniverse.run_one_function(
                                    function_call,
                                    stream_callback=stream_callback,
                                )

                                # Get captured output and redirect to stderr
                                captured_output = stdout_capture.getvalue()
                                if captured_output:
                                    self.logger.debug(
                                        f"[{tool_name}] Captured stdout: {captured_output}"
                                    )
                                    # Write to stderr to avoid polluting stdout
                                    print(captured_output, file=sys.stderr, end="")

                                return result
                            finally:
                                sys.stdout = old_stdout

                        run_callable = _run_with_stdout_capture
                    else:
                        # In HTTP/SSE mode, no need to capture stdout
                        run_callable = functools.partial(
                            self.tooluniverse.run_one_function,
                            function_call,
                            stream_callback=stream_callback,
                        )

                    result = await loop.run_in_executor(self.executor, run_callable)

                    # Ensure result is properly serialized to JSON
                    if isinstance(result, str):
                        # Try to parse as JSON to validate, if fails wrap it
                        try:
                            json.loads(result)
                            return result
                        except (json.JSONDecodeError, ValueError):
                            # Not valid JSON, wrap it
                            return json.dumps({"result": result}, ensure_ascii=False)
                    elif isinstance(result, (dict, list)):
                        return json.dumps(result, ensure_ascii=False, default=str)
                    else:
                        # For other types, convert to JSON
                        return json.dumps({"result": str(result)}, ensure_ascii=False)

                except Exception as e:
                    error_msg = f"Error executing {tool_name}: {str(e)}"
                    self.logger.error(
                        f"{tool_name} execution failed: {error_msg}", exc_info=True
                    )
                    return json.dumps(
                        {"error": error_msg, "error_type": type(e).__name__},
                        ensure_ascii=False,
                    )

            # Set function metadata (use exposed_name for MCP registration)
            dynamic_tool_function.__name__ = exposed_name
            dynamic_tool_function.__signature__ = inspect.Signature(func_params)
            annotations = param_annotations.copy()
            annotations["return"] = str
            dynamic_tool_function.__annotations__ = annotations

            # Create detailed docstring for internal use, but use clean description for FastMCP
            param_docs = []
            for param_name, param_info in properties.items():
                param_desc = param_info.get("description", f"{param_name} parameter")
                param_type = param_info.get("type", "string")
                is_required = param_name in required_params
                required_text = "required" if is_required else "optional"
                param_docs.append(
                    f"    {param_name} ({param_type}, {required_text}): {param_desc}"
                )

            # Set a simple docstring for the function (internal use)
            dynamic_tool_function.__doc__ = f"""{description}

Returns:
    str: Tool execution result
"""

            # Get tool annotations (with defaults and overrides)
            annotations_dict = self._get_tool_annotations(tool_config)

            # Convert to MCP ToolAnnotations object
            from mcp.types import ToolAnnotations

            tool_annotations = ToolAnnotations(
                readOnlyHint=annotations_dict.get("readOnlyHint"),
                destructiveHint=annotations_dict.get("destructiveHint"),
            )

            # Register with FastMCP using exposed_name for MCP, but tool execution uses original tool_name
            self.tool(description=description, annotations=tool_annotations)(
                dynamic_tool_function
            )

        except Exception as e:
            self.logger.error(f"Error creating MCP tool from config: {e}")
            self.logger.error(f"Error type: {type(e)}")
            import traceback

            self.logger.error(f"Traceback: {traceback.format_exc()}")
            self.logger.debug(f"Tool config: {tool_config}")
            # Don't raise - continue with other tools
            return


# Convenience function for quick server creation
def create_smcp_server(
    name: str = "SMCP Server",
    tool_categories: Optional[List[str]] = None,
    search_enabled: bool = True,
    **kwargs,
) -> SMCP:
    """Create a configured SMCP server instance.

    Convenience wrapper around ``SMCP(...)`` with sensible defaults.

    Args:
        name: Human-readable server name.
        tool_categories: ToolUniverse categories to load (None loads all).
        search_enabled: Enable AI-powered tool discovery.
        **kwargs: Additional SMCP / FastMCP configuration options.

    Returns:
        Configured SMCP server instance ready to run.
    """
    return SMCP(
        name=name,
        tool_categories=tool_categories,
        search_enabled=search_enabled,
        **kwargs,
    )
