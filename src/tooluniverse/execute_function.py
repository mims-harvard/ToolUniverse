"""
ToolUniverse Function Execution Module

This module provides the core ToolUniverse class for managing and executing various scientific and data tools.
It supports loading tools from JSON configurations, organizing them by categories, validating function calls,
and executing tools with proper error handling and caching.

The module includes support for:
- GraphQL tools (OpenTarget, OpenTarget Genetics)
- RESTful API tools (Monarch, ChEMBL, PubChem, etc.)
- FDA drug labeling and adverse event tools
- Clinical trials tools
- Literature search tools (EuropePMC, Semantic Scholar, PubTator)
- Biological databases (HPA, Reactome, UniProt)
- MCP (Model Context Protocol) clients and auto-loaders
- Enrichment analysis tools
- Package management tools

Classes:
    ToolUniverse: Main class for tool management and execution

Constants:
    default_tool_files: Default mapping of tool categories to JSON file paths
    tool_type_mappings: Mapping of tool type strings to their implementation classes
"""

import asyncio
import copy
import inspect
import json
import random
import string
import os
import time
import hashlib
import warnings
import threading
from pathlib import Path
from contextlib import nullcontext
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from .utils import read_json_list, evaluate_function_call, extract_function_call_json
from .exceptions import (
    ToolError,
    ToolUnavailableError,
    ToolValidationError,
    ToolConfigError,
    ToolServerError,
)
from .tool_registry import (
    auto_discover_tools,
    get_tool_registry,
    register_external_tool,
    get_tool_class_lazy,
    get_tool_errors,
    mark_tool_unavailable,
)
from .logging_config import (
    get_logger,
    debug,
    info,
    warning,
    error,
    set_log_level,
)
from .cache.result_cache_manager import ResultCacheManager
from .output_hook import HookManager
from .default_config import default_tool_files, get_default_hook_config

# Determine the directory where the current file is located
current_dir = os.path.dirname(os.path.abspath(__file__))

# Check if lazy loading is enabled (default: True for better performance)
_TRUTHY_VALUES = {"true", "1", "yes"}
LAZY_LOADING_ENABLED = (
    os.getenv("TOOLUNIVERSE_LAZY_LOADING", "true").lower() in _TRUTHY_VALUES
)

if LAZY_LOADING_ENABLED:
    # Use lazy auto-discovery by default (much faster)
    debug("Starting lazy tool auto-discovery...")
    tool_type_mappings = auto_discover_tools(lazy=True)
else:
    # Use full auto-discovery (slower but ensures all tools are immediately available)
    debug("Starting full tool auto-discovery...")
    tool_type_mappings = auto_discover_tools(lazy=False)

# Update the registry with any manually added tools
tool_type_mappings = get_tool_registry()

if LAZY_LOADING_ENABLED:
    debug(
        f"Lazy tool registry initialized with {len(tool_type_mappings)} immediately available tools"
    )
else:
    debug(f"Full tool registry initialized with {len(tool_type_mappings)} tools")

for _tool_name, _tool_class in sorted(tool_type_mappings.items()):
    debug(f"  - {_tool_name}: {_tool_class.__name__}")


@dataclass
class _BatchCacheInfo:
    namespace: str
    version: str
    cache_key: str


@dataclass
class _BatchJob:
    signature: str
    call: Dict[str, Any]
    function_name: str
    arguments: Dict[str, Any]
    indices: List[int] = field(default_factory=list)
    tool_instance: Any = None
    cache_info: Optional[_BatchCacheInfo] = None
    cache_key_composed: Optional[str] = None
    skip_execution: bool = False


class ToolCallable:
    """
    A callable wrapper for a tool that validates kwargs and calls run_one_function.

    This class provides the dynamic function interface for tools, allowing
    them to be called like regular Python functions with keyword arguments.
    """

    def __init__(self, engine: "ToolUniverse", tool_name: str):
        self.engine = engine
        self.tool_name = tool_name
        self.schema = engine.all_tool_dict[tool_name]["parameter"]
        self.__doc__ = engine.all_tool_dict[tool_name].get("description", tool_name)

    def __call__(
        self, *, stream_callback=None, use_cache=False, validate=True, **kwargs
    ):
        """
        Execute the tool with the provided keyword arguments.

        Context-aware execution - works in both sync and async contexts.

        In sync context:
            result = tu.tools.some_tool(param="value")  # Returns result directly

        In async context:
            result = await tu.tools.some_tool(param="value")  # Returns coroutine

        Args:
            stream_callback: Optional callback for streaming responses
            use_cache: Whether to use result caching
            validate: Whether to validate parameters against schema
            **kwargs: Tool-specific arguments

        Returns:
            Tool execution result (sync) or coroutine (async)
        """
        function_call = {"name": self.tool_name, "arguments": kwargs}

        # Detect if we're in an async context
        try:
            asyncio.get_running_loop()
            # In async context - return coroutine
            return self._call_async(function_call, stream_callback, use_cache, validate)
        except RuntimeError:
            # Not in async context - execute synchronously
            return self._call_sync(function_call, stream_callback, use_cache, validate)

    def _call_sync(self, function_call, stream_callback, use_cache, validate):
        """Synchronous execution - handles both sync and async tools."""
        # Check if tool is async
        function_name = function_call.get("name")
        tool_instance = (
            self.engine._get_tool_instance(function_name, cache=True)
            if function_name
            else None
        )

        if tool_instance and inspect.iscoroutinefunction(tool_instance.run):
            # Async tool in sync context - use asyncio.run()
            return asyncio.run(
                self.engine.run_one_function_async(
                    function_call,
                    stream_callback=stream_callback,
                    use_cache=use_cache,
                    validate=validate,
                )
            )
        else:
            # Sync tool - use regular execution
            return self.engine.run_one_function(
                function_call,
                stream_callback=stream_callback,
                use_cache=use_cache,
                validate=validate,
            )

    async def _call_async(self, function_call, stream_callback, use_cache, validate):
        """Asynchronous execution."""
        return await self.engine.run_one_function_async(
            function_call,
            stream_callback=stream_callback,
            use_cache=use_cache,
            validate=validate,
        )


class ToolNamespace:
    """
    Dynamic namespace for accessing tools as callable functions.

    This class provides the `tu.tools.tool_name(**kwargs)` interface,
    dynamically creating ToolCallable instances for each available tool.
    """

    def __init__(self, engine: "ToolUniverse"):
        self.engine = engine

    def __getattr__(self, name: str) -> ToolCallable:
        """Return a ToolCallable for the requested tool name."""
        if name in self.engine.all_tool_dict:
            return ToolCallable(self.engine, name)

        # Attempt a targeted on-demand load for this tool name
        try:
            self.engine.load_tools(include_tools=[name])
        except Exception:
            # Ignore load errors here; we'll surface a clearer error below if still missing
            pass
        if name in self.engine.all_tool_dict:
            return ToolCallable(self.engine, name)

        # As a fallback, force full discovery once
        try:
            self.engine.force_full_discovery()
        except Exception:
            # Ignore discovery errors; report consolidated reason below
            pass
        if name in self.engine.all_tool_dict:
            return ToolCallable(self.engine, name)

        # Build a helpful reason summary
        try:
            status = self.engine.get_lazy_loading_status()
            reason = (
                f"after targeted load and full discovery; "
                f"lazy_loading_enabled={status.get('lazy_loading_enabled')}, "
                f"loaded_tools_count={status.get('loaded_tools_count')}, "
                f"immediately_available_tools={status.get('immediately_available_tools')}"
            )
        except Exception:
            reason = "after targeted load and full discovery"

        raise AttributeError(f"Tool '{name}' not found ({reason})")

    def __len__(self) -> int:
        """Return the number of available tools."""
        return len(self.engine.all_tool_dict)

    def __iter__(self):
        """Iterate over tool names."""
        return iter(self.engine.all_tool_dict.keys())

    def __contains__(self, name: str) -> bool:
        """Check if a tool exists."""
        return name in self.engine.all_tool_dict

    def refresh(self):
        """Refresh tool discovery (re-discover MCP/remote tools)."""
        self.engine.refresh_tools()

    def eager_load(self, names: Optional[List[str]] = None):
        """Pre-instantiate tools to reduce first-call latency."""
        self.engine.eager_load_tools(names)


class ToolUniverse:
    """
    A comprehensive tool management system for loading, organizing, and executing various scientific and data tools.

    The ToolUniverse class provides a centralized interface for managing different types of tools including
    GraphQL tools, RESTful APIs, MCP clients, and specialized scientific tools. It handles tool loading,
    filtering, caching, and execution.

    Attributes:
        all_tools (list): List of all loaded tool configurations
        all_tool_dict (dict): Dictionary mapping tool names to their configurations
        tool_category_dicts (dict): Dictionary organizing tools by category
        tool_files (dict): Dictionary mapping category names to their JSON file paths
        callable_functions (dict): Cache of instantiated tool objects
    """

    # Maximum tool name length for MCP compatibility
    # 50 chars for tool name + 14 chars for 'tooluniverse__' prefix = 64 chars (Claude's limit)
    MAX_TOOL_NAME_LENGTH = 45

    def __init__(
        self,
        tool_files=default_tool_files,
        keep_default_tools=True,
        log_level: str = None,
        hooks_enabled: bool = False,
        hook_config: dict = None,
        hook_type: str = None,
        enable_name_shortening: bool = False,
    ):
        """
        Initialize the ToolUniverse with tool file configurations.

        Args:
            tool_files (dict, optional): Dictionary mapping category names to JSON file paths.
                                       Defaults to default_tool_files.
            keep_default_tools (bool, optional): Whether to keep default tools when custom
                                               tool_files are provided. Defaults to True.
            log_level (str, optional): Log level for this instance. Can be 'DEBUG', 'INFO',
                                     'WARNING', 'ERROR', 'CRITICAL'. If None, uses global setting.
            hooks_enabled (bool, optional): Whether to enable output hooks. Defaults to False.
            hook_config (dict, optional): Configuration for hooks. If None, uses default config.
            hook_type (str or list, optional): Simple hook type selection. Can be 'SummarizationHook',
                                             'FileSaveHook', or a list of both. Defaults to 'SummarizationHook'.
                                             If both hook_config and hook_type are provided, hook_config takes precedence.
            enable_name_shortening (bool, optional): Whether to enable automatic tool name shortening
                                                   for MCP compatibility. Defaults to False.
        """
        # Set log level if specified
        if log_level is not None:
            set_log_level(log_level)

        # Get logger for this class
        self.logger = get_logger("ToolUniverse")

        # Initialize name mapper for shortening and alias support
        from .tool_name_utils import ToolNameMapper

        self.name_mapper = ToolNameMapper()
        self.enable_name_shortening = enable_name_shortening

        if enable_name_shortening:
            self.logger.debug("Name shortening enabled for MCP compatibility")
        else:
            self.logger.debug("Name mapper initialized for alias support only")

        # Initialize any necessary attributes here FIRST
        self.all_tools: List[Dict[str, Any]] = []
        self.all_tool_dict: Dict[str, Dict[str, Any]] = {}
        self.tool_category_dicts: Dict[str, List[Dict[str, Any]]] = {}
        self.tool_finder = None
        if tool_files is None:
            tool_files = default_tool_files
        elif keep_default_tools:
            default_tool_files.update(tool_files)
            tool_files = default_tool_files
        self.tool_files = tool_files

        self.logger.debug("Tool files:")
        self.logger.debug(json.dumps(tool_files, indent=2))
        self.callable_functions = {}

        # Refresh the global tool_type_mappings to include any tools registered during imports
        global tool_type_mappings
        tool_type_mappings = get_tool_registry()

        # Initialize hook system AFTER attributes are initialized
        self.hooks_enabled = hooks_enabled
        if self.hooks_enabled:
            # Determine hook configuration
            if hook_config is not None:
                # Use provided hook_config (takes precedence)
                final_hook_config = hook_config
                self.logger.info("Using provided hook_config")
            elif hook_type is not None:
                # Use hook_type to generate simple configuration
                final_hook_config = self._create_hook_config_from_type(hook_type)
                self.logger.info(f"Using hook_type: {hook_type}")
            else:
                # Use default configuration with SummarizationHook
                final_hook_config = get_default_hook_config()
                self.logger.info("Using default hook configuration (SummarizationHook)")

            self.hook_manager = HookManager(final_hook_config, self)
            self.logger.info("Output hooks enabled")
        else:
            self.hook_manager = None
            self.logger.debug("Output hooks disabled")

        # Initialize caching configuration
        cache_enabled = (
            os.getenv("TOOLUNIVERSE_CACHE_ENABLED", "true").lower() in _TRUTHY_VALUES
        )
        persistence_enabled = (
            os.getenv("TOOLUNIVERSE_CACHE_PERSIST", "true").lower() in _TRUTHY_VALUES
        )
        memory_size = int(os.getenv("TOOLUNIVERSE_CACHE_MEMORY_SIZE", "256"))
        default_ttl_env = os.getenv("TOOLUNIVERSE_CACHE_DEFAULT_TTL")
        default_ttl = int(default_ttl_env) if default_ttl_env else None
        singleflight_enabled = (
            os.getenv("TOOLUNIVERSE_CACHE_SINGLEFLIGHT", "true").lower()
            in _TRUTHY_VALUES
        )

        cache_path = os.getenv("TOOLUNIVERSE_CACHE_PATH")
        if not cache_path and persistence_enabled:
            base_dir = os.getenv("TOOLUNIVERSE_CACHE_DIR")
            if not base_dir:
                base_dir = os.path.join(str(Path.home()), ".tooluniverse")
            os.makedirs(base_dir, exist_ok=True)
            cache_path = os.path.join(base_dir, "cache.sqlite")

        self.cache_manager = ResultCacheManager(
            memory_size=memory_size,
            persistent_path=cache_path if persistence_enabled else None,
            enabled=cache_enabled,
            persistence_enabled=persistence_enabled,
            singleflight=singleflight_enabled,
            default_ttl=default_ttl,
        )

        self._strict_validation = (
            os.getenv("TOOLUNIVERSE_STRICT_VALIDATION", "false").lower()
            in _TRUTHY_VALUES
        )

        # Lenient type coercion: auto-convert parameter types for better UX
        self.lenient_type_coercion = (
            os.getenv("TOOLUNIVERSE_COERCE_TYPES", "true").lower() in _TRUTHY_VALUES
        )

        # Initialize dynamic tools namespace
        self.tools = ToolNamespace(self)

    def register_custom_tool(
        self,
        tool_class,
        tool_name=None,
        tool_config=None,
        instantiate=False,
        tool_instance=None,
    ):
        """
        Register a custom tool class or instance at runtime.

        Args:
            tool_class: The tool class to register (required if tool_instance is None)
            tool_name (str, optional): Name to register under. Uses class name if None.
            tool_config (dict, optional): Tool configuration dictionary to add to all_tools
            instantiate (bool, optional): If True, immediately instantiate and cache the tool.
                                         Defaults to False for backward compatibility.
            tool_instance (optional): Pre-instantiated tool object. If provided, tool_class
                                     is inferred from the instance.

        Returns:
            str: The name the tool was registered under

        Examples:
            # Register tool class only (lazy instantiation)
            tu.register_custom_tool(MyTool, tool_config={...})

            # Register and immediately instantiate
            tu.register_custom_tool(MyTool, tool_config={...}, instantiate=True)

            # Register pre-instantiated tool
            instance = MyTool({...})
            tu.register_custom_tool(tool_class=MyTool, tool_instance=instance, tool_config={...})
        """
        # If tool_instance is provided, infer tool_class from it
        if tool_instance is not None:
            tool_class = tool_instance.__class__
        elif tool_class is None:
            raise ValueError("Either tool_class or tool_instance must be provided")

        name = tool_name or tool_class.__name__

        # Register the tool class to global registry
        register_external_tool(name, tool_class)

        # Update the global tool_type_mappings
        global tool_type_mappings
        tool_type_mappings = get_tool_registry()

        # Process tool_config if provided
        if tool_config:
            # Ensure the config has the correct type
            if "type" not in tool_config:
                tool_config["type"] = name

            # Add MCP annotations to tool config
            from .tool_defaults import add_annotations_to_tool_config

            add_annotations_to_tool_config(tool_config)

            self.all_tools.append(tool_config)
            tool_name_in_config = tool_config.get("name", name)
            self.all_tool_dict[tool_name_in_config] = tool_config

            # Handle tool instantiation
            if tool_instance is not None:
                # Use provided instance
                self.callable_functions[tool_name_in_config] = tool_instance
                self.logger.debug(
                    f"Registered pre-instantiated tool '{tool_name_in_config}'"
                )
            elif instantiate:
                # Instantiate now
                try:
                    # Use the same logic as _get_or_initialize_tool (line 2318)
                    # Try to instantiate with tool_config parameter
                    try:
                        instance = tool_class(tool_config=tool_config)
                    except TypeError:
                        # If tool doesn't accept tool_config, try without parameters
                        instance = tool_class()

                    self.callable_functions[tool_name_in_config] = instance
                    self.logger.debug(
                        f"Instantiated and cached tool '{tool_name_in_config}'"
                    )
                except Exception as e:
                    self.logger.error(
                        f"Failed to instantiate tool '{tool_name_in_config}': {e}"
                    )
                    raise
            # else: lazy instantiation (existing behavior)

            # Add to category for proper organization
            category = tool_config.get("category", "custom")
            if category not in self.tool_category_dicts:
                self.tool_category_dicts[category] = []
            if tool_name_in_config not in self.tool_category_dicts[category]:
                self.tool_category_dicts[category].append(tool_name_in_config)

        self.logger.info(f"Custom tool '{name}' registered successfully!")
        return name

    def force_full_discovery(self):
        """
        Force full tool discovery, importing all tool modules immediately.

        This can be useful when you need to ensure all tools are available
        immediately, bypassing lazy loading.

        Returns:
            dict: Updated tool registry with all discovered tools
        """
        global tool_type_mappings
        self.logger.info("Forcing full tool discovery...")

        tool_type_mappings = auto_discover_tools(lazy=False)
        self.logger.info(
            f"Full discovery complete. {len(tool_type_mappings)} tools available."
        )

        return tool_type_mappings

    def get_lazy_loading_status(self):
        """
        Get information about lazy loading status and available tools.

        Returns:
            dict: Dictionary with lazy loading status and tool counts
        """
        from .tool_registry import _discovery_completed, _lazy_registry

        return {
            "lazy_loading_enabled": LAZY_LOADING_ENABLED,
            "full_discovery_completed": _discovery_completed,
            "immediately_available_tools": len(tool_type_mappings),
            "lazy_mappings_available": len(_lazy_registry),
            "loaded_tools_count": (
                len(self.all_tools) if hasattr(self, "all_tools") else 0
            ),
        }

    def get_tool_types(self):
        """
        Get the types of tools available in the tool files.

        Returns:
            list: A list of tool type names (category keys).
        """
        return list(self.tool_files.keys())

    def _get_api_key(self, key_name: str):
        """Get API key from environment variables."""
        return os.getenv(key_name)

    def _check_api_key_requirements(self, tool_config):
        """
        Check if a tool's required API keys are available.
        Also supports optional_api_keys which enhance performance but don't block loading.

        Args:
            tool_config (dict): Tool configuration containing optional 'required_api_keys' and 'optional_api_keys' fields

        Returns:
            tuple: (bool, list) - (all_keys_available, missing_keys)
        """
        required_keys = tool_config.get("required_api_keys", [])
        optional_keys = tool_config.get("optional_api_keys", [])

        missing_keys = []

        # Check required keys (all must be available)
        for key in required_keys:
            if not self._get_api_key(key):
                missing_keys.append(key)

        # Check optional keys (log if missing, but don't block loading)
        # Optional keys enhance performance but tools still work without them
        if optional_keys:
            optional_available = any(self._get_api_key(key) for key in optional_keys)
            if not optional_available:
                tool_name = tool_config.get("name", "unknown")
                self.logger.debug(
                    f"Tool '{tool_name}': Optional API keys not set for better performance: {', '.join(optional_keys)}"
                )

        # Tool is valid if all required keys are available
        # Optional keys do NOT block loading
        all_valid = len(missing_keys) == 0

        return all_valid, missing_keys

    def generate_env_template(
        self, all_missing_keys, output_file: str = ".env.template"
    ):
        """Generate a template .env file with all required API keys"""
        try:
            with open(output_file, "w") as f:
                f.write("# API Keys for ToolUniverse\n")
                f.write("# Copy this file to .env and fill in your actual API keys\n\n")

                for key in sorted(all_missing_keys):
                    f.write(f"{key}=your_api_key_here\n\n")

            self.logger.info(
                f"Generated API key template: {output_file}. Copy this file to .env and fill in your API keys"
            )
        except OSError as e:
            self.logger.warning(
                f"Could not generate {output_file} (likely read-only file system): {e}"
            )

    def _create_hook_config_from_type(self, hook_type):
        """
        Create hook configuration from simple hook_type parameter.

        Args:
            hook_type (str or list): Hook type(s) to enable. Can be 'SummarizationHook',
                                   'FileSaveHook', or a list of both.

        Returns:
            dict: Generated hook configuration
        """
        # Handle single hook type
        if isinstance(hook_type, str):
            hook_types = [hook_type]
        else:
            hook_types = hook_type

        # Validate hook types
        valid_types = ["SummarizationHook", "FileSaveHook"]
        for htype in hook_types:
            if htype not in valid_types:
                raise ValueError(
                    f"Invalid hook_type: {htype}. Valid types are: {valid_types}"
                )

        # Create hooks list
        hooks = []

        for htype in hook_types:
            if htype == "SummarizationHook":
                hooks.append(
                    {
                        "name": "summarization_hook",
                        "type": "SummarizationHook",
                        "enabled": True,
                        "conditions": {
                            "output_length": {"operator": ">", "threshold": 5000}
                        },
                        "hook_config": {
                            "chunk_size": 32000,
                            "focus_areas": "key_findings_and_results",
                            "max_summary_length": 3000,
                        },
                    }
                )
            elif htype == "FileSaveHook":
                hooks.append(
                    {
                        "name": "file_save_hook",
                        "type": "FileSaveHook",
                        "enabled": True,
                        "conditions": {
                            "output_length": {"operator": ">", "threshold": 1000}
                        },
                        "hook_config": {
                            "temp_dir": None,
                            "file_prefix": "tool_output",
                            "include_metadata": True,
                            "auto_cleanup": False,
                            "cleanup_age_hours": 24,
                        },
                    }
                )

        return {"hooks": hooks}

    def load_tools(
        self,
        tool_type=None,
        exclude_tools=None,
        exclude_categories=None,
        include_tools=None,
        tool_config_files=None,
        tools_file=None,
        include_tool_types=None,
        exclude_tool_types=None,
    ):
        """
        Loads tool definitions from JSON files into the instance's tool registry.

        If `tool_type` is None, loads all available tool categories from `self.tool_files`.
        Otherwise, loads only the specified tool categories.

        After loading, deduplicates tools by their 'name' field and updates the internal tool list.
        Also refreshes the tool name and description mapping.

        Args:
            tool_type (list, optional): List of tool category names to load. If None, loads all categories.
            exclude_tools (list, optional): List of specific tool names to exclude from loading.
            exclude_categories (list, optional): List of tool categories to exclude from loading.
            include_tools (list or str, optional): List of specific tool names to include, or path to a text file
                                                  containing tool names (one per line). If provided, only these tools
                                                  will be loaded regardless of categories.
            tool_config_files (dict, optional): Additional tool configuration files to load.
                                               Format: {"category_name": "/path/to/config.json"}
            tools_file (str, optional): Path to a text file containing tool names to include (one per line).
                                       Alternative to include_tools when providing a file path.
            include_tool_types (list, optional): List of tool types to include (e.g., ["OpenTarget", "ChEMBLTool"]).
                                                If provided, only tools with these types will be loaded.
            exclude_tool_types (list, optional): List of tool types to exclude (e.g., ["ToolFinderEmbedding"]).
                                                Tools with these types will be excluded.

        Side Effects:
            - Updates `self.all_tools` with loaded and deduplicated tools.
            - Updates `self.tool_category_dicts` with loaded tools per category.
            - Calls `self.refresh_tool_name_desc()` to update tool name/description mapping.
            - Prints the number of tools before and after loading.

        Examples:
            # Load specific tools by name
            tu.load_tools(include_tools=["UniProt_get_entry_by_accession", "ChEMBL_get_molecule_by_chembl_id"])

            # Load tools from a file
            tu.load_tools(tools_file="/path/to/tool_names.txt")

            # Include only specific tool types
            tu.load_tools(include_tool_types=["OpenTarget", "ChEMBLTool"])

            # Exclude specific tool types
            tu.load_tools(exclude_tool_types=["ToolFinderEmbedding", "Unknown"])

            # Load additional config files
            tu.load_tools(tool_config_files={"custom_tools": "/path/to/custom_tools.json"})

            # Combine multiple options
            tu.load_tools(
                tool_type=["uniprot", "ChEMBL"],
                exclude_tools=["problematic_tool"],
                exclude_tool_types=["Unknown"],
                tool_config_files={"custom": "/path/to/custom.json"}
            )
        """
        self.logger.debug(f"Number of tools before load tools: {len(self.all_tools)}")

        # Handle tools_file parameter (alternative to include_tools)
        if tools_file:
            include_tools = self._load_tool_names_from_file(tools_file)

        # Handle include_tools parameter
        if isinstance(include_tools, str):
            # If include_tools is a string, treat it as a file path
            include_tools = self._load_tool_names_from_file(include_tools)

        # Convert parameters to sets for efficient lookup
        exclude_tools_set = set(exclude_tools or [])
        exclude_categories_set = set(exclude_categories or [])
        include_tools_set = set(include_tools or []) if include_tools else None
        include_tool_types_set = (
            set(include_tool_types or []) if include_tool_types else None
        )
        exclude_tool_types_set = (
            set(exclude_tool_types or []) if exclude_tool_types else None
        )

        # Log operations
        if exclude_tools_set:
            self.logger.info(
                f"Excluding tools by name: {', '.join(list(exclude_tools_set)[:5])}{'...' if len(exclude_tools_set) > 5 else ''}"
            )
        if exclude_categories_set:
            self.logger.info(
                f"Excluding categories: {', '.join(exclude_categories_set)}"
            )
        if include_tools_set:
            self.logger.info(
                f"Including only specific tools: {len(include_tools_set)} tools specified"
            )
        if include_tool_types_set:
            self.logger.info(
                f"Including only tool types: {', '.join(include_tool_types_set)}"
            )
        if exclude_tool_types_set:
            self.logger.info(
                f"Excluding tool types: {', '.join(exclude_tool_types_set)}"
            )
        if tool_config_files:
            self.logger.info(
                f"Loading additional config files: {', '.join(tool_config_files.keys())}"
            )

        # Merge additional config files with existing tool_files
        all_tool_files = self.tool_files.copy()
        if tool_config_files:
            # Validate that additional config files exist
            for category, file_path in tool_config_files.items():
                if os.path.exists(file_path):
                    all_tool_files[category] = file_path
                    self.logger.debug(
                        f"Added config file for category '{category}': {file_path}"
                    )
                else:
                    self.logger.warning(
                        f"Config file for category '{category}' not found: {file_path}"
                    )

        # Determine which categories to process
        if tool_type is None:
            categories_to_load = [
                cat
                for cat in all_tool_files.keys()
                if cat not in exclude_categories_set
            ]
        else:
            assert isinstance(tool_type, list), (
                "tool_type must be a list of tool category names"
            )
            categories_to_load = [
                cat for cat in tool_type if cat not in exclude_categories_set
            ]

        # Track existing tools before loading new ones (for merge mode)
        # When include_tools is specified, we preserve previously loaded tools
        existing_tool_names = (
            {t.get("name") for t in self.all_tools if isinstance(t, dict)}
            if include_tools_set
            else None
        )

        # Load tools from specified categories
        for each in categories_to_load:
            if each in all_tool_files:
                try:
                    loaded_data = read_json_list(all_tool_files[each])

                    # Handle different data formats
                    if isinstance(loaded_data, dict):
                        # Convert dict of tools to list of tools
                        loaded_tool_list = list(loaded_data.values())
                        self.logger.debug(
                            f"Converted dict to list: {len(loaded_tool_list)} tools"
                        )
                    elif isinstance(loaded_data, list):
                        loaded_tool_list = loaded_data
                    else:
                        self.logger.warning(
                            f"Unexpected data format from {all_tool_files[each]}: {type(loaded_data)}"
                        )
                        continue

                    # Add MCP annotations to each tool config
                    from .tool_defaults import add_annotations_to_tool_config

                    for tool in loaded_tool_list:
                        if isinstance(tool, dict):
                            # Set source_file and category for proper annotation derivation
                            if "source_file" not in tool:
                                tool["source_file"] = all_tool_files[each]
                            if "category" not in tool:
                                tool["category"] = each
                            add_annotations_to_tool_config(tool)

                    self.all_tools += loaded_tool_list
                    self.tool_category_dicts[each] = loaded_tool_list
                    self.logger.debug(
                        f"Loaded {len(loaded_tool_list)} tools from category '{each}'"
                    )
                except Exception as e:
                    # Optional tool files (FileNotFoundError) should not be treated as errors
                    error_msg = str(e)
                    if "No such file or directory" in error_msg or isinstance(
                        e, FileNotFoundError
                    ):
                        self.logger.debug(
                            f"Optional tool category '{each}' not found: {all_tool_files.get(each)}"
                        )
                    else:
                        # Real errors (parsing, permissions, etc.) should still be logged
                        self.logger.error(
                            f"Error loading tools from category '{each}': {e}"
                        )
            else:
                self.logger.warning(
                    f"Tool category '{each}' not found in available tool files"
                )

        # Load auto-discovered configs from decorators
        self._load_auto_discovered_configs()

        # Filter and deduplicate tools
        self._filter_and_deduplicate_tools(
            exclude_tools_set,
            include_tools_set,
            include_tool_types_set,
            exclude_tool_types_set,
            existing_tool_names,
        )

        # Process MCP Auto Loader tools
        self.logger.debug("Checking for MCP Auto Loader tools...")
        self._process_mcp_auto_loaders()

    def _load_tool_names_from_file(self, file_path):
        """
        Load tool names from a text file (one tool name per line).

        Args:
            file_path (str): Path to the text file containing tool names

        Returns:
            list: List of tool names loaded from the file
        """
        try:
            if not os.path.exists(file_path):
                self.logger.error(f"Tools file not found: {file_path}")
                return []

            with open(file_path, "r", encoding="utf-8") as f:
                tool_names = []
                for _line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if line and not line.startswith(
                        "#"
                    ):  # Skip empty lines and comments
                        tool_names.append(line)

            self.logger.info(
                f"Loaded {len(tool_names)} tool names from file: {file_path}"
            )
            return tool_names

        except Exception as e:
            self.logger.error(f"Error loading tool names from file {file_path}: {e}")
            return []

    def _filter_and_deduplicate_tools(
        self,
        exclude_tools_set,
        include_tools_set,
        include_tool_types_set=None,
        exclude_tool_types_set=None,
        existing_tool_names=None,
    ):
        """
        Filter tools based on inclusion/exclusion criteria and remove duplicates.

        Args:
            exclude_tools_set (set): Set of tool names to exclude
            include_tools_set (set or None): Set of tool names to include (if None, include all)
            include_tool_types_set (set or None): Set of tool types to include (if None, include all)
            exclude_tool_types_set (set or None): Set of tool types to exclude (if None, exclude none)
            existing_tool_names (set or None): Set of tool names that were already loaded before this call.
                                               These tools will be preserved even if not in include_tools_set.
                                               Used for merge mode when loading specific tools.
        """
        tool_name_list = []
        dedup_all_tools = []
        all_missing_keys = set()
        duplicate_names = set()
        excluded_tools_count = 0
        included_tools_count = 0
        missing_included_tools = set()

        # If include_tools_set is specified, track which tools we found
        if include_tools_set:
            missing_included_tools = include_tools_set.copy()

        for each in self.all_tools:
            # Handle both dict and string entries
            if isinstance(each, dict):
                tool_name = each.get("name", "")
                tool_type = each.get("type", "Unknown")
            elif isinstance(each, str):
                self.logger.warning(f"Found string in all_tools: {each}")
                continue
            else:
                self.logger.warning(f"Unknown type in all_tools: {type(each)} - {each}")
                continue

            # Check tool type inclusion/exclusion
            if include_tool_types_set and tool_type not in include_tool_types_set:
                self.logger.debug(
                    f"Excluding tool '{tool_name}' - type '{tool_type}' not in include list"
                )
                continue

            if exclude_tool_types_set and tool_type in exclude_tool_types_set:
                self.logger.debug(
                    f"Excluding tool '{tool_name}' - type '{tool_type}' is excluded"
                )
                continue

            # Preserve existing tools (merge mode)
            # If this tool was already loaded before this call, keep it regardless of filters
            if existing_tool_names and tool_name in existing_tool_names:
                # Skip excluded tools even if previously loaded
                if tool_name in exclude_tools_set:
                    excluded_tools_count += 1
                    self.logger.debug(
                        f"Excluding previously loaded tool by name: {tool_name}"
                    )
                    continue

                # Keep this existing tool
                if tool_name not in tool_name_list:
                    tool_name_list.append(tool_name)
                    dedup_all_tools.append(each)
                else:
                    duplicate_names.add(tool_name)
                continue

            # If include_tools_set is specified, only include tools in that set
            if include_tools_set:
                if tool_name not in include_tools_set:
                    continue
                else:
                    missing_included_tools.discard(tool_name)
                    included_tools_count += 1

            # Skip excluded tools
            if tool_name in exclude_tools_set:
                excluded_tools_count += 1
                self.logger.debug(f"Excluding tool by name: {tool_name}")
                continue

            # Check API key requirements
            if "required_api_keys" in each:
                all_keys_available, missing_keys = self._check_api_key_requirements(
                    each
                )
                if not all_keys_available:
                    all_missing_keys.update(missing_keys)
                    self.logger.debug(
                        f"Skipping tool '{tool_name}' due to missing API keys: {', '.join(missing_keys)}"
                    )
                    continue

            # Check API key requirements for AgenticTool type
            if each.get("type") == "AgenticTool":
                from .agentic_tool import AgenticTool

                if not AgenticTool.has_any_api_keys():
                    self.logger.debug(
                        f"Skipping agentic tool '{tool_name}' due to missing LLM API keys"
                    )
                    all_missing_keys.add(
                        "LLM API keys (AZURE_OPENAI_API_KEY, OPENROUTER_API_KEY, or GEMINI_API_KEY)"
                    )
                    continue

            # Handle duplicates
            if tool_name not in tool_name_list:
                tool_name_list.append(tool_name)
                dedup_all_tools.append(each)
            else:
                duplicate_names.add(tool_name)

        # Report statistics
        if duplicate_names:
            self.logger.debug(
                f"Duplicate tool names found and dropped: {', '.join(list(duplicate_names)[:5])}{'...' if len(duplicate_names) > 5 else ''}"
            )
        if excluded_tools_count > 0:
            self.logger.info(f"Excluded {excluded_tools_count} tools by name")
        if include_tools_set:
            self.logger.info(f"Included {included_tools_count} tools by name filter")
            if missing_included_tools:
                self.logger.warning(
                    f"Could not find {len(missing_included_tools)} requested tools: {', '.join(list(missing_included_tools)[:5])}{'...' if len(missing_included_tools) > 5 else ''}"
                )

        self.all_tools = dedup_all_tools
        self.refresh_tool_name_desc()

        info(f"Number of tools after load tools: {len(self.all_tools)}")

        # Generate template for missing API keys
        if len(all_missing_keys) > 0:
            warning(
                f"Some tools will not be loaded due to missing API keys: {', '.join(all_missing_keys)}"
            )
            # info("Generating .env.template file with missing API keys...")
            self.generate_env_template(all_missing_keys)

    def _load_auto_discovered_configs(self):
        """
        Load auto-discovered configs from the decorator registry.

        This method loads tool configurations that were registered automatically
        via the @register_tool decorator with config parameter.
        """
        from .tool_registry import get_config_registry

        discovered_configs = get_config_registry()

        if discovered_configs:
            self.logger.debug(
                f"Loading {len(discovered_configs)} auto-discovered tool configs"
            )
            for _tool_type, config in discovered_configs.items():
                # Add to all_tools if not already present
                if "name" in config and config["name"] not in [
                    tool.get("name")
                    for tool in self.all_tools
                    if isinstance(tool, dict)
                ]:
                    self.all_tools.append(config)
                    self.logger.debug(f"Added auto-discovered config: {config['name']}")

    def _process_mcp_auto_loaders(self):
        """
        Process any MCPAutoLoaderTool instances to automatically discover and register MCP tools.

        This method scans through all loaded tools for MCPAutoLoaderTool instances and runs their
        auto-discovery process to find and register MCP tools from configured servers. It handles
        async operations properly with cleanup and error handling.

        Side Effects:
            - May add new tools to the tool registry
            - Prints debug information about the discovery process
            - Updates tool counts after MCP registration
        """
        self.logger.debug("Starting _process_mcp_auto_loaders")
        import asyncio
        import warnings

        auto_loaders = []
        self.logger.debug(f"Checking {len(self.all_tools)} tools for MCPAutoLoaderTool")
        for tool_config in self.all_tools:
            if tool_config.get("type") == "MCPAutoLoaderTool":
                auto_loaders.append(tool_config)
                self.logger.debug(f"Found MCPAutoLoaderTool: {tool_config['name']}")

        if not auto_loaders:
            self.logger.debug("No MCP Auto Loader tools found")
            return

        info(f"Found {len(auto_loaders)} MCP Auto Loader tool(s), processing...")

        # Check if we're already in an event loop
        try:
            asyncio.get_running_loop()
            in_event_loop = True
            self.logger.debug("Already in an event loop, using async approach")
        except RuntimeError:
            in_event_loop = False
            self.logger.debug("No event loop running, will create new one")

        # Process each auto loader
        for loader_config in auto_loaders:
            self.logger.debug(f"Processing loader: {loader_config['name']}")
            try:
                # Validate required fields before creating instance
                if not loader_config.get("server_url"):
                    error_msg = f"MCPAutoLoaderTool '{loader_config['name']}' is missing required field 'server_url'"
                    self.logger.error(error_msg)
                    warning(error_msg)
                    continue

                # Create auto loader instance
                self.logger.debug("Creating auto loader instance...")
                auto_loader = get_tool_class_lazy("MCPAutoLoaderTool")(loader_config)
                self.logger.debug("Auto loader instance created")

                # Run auto-load process with proper session cleanup and timeout
                self.logger.debug("Starting auto-load process...")

                async def _run_auto_load(loader):
                    """Run auto-load with proper cleanup"""
                    try:
                        # Get timeout from loader config or use default (30 seconds)
                        timeout = loader_config.get("timeout", 30)
                        result = await asyncio.wait_for(
                            loader.auto_load_and_register(self), timeout=timeout
                        )
                        return result
                    except asyncio.TimeoutError:
                        error_msg = f"MCP Auto Loader '{loader_config['name']}' timed out after {timeout} seconds"
                        self.logger.warning(error_msg)
                        warning(error_msg)
                        return {
                            "discovered_count": 0,
                            "registered_count": 0,
                            "tools": [],
                            "registered_tools": [],
                            "error": "timeout",
                        }
                    finally:
                        # Ensure session cleanup
                        await loader._close_session()

                if in_event_loop:
                    # We're already in an event loop, so we can't use run_until_complete
                    # Instead, we'll skip MCP auto-loading for now and warn the user
                    warning(
                        f"Warning: Cannot process MCP Auto Loader '{loader_config['name']}' because we're already in an event loop."
                    )
                    self.logger.debug(
                        "This is a known limitation when SMCP is used within an async context."
                    )
                    self.logger.debug(
                        "MCP tools will need to be loaded manually or the server should be run outside of an async context."
                    )
                    continue
                else:
                    # No event loop, safe to create one
                    # Suppress ResourceWarnings during cleanup
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore", ResourceWarning)

                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            self.logger.debug("Running auto_load_and_register...")
                            result = loop.run_until_complete(
                                _run_auto_load(auto_loader)
                            )
                            self.logger.debug(
                                f"Auto-load completed with result: {result}"
                            )

                            info(
                                f"MCP Auto Loader '{loader_config['name']}' processed:"
                            )
                            info(
                                f"  - Discovered: {result.get('discovered_count', 0)} tools"
                            )
                            info(
                                f"  - Registered: {result.get('registered_count', 0)} tools"
                            )

                            # Print detailed tool information
                            if result.get("tools"):
                                print(
                                    f"  📋 Discovered MCP tools: {', '.join(result['tools'])}"
                                )

                            if result.get("registered_tools"):
                                print(
                                    f"  🔧 Registered tools in ToolUniverse: {', '.join(result['registered_tools'])}"
                                )
                                self.logger.debug(
                                    f"  - Tools: {', '.join(result['registered_tools'])}"
                                )

                            # Show available tools in callable_functions
                            expert_tools = [
                                name
                                for name in self.callable_functions.keys()
                                if name.startswith("expert_")
                            ]
                            if expert_tools:
                                print(
                                    f"  ✅ Expert tools now available: {', '.join(expert_tools)}"
                                )
                            else:
                                print(
                                    "  ⚠️  No expert tools found in callable_functions after registration"
                                )

                        finally:
                            self.logger.debug("Closing async loop...")
                            # Clean up any remaining tasks
                            try:
                                pending = asyncio.all_tasks(loop)
                                for task in pending:
                                    task.cancel()
                                if pending:
                                    loop.run_until_complete(
                                        asyncio.gather(*pending, return_exceptions=True)
                                    )
                            except Exception:
                                pass  # Ignore cleanup errors
                            finally:
                                loop.close()
                            self.logger.debug("Async loop closed")

            except Exception as e:
                self.logger.debug(f"Exception in auto loader processing: {e}")
                import traceback

                traceback.print_exc()
                self.logger.debug(
                    f"Failed to process MCP Auto Loader '{loader_config['name']}': {str(e)}"
                )

        # Update tool count after MCP registration
        self.logger.debug(
            f"Number of tools after MCP auto-loading: {len(self.all_tool_dict)}"
        )
        self.logger.debug("_process_mcp_auto_loaders completed")

    def list_built_in_tools(self, mode="config", scan_all=False):
        """
        List all built-in tool categories and their statistics with different modes.

        This method provides a comprehensive overview of all available tools in the ToolUniverse,
        organized by categories. It reads directly from the default tool files to gather statistics,
        so it works even before calling load_tools().

        Args:
            mode (str, optional): Organization mode for tools. Defaults to 'config'.
                - 'config': Organize by config file categories (original behavior)
                - 'type': Organize by tool types (implementation classes)
                - 'list_name': Return a list of all tool names
                - 'list_spec': Return a list of all tool specifications
            scan_all (bool, optional): Whether to scan all JSON files in data directory recursively.
                If True, scans all JSON files in data/ and its subdirectories.
                If False (default), uses predefined tool file mappings.

        Returns:
            dict or list:
                - For 'config' and 'type' modes: A dictionary containing tool statistics
                - For 'list_name' mode: A list of all tool names
                - For 'list_spec' mode: A list of all tool specifications

        Example:
            >>> tool_universe = ToolUniverse()
            >>> # Group by config file categories (predefined files only)
            >>> stats = tool_universe.list_built_in_tools(mode='config')
            >>> # Scan all JSON files in data directory recursively
            >>> stats = tool_universe.list_built_in_tools(mode='config', scan_all=True)
            >>> # Get all tool names from all JSON files
            >>> tool_names = tool_universe.list_built_in_tools(mode='list_name', scan_all=True)

        Note:
            - This method reads directly from tool files and works without calling load_tools()
            - Tools are deduplicated across categories, so the same tool won't be counted multiple times
            - The summary is automatically printed to console when this method is called (except for list_name and list_spec modes)
            - When scan_all=True, all JSON files in data/ and subdirectories are scanned
        """
        if mode not in ["config", "type", "list_name", "list_spec"]:
            # Handle invalid modes gracefully
            if mode is None:
                mode = "config"  # Default to config mode
            else:
                # For invalid string modes, return error info instead of raising
                return {
                    "error": f"Invalid mode '{mode}'. Must be one of: 'config', 'type', 'list_name', 'list_spec'"
                }

        # For list_name and list_spec modes, we can return early with just the data
        if mode in ["list_name", "list_spec"]:
            all_tools = []
            all_tool_names = set()  # For deduplication across categories

            if scan_all:
                # Scan all JSON files in data directory recursively
                all_tools, all_tool_names = self._scan_all_json_files()
            else:
                # Use predefined tool files (original behavior)
                all_tools, all_tool_names = self._scan_predefined_files()

            # Deduplicate tools by name
            unique_tools = {}
            for tool in all_tools:
                if tool["name"] not in unique_tools:
                    unique_tools[tool["name"]] = tool

            if mode == "list_name":
                return sorted(list(unique_tools.keys()))
            elif mode == "list_spec":
                return list(unique_tools.values())

        # Original logic for config and type modes
        result = {
            "categories": {},
            "total_categories": 0,
            "total_tools": 0,
            "mode": mode,
            "summary": "",
        }

        if scan_all:
            # Scan all JSON files in data directory recursively
            all_tools, all_tool_names = self._scan_all_json_files()

            # For config mode with scan_all, organize by file names
            if mode == "config":
                file_tools_map = {}
                for tool in all_tools:
                    # Get the source file for this tool (we need to track this)
                    # For now, we'll organize by tool type as a fallback
                    tool_type = tool.get("type", "Unknown")
                    if tool_type not in file_tools_map:
                        file_tools_map[tool_type] = []
                    file_tools_map[tool_type].append(tool)

                for category, tools in file_tools_map.items():
                    result["categories"][category] = {"count": len(tools)}
        else:
            # Use predefined tool files (original behavior)
            all_tools, all_tool_names = self._scan_predefined_files()

            # Read tools from each category file
            for category, file_path in self.tool_files.items():
                try:
                    # Read the JSON file for this category
                    tools_in_category = read_json_list(file_path)

                    if mode == "config":
                        tool_names = [tool["name"] for tool in tools_in_category]
                        result["categories"][category] = {"count": len(tool_names)}

                except Exception as e:
                    warning(
                        f"Warning: Could not read tools from {category} ({file_path}): {e}"
                    )
                    if mode == "config":
                        result["categories"][category] = {"count": 0}

        # If mode is 'type', organize by tool types instead
        if mode == "type":
            # Deduplicate tools by name first
            unique_tools = {}
            for tool in all_tools:
                if tool["name"] not in unique_tools:
                    unique_tools[tool["name"]] = tool

            # Group by tool type
            type_groups = {}
            for tool in unique_tools.values():
                tool_type = tool.get("type", "Unknown")
                if tool_type not in type_groups:
                    type_groups[tool_type] = []
                type_groups[tool_type].append(tool["name"])

            # Build result for type mode
            for tool_type, tool_names in type_groups.items():
                result["categories"][tool_type] = {
                    "count": len(tool_names),
                    "tools": sorted(tool_names),
                }

        # Calculate totals
        result["total_categories"] = len(result["categories"])
        result["total_tools"] = len(all_tool_names)

        # Generate summary information
        mode_title = "Config File Categories" if mode == "config" else "Tool Types"
        summary_lines = [
            "=" * 60,
            f"🔧 ToolUniverse Built-in Tools Overview ({mode_title})",
            "=" * 60,
            f"📊 Total Categories: {result['total_categories']}",
            f"🛠️  Total Unique Tools: {result['total_tools']}",
            f"📋 Organization Mode: {mode}",
            "",
            f"📂 {mode_title} Breakdown:",
            "-" * 40,
        ]

        # Sort categories by tool count (descending) for better visualization
        sorted_categories = sorted(
            result["categories"].items(), key=lambda x: x[1]["count"], reverse=True
        )

        for category, category_info in sorted_categories:
            count = category_info["count"]
            # Add visual indicators for different tool counts
            if count >= 10:
                icon = "🟢"
            elif count >= 5:
                icon = "🟡"
            elif count >= 1:
                icon = "🟠"
            else:
                icon = "🔴"

            # Format category name to be more readable
            if mode == "config":
                display_name = category.replace("_", " ").title()
            else:
                display_name = category

            summary_lines.append(f"  {icon} {display_name:<35} {count:>3} tools")

            # For type mode, optionally show some tool examples
            if (
                mode == "type"
                and "tools" in category_info
                and len(category_info["tools"]) <= 5
            ):
                for tool_name in category_info["tools"]:
                    summary_lines.append(f"    └─ {tool_name}")
            elif (
                mode == "type"
                and "tools" in category_info
                and len(category_info["tools"]) > 5
            ):
                for tool_name in category_info["tools"][:3]:
                    summary_lines.append(f"    └─ {tool_name}")
                summary_lines.append(
                    f"    └─ ... and {len(category_info['tools']) - 3} more"
                )

        summary_lines.extend(
            ["-" * 40, "✅ Ready to use! Call load_tools() to initialize.", "=" * 60]
        )

        result["summary"] = "\n".join(summary_lines)

        # Print summary to console directly
        print(result["summary"])

        return result

    def _read_tools_from_file(self, file_path):
        """
        Read tools from a single JSON file with error handling.

        Args:
            file_path (str): Path to the JSON file

        Returns:
            list: List of tool configurations from the file
        """
        try:
            tools_in_file = read_json_list(file_path)

            # Handle different data formats
            if isinstance(tools_in_file, dict):
                # Convert dict of tools to list of tools
                tools_in_file = list(tools_in_file.values())
            elif not isinstance(tools_in_file, list):
                # Skip files that don't contain tool configurations
                return []

            # Validate tools have required fields
            valid_tools = []
            for tool in tools_in_file:
                # Validate that tool is a dict, has "name" field, and name is a string
                if isinstance(tool, dict) and "name" in tool:
                    name_value = tool["name"]
                    # Ensure name is a string (not a dict/object) - this filters out schema files
                    if isinstance(name_value, str):
                        valid_tools.append(tool)

            return valid_tools

        except Exception as e:
            warning(f"Warning: Could not read tools from {file_path}: {e}")
            return []

    def _scan_predefined_files(self):
        """
        Scan predefined tool files (original behavior).

        Returns:
            tuple: (all_tools, all_tool_names) where all_tools is a list of tool configs
                   and all_tool_names is a set of tool names for deduplication
        """
        all_tools = []
        all_tool_names = set()

        # Read tools from each category file
        for _category, file_path in self.tool_files.items():
            tools_in_category = self._read_tools_from_file(file_path)
            all_tools.extend(tools_in_category)
            # Only add string names to the set (filter out any non-string names as extra safety)
            tool_names = [
                tool["name"]
                for tool in tools_in_category
                if isinstance(tool.get("name"), str)
            ]
            all_tool_names.update(tool_names)

        # Also include remote tools
        try:
            remote_dir = os.path.join(current_dir, "data", "remote_tools")
            if os.path.isdir(remote_dir):
                for fname in os.listdir(remote_dir):
                    if not fname.lower().endswith(".json"):
                        continue
                    fpath = os.path.join(remote_dir, fname)
                    remote_tools = self._read_tools_from_file(fpath)
                    if remote_tools:
                        all_tools.extend(remote_tools)
                        # Only add string names to the set (filter out any non-string names as extra safety)
                        tool_names = [
                            tool["name"]
                            for tool in remote_tools
                            if isinstance(tool.get("name"), str)
                        ]
                        all_tool_names.update(tool_names)
        except Exception as e:
            warning(f"Warning: Failed to scan remote tools directory: {e}")

        return all_tools, all_tool_names

    def _scan_all_json_files(self):
        """
        Recursively scan all JSON files in the data directory and its subdirectories.

        Returns:
            tuple: (all_tools, all_tool_names) where all_tools is a list of tool configs
                   and all_tool_names is a set of tool names for deduplication
        """
        all_tools = []
        all_tool_names = set()

        # Get the data directory path
        data_dir = os.path.join(current_dir, "data")

        if not os.path.exists(data_dir):
            warning(f"Warning: Data directory not found: {data_dir}")
            return all_tools, all_tool_names

        # Recursively find all JSON files, excluding schema files
        json_files = []
        for root, _dirs, files in os.walk(data_dir):
            # Skip schemas directory (contains JSON schema definition files, not tool configs)
            if "schemas" in root:
                continue
            for file in files:
                if file.lower().endswith(".json"):
                    # Skip files with "schema" in the name
                    if "schema" in file.lower():
                        continue
                    json_files.append(os.path.join(root, file))

        self.logger.debug(f"Found {len(json_files)} JSON files to scan")

        # Read tools from each JSON file using the common method
        for json_file in json_files:
            tools_in_file = self._read_tools_from_file(json_file)
            if tools_in_file:
                all_tools.extend(tools_in_file)
                # Only add string names to the set (filter out any non-string names as extra safety)
                tool_names = [
                    tool["name"]
                    for tool in tools_in_file
                    if isinstance(tool.get("name"), str)
                ]
                all_tool_names.update(tool_names)
                self.logger.debug(f"Loaded {len(tools_in_file)} tools from {json_file}")

        self.logger.info(
            f"Scanned {len(json_files)} JSON files, found {len(all_tools)} tools"
        )
        return all_tools, all_tool_names

    def refresh_tool_name_desc(
        self,
        enable_full_desc=False,
        include_names=None,
        exclude_names=None,
        include_categories=None,
        exclude_categories=None,
    ):
        """
        Refresh the tool name and description mappings with optional filtering.

        This method rebuilds the internal tool dictionary and generates filtered lists of tool names
        and descriptions based on the provided filter criteria.

        Args:
            enable_full_desc (bool, optional): If True, includes full tool JSON as description.
                                             If False, uses "name: description" format. Defaults to False.
            include_names (list, optional): List of tool names to include.
            exclude_names (list, optional): List of tool names to exclude.
            include_categories (list, optional): List of categories to include.
            exclude_categories (list, optional): List of categories to exclude.

        Returns:
            tuple: A tuple containing (tool_name_list, tool_desc_list) after filtering.
        """
        tool_name_list = []
        tool_desc_list = []
        for tool in self.all_tools:
            # Use the stored original name if available (avoids re-shortening
            # an already-shortened name when this method is called multiple times)
            original_name = tool.get("original_name", tool["name"])

            # If shortening enabled, use shortened name as primary key
            if self.enable_name_shortening:
                shortened_name = self.name_mapper.get_shortened(
                    original_name, max_length=self.MAX_TOOL_NAME_LENGTH
                )
                tool["name"] = shortened_name  # Overwrite with shortened name
                tool["original_name"] = original_name  # Store original for reference
            else:
                shortened_name = original_name

            # Use shortened name throughout (it's now the primary identifier)
            tool_name_list.append(shortened_name)
            if enable_full_desc:
                tool_desc_list.append(json.dumps(tool))
            else:
                tool_desc_list.append(shortened_name + ": " + tool["description"])

            # Store with SHORTENED name as key (primary identifier)
            self.all_tool_dict[shortened_name] = tool

            # Register aliases with the name mapper for backward compatibility
            if "aliases" in tool and tool["aliases"]:
                for alias in tool["aliases"]:
                    self.name_mapper.add_alias(alias, shortened_name)

        # Apply filtering if any filter argument is provided
        if any([include_names, exclude_names, include_categories, exclude_categories]):
            tool_name_list, tool_desc_list = self.filter_tool_lists(
                tool_name_list,
                tool_desc_list,
                include_names=include_names,
                exclude_names=exclude_names,
                include_categories=include_categories,
                exclude_categories=exclude_categories,
            )

        self.logger.debug(
            f"Number of tools after refresh and filter: {len(tool_name_list)}"
        )

        return tool_name_list, tool_desc_list

    def prepare_one_tool_prompt(self, tool):
        """
        Prepare a single tool configuration for prompt usage by filtering to essential keys.

        Args:
            tool (dict): Tool configuration dictionary.

        Returns:
            dict: Tool configuration with only essential keys for prompting.
        """
        valid_keys = ["name", "description", "parameter", "required"]
        tool = copy.deepcopy(tool)
        for key in list(tool.keys()):
            if key not in valid_keys:
                del tool[key]
        return tool

    def prepare_tool_prompts(self, tool_list, mode="prompt", valid_keys=None):
        """
        Prepare a list of tool configurations for different usage modes.

        Args:
            tool_list (list): List of tool configuration dictionaries.
            mode (str): Preparation mode. Options:
                - 'prompt': Keep essential keys for prompting (name, description, parameter, required)
                - 'example': Keep extended keys for examples (name, description, parameter, required, query_schema, fields, label, type)
                - 'custom': Use custom valid_keys parameter
            valid_keys (list, optional): Custom list of keys to keep when mode='custom'.

        Returns:
            list: List of tool configurations with only specified keys.
        """
        if mode == "prompt":
            valid_keys = ["name", "description", "parameter", "required"]
        elif mode == "example":
            valid_keys = [
                "name",
                "description",
                "parameter",
                "required",
                "query_schema",
                "fields",
                "label",
                "type",
            ]
        elif mode == "custom":
            if valid_keys is None:
                raise ValueError("valid_keys must be provided when mode='custom'")
        else:
            raise ValueError(
                f"Invalid mode: {mode}. Must be 'prompt', 'example', or 'custom'"
            )

        copied_list = copy.deepcopy(tool_list)
        for tool in copied_list:
            # Create a list of keys to avoid modifying the dictionary during iteration
            for key in list(tool.keys()):
                if key not in valid_keys:
                    del tool[key]
        return copied_list

    def get_tool_specification_by_names(self, tool_names, format="default"):
        """
        Retrieve tool specifications by their names using tool_specification method.

        Args:
            tool_names (list): List of tool names to retrieve.
            format (str, optional): Output format. Options: 'default', 'openai'.
                                   If 'openai', returns OpenAI function calling format. Defaults to 'default'.

        Returns:
            list: List of tool specifications for the specified names.
                 Tools not found will be reported but not included in the result.
        """
        picked_tool_list = []
        for each_name in tool_names:
            tool_spec = self.tool_specification(each_name, format=format)
            if tool_spec:
                picked_tool_list.append(tool_spec)
        return picked_tool_list

    def get_one_tool_by_one_name(self, tool_name, return_prompt=True):
        """
        Retrieve a single tool specification by name, optionally prepared for prompting.

        This is a convenience method that calls get_one_tool_by_one_name.

        Args:
            tool_name (str): Name of the tool to retrieve.
            return_prompt (bool, optional): If True, returns tool prepared for prompting.
                                          If False, returns full tool configuration. Defaults to True.

        Returns:
            dict or None: Tool configuration if found, None otherwise.
        """
        warning(
            "The 'get_one_tool_by_one_name' method is deprecated and will be removed in a future version. "
            "Please use 'tool_specification' instead."
        )
        return self.tool_specification(tool_name, return_prompt=return_prompt)

    def tool_specification(self, tool_name, return_prompt=False, format="default"):
        """
        Retrieve a single tool configuration by name.

        Args:
            tool_name (str): Name of the tool to retrieve.
            return_prompt (bool, optional): If True, returns tool prepared for prompting.
                                          If False, returns full tool configuration. Defaults to False.
            format (str, optional): Output format. Options: 'default', 'openai'.
                                   If 'openai', returns OpenAI function calling format. Defaults to 'default'.

        Returns:
            dict or None: Tool configuration if found, None otherwise.
        """
        if tool_name not in self.all_tool_dict:
            warning(f"Tool name {tool_name} not found in the loaded tools.")
            return None

        tool_config = self.all_tool_dict[tool_name]

        if return_prompt:
            return self.prepare_one_tool_prompt(tool_config)

        # Process parameter schema based on format
        if "parameter" in tool_config and isinstance(tool_config["parameter"], dict):
            import copy

            processed_config = copy.deepcopy(tool_config)
            parameter_schema = processed_config["parameter"]

            if (
                "properties" in parameter_schema
                and parameter_schema["properties"] is not None
            ):
                required_properties = parameter_schema.get("required", [])

                if format == "openai":
                    # For OpenAI format: remove property-level required fields
                    for _prop_name, prop_config in parameter_schema[
                        "properties"
                    ].items():
                        if isinstance(prop_config, dict) and "required" in prop_config:
                            del prop_config["required"]

                    # Ensure required is a list
                    if not isinstance(parameter_schema.get("required"), list):
                        parameter_schema["required"] = (
                            required_properties if required_properties else []
                        )

                    return {
                        "name": processed_config["name"],
                        "description": processed_config["description"],
                        "parameters": parameter_schema,
                    }
                else:
                    # For default format: add required fields to properties
                    for prop_name, prop_config in parameter_schema[
                        "properties"
                    ].items():
                        if isinstance(prop_config, dict):
                            prop_config["required"] = prop_name in required_properties

                    return processed_config

        return tool_config

    def get_tool_type_by_name(self, tool_name):
        """
        Get the type of a tool by its name.

        Args:
            tool_name (str): Name of the tool.

        Returns:
            str: The type of the tool.

        Raises:
            KeyError: If the tool name is not found in loaded tools.
        """
        return self.all_tool_dict[tool_name]["type"]

    def call_id_gen(self):
        """
        Generate a random call ID for function calls.

        Returns:
            str: A random 9-character string composed of letters and digits.
        """
        return "".join(random.choices(string.ascii_letters + string.digits, k=9))

    def tool_to_str(self, tool_list):
        """
        Convert a list of tool configurations to a formatted string.

        Args:
            tool_list (list): List of tool configuration dictionaries.

        Returns:
            str: JSON-formatted string representation of the tools, with each tool
                 separated by double newlines.
        """
        return "\n\n".join(json.dumps(obj, indent=4) for obj in tool_list)

    def extract_function_call_json(
        self, lst, return_message=False, verbose=True, format="llama"
    ):
        """
        Extract function call JSON from input data.

        This method delegates to the utility function extract_function_call_json.

        Args:
            lst: Input data containing function call information.
            return_message (bool, optional): Whether to return message along with JSON. Defaults to False.
            verbose (bool, optional): Whether to enable verbose output. Defaults to True.
            format (str, optional): Format type for extraction. Defaults to 'llama'.

        Returns:
            dict or tuple: Function call JSON, optionally with message if return_message is True.
        """
        return extract_function_call_json(
            lst, return_message=return_message, verbose=verbose, format=format
        )

    def return_all_loaded_tools(self):
        """
        Return a deep copy of all loaded tools.

        Returns:
            list: A deep copy of the all_tools list to prevent external modification.
        """
        return copy.deepcopy(self.all_tools)

    def _execute_function_call_list(
        self,
        function_calls: List[Dict[str, Any]],
        stream_callback=None,
        use_cache: bool = False,
        max_workers: Optional[int] = None,
    ) -> List[Any]:
        """Execute a list of function calls, optionally in parallel.

        Args:
            function_calls: Ordered list of function call dictionaries.
            stream_callback: Optional streaming callback.
            use_cache: Whether to enable cache lookups for each call.
            max_workers: Maximum parallel workers; values <=1 fall back to sequential execution.

        Returns:
            List of results aligned with ``function_calls`` order.
        """

        if not function_calls:
            return []

        if stream_callback is not None and max_workers and max_workers > 1:
            # Streaming multiple calls concurrently is ambiguous; fall back to sequential execution.
            self.logger.warning(
                "stream_callback is not supported with parallel batch execution; falling back to sequential mode"
            )
            max_workers = 1

        jobs = self._build_batch_jobs(function_calls)
        results: List[Any] = [None] * len(function_calls)

        jobs_to_run = self._prime_batch_cache(jobs, use_cache, results)
        if not jobs_to_run:
            return results

        self._execute_batch_jobs(
            jobs_to_run,
            results,
            stream_callback=stream_callback,
            use_cache=use_cache,
            max_workers=max_workers,
        )

        return results

    def _build_batch_jobs(
        self, function_calls: List[Dict[str, Any]]
    ) -> List[_BatchJob]:
        signature_to_job: Dict[str, _BatchJob] = {}
        jobs: List[_BatchJob] = []

        for idx, call in enumerate(function_calls):
            function_name = call.get("name", "")
            arguments = call.get("arguments", {})
            if not isinstance(arguments, dict):
                arguments = {}

            signature = json.dumps(
                {"name": function_name, "arguments": arguments}, sort_keys=True
            )

            job = signature_to_job.get(signature)
            if job is None:
                job = _BatchJob(
                    signature=signature,
                    call=call,
                    function_name=function_name,
                    arguments=arguments,
                )
                signature_to_job[signature] = job
                jobs.append(job)

            job.indices.append(idx)

        return jobs

    def _prime_batch_cache(
        self,
        jobs: List[_BatchJob],
        use_cache: bool,
        results: List[Any],
    ) -> List[_BatchJob]:
        if not (
            use_cache and self.cache_manager is not None and self.cache_manager.enabled
        ):
            return jobs

        cache_requests: List[Dict[str, str]] = []
        for job in jobs:
            if not job.function_name:
                continue

            tool_instance = self._ensure_tool_instance(job)
            if (
                not tool_instance
                or not getattr(tool_instance, "supports_caching", lambda: True)()
            ):
                continue

            cache_key = tool_instance.get_cache_key(job.arguments or {})
            cache_info = _BatchCacheInfo(
                namespace=tool_instance.get_cache_namespace(),
                version=tool_instance.get_cache_version(),
                cache_key=cache_key,
            )
            job.cache_info = cache_info
            job.cache_key_composed = self.cache_manager.compose_key(
                cache_info.namespace, cache_info.version, cache_info.cache_key
            )
            cache_requests.append(
                {
                    "namespace": cache_info.namespace,
                    "version": cache_info.version,
                    "cache_key": cache_info.cache_key,
                }
            )

        if cache_requests:
            cache_hits = self.cache_manager.bulk_get(cache_requests)
            if cache_hits:
                for job in jobs:
                    if job.cache_key_composed and job.cache_key_composed in cache_hits:
                        cached_value = cache_hits[job.cache_key_composed]
                        for idx in job.indices:
                            results[idx] = cached_value
                        job.skip_execution = True

        return [job for job in jobs if not job.skip_execution]

    def _execute_batch_jobs(
        self,
        jobs_to_run: List[_BatchJob],
        results: List[Any],
        *,
        stream_callback,
        use_cache: bool,
        max_workers: Optional[int],
    ) -> None:
        if not jobs_to_run:
            return

        tool_semaphores: Dict[str, Optional[threading.Semaphore]] = {}

        def run_job(job: _BatchJob):
            semaphore = self._get_tool_semaphore(job, tool_semaphores)
            if semaphore:
                semaphore.acquire()
            try:
                # Check if tool is async
                tool_instance = self._ensure_tool_instance(job)
                if tool_instance and inspect.iscoroutinefunction(tool_instance.run):
                    # Async tool in sync context - use asyncio.run()
                    result = asyncio.run(
                        self.run_one_function_async(
                            job.call,
                            stream_callback=stream_callback,
                            use_cache=use_cache,
                        )
                    )
                else:
                    # Sync tool - use regular execution
                    result = self.run_one_function(
                        job.call,
                        stream_callback=stream_callback,
                        use_cache=use_cache,
                    )
            finally:
                if semaphore:
                    semaphore.release()

            for idx in job.indices:
                results[idx] = result

        if max_workers and max_workers > 1:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(run_job, job) for job in jobs_to_run]
                for future in as_completed(futures):
                    future.result()
        else:
            for job in jobs_to_run:
                run_job(job)

    def _ensure_tool_instance(self, job: _BatchJob):
        if job.tool_instance is None and job.function_name:
            job.tool_instance = self._get_tool_instance(job.function_name, cache=True)
        return job.tool_instance

    def _get_tool_semaphore(
        self,
        job: _BatchJob,
        tool_semaphores: Dict[str, Optional[threading.Semaphore]],
    ) -> Optional[threading.Semaphore]:
        if job.function_name not in tool_semaphores:
            tool_instance = self._ensure_tool_instance(job)
            limit = (
                tool_instance.get_batch_concurrency_limit()
                if tool_instance is not None
                else 0
            )
            self.logger.debug("Batch concurrency for %s: %s", job.function_name, limit)
            if limit and limit > 0:
                tool_semaphores[job.function_name] = threading.Semaphore(limit)
            else:
                tool_semaphores[job.function_name] = None

        return tool_semaphores[job.function_name]

    def run(
        self,
        fcall_str,
        return_message=False,
        verbose=True,
        format="llama",
        stream_callback=None,
        use_cache: bool = False,
        max_workers: Optional[int] = None,
    ):
        """
        Context-aware execution - works in both sync and async contexts.

        In sync context:
            result = tu.run(...)  # Returns result directly (may block for async tools)

        In async context:
            result = await tu.run(...)  # Returns coroutine, non-blocking

        This method automatically detects the context and behaves appropriately.

        Args:
            fcall_str: Input string or data containing function call information.
            return_message (bool, optional): Whether to return formatted messages. Defaults to False.
            verbose (bool, optional): Whether to enable verbose output. Defaults to True.
            format (str, optional): Format type for parsing. Defaults to 'llama'.
            stream_callback: Optional callback for streaming responses.
            use_cache (bool, optional): Whether to use result caching. Defaults to False.
            max_workers (Optional[int]): Max workers for parallel batch execution (sync only).

        Returns:
            Result (sync) or coroutine (async) depending on context.
        """
        # Detect if we're in an async context
        try:
            asyncio.get_running_loop()
            # We're in an async context - return coroutine
            return self._run_async(
                fcall_str,
                return_message=return_message,
                verbose=verbose,
                format=format,
                stream_callback=stream_callback,
                use_cache=use_cache,
            )
        except RuntimeError:
            # Not in async context - run synchronously
            return self._run_sync(
                fcall_str,
                return_message=return_message,
                verbose=verbose,
                format=format,
                stream_callback=stream_callback,
                use_cache=use_cache,
                max_workers=max_workers,
            )

    def _run_sync(
        self,
        fcall_str,
        return_message=False,
        verbose=True,
        format="llama",
        stream_callback=None,
        use_cache=False,
        max_workers=None,
    ):
        """
        Synchronous execution implementation (original run logic).

        For async tools, this will create an event loop if needed.
        """
        if return_message:
            function_call_json, message = self.extract_function_call_json(
                fcall_str, return_message=return_message, verbose=verbose, format=format
            )
        else:
            function_call_json = self.extract_function_call_json(
                fcall_str, return_message=return_message, verbose=verbose, format=format
            )
            message = ""

        if function_call_json is None:
            error("Not a function call")
            return None

        if isinstance(function_call_json, list):
            batch_results = self._execute_function_call_list(
                function_call_json,
                stream_callback=stream_callback,
                use_cache=use_cache,
                max_workers=max_workers,
            )
            if not return_message:
                return batch_results
            return self._format_batch_as_messages(
                batch_results, function_call_json, message
            )

        # Single execution - check if tool is async
        function_name = function_call_json.get("name", "")
        function_name = self._resolve_tool_name(function_name)
        tool_instance = (
            self._get_tool_instance(function_name, cache=True)
            if function_name
            else None
        )

        if tool_instance and inspect.iscoroutinefunction(tool_instance.run):
            self.logger.debug(f"Running async tool '{function_name}' in sync context")
            try:
                asyncio.get_running_loop()
                raise RuntimeError(
                    f"Tool '{function_name}' is async. You're in an async context - use 'await tu.run(...)' instead."
                )
            except RuntimeError as e:
                if "no running event loop" not in str(e).lower():
                    raise
                return asyncio.run(
                    self.run_one_function_async(
                        function_call_json,
                        stream_callback=stream_callback,
                        use_cache=use_cache,
                    )
                )

        return self.run_one_function(
            function_call_json,
            stream_callback=stream_callback,
            use_cache=use_cache,
        )

    def _format_batch_as_messages(self, batch_results, function_call_json, message):
        """Format batch results as tool/assistant message dicts for return_message mode."""
        call_results = []
        for idx, call_result in enumerate(batch_results):
            call_id = self.call_id_gen()
            function_call_json[idx]["call_id"] = call_id
            call_results.append(
                {
                    "role": "tool",
                    "content": json.dumps({"content": call_result, "call_id": call_id}),
                }
            )
        return [
            {
                "role": "assistant",
                "content": message,
                "tool_calls": json.dumps(function_call_json),
            }
        ] + call_results

    async def _run_async(
        self,
        fcall_str,
        return_message=False,
        verbose=True,
        format="llama",
        stream_callback=None,
        use_cache=False,
    ):
        """
        Asynchronous execution implementation (non-blocking).

        Handles both sync and async tools in async context.
        """
        if return_message:
            function_call_json, message = self.extract_function_call_json(
                fcall_str, return_message=return_message, verbose=verbose, format=format
            )
        else:
            function_call_json = self.extract_function_call_json(
                fcall_str, return_message=return_message, verbose=verbose, format=format
            )
            message = ""

        if function_call_json is None:
            error("Not a function call")
            return None

        if isinstance(function_call_json, list):
            batch_results = await self._execute_function_call_list_async(
                function_call_json,
                stream_callback=stream_callback,
                use_cache=use_cache,
            )
            if not return_message:
                return batch_results
            return self._format_batch_as_messages(
                batch_results, function_call_json, message
            )

        return await self.run_one_function_async(
            function_call_json,
            stream_callback=stream_callback,
            use_cache=use_cache,
        )

    async def _execute_function_call_list_async(
        self,
        function_call_list,
        stream_callback=None,
        use_cache=False,
    ):
        """
        Execute multiple function calls asynchronously and in parallel.

        Uses return_exceptions=True so one failure does not abort others.
        """
        tasks = [
            self.run_one_function_async(
                call,
                stream_callback=stream_callback,
                use_cache=use_cache,
            )
            for call in function_call_list
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        processed_results = []
        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                function_name = function_call_list[idx].get("name", "unknown")
                arguments = function_call_list[idx].get("arguments", {})
                classified_error = self._classify_exception(
                    result, function_name, arguments
                )
                processed_results.append(
                    self._create_dual_format_error(classified_error)
                )
            else:
                processed_results.append(result)

        return processed_results

    def _resolve_tool_name(self, function_name: str) -> str:
        """
        Resolve tool name to its primary identifier.

        Uses the ToolNameMapper to handle:
        1. Aliases (e.g., old tool names) -> primary name
        2. Original names -> shortened names (if shortening enabled)
        3. Already primary names -> return as-is

        Args:
            function_name: Tool name (can be alias, original, or shortened)

        Returns:
            str: Resolved tool name (primary identifier in all_tool_dict)
        """
        if function_name:
            # Let the mapper handle all resolution (aliases, original->short, etc.)
            resolved = self.name_mapper.resolve(
                function_name, max_length=self.MAX_TOOL_NAME_LENGTH
            )
            # Only return resolved name if it exists in all_tool_dict
            if resolved in self.all_tool_dict:
                return resolved
        return function_name

    def run_one_function(
        self, function_call_json, stream_callback=None, use_cache=False, validate=True
    ):
        """
        Execute a single function call.

        This method validates the function call, initializes the tool if necessary,
        and executes it with the provided arguments. If hooks are enabled, it also
        applies output hooks to process the result.

        Args:
            function_call_json (dict): Dictionary containing function name and arguments.
            stream_callback (callable, optional): Callback for streaming responses.
            use_cache (bool, optional): Whether to use result caching. Defaults to False.
            validate (bool, optional): Whether to validate parameters against schema. Defaults to True.

        Returns:
            str or dict: Result from the tool execution, or error message if validation fails.
        """
        function_name = function_call_json.get("name", "")
        arguments = function_call_json.get("arguments", {})

        # Resolve original names to shortened names (all_tool_dict uses shortened as keys)
        function_name = self._resolve_tool_name(function_name)

        # Handle malformed queries gracefully
        if not function_name:
            return {"error": "Missing or empty function name"}

        if not isinstance(arguments, dict):
            return {
                "error": f"Arguments must be a dictionary, got {type(arguments).__name__}"
            }

        tool_instance = None
        cache_namespace = None
        cache_version = None
        cache_key = None
        composed_cache_key = None
        cache_guard = nullcontext()

        cache_enabled = (
            use_cache and self.cache_manager is not None and self.cache_manager.enabled
        )

        if cache_enabled:
            tool_instance = self._get_tool_instance(function_name, cache=True)
            if (
                tool_instance
                and getattr(tool_instance, "supports_caching", lambda: True)()
            ):
                cache_namespace = tool_instance.get_cache_namespace()
                cache_version = tool_instance.get_cache_version()
                cache_key = self._make_cache_key(
                    function_name, arguments, tool_instance
                )
                composed_cache_key = self.cache_manager.compose_key(
                    cache_namespace, cache_version, cache_key
                )
                cached_value = self.cache_manager.get(
                    namespace=cache_namespace,
                    version=cache_version,
                    cache_key=cache_key,
                )
                if cached_value is not None:
                    self.logger.debug(f"Cache hit for {function_name}")
                    return cached_value
                cache_guard = self.cache_manager.singleflight_guard(composed_cache_key)
            else:
                cache_enabled = False

        with cache_guard:
            if cache_enabled:
                cached_value = self.cache_manager.get(
                    namespace=cache_namespace,
                    version=cache_version,
                    cache_key=cache_key,
                )
                if cached_value is not None:
                    self.logger.debug(
                        f"Cache hit for {function_name} (after singleflight wait)"
                    )
                    return cached_value

            # Coerce types if lenient coercion is enabled
            if self.lenient_type_coercion:
                arguments = self._coerce_arguments_to_schema(function_name, arguments)
                # Update the original dict so coerced arguments are used
                function_call_json["arguments"] = arguments

            # Validate parameters if requested
            if validate:
                validation_error = self._validate_parameters(function_name, arguments)
                if validation_error:
                    return self._create_dual_format_error(validation_error)
            else:
                # When validate=False, perform lightweight checks:
                # 1. Verify tool exists in all_tool_dict
                # 2. No parameter validation (for performance)
                if function_name not in self.all_tool_dict:
                    return self._create_dual_format_error(
                        ToolValidationError(
                            f"Tool '{function_name}' not found",
                            details={"tool_name": function_name},
                        )
                    )

            # Execute the tool
            tool_arguments = arguments
            try:
                if tool_instance is None:
                    tool_instance = self._get_tool_instance(function_name, cache=True)

                if tool_instance:
                    result, tool_arguments = self._execute_tool_with_stream(
                        tool_instance, arguments, stream_callback, use_cache, validate
                    )
                else:
                    # Try to auto-load tools if dictionary is empty
                    if not self._auto_load_tools_if_empty(function_name):
                        error_msg = "Failed to auto-load tools"
                        return self._create_dual_format_error(
                            ToolUnavailableError(
                                error_msg,
                                next_steps=[
                                    "Manually run tu.load_tools()",
                                    "Check tool configuration",
                                ],
                            )
                        )

                    # Try to get the tool instance again after loading
                    tool_instance = self._get_tool_instance(function_name, cache=True)
                    if tool_instance:
                        result, tool_arguments = self._execute_tool_with_stream(
                            tool_instance,
                            arguments,
                            stream_callback,
                            use_cache,
                            validate,
                        )
                    else:
                        error_msg = (
                            f"Tool '{function_name}' not found even after loading tools"
                        )
                        return self._create_dual_format_error(
                            ToolUnavailableError(
                                error_msg,
                                next_steps=[
                                    "Check tool name spelling",
                                    "Verify tool is available in loaded categories",
                                ],
                            )
                        )
            except Exception as e:
                # Classify and return structured error
                classified_error = self._classify_exception(e, function_name, arguments)
                return self._create_dual_format_error(classified_error)

            # Apply output hooks if enabled
            if self.hook_manager:
                context = {
                    "tool_name": function_name,
                    "tool_type": (
                        tool_instance.__class__.__name__
                        if tool_instance is not None
                        else "unknown"
                    ),
                    "execution_time": time.time(),
                    "arguments": tool_arguments,
                }
                result = self.hook_manager.apply_hooks(
                    result, function_name, tool_arguments, context
                )

            # Cache result if enabled
            if (
                cache_enabled
                and tool_instance
                and getattr(tool_instance, "supports_caching", lambda: True)()
            ):
                if cache_key is None:
                    cache_key = self._make_cache_key(
                        function_name, arguments, tool_instance
                    )
                if cache_namespace is None:
                    cache_namespace = tool_instance.get_cache_namespace()
                if cache_version is None:
                    cache_version = tool_instance.get_cache_version()
                ttl = tool_instance.get_cache_ttl(result)
                self.cache_manager.set(
                    namespace=cache_namespace,
                    version=cache_version,
                    cache_key=cache_key,
                    value=result,
                    ttl=ttl,
                )

            return result

    async def run_one_function_async(
        self, function_call_json, stream_callback=None, use_cache=False, validate=True
    ):
        """
        Async version of run_one_function.

        Execute a single function call asynchronously (non-blocking).
        Handles both sync and async tools intelligently.
        """
        function_name = function_call_json.get("name", "")
        arguments = function_call_json.get("arguments", {})

        # Resolve original names to shortened names
        function_name = self._resolve_tool_name(function_name)

        # Handle malformed queries gracefully
        if not function_name:
            return {"error": "Missing or empty function name"}

        if not isinstance(arguments, dict):
            return {
                "error": f"Arguments must be a dictionary, got {type(arguments).__name__}"
            }

        tool_instance = None
        cache_namespace = None
        cache_version = None
        cache_key = None

        cache_enabled = (
            use_cache and self.cache_manager is not None and self.cache_manager.enabled
        )

        if cache_enabled:
            tool_instance = self._get_tool_instance(function_name, cache=True)
            if (
                tool_instance
                and getattr(tool_instance, "supports_caching", lambda: True)()
            ):
                cache_namespace = tool_instance.get_cache_namespace()
                cache_version = tool_instance.get_cache_version()
                cache_key = self._make_cache_key(
                    function_name, arguments, tool_instance
                )
                cached_value = self.cache_manager.get(
                    namespace=cache_namespace,
                    version=cache_version,
                    cache_key=cache_key,
                )
                if cached_value is not None:
                    self.logger.debug(f"Cache hit for {function_name}")
                    return cached_value
            else:
                cache_enabled = False

        # Note: cache_guard (singleflight) is not async-compatible, skipping for now
        # In async context, multiple concurrent calls will execute independently

        # Coerce types if lenient coercion is enabled
        if self.lenient_type_coercion:
            arguments = self._coerce_arguments_to_schema(function_name, arguments)
            function_call_json["arguments"] = arguments

        # Validate parameters if requested
        if validate:
            validation_error = self._validate_parameters(function_name, arguments)
            if validation_error:
                return self._create_dual_format_error(validation_error)
        else:
            if function_name not in self.all_tool_dict:
                return self._create_dual_format_error(
                    ToolValidationError(
                        f"Tool '{function_name}' not found",
                        details={"tool_name": function_name},
                    )
                )

        # Execute the tool
        tool_arguments = arguments
        try:
            if tool_instance is None:
                tool_instance = self._get_tool_instance(function_name, cache=True)

            if tool_instance:
                result, tool_arguments = await self._execute_tool_with_stream_async(
                    tool_instance, arguments, stream_callback, use_cache, validate
                )
            else:
                # Try to auto-load tools if dictionary is empty
                if not self._auto_load_tools_if_empty(function_name):
                    error_msg = "Failed to auto-load tools"
                    return self._create_dual_format_error(
                        ToolUnavailableError(
                            error_msg,
                            next_steps=[
                                "Manually run tu.load_tools()",
                                "Check tool configuration",
                            ],
                        )
                    )

                # Try to get the tool instance again after loading
                tool_instance = self._get_tool_instance(function_name, cache=True)
                if tool_instance:
                    result, tool_arguments = await self._execute_tool_with_stream_async(
                        tool_instance,
                        arguments,
                        stream_callback,
                        use_cache,
                        validate,
                    )
                else:
                    error_msg = (
                        f"Tool '{function_name}' not found even after loading tools"
                    )
                    return self._create_dual_format_error(
                        ToolUnavailableError(
                            error_msg,
                            next_steps=[
                                "Check tool name spelling",
                                "Verify tool is available in loaded categories",
                            ],
                        )
                    )
        except Exception as e:
            # Classify and return structured error
            classified_error = self._classify_exception(e, function_name, arguments)
            return self._create_dual_format_error(classified_error)

        # Apply output hooks if enabled
        if self.hook_manager:
            context = {
                "tool_name": function_name,
                "tool_type": (
                    tool_instance.__class__.__name__
                    if tool_instance is not None
                    else "unknown"
                ),
                "execution_time": time.time(),
                "arguments": tool_arguments,
            }
            result = self.hook_manager.apply_hooks(
                result, function_name, tool_arguments, context
            )

        # Cache result if enabled
        if (
            cache_enabled
            and tool_instance
            and getattr(tool_instance, "supports_caching", lambda: True)()
        ):
            if cache_key is None:
                cache_key = self._make_cache_key(
                    function_name, arguments, tool_instance
                )
            if cache_namespace is None:
                cache_namespace = tool_instance.get_cache_namespace()
            if cache_version is None:
                cache_version = tool_instance.get_cache_version()
            ttl = tool_instance.get_cache_ttl(result)
            self.cache_manager.set(
                namespace=cache_namespace,
                version=cache_version,
                cache_key=cache_key,
                value=result,
                ttl=ttl,
            )

        return result

    def _execute_tool_with_stream(
        self, tool_instance, arguments, stream_callback, use_cache=False, validate=True
    ):
        """Invoke a tool, forwarding stream callbacks and other parameters when supported."""

        tool_arguments = arguments
        stream_flag_key = (
            getattr(tool_instance, "STREAM_FLAG_KEY", None) if stream_callback else None
        )

        if isinstance(arguments, dict):
            tool_arguments = dict(arguments)

            if (
                stream_callback
                and stream_flag_key
                and stream_flag_key not in tool_arguments
            ):
                tool_arguments[stream_flag_key] = True

        # Try to pass all available parameters to the tool
        try:
            signature = inspect.signature(tool_instance.run)
            params = signature.parameters

            # Build kwargs based on what the tool accepts
            kwargs = {}

            # Always include arguments as first positional argument
            if stream_callback is not None and "stream_callback" in params:
                kwargs["stream_callback"] = stream_callback
            if "use_cache" in params:
                kwargs["use_cache"] = use_cache
            if "validate" in params:
                kwargs["validate"] = validate

            # Call with all supported parameters
            result = tool_instance.run(tool_arguments, **kwargs)
            if inspect.iscoroutine(result):
                result = asyncio.run(result)
            return result, tool_arguments

        except (ValueError, TypeError) as e:
            # If inspection fails or tool doesn't accept extra params,
            # fall back to simple execution with just arguments
            self.logger.debug(f"Falling back to simple run() call: {e}")
            result = tool_instance.run(tool_arguments)
            if inspect.iscoroutine(result):
                result = asyncio.run(result)
            return result, tool_arguments

    async def _invoke_tool_async(self, tool_instance, tool_arguments, **kwargs):
        """Invoke tool.run, using await for async tools or a thread pool for sync tools."""
        tool_name = getattr(tool_instance, "name", "unknown")
        if inspect.iscoroutinefunction(tool_instance.run):
            self.logger.debug(f"Executing async tool: {tool_name}")
            return await tool_instance.run(tool_arguments, **kwargs)
        self.logger.debug(f"Executing sync tool in thread pool: {tool_name}")
        return await asyncio.to_thread(tool_instance.run, tool_arguments, **kwargs)

    async def _execute_tool_with_stream_async(
        self, tool_instance, arguments, stream_callback, use_cache=False, validate=True
    ):
        """
        Async version of _execute_tool_with_stream.

        Handles both sync and async tools: async tools are awaited directly,
        sync tools run in a thread pool.
        """
        tool_arguments = arguments
        stream_flag_key = (
            getattr(tool_instance, "STREAM_FLAG_KEY", None) if stream_callback else None
        )

        if isinstance(arguments, dict):
            tool_arguments = dict(arguments)
            if (
                stream_callback
                and stream_flag_key
                and stream_flag_key not in tool_arguments
            ):
                tool_arguments[stream_flag_key] = True

        try:
            signature = inspect.signature(tool_instance.run)
            params = signature.parameters

            kwargs = {}
            if stream_callback is not None and "stream_callback" in params:
                kwargs["stream_callback"] = stream_callback
            if "use_cache" in params:
                kwargs["use_cache"] = use_cache
            if "validate" in params:
                kwargs["validate"] = validate

            result = await self._invoke_tool_async(
                tool_instance, tool_arguments, **kwargs
            )
            return result, tool_arguments

        except (ValueError, TypeError) as e:
            self.logger.debug(f"Falling back to simple run() call: {e}")
            result = await self._invoke_tool_async(tool_instance, tool_arguments)
            return result, tool_arguments

    def toggle_hooks(self, enabled: bool):
        """
        Enable or disable output hooks globally.

        This method allows runtime control of the hook system. When enabled,
        it initializes the HookManager if not already present. When disabled,
        it deactivates the HookManager.

        Args:
            enabled (bool): True to enable hooks, False to disable
        """
        self.hooks_enabled = enabled
        if enabled and not self.hook_manager:
            self.hook_manager = HookManager({}, self)
            self.logger.info("Output hooks enabled")
        elif self.hook_manager:
            self.hook_manager.toggle_hooks(enabled)
            self.logger.info(f"Output hooks {'enabled' if enabled else 'disabled'}")
        else:
            self.logger.debug("Output hooks disabled")

    def init_tool(self, tool=None, tool_name=None, add_to_cache=True):
        """
        Initialize a tool instance from configuration or name.

        This method creates a new tool instance using the tool type mappings and
        optionally caches it for future use. It handles special cases like the
        OpentargetToolDrugNameMatch which requires additional dependencies.

        Args:
            tool (dict, optional): Tool configuration dictionary. Either this or tool_name must be provided.
            tool_name (str, optional): Name of the tool type to initialize. Either this or tool must be provided.
            add_to_cache (bool, optional): Whether to cache the initialized tool. Defaults to True.

        Returns:
            object: Initialized tool instance or None if initialization fails.

        Raises:
            KeyError: If the tool type is not found in tool_type_mappings.
        """
        global tool_type_mappings

        try:
            if tool_name is not None:
                # Use lazy loading to get the tool class
                tool_class = get_tool_class_lazy(tool_name)
                if tool_class is None:
                    raise KeyError(f"Tool type '{tool_name}' not found in registry")
                new_tool = tool_class()
            else:
                tool_type = tool["type"]
                tool_name = tool["name"]

                # Use lazy loading to get the tool class
                tool_class = get_tool_class_lazy(tool_type)
                if tool_class is None:
                    # Fallback to old method if lazy loading fails
                    if tool_type not in tool_type_mappings:
                        # Refresh registry and try again
                        tool_type_mappings = get_tool_registry()
                    if tool_type not in tool_type_mappings:
                        raise KeyError(f"Tool type '{tool_type}' not found in registry")
                    tool_class = tool_type_mappings[tool_type]

                if "OpentargetToolDrugNameMatch" == tool_type:
                    if (
                        "FDADrugLabelGetDrugGenericNameTool"
                        not in self.callable_functions
                    ):
                        drug_tool_class = get_tool_class_lazy(
                            "FDADrugLabelGetDrugGenericNameTool"
                        )
                        if drug_tool_class is None:
                            drug_tool_class = tool_type_mappings[
                                "FDADrugLabelGetDrugGenericNameTool"
                            ]
                        self.callable_functions[
                            "FDADrugLabelGetDrugGenericNameTool"
                        ] = drug_tool_class()
                    new_tool = tool_class(
                        tool_config=tool,
                        drug_generic_tool=self.callable_functions[
                            "FDADrugLabelGetDrugGenericNameTool"
                        ],
                    )
                elif tool_type in [
                    "ToolFinderEmbedding",
                    "ComposeTool",
                    "ToolFinderLLM",
                    "ToolFinderKeyword",
                    "SmolAgentTool",
                    "ListTools",
                    "GrepTools",
                    "GetToolInfo",
                    "ExecuteTool",
                ]:
                    # Tool discovery tools need tooluniverse parameter
                    new_tool = tool_class(tool_config=tool, tooluniverse=self)
                else:
                    new_tool = tool_class(tool_config=tool)

            if add_to_cache:
                self.callable_functions[tool_name] = new_tool
            return new_tool

        except Exception as e:
            tool_type = tool_name if tool_name else tool.get("type")
            mark_tool_unavailable(tool_type, e)
            self.logger.warning(f"Failed to initialize '{tool_type}': {e}")
            try:
                with open("/tmp/tu_init_error.txt", "a") as f:
                    f.write(f"Failed to initialize '{tool_type}': {e}\nTraceback:\n")
                    import traceback

                    traceback.print_exc(file=f)
            except Exception:
                pass

            # Hide tools that cannot be initialized (e.g., missing optional deps)
            try:
                # Remove from dictionaries so it doesn't appear in listings
                if tool_name and tool_name in self.all_tool_dict:
                    self.all_tool_dict.pop(tool_name, None)
                elif tool and tool.get("name") in self.all_tool_dict:
                    self.all_tool_dict.pop(tool.get("name"), None)

                # Also remove from category dicts if present
                try:
                    name_to_remove = tool_name or (tool.get("name") if tool else None)
                    if name_to_remove and hasattr(self, "tool_category_dicts"):
                        for _cat, _tools in list(self.tool_category_dicts.items()):
                            self.tool_category_dicts[_cat] = [
                                t for t in _tools if t.get("name") != name_to_remove
                            ]
                except Exception:
                    pass
            except Exception:
                # Best-effort cleanup only
                pass
            return None  # Return None instead of raising

    def _get_tool_instance(self, function_name: str, cache: bool = True):
        """Get or create tool instance with optional caching."""
        # Resolve original names to shortened names (all_tool_dict uses shortened as keys)
        function_name = self._resolve_tool_name(function_name)

        # Check cache first
        if function_name in self.callable_functions:
            return self.callable_functions[function_name]

        # Check if known unavailable
        tool_errors = get_tool_errors()
        if function_name in tool_errors:
            self.logger.debug(f"Tool {function_name} is unavailable")
            return None

        # Try to initialize
        if function_name in self.all_tool_dict:
            return self.init_tool(self.all_tool_dict[function_name], add_to_cache=cache)

        return None

    def _auto_load_tools_if_empty(self, function_name: str = None) -> bool:
        """
        Automatically load tools if the tools dictionary is empty.

        Args:
            function_name: Optional tool name to check after loading

        Returns:
            bool: True if tools were loaded successfully, False otherwise
        """
        if not self.all_tool_dict:
            print(
                "⚠️  Warning: No tools loaded. Automatically running tu.load_tools()..."
            )
            try:
                self.load_tools()
                print("✅ Tools loaded successfully.")
                return True
            except Exception as load_error:
                print(f"❌ Failed to auto-load tools: {load_error}")
                return False
        return True

    def _make_cache_key(
        self, function_name: str, arguments: dict, tool_instance=None
    ) -> str:
        """Generate cache key by delegating to BaseTool.

        Args:
            function_name: Name of the tool/function
            arguments: Arguments passed to the tool
            tool_instance: Optional pre-fetched tool instance to avoid recreation

        Returns:
            Cache key string
        """
        if tool_instance is None:
            tool_instance = self._get_tool_instance(function_name, cache=True)

        if tool_instance:
            return tool_instance.get_cache_key(arguments)

        # Fallback: simple hash-based key
        serialized = json.dumps(
            {"name": function_name, "args": arguments}, sort_keys=True
        )
        return hashlib.md5(serialized.encode()).hexdigest()

    def _coerce_value_to_type(self, value: Any, schema: dict) -> Any:
        """
        Coerce a value to match the schema's expected type.

        This function attempts to convert string values to integers, floats,
        or booleans when the schema expects those types. This makes the
        system more lenient with user input from LLMs that provide numeric
        values as strings.

        Args:
            value: The value to coerce
            schema: The JSON schema definition for this value

        Returns:
            The coerced value (or original if coercion fails or not applicable)
        """
        # Only coerce string values
        if not isinstance(value, str):
            return value

        # Handle anyOf/oneOf schemas by recursively trying each option
        if "anyOf" in schema:
            for option in schema["anyOf"]:
                coerced = self._coerce_value_to_type(value, option)
                if coerced is not value:  # Coercion succeeded
                    return coerced
            return value

        if "oneOf" in schema:
            for option in schema["oneOf"]:
                coerced = self._coerce_value_to_type(value, option)
                if coerced is not value:  # Coercion succeeded
                    return coerced
            return value

        # Handle array types
        if schema.get("type") == "array" and "items" in schema:
            if isinstance(value, list):
                # Recursively coerce array items
                items_schema = schema["items"]
                return [
                    self._coerce_value_to_type(item, items_schema) for item in value
                ]
            return value

        # Get the expected type
        expected_type = schema.get("type")

        # Don't coerce if schema expects string type
        if expected_type == "string":
            return value

        # Try to coerce based on expected type
        if expected_type == "integer":
            try:
                # Only parse as int if it represents an integer (not a float)
                if "." not in value:
                    return int(value)
            except (ValueError, TypeError):
                # If coercion fails, return the original value as per function design
                pass
        elif expected_type == "number":
            try:
                return float(value)
            except (ValueError, TypeError):
                pass
        elif expected_type == "boolean":
            # Handle common boolean string representations
            lower_value = value.lower().strip()
            if lower_value in ("true", "1", "yes", "on"):
                return True
            elif lower_value in ("false", "0", "no", "off"):
                return False

        return value

    def _coerce_arguments_to_schema(self, function_name: str, arguments: dict) -> dict:
        """
        Coerce all arguments for a tool to match their schema expectations.

        Args:
            function_name: Name of the tool
            arguments: Dictionary of arguments to coerce

        Returns:
            New dictionary with coerced arguments
        """
        if function_name not in self.all_tool_dict:
            return arguments

        tool_config = self.all_tool_dict[function_name]
        parameter_schema = tool_config.get("parameter", {})
        properties = parameter_schema.get("properties", {})

        if not properties:
            return arguments

        coerced_args = {}
        for param_name, param_value in arguments.items():
            if param_name in properties:
                param_schema = properties[param_name]
                coerced_value = self._coerce_value_to_type(param_value, param_schema)

                # Log when coercion occurs
                if coerced_value != param_value:
                    self.logger.debug(
                        f"Coerced parameter '{param_name}' from "
                        f"{param_value!r} ({type(param_value).__name__}) "
                        f"to {coerced_value!r} ({type(coerced_value).__name__})"
                    )

                coerced_args[param_name] = coerced_value
            else:
                coerced_args[param_name] = param_value

        return coerced_args

    def _validate_parameters(
        self, function_name: str, arguments: dict
    ) -> Optional[ToolError]:
        """Validate parameters by delegating to BaseTool."""
        if function_name not in self.all_tool_dict:
            # Try to auto-load tools if dictionary is empty
            if not self._auto_load_tools_if_empty(function_name):
                return ToolUnavailableError("Failed to auto-load tools")

            # Check again after loading
            if function_name not in self.all_tool_dict:
                return ToolUnavailableError(
                    f"Tool '{function_name}' not found even after loading tools"
                )

        tool_instance = self._get_tool_instance(function_name, cache=True)
        if not tool_instance:
            # Check if we have a recorded error for this tool
            tool_errors = get_tool_errors()
            if function_name in tool_errors:
                error_info = tool_errors[function_name]
                return ToolConfigError(
                    f"Failed to initialize tool for validation: {error_info['error']}"
                )
            return ToolConfigError("Failed to initialize tool for validation")

        # Check if tool has validate_parameters method (for backward compatibility)
        if hasattr(tool_instance, "validate_parameters"):
            return tool_instance.validate_parameters(arguments)
        else:
            # Fallback for old-style tools without validate_parameters
            # Just return None (no validation) to maintain backward compatibility
            return None

    def _check_basic_type(self, value: Any, expected_type: str) -> bool:
        """Check if value matches expected basic type."""
        type_mapping = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "object": dict,
            "array": list,
        }

        if expected_type not in type_mapping:
            return True  # Unknown type, skip validation

        expected_python_type = type_mapping[expected_type]
        return isinstance(value, expected_python_type)

    def _classify_exception(
        self, exception: Exception, function_name: str, arguments: dict
    ) -> ToolError:
        """Classify exception by delegating to BaseTool."""
        tool_instance = self._get_tool_instance(function_name, cache=True)

        if tool_instance:
            return tool_instance.handle_error(exception)

        # Fallback for tool instance creation failure
        return ToolServerError(f"Unexpected error calling {function_name}: {exception}")

    def _create_dual_format_error(self, error: ToolError) -> dict:
        """Create dual-format error response for backward compatibility."""
        return {
            "status": "error",  # Consistent status field
            "error": str(error),  # Backward compatible string
            "error_details": error.to_dict(),  # New structured format
        }

    def refresh_tools(self):
        """Refresh tool discovery (re-discover MCP/remote tools, reload configs)."""
        # TODO: Implement MCP tool re-discovery
        # For now, just reload tool configurations
        self.logger.info("Refreshing tool configurations...")
        # This could be extended to re-discover MCP tools, reload configs, etc.
        self.logger.info("Tool refresh completed")

    def eager_load_tools(self, names: Optional[List[str]] = None):
        """Pre-instantiate tools to reduce first-call latency."""
        tool_names = names or list(self.all_tool_dict.keys())
        self.logger.info(f"Eager loading {len(tool_names)} tools...")

        for tool_name in tool_names:
            if (
                tool_name in self.all_tool_dict
                and tool_name not in self.callable_functions
            ):
                try:
                    self.init_tool(self.all_tool_dict[tool_name], add_to_cache=True)
                    self.logger.debug(f"Eager loaded: {tool_name}")
                except Exception as e:
                    self.logger.warning(f"Failed to eager load {tool_name}: {e}")

        self.logger.info(
            f"Eager loading completed. {len(self.callable_functions)} tools cached."
        )

    @property
    def _cache(self):
        """Access to the internal cache for testing purposes."""
        if self.cache_manager:
            return self.cache_manager.memory
        return {}

    def clear_cache(self):
        """Clear the result cache."""
        if self.cache_manager:
            self.cache_manager.clear()
        self.logger.info("Result cache cleared")

    def clear_tools(self, clear_cache=False):
        """
        Clear all loaded tools from the registry.

        This method resets the tool registry to its initial empty state, allowing you to:
        - Free memory after loading many tools
        - Reset state between different workflows
        - Load a fresh set of tools for a new context
        - Control which tools are visible to tool finder

        Args:
            clear_cache (bool, optional): Whether to also clear the result cache.
                                         Defaults to False.

        Examples:
            # Clear tools but keep cached results
            tu.clear_tools()

            # Clear both tools and cached results
            tu.clear_tools(clear_cache=True)

            # Load specific tools after clearing
            tu.clear_tools()
            tu.load_tools(include_tools=["UniProt_get_entry_by_accession"])

        Note:
            - This does not affect tool instances in callable_functions cache
            - Subsequent tool access will trigger on-demand loading
            - Use clear_cache=True if you also want to clear result cache
        """
        # Clear tool registry
        self.all_tools = []
        self.all_tool_dict = {}
        self.tool_category_dicts = {}

        # Clear instantiated tool instances
        self.callable_functions = {}

        self.logger.info("Tool registry cleared")

        # Optionally clear result cache
        if clear_cache:
            self.clear_cache()

    def get_cache_stats(self) -> Dict[str, Any]:
        """Return cache statistics."""
        if not self.cache_manager:
            return {"enabled": False}
        return self.cache_manager.stats()

    def dump_cache(self, namespace: Optional[str] = None):
        """Iterate over cached entries (persistent layer only)."""
        if not self.cache_manager:
            return iter([])
        return self.cache_manager.dump(namespace=namespace)

    def close(self):
        """Release resources."""
        if self.cache_manager:
            self.cache_manager.close()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    def get_tool_health(self, tool_name: str = None) -> dict:
        """Get health status for tool(s)."""
        tool_errors = get_tool_errors()

        if tool_name:
            if tool_name in tool_errors:
                return tool_errors[tool_name]
            elif tool_name in self.all_tool_dict:
                return {"available": True}
            return {"available": False, "error": "Not found"}

        # Summary for all tools
        return {
            "total": len(self.all_tool_dict),
            "available": len(self.all_tool_dict) - len(tool_errors),
            "unavailable": len(tool_errors),
            "unavailable_list": list(tool_errors.keys()),
            "details": tool_errors,
        }

    def check_function_call(self, fcall_str, function_config=None, format="llama"):
        """
        Validate a function call against tool configuration.

        This method checks if a function call is valid by verifying the function name
        exists and the arguments match the expected parameters.

        Args:
            fcall_str: Function call string or data to validate.
            function_config (dict, optional): Specific function configuration to validate against.
                                            If None, uses the loaded tool configuration.
            format (str, optional): Format type for parsing. Defaults to 'llama'.

        Returns:
            tuple: A tuple of (is_valid, message) where:
                - is_valid (bool): True if the function call is valid, False otherwise
                - message (str): Error message if invalid, empty if valid
        """
        function_call_json = self.extract_function_call_json(fcall_str, format=format)
        if function_call_json is not None:
            if function_config is not None:
                return evaluate_function_call(function_config, function_call_json)
            function_name = function_call_json["name"]
            if function_name not in self.all_tool_dict:
                return (
                    False,
                    f"Function name {function_name} not found in loaded tools.",
                )
            return evaluate_function_call(
                self.all_tool_dict[function_name], function_call_json
            )
        else:
            return False, "Invalid JSON string of function call"

    def export_tool_names(self, output_file, category_filter=None):
        """
        Export tool names to a text file (one per line).

        Args:
            output_file (str): Path to the output file
            category_filter (list, optional): List of categories to filter by
        """
        try:
            tools_to_export = []

            if category_filter:
                # Filter by categories
                for category in category_filter:
                    if category in self.tool_category_dicts:
                        tools_to_export.extend(
                            [
                                tool["name"]
                                for tool in self.tool_category_dicts[category]
                            ]
                        )
            else:
                # Export all tools
                tools_to_export = [tool["name"] for tool in self.all_tools]

            # Remove duplicates and sort
            tools_to_export = sorted(set(tools_to_export))

            with open(output_file, "w", encoding="utf-8") as f:
                f.write("# ToolUniverse Tool Names\n")
                f.write(f"# Generated automatically - {len(tools_to_export)} tools\n")
                if category_filter:
                    f.write(f"# Categories: {', '.join(category_filter)}\n")
                f.write("\n")

                for tool_name in tools_to_export:
                    f.write(f"{tool_name}\n")

            self.logger.info(
                f"Exported {len(tools_to_export)} tool names to {output_file}"
            )
            return tools_to_export

        except Exception as e:
            self.logger.error(f"Error exporting tool names to {output_file}: {e}")
            return []

    def filter_tools(
        self,
        include_tools=None,
        exclude_tools=None,
        include_tool_types=None,
        exclude_tool_types=None,
    ):
        """
        Filter tools based on inclusion/exclusion criteria.

        Args:
            include_tools (set, optional): Set of tool names to include
            exclude_tools (set, optional): Set of tool names to exclude
            include_tool_types (set, optional): Set of tool types to include
            exclude_tool_types (set, optional): Set of tool types to exclude

        Returns:
            list: Filtered list of tool configurations
        """
        if not hasattr(self, "all_tools") or not self.all_tools:
            self.logger.warning("No tools loaded. Call load_tools() first.")
            return []

        filtered_tools = []
        for tool in self.all_tools:
            tool_name = tool.get("name", "")
            tool_type = tool.get("type", "")

            # Check inclusion/exclusion criteria
            if include_tools and tool_name not in include_tools:
                continue
            if exclude_tools and tool_name in exclude_tools:
                continue
            if include_tool_types and tool_type not in include_tool_types:
                continue
            if exclude_tool_types and tool_type in exclude_tool_types:
                continue

            filtered_tools.append(tool)

        return filtered_tools

    def get_required_parameters(self, tool_name):
        """
        Get required parameters for a specific tool.

        Args:
            tool_name (str): Name of the tool

        Returns:
            list: List of required parameter names
        """
        if tool_name not in self.all_tool_dict:
            self.logger.warning(f"Tool '{tool_name}' not found")
            return []

        tool_config = self.all_tool_dict[tool_name]
        parameter_schema = tool_config.get("parameter", {})
        return parameter_schema.get("required", [])

    def get_available_tools(self, category_filter=None, name_only=True):
        """
        Get available tools, optionally filtered by category.

        Args:
            category_filter (list, optional): List of categories to filter by
            name_only (bool): If True, return only tool names; if False, return full configs

        Returns:
            list: List of tool names or tool configurations
        """
        if not hasattr(self, "all_tools") or not self.all_tools:
            self.logger.warning("No tools loaded. Call load_tools() first.")
            return []

        if category_filter:
            filtered_tools = []
            for tool in self.all_tools:
                tool_type = tool.get("type", "")
                if tool_type in category_filter:
                    filtered_tools.append(tool)
        else:
            filtered_tools = self.all_tools

        if name_only:
            return [tool["name"] for tool in filtered_tools]
        else:
            return filtered_tools

    def find_tools_by_pattern(self, pattern, search_in="name", case_sensitive=False):
        """
        Find tools matching a pattern in their name or description.

        Args:
            pattern (str): Pattern to search for
            search_in (str): Where to search - 'name', 'description', or 'both'
            case_sensitive (bool): Whether search should be case sensitive

        Returns:
            list: List of matching tool configurations
        """
        if not hasattr(self, "all_tools") or not self.all_tools:
            self.logger.warning("No tools loaded. Call load_tools() first.")
            return []

        # Handle None or empty pattern
        if pattern is None or pattern == "":
            return self.all_tools

        import re

        flags = 0 if case_sensitive else re.IGNORECASE

        matching_tools = []
        for tool in self.all_tools:
            found = False

            if search_in in ["name", "both"]:
                tool_name = tool.get("name", "")
                if re.search(pattern, tool_name, flags):
                    found = True

            if search_in in ["description", "both"] and not found:
                tool_desc = tool.get("description", "")
                if re.search(pattern, tool_desc, flags):
                    found = True

            if found:
                matching_tools.append(tool)

        self.logger.info(
            f"Found {len(matching_tools)} tools matching pattern '{pattern}'"
        )
        return matching_tools

    # ============ DEPRECATED METHODS (Kept for backward compatibility) ============
    # These methods are deprecated and will be removed in v2.0. Use the recommended
    # alternatives instead. All methods below maintain backward compatibility but
    # issue deprecation warnings when called.

    def get_tool_by_name(self, tool_names, format="default"):
        """
        Retrieve tool configurations by their names.

        DEPRECATED: Use tool_specification() instead.

        Args:
            tool_names (list): List of tool names to retrieve.
            format (str, optional): Output format. Options: 'default', 'openai'.
                                   If 'openai', returns OpenAI function calling format. Defaults to 'default'.

        Returns:
            list: List of tool configurations for the specified names.
                 Tools not found will be reported but not included in the result.
        """
        warnings.warn(
            "get_tool_by_name() is deprecated and will be removed in v2.0. "
            "Use tool_specification() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.get_tool_specification_by_names(tool_names, format=format)

    def get_tool_description(self, tool_name):
        """
        Get the description of a tool by its name.

        DEPRECATED: Use tool_specification() instead.

        Args:
            tool_name (str): Name of the tool.

        Returns:
            dict or None: Tool configuration if found, None otherwise.
        """
        warnings.warn(
            "get_tool_description() is deprecated and will be removed in v2.0. "
            "Use tool_specification() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.get_one_tool_by_one_name(tool_name)

    def remove_keys(self, tool_list, invalid_keys):
        """
        Remove specified keys from a list of tool configurations.

        DEPRECATED: Use prepare_tool_prompts(mode='custom', valid_keys=...) instead.

        Args:
            tool_list (list): List of tool configuration dictionaries.
            invalid_keys (list): List of keys to remove from each tool configuration.

        Returns:
            list: Deep copy of tool list with specified keys removed.
        """
        warnings.warn(
            "remove_keys() is deprecated and will be removed in v2.0. "
            "Use prepare_tool_prompts(mode='custom', valid_keys=...) instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        copied_list = copy.deepcopy(tool_list)
        for tool in copied_list:
            # Create a list of keys to avoid modifying the dictionary during iteration
            for key in list(tool.keys()):
                if key in invalid_keys:
                    del tool[key]
        return copied_list

    def prepare_tool_examples(self, tool_list):
        """
        Prepare tool configurations for example usage by keeping extended set of keys.

        DEPRECATED: Use prepare_tool_prompts(mode='example') instead.

        Args:
            tool_list (list): List of tool configuration dictionaries.

        Returns:
            list: Deep copy of tool list with only example-relevant keys.
        """
        warnings.warn(
            "prepare_tool_examples() is deprecated and will be removed in v2.0. "
            "Use prepare_tool_prompts(mode='example') instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.prepare_tool_prompts(tool_list, mode="example")

    def select_tools(
        self,
        include_names=None,
        exclude_names=None,
        include_categories=None,
        exclude_categories=None,
    ):
        """
        Select tools based on tool names and/or categories (tool_files keys).

        DEPRECATED: Use filter_tools() instead.

        Args:
            include_names (list, optional): List of tool names to include. If None, include all.
            exclude_names (list, optional): List of tool names to exclude.
            include_categories (list, optional): List of categories (tool_files keys) to include.
                                               If None, include all.
            exclude_categories (list, optional): List of categories (tool_files keys) to exclude.

        Returns:
            list: List of selected tool configurations.
        """
        warnings.warn(
            "select_tools() is deprecated and will be removed in v2.0. "
            "Use filter_tools() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        selected_tools = []

        # If no category filters are specified, use all_tools directly
        # This ensures we include auto-discovered tools that might not be in tool_category_dicts
        if include_categories is None and exclude_categories is None:
            selected_tools = list(self.all_tools)
        else:
            # If categories are specified, use self.tool_category_dicts to filter
            categories = set(self.tool_category_dicts.keys())
            if include_categories is not None:
                categories &= set(include_categories)
            if exclude_categories is not None:
                categories -= set(exclude_categories)
            # Gather tools from selected categories
            for cat in categories:
                selected_tools.extend(self.tool_category_dicts[cat])
        # Further filter by names if needed
        if include_names is not None:
            selected_tools = [
                tool for tool in selected_tools if tool["name"] in include_names
            ]
        if exclude_names is not None:
            selected_tools = [
                tool for tool in selected_tools if tool["name"] not in exclude_names
            ]
        return selected_tools

    def filter_tool_lists(
        self,
        tool_name_list,
        tool_desc_list,
        include_names=None,
        exclude_names=None,
        include_categories=None,
        exclude_categories=None,
    ):
        """
        Directly filter tool name and description lists based on names and/or categories.

        DEPRECATED: Use filter_tools() and manual list filtering instead.

        Args:
            tool_name_list (list): List of tool names to filter.
            tool_desc_list (list): List of tool descriptions to filter (must correspond to tool_name_list).
            include_names (list, optional): List of tool names to include.
            exclude_names (list, optional): List of tool names to exclude.
            include_categories (list, optional): List of categories to include.
            exclude_categories (list, optional): List of categories to exclude.

        Returns:
            tuple: A tuple containing (filtered_tool_name_list, filtered_tool_desc_list).
        """
        warnings.warn(
            "filter_tool_lists() is deprecated and will be removed in v2.0. "
            "Use filter_tools() and manual list filtering instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        # Build a set of allowed tool names using select_tools for category filtering
        allowed_names = set()
        if any([include_names, exclude_names, include_categories, exclude_categories]):
            filtered_tools = self.select_tools(
                include_names=include_names,
                exclude_names=exclude_names,
                include_categories=include_categories,
                exclude_categories=exclude_categories,
            )
            allowed_names = set(tool["name"] for tool in filtered_tools)
        else:
            allowed_names = set(tool_name_list)

        # Filter lists by allowed_names
        filtered_tool_name_list = []
        filtered_tool_desc_list = []
        for name, desc in zip(tool_name_list, tool_desc_list):
            if name in allowed_names:
                filtered_tool_name_list.append(name)
                filtered_tool_desc_list.append(desc)
        return filtered_tool_name_list, filtered_tool_desc_list

    def load_tools_from_names_list(self, tool_names, clear_existing=True):
        """
        Load only specific tools by their names.

        DEPRECATED: Use load_tools(include_tools=...) instead.

        Args:
            tool_names (list): List of tool names to load
            clear_existing (bool): Whether to clear existing tools first

        Returns:
            int: Number of tools successfully loaded
        """
        warnings.warn(
            "load_tools_from_names_list() is deprecated and will be removed in v2.0. "
            "Use load_tools(include_tools=...) instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        if clear_existing:
            self.all_tools = []
            self.all_tool_dict = {}
            self.tool_category_dicts = {}

        # Use the enhanced load_tools method
        original_count = len(self.all_tools)
        self.load_tools(include_tools=tool_names)
        return len(self.all_tools) - original_count

    def load_space(self, uri: str, **kwargs) -> Dict[str, Any]:
        """
        Load Space configuration and apply it to the ToolUniverse instance.

        This is a high-level method that loads a Space configuration from various
        sources (HuggingFace, local files, HTTP URLs) and applies the tool settings
        to the current instance.

        Args:
            uri: Space URI (e.g., "hf:user/repo", "./config.yaml", "https://example.com/config.yaml")
            **kwargs: Additional parameters to override Space configuration
                     (e.g., exclude_tools=["tool1"], include_tools=["tool2"])

        Returns:
            dict: The loaded Space configuration

        Examples:
            # Load from HuggingFace
            config = tu.load_space("hf:community/proteomics-toolkit")

            # Load local file with overrides
            config = tu.load_space("./my-config.yaml", exclude_tools=["slow_tool"])

            # Load from HTTP URL
            config = tu.load_space("https://example.com/config.yaml")
        """
        # Lazy import to avoid circular import issues
        from .space import SpaceLoader

        # Load Space configuration
        loader = SpaceLoader()
        config = loader.load(uri)

        # Extract tool configuration
        tools_config = config.get("tools", {})

        # Handle tools_file parameter
        tools_file_param = kwargs.get("tools_file")

        # Merge with override parameters
        tool_type = kwargs.get("tool_type") or tools_config.get("categories")
        exclude_tools = kwargs.get("exclude_tools") or tools_config.get(
            "exclude_tools", []
        )
        exclude_categories = kwargs.get("exclude_categories") or tools_config.get(
            "exclude_categories", []
        )
        include_tools = kwargs.get("include_tools") or tools_config.get(
            "include_tools", []
        )
        include_tool_types = kwargs.get("include_tool_types") or tools_config.get(
            "include_tool_types", []
        )
        exclude_tool_types = kwargs.get("exclude_tool_types") or tools_config.get(
            "exclude_tool_types", []
        )

        # Load tools with merged configuration
        self.load_tools(
            tool_type=tool_type,
            exclude_tools=exclude_tools,
            exclude_categories=exclude_categories,
            include_tools=include_tools,
            tools_file=tools_file_param,  # KEY FIX: Pass tools_file
            include_tool_types=include_tool_types,
            exclude_tool_types=exclude_tool_types,
        )

        # Store the configuration for reference
        self._current_space_config = config

        # Apply additional configurations (LLM, hooks, etc.)
        try:
            # Apply LLM configuration if present
            llm_config = config.get("llm_config")
            if llm_config:
                self._apply_llm_config(llm_config)

            # Apply hooks configuration if present
            hooks_config = config.get("hooks")
            if hooks_config:
                self._apply_hooks_config(hooks_config)

            # Store metadata
            self._store_space_metadata(config)

        except Exception as e:
            # Use print since logging might not be available
            print(f"⚠️  Failed to apply Space configurations: {e}")

        return config

    def _apply_llm_config(self, llm_config: Dict[str, Any]):
        """
        Apply LLM configuration from Space.

        Args:
            llm_config: LLM configuration dictionary
        """
        try:
            import os

            # Store LLM configuration
            self._space_llm_config = llm_config

            # Set environment variables for LLM configuration
            # Set configuration mode
            mode = llm_config.get("mode", "default")
            os.environ["TOOLUNIVERSE_LLM_CONFIG_MODE"] = mode

            # Set default provider
            if "default_provider" in llm_config:
                os.environ["TOOLUNIVERSE_LLM_DEFAULT_PROVIDER"] = llm_config[
                    "default_provider"
                ]

            # Set model mappings
            models = llm_config.get("models", {})
            for task, model in models.items():
                env_var = f"TOOLUNIVERSE_LLM_MODEL_{task.upper()}"
                os.environ[env_var] = model

            # Set temperature
            temperature = llm_config.get("temperature")
            if temperature is not None:
                os.environ["TOOLUNIVERSE_LLM_TEMPERATURE"] = str(temperature)

            # Note: max_tokens is handled by LLM client automatically, not needed here

            print(
                f"🤖 LLM configuration applied: {llm_config.get('default_provider', 'unknown')}"
            )

        except Exception as e:
            print(f"⚠️  Failed to apply LLM configuration: {e}")

    def _apply_hooks_config(self, hooks_config: List[Dict[str, Any]]):
        """
        Apply hooks configuration from Space.

        Args:
            hooks_config: Hooks configuration list
        """
        try:
            # Convert Space hooks format to ToolUniverse hook_config format
            hook_config = {
                "hooks": hooks_config,
                "global_settings": {
                    "default_timeout": 30,
                    "max_hook_depth": 3,
                    "enable_hook_caching": True,
                    "hook_execution_order": "priority_desc",
                },
            }

            # Enable hooks if not already enabled
            if not self.hooks_enabled:
                self.toggle_hooks(True)

            # Update hook manager configuration
            if self.hook_manager:
                self.hook_manager.config = hook_config
                self.hook_manager._load_hooks()
                print(f"🔗 Hooks configuration applied: {len(hooks_config)} hooks")
            else:
                print("⚠️  Hook manager not available")

        except Exception as e:
            print(f"⚠️  Failed to apply hooks configuration: {e}")

    def _store_space_metadata(self, config: Dict[str, Any]):
        """
        Store Space metadata for reference.

        Args:
            config: Space configuration dictionary
        """
        try:
            # Store metadata
            self._space_metadata = {
                "name": config.get("name"),
                "version": config.get("version"),
                "description": config.get("description"),
                "tags": config.get("tags", []),
                "required_env": config.get("required_env", []),
            }

            # Check for missing environment variables
            if config.get("required_env"):
                import os

                missing_env = [
                    env for env in config["required_env"] if not os.getenv(env)
                ]
                if missing_env:
                    print(f"⚠️  Missing environment variables: {', '.join(missing_env)}")

        except Exception as e:
            print(f"⚠️  Failed to store Space metadata: {e}")

    def get_space_llm_config(self) -> Optional[Dict[str, Any]]:
        """
        Get the current Space LLM configuration.

        Returns:
            LLM configuration dictionary or None if not set
        """
        return getattr(self, "_space_llm_config", None)

    def get_space_metadata(self) -> Optional[Dict[str, Any]]:
        """
        Get the current Space metadata.

        Returns:
            Space metadata dictionary or None if not set
        """
        return getattr(self, "_space_metadata", None)
