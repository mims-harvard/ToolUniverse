"""
Output Hook System for ToolUniverse

This module provides a comprehensive hook-based output processing system that allows
for intelligent post-processing of tool outputs. The system supports various types
of hooks including summarization, filtering, and transformation hooks.

Key Components:
- HookRule: Defines conditions for when hooks should trigger
- OutputHook: Base class for all output hooks
- SummarizationHook: Specialized hook for output summarization
- HookManager: Manages and coordinates all hooks

The hook system integrates seamlessly with ToolUniverse's existing architecture,
leveraging AgenticTool and ComposeTool for intelligent output processing.
"""

import json
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from pathlib import Path
from tooluniverse.logging_config import get_logger

_logger = get_logger(__name__)


class HookRule:
    """
    Defines rules for when hooks should be triggered.

    This class evaluates various conditions to determine if a hook should
    be applied to a tool's output. Supports multiple condition types including
    output length, content type, and tool-specific criteria.

    Args:
        conditions (Dict[str, Any]): Dictionary containing condition specifications

    Attributes:
        conditions (Dict[str, Any]): The condition specifications
    """

    def __init__(self, conditions: Dict[str, Any]):
        """
        Initialize the hook rule with conditions.

        Args:
            conditions (Dict[str, Any]): Condition specifications including
                output_length, content_type, tool_type, etc.
        """
        self.conditions = conditions

    def evaluate(
        self,
        result: Any,
        tool_name: str,
        arguments: Dict[str, Any],
        context: Dict[str, Any],
    ) -> bool:
        """
        Evaluate whether the rule conditions are met.

        Args:
            result (Any): The tool output to evaluate
            tool_name (str): Name of the tool that produced the output
            arguments (Dict[str, Any]): Arguments passed to the tool
            context (Dict[str, Any]): Additional context information

        Returns
            bool: True if conditions are met, False otherwise
        """
        # Evaluate output length conditions
        if "output_length" in self.conditions:
            result_str = str(result)
            length_condition = self.conditions["output_length"]
            threshold = length_condition.get("threshold", 5000)
            operator = length_condition.get("operator", ">")

            if operator == ">":
                return len(result_str) > threshold
            elif operator == ">=":
                return len(result_str) >= threshold
            elif operator == "<":
                return len(result_str) < threshold
            elif operator == "<=":
                return len(result_str) <= threshold

        # Evaluate content type conditions
        if "content_type" in self.conditions:
            content_type = self.conditions["content_type"]
            if content_type == "json" and isinstance(result, dict):
                return True
            elif content_type == "text" and isinstance(result, str):
                return True

        # Evaluate tool type conditions
        if "tool_type" in self.conditions:
            tool_type = context.get("tool_type", "")
            return tool_type == self.conditions["tool_type"]

        # Evaluate tool name conditions
        if "tool_name" in self.conditions:
            return tool_name == self.conditions["tool_name"]

        # If no specific conditions are met, return True for general rules
        return True


class OutputHook:
    """
    Base class for all output hooks.

    This abstract base class defines the interface that all output hooks must implement.
    Hooks are used to process tool outputs after execution, enabling features like
    summarization, filtering, transformation, and validation.

    Args:
        config (Dict[str, Any]): Hook configuration including name, enabled status,
            priority, and conditions

    Attributes:
        config (Dict[str, Any]): Hook configuration
        name (str): Name of the hook
        enabled (bool): Whether the hook is enabled
        priority (int): Hook priority (lower numbers execute first)
        rule (HookRule): Rule for when this hook should trigger
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the output hook with configuration.

        Args:
            config (Dict[str, Any]): Hook configuration containing:
                - name: Hook identifier
                - enabled: Whether hook is active
                - priority: Execution priority
                - conditions: Trigger conditions
        """
        self.config = config
        self.name = config.get("name", "unnamed_hook")
        self.enabled = config.get("enabled", True)
        self.priority = config.get("priority", 1)
        self.rule = HookRule(config.get("conditions", {}))

    def should_trigger(
        self,
        result: Any,
        tool_name: str,
        arguments: Dict[str, Any],
        context: Dict[str, Any],
    ) -> bool:
        """
        Determine if this hook should be triggered for the given output.

        Args:
            result (Any): The tool output to evaluate
            tool_name (str): Name of the tool that produced the output
            arguments (Dict[str, Any]): Arguments passed to the tool
            context (Dict[str, Any]): Additional context information

        Returns
            bool: True if hook should trigger, False otherwise
        """
        if not self.enabled:
            return False
        return self.rule.evaluate(result, tool_name, arguments, context)

    def process(
        self,
        result: Any,
        tool_name: str | None = None,
        arguments: Dict[str, Any] | None = None,
        context: Dict[str, Any] | None = None,
    ) -> Any:
        """
        Process the tool output.

        This method must be implemented by subclasses to define the specific
        processing logic for the hook.

        Args:
            result (Any): The tool output to process
            tool_name (str): Name of the tool that produced the output
            arguments (Dict[str, Any]): Arguments passed to the tool
            context (Dict[str, Any]): Additional context information

        Returns
            Any: The processed output

        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError("Subclasses must implement process method")


@dataclass
class SummarizationHookConfig:
    composer_tool: str = "OutputSummarizationComposer"
    chunk_size: int = (
        30000  # Increased to 30000 to minimize chunk count and improve success rate
    )
    focus_areas: str = "key_findings_and_results"
    max_summary_length: int = 3000
    composer_timeout_sec: int = 300

    def validate(self) -> "SummarizationHookConfig":
        # Validate numeric fields; clamp to sensible defaults if invalid
        if not isinstance(self.chunk_size, int) or self.chunk_size <= 0:
            self.chunk_size = 30000
        if not isinstance(self.max_summary_length, int) or self.max_summary_length <= 0:
            self.max_summary_length = 3000
        if (
            not isinstance(self.composer_timeout_sec, int)
            or self.composer_timeout_sec <= 0
        ):
            self.composer_timeout_sec = 300
        if not isinstance(self.composer_tool, str) or not self.composer_tool:
            self.composer_tool = "OutputSummarizationComposer"
        return self


class SummarizationHook(OutputHook):
    """
    Hook for intelligent output summarization using AI.

    This hook uses the ToolUniverse's AgenticTool and ComposeTool infrastructure
    to provide intelligent summarization of long tool outputs. It supports
    chunking large outputs, processing each chunk with AI, and merging results.

    Args:
        config (Dict[str, Any]): Hook configuration including summarization parameters
        tooluniverse: Reference to the ToolUniverse instance

    Attributes:
        tooluniverse: ToolUniverse instance for tool execution
        composer_tool (str): Name of the ComposeTool for summarization
        chunk_size (int): Size of chunks for processing large outputs
        focus_areas (str): Areas to focus on during summarization
        max_summary_length (int): Maximum length of final summary
    """

    def __init__(self, config: Dict[str, Any] | SummarizationHookConfig, tooluniverse):
        """
        Initialize the summarization hook.

        Args:
            config (Dict[str, Any]): Hook configuration
            tooluniverse: ToolUniverse instance for executing summarization tools
        """
        super().__init__(config if isinstance(config, dict) else {"hook_config": {}})
        self.tooluniverse = tooluniverse
        # Normalize input to config dataclass
        if isinstance(config, SummarizationHookConfig):
            cfg = config
        else:
            raw = config.get("hook_config", {}) if isinstance(config, dict) else {}
            # Breaking change: only support composer_tool going forward
            cfg = SummarizationHookConfig(
                composer_tool=raw.get("composer_tool", "OutputSummarizationComposer"),
                # Default should match SummarizationHookConfig and documentation.
                chunk_size=raw.get("chunk_size", 30000),
                focus_areas=raw.get("focus_areas", "key_findings_and_results"),
                max_summary_length=raw.get("max_summary_length", 3000),
                composer_timeout_sec=raw.get("composer_timeout_sec", 300),
            )
        self.config_obj = cfg.validate()
        self.composer_tool = self.config_obj.composer_tool
        self.chunk_size = self.config_obj.chunk_size
        self.focus_areas = self.config_obj.focus_areas
        self.max_summary_length = self.config_obj.max_summary_length
        self.composer_timeout_sec = self.config_obj.composer_timeout_sec

    def process(
        self,
        result: Any,
        tool_name: Optional[str] = None,
        arguments: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Execute summarization processing using Compose Summarizer Tool.

        This method orchestrates the summarization workflow by:
        1. Preparing parameters for the Compose Summarizer Tool
        2. Calling the tool through ToolUniverse
        3. Processing and returning the summarized result

        Args:
            result (Any): The tool output to summarize
            tool_name (str): Name of the tool that produced the output
            arguments (Dict[str, Any]): Arguments passed to the tool
            context (Dict[str, Any]): Additional context information

        Returns
            Any: The summarized output, or original output if summarization fails
        """
        try:
            # Backward-compat: allow calling process(result) only
            if tool_name is None:
                tool_name = "unknown_tool"
            if arguments is None:
                arguments = {}
            if context is None:
                context = {}
            # Explicitly preserve None and empty string semantics
            if result is None:
                return None
            if isinstance(result, str) and result == "":
                return ""
            # Debug: basic context
            try:
                _len = len(str(result))
            except Exception:
                _len = -1
            _logger.debug(
                "SummarizationHook process: tool=%s, result_len=%s, chunk_size=%s, max_summary_length=%s",
                tool_name,
                _len,
                self.chunk_size,
                self.max_summary_length,
            )
            # Check if the required tools are available
            if (
                self.composer_tool not in self.tooluniverse.callable_functions
                and self.composer_tool not in self.tooluniverse.all_tool_dict
            ):
                _logger.warning(
                    "Summarization tool '%s' not available; returning original output",
                    self.composer_tool,
                )
                return result

            # Prepare parameters for Compose Summarizer Tool
            composer_args = {
                "tool_output": str(result),
                "query_context": self._extract_query_context(context),
                "tool_name": tool_name,
                "chunk_size": self.chunk_size,
                "focus_areas": self.focus_areas,
                "max_summary_length": self.max_summary_length,
            }

            # Call Compose Summarizer Tool through ToolUniverse
            _logger.debug(
                "Calling composer tool '%s' (timeout=%ss)",
                self.composer_tool,
                self.composer_timeout_sec,
            )
            # Run composer with timeout to avoid hangs
            try:
                from concurrent.futures import (
                    ThreadPoolExecutor,
                )

                def _call_composer():
                    return self.tooluniverse.run_one_function(
                        {"name": self.composer_tool, "arguments": composer_args}
                    )

                with ThreadPoolExecutor(max_workers=1) as _pool:
                    _future = _pool.submit(_call_composer)
                    composer_result = _future.result(timeout=self.composer_timeout_sec)
            except Exception as _e_timeout:
                # Timeout or execution error; log and fall back to original output
                _logger.warning("Composer execution failed/timeout: %s", _e_timeout)
                return result
            # Debug: show composer result meta
            try:
                if isinstance(composer_result, dict):
                    success = composer_result.get("success", False)
                    summary_len = len(composer_result.get("summary", ""))
                    _logger.debug(
                        "Composer result: success=%s summary_len=%s",
                        success,
                        summary_len,
                    )
            except Exception as _e_dbg:
                _logger.debug("Debug error inspecting composer_result: %s", _e_dbg)

            # Process Compose Tool result
            if isinstance(composer_result, dict) and composer_result.get("success"):
                return composer_result.get("summary", result)
            elif isinstance(composer_result, str):
                return composer_result
            else:
                _logger.warning(
                    "Compose Summarizer Tool returned unexpected result: %s",
                    composer_result,
                )
                return result

        except Exception as e:
            error_msg = str(e)
            _logger.error("Error in summarization hook: %s", error_msg)
            # Check if the error is due to missing tools
            if "not found" in error_msg.lower() or "ToolOutputSummarizer" in error_msg:
                _logger.error(
                    "Required summarization tools are not available. Please ensure the SMCP server is started with hooks enabled."
                )
            return result

    def _extract_query_context(self, context: Dict[str, Any]) -> str:
        """
        Extract query context from execution context.

        This method attempts to identify the original user query or intent
        from the context information to provide better summarization.

        Args:
            context (Dict[str, Any]): Execution context containing arguments and metadata

        Returns
            str: Extracted query context or fallback description
        """
        arguments = context.get("arguments", {})

        # Common query parameter names
        query_keys = ["query", "question", "input", "text", "search_term", "prompt"]
        for key in query_keys:
            if key in arguments:
                return str(arguments[key])

        # If no explicit query found, return tool name as context
        return f"Tool execution: {context.get('tool_name', 'unknown')}"


class HookManager:
    """
    Manages and coordinates all output hooks.

    The HookManager is responsible for loading hook configurations, creating
    hook instances, and applying hooks to tool outputs. It provides a unified
    interface for hook management and supports dynamic configuration updates.

    Args:
        config (Dict[str, Any]): Hook manager configuration
        tooluniverse: Reference to the ToolUniverse instance

    Attributes:
        config (Dict[str, Any]): Hook manager configuration
        tooluniverse: ToolUniverse instance for tool execution
        hooks (List[OutputHook]): List of loaded hook instances
        enabled (bool): Whether hook processing is enabled
        config_path (str): Path to hook configuration file
    """

    def __init__(self, config: Dict[str, Any], tooluniverse):
        """
        Initialize the hook manager.

        Args:
            config (Dict[str, Any]): Configuration for hook manager
            tooluniverse: ToolUniverse instance for executing tools
        """
        self.config = config
        self.tooluniverse = tooluniverse
        self.hooks: List[OutputHook] = []
        self.enabled = True
        # Alias for tests that expect hooks_enabled flag
        self.hooks_enabled = self.enabled
        self.config_path = config.get("config_path", "template/hook_config.json")
        self._pending_tools_to_load: List[str] = []
        # Cache excluded patterns for performance
        self._excluded_patterns_cache = None
        self._load_hook_config()

        # Validate LLM API keys before loading hooks
        if not self._validate_llm_api_keys():
            _logger.warning("LLM API keys not available. Hooks will be disabled.")
            _logger.info(
                "To enable hooks, please set LLM API keys environment variable."
            )
            # Disable hook processing but still ensure required tools are available
            # Tests expect hook-related tools (e.g., ToolOutputSummarizer) to be registered
            # in ToolUniverse.callable_functions even when hooks are disabled.
            self.enabled = False

            try:
                # Proactively load tools required by summarization hooks so they are discoverable
                all_hook_configs = []
                global_hooks = (
                    self.config.get("hooks", [])
                    if isinstance(self.config, dict)
                    else []
                )
                for hook_cfg in global_hooks:
                    all_hook_configs.append(hook_cfg)

                # Attempt auto-load based on config; if config is empty, fall back to ensuring summarization tools
                self._auto_load_hook_tools(all_hook_configs)
                # Ensure tools are pre-instantiated into callable_functions if possible
                self._ensure_hook_tools_loaded()
            except Exception as _e:
                # Non-fatal: we still proceed with disabled hooks
                _logger.warning("Failed to preload hook tools without API keys: %s", _e)

            # Do not proceed to create hook instances when disabled
            # Keep hooks list empty and reflect flags
            self.hooks_enabled = self.enabled
            return

        self._load_hooks()
        self.hooks_enabled = self.enabled

    def apply_hooks(
        self,
        result: Any,
        tool_name: str,
        arguments: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        """
        Apply all applicable hooks to the tool output.

        This method iterates through all loaded hooks, checks if they should
        be applied to the current output, and processes the output through
        each applicable hook in priority order.

        Args:
            result (Any): The tool output to process
            tool_name (str): Name of the tool that produced the output
            arguments (Dict[str, Any]): Arguments passed to the tool
            context (Dict[str, Any]): Additional context information

        Returns
            Any: The processed output after applying all applicable hooks
        """
        if not self.enabled:
            return result

        # Load pending tools if ToolUniverse is now ready
        self._load_pending_tools()

        # Prevent recursive hook processing
        if self._is_hook_tool(tool_name):
            return result

        # Sort hooks by priority (lower numbers execute first)
        sorted_hooks = sorted(self.hooks, key=lambda h: h.priority)

        for hook in sorted_hooks:
            if not hook.enabled:
                continue

            # Check if hook is applicable to current tool
            if self._is_hook_applicable(hook, tool_name, context):
                if hook.should_trigger(result, tool_name, arguments, context):
                    _logger.debug(
                        "Applying hook: %s for tool: %s", hook.name, tool_name
                    )
                    result = hook.process(result, tool_name, arguments, context)

        return result

    def _validate_llm_api_keys(self) -> bool:
        """
        Validate that LLM API keys are available for hook tools.

        Returns
            bool: True if API keys are available, False otherwise
        """
        from .agentic_tool import AgenticTool

        if AgenticTool.has_any_api_keys():
            _logger.debug("LLM API keys validated successfully")
            return True
        else:
            _logger.error("LLM API key validation failed: No API keys available")
            _logger.info("To enable hooks, please set API key environment variables.")
            return False

    def enable_hook(self, hook_name: str):
        """
        Enable a specific hook by name.

        Args:
            hook_name (str): Name of the hook to enable
        """
        hook = self.get_hook(hook_name)
        if hook:
            hook.enabled = True
            _logger.info("Enabled hook: %s", hook_name)
        else:
            _logger.error("Hook not found: %s", hook_name)

    def disable_hook(self, hook_name: str):
        """
        Disable a specific hook by name.

        Args:
            hook_name (str): Name of the hook to disable
        """
        hook = self.get_hook(hook_name)
        if hook:
            hook.enabled = False
            _logger.info("Disabled hook: %s", hook_name)
        else:
            _logger.error("Hook not found: %s", hook_name)

    def toggle_hooks(self, enabled: bool):
        """
        Enable or disable all hooks globally.

        Args:
            enabled (bool): True to enable all hooks, False to disable
        """
        self.enabled = enabled
        self.hooks_enabled = enabled
        status = "enabled" if enabled else "disabled"
        _logger.info("Hooks %s", status)

    # Backward-compat: tests reference enable_hooks/disable_hooks APIs
    def enable_hooks(self):
        """Enable hooks and (re)load configurations and required tools."""
        self.toggle_hooks(True)
        # Ensure tools and hooks are ready
        self._ensure_hook_tools_loaded()
        self._load_hooks()

    def disable_hooks(self):
        """Disable hooks and clear in-memory hook instances."""
        self.toggle_hooks(False)
        # Do not destroy config; just clear active hooks
        self.hooks = []

    def reload_config(self, config_path: Optional[str] = None):
        """
        Reload hook configuration from file.

        Args:
            config_path (Optional[str]): Path to configuration file.
                If None, uses the current config_path
        """
        if config_path:
            self.config_path = config_path
        self._excluded_patterns_cache = None  # Clear cache on reload
        self._load_hook_config()
        self._load_hooks()
        _logger.info("Reloaded hook configuration")

    def get_hook(self, hook_name: str) -> Optional[OutputHook]:
        """
        Get a hook instance by name.

        Args:
            hook_name (str): Name of the hook to retrieve

        Returns
            Optional[OutputHook]: Hook instance if found, None otherwise
        """
        for hook in self.hooks:
            if hook.name == hook_name:
                return hook
        return None

    def _load_hook_config(self):
        """
        Load hook configuration from file.

        This method attempts to load the hook configuration from the specified
        file path, handling both package resources and file system paths.
        If the config is already provided and not empty, it uses that instead.
        """
        # If config is already provided and not empty, use it
        if self.config and (
            ("hooks" in self.config)
            or ("tool_specific_hooks" in self.config)
            or ("category_hooks" in self.config)
        ):
            return

        try:
            config_file = self._get_config_file_path()
            content = (
                config_file.read_text(encoding="utf-8")
                if hasattr(config_file, "read_text")
                else Path(config_file).read_text(encoding="utf-8")
            )
            self.config = json.loads(content)
            self._excluded_patterns_cache = None  # Clear cache on reload
        except Exception as e:
            print(f"Warning: Could not load hook config: {e}")
            if not self.config:
                self.config = {}

    def _get_config_file_path(self):
        """
        Get the path to the hook configuration file.

        Returns
            Path: Path to the configuration file
        """
        try:
            import importlib.resources as pkg_resources
        except ImportError:
            import importlib_resources as pkg_resources

        try:
            data_files = pkg_resources.files("tooluniverse.template")
            config_file = data_files / "hook_config.json"
            return config_file
        except Exception:
            # Fallback to file-based path resolution
            current_dir = Path(__file__).parent
            config_file = current_dir / "template" / "hook_config.json"
            return config_file

    def _load_hooks(self):
        """
        Load hook configurations and create hook instances.

        This method processes the configuration and creates appropriate
        hook instances for global, tool-specific, and category-specific hooks.
        It also automatically loads any tools required by the hooks.
        """
        self.hooks = []

        # Collect all hook configs first to determine required tools
        all_hook_configs = []

        # Load global hooks
        global_hooks = self.config.get("hooks", [])
        for hook_config in global_hooks:
            all_hook_configs.append(hook_config)

        # Load tool-specific hooks
        tool_specific_hooks = self.config.get("tool_specific_hooks", {})
        for tool_name, tool_hook_config in tool_specific_hooks.items():
            if tool_hook_config.get("enabled", True):
                tool_hooks = tool_hook_config.get("hooks", [])
                for hook_config in tool_hooks:
                    hook_config["tool_name"] = tool_name
                    all_hook_configs.append(hook_config)

        # Load category-specific hooks
        category_hooks = self.config.get("category_hooks", {})
        for category_name, category_hook_config in category_hooks.items():
            if category_hook_config.get("enabled", True):
                category_hooks_list = category_hook_config.get("hooks", [])
                for hook_config in category_hooks_list:
                    hook_config["category"] = category_name
                    all_hook_configs.append(hook_config)

        # Auto-load required tools for hooks
        self._auto_load_hook_tools(all_hook_configs)

        # Note: Hook tools will be pre-loaded when ToolUniverse.load_tools() is called
        # This is handled in the _load_pending_tools method

        # Create hook instances
        for hook_config in all_hook_configs:
            hook = self._create_hook_instance(hook_config)
            if hook:
                self.hooks.append(hook)

    def _auto_load_hook_tools(self, hook_configs: List[Dict[str, Any]]):
        """
        Automatically load tools required by hooks.

        This method analyzes hook configurations to determine which tools
        are needed and automatically loads them into the ToolUniverse.

        Args:
            hook_configs (List[Dict[str, Any]]): List of hook configurations
        """
        required_tools = set()

        for hook_config in hook_configs:
            hook_type = hook_config.get("type", "SummarizationHook")
            hook_config_section = hook_config.get("hook_config", {})

            # Determine required tools based on hook type
            if hook_type == "SummarizationHook":
                composer_tool = hook_config_section.get(
                    "composer_tool", "OutputSummarizationComposer"
                )
                required_tools.add(composer_tool)
                # Also need the agentic tool for summarization
                required_tools.add("ToolOutputSummarizer")
            elif hook_type == "FilteringHook":
                # Add filtering-related tools if any
                pass
            elif hook_type == "FormattingHook":
                # Add formatting-related tools if any
                pass
            elif hook_type == "ValidationHook":
                # Add validation-related tools if any
                pass
            elif hook_type == "LoggingHook":
                # Add logging-related tools if any
                pass

        # Load required tools
        if required_tools:
            tools_to_load = []
            for tool in required_tools:
                # Map tool names to their categories
                if tool in ["OutputSummarizationComposer", "ToolOutputSummarizer"]:
                    tools_to_load.append("output_summarization")
                # Add more mappings as needed

            if tools_to_load:
                try:
                    # Ensure ComposeTool is available
                    from .compose_tool import ComposeTool
                    from .tool_registry import register_external_tool

                    register_external_tool("ComposeTool", ComposeTool)

                    # Check if ToolUniverse is fully initialized
                    if hasattr(self.tooluniverse, "all_tools"):
                        # Load the tools and verify they were loaded
                        self.tooluniverse.load_tools(tools_to_load)

                        # Verify that the required tools are actually available
                        missing_tools = []
                        for tool in required_tools:
                            if (
                                tool not in self.tooluniverse.callable_functions
                                and tool not in self.tooluniverse.all_tool_dict
                            ):
                                missing_tools.append(tool)

                        if missing_tools:
                            _logger.warning(
                                "Some hook tools could not be loaded: %s", missing_tools
                            )
                            _logger.info("This may cause summarization hooks to fail.")
                        else:
                            _logger.info(
                                "Auto-loaded hook tools: %s",
                                ", ".join(tools_to_load),
                            )
                    else:
                        # Store tools to load later when ToolUniverse is ready
                        self._pending_tools_to_load = tools_to_load
                        _logger.info(
                            "Hook tools queued for loading: %s",
                            ", ".join(tools_to_load),
                        )
                except Exception as e:
                    _logger.warning("Could not auto-load hook tools: %s", e)
                    _logger.info("This will cause summarization hooks to fail.")

    def _ensure_hook_tools_loaded(self):
        """
        Ensure that tools required by hooks are loaded.

        This method is called during HookManager initialization to make sure
        the necessary tools (like output_summarization tools) are available.

        Note: Hook tools (especially AgenticTool types like ToolOutputSummarizer)
        may be filtered out during normal loading if LLM API keys are not
        available. This method force-loads them directly from the JSON config
        to ensure they are always available for discovery, even if they won't
        function without API keys.
        """
        try:
            # Ensure ComposeTool and AgenticTool are available in registry
            from .compose_tool import ComposeTool
            from .agentic_tool import AgenticTool
            from .tool_registry import register_external_tool

            register_external_tool("ComposeTool", ComposeTool)
            register_external_tool("AgenticTool", AgenticTool)

            # Load output_summarization tools if not already loaded
            if (
                not hasattr(self.tooluniverse, "tool_category_dicts")
                or "output_summarization" not in self.tooluniverse.tool_category_dicts
            ):
                _logger.info("Loading output_summarization tools for hooks")
                self.tooluniverse.load_tools(["output_summarization"])

            # Required hook tools
            required_tools = ["ToolOutputSummarizer", "OutputSummarizationComposer"]

            # Force-load hook tools filtered out (e.g., AgenticTool w/o API keys)
            # This ensures tools are available for discovery even if not executable
            missing_from_dict = [
                t
                for t in required_tools
                if t not in getattr(self.tooluniverse, "all_tool_dict", {})
            ]

            if missing_from_dict:
                _logger.info(
                    "Force-loading hook tools that were filtered out: %s",
                    missing_from_dict,
                )
                self._force_load_hook_tools_from_json(missing_from_dict)

            # Pre-instantiate hook tools to ensure they're available in callable_functions
            for tool_name in required_tools:
                if (
                    tool_name in self.tooluniverse.all_tool_dict
                    and tool_name not in self.tooluniverse.callable_functions
                ):
                    try:
                        self.tooluniverse.init_tool(
                            self.tooluniverse.all_tool_dict[tool_name],
                            add_to_cache=True,
                        )
                        _logger.debug("Pre-loaded hook tool: %s", tool_name)
                    except Exception as e:
                        _logger.warning(
                            "Failed to pre-load hook tool %s: %s", tool_name, e
                        )

            # Verify the tools were loaded
            missing_tools = []
            for tool in required_tools:
                if (
                    hasattr(self.tooluniverse, "callable_functions")
                    and tool not in self.tooluniverse.callable_functions
                    and hasattr(self.tooluniverse, "all_tool_dict")
                    and tool not in self.tooluniverse.all_tool_dict
                ):
                    missing_tools.append(tool)

            if missing_tools:
                _logger.warning(
                    "Some hook tools could not be loaded: %s", missing_tools
                )
                _logger.info("This may cause summarization hooks to fail")
            else:
                _logger.info("Hook tools loaded successfully: %s", required_tools)

        except Exception as e:
            _logger.error("Error loading hook tools: %s", e)
            _logger.info("This will cause summarization hooks to fail")

    def _force_load_hook_tools_from_json(self, tool_names: List[str]):
        """
        Force-load hook tools from JSON, bypassing API key checks.

        This is necessary because AgenticTool types get filtered out during
        normal loading when LLM API keys are not available. Hook tools need
        to be available for discovery even without proper API keys.

        Args:
            tool_names: List of tool names to force-load
        """
        import json
        import os

        # Path to the output_summarization_tools.json file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(current_dir, "data", "output_summarization_tools.json")

        if not os.path.exists(json_path):
            _logger.warning("Hook tools JSON not found: %s", json_path)
            return

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                tools_data = json.load(f)

            for tool_config in tools_data:
                tool_name = tool_config.get("name")
                if tool_name in tool_names:
                    # Add to all_tool_dict for discovery
                    if hasattr(self.tooluniverse, "all_tool_dict"):
                        self.tooluniverse.all_tool_dict[tool_name] = tool_config
                        _logger.debug(
                            "Force-added hook tool to all_tool_dict: %s", tool_name
                        )

                    # Add to all_tools list if not present
                    if hasattr(self.tooluniverse, "all_tools"):
                        existing_names = [
                            t.get("name")
                            for t in self.tooluniverse.all_tools
                            if isinstance(t, dict)
                        ]
                        if tool_name not in existing_names:
                            self.tooluniverse.all_tools.append(tool_config)
                            _logger.debug(
                                "Force-added hook tool to all_tools: %s", tool_name
                            )

        except Exception as e:
            _logger.warning("Failed to force-load hook tools from JSON: %s", e)

    def _load_pending_tools(self):
        """
        Load any pending tools that were queued during initialization.

        This method is called when hooks are applied to ensure that any tools
        that couldn't be loaded during HookManager initialization are loaded
        once the ToolUniverse is fully ready.
        """
        if self._pending_tools_to_load and hasattr(self.tooluniverse, "all_tools"):
            try:
                self.tooluniverse.load_tools(self._pending_tools_to_load)
                _logger.info(
                    "Loaded pending hook tools: %s",
                    ", ".join(self._pending_tools_to_load),
                )
                self._pending_tools_to_load = []  # Clear the pending list
            except Exception as e:
                _logger.warning("Could not load pending hook tools: %s", e)

        # Pre-load hook tools if they're available but not instantiated
        self._ensure_hook_tools_loaded()

    def _is_hook_tool(self, tool_name: str) -> bool:
        """
        Check if a tool is a hook-related tool that should not be processed by hooks.

        This prevents recursive hook processing where hook tools (like ToolOutputSummarizer)
        produce output that would trigger more hook processing.

        Args:
            tool_name (str): Name of the tool to check

        Returns
            bool: True if the tool is a hook tool and should be excluded from hook processing
        """
        # Cache excluded patterns for performance
        if self._excluded_patterns_cache is None:
            hook_tool_names = [
                "ToolOutputSummarizer",
                "OutputSummarizationComposer",
            ]
            exclude_tools = self.config.get("exclude_tools", [])
            self._excluded_patterns_cache = hook_tool_names + exclude_tools

        # Check for exact match or wildcard pattern match
        for pattern in self._excluded_patterns_cache:
            if pattern.endswith("*"):
                if tool_name.startswith(pattern[:-1]):
                    return True
            elif tool_name == pattern:
                return True

        return False

    def _create_hook_instance(
        self, hook_config: Dict[str, Any]
    ) -> Optional[OutputHook]:
        """
        Create a hook instance based on configuration.

        This method creates hook instances and applies hook type-specific defaults
        from the configuration before initializing the hook.

        Args:
            hook_config (Dict[str, Any]): Hook configuration

        Returns
            Optional[OutputHook]: Created hook instance or None if type not supported
        """
        hook_type = hook_config.get("type", "SummarizationHook")

        # Apply hook type-specific defaults
        enhanced_config = self._apply_hook_type_defaults(hook_config)

        if hook_type == "SummarizationHook":
            return SummarizationHook(enhanced_config, self.tooluniverse)
        elif hook_type == "FileSaveHook":
            # Merge hook_config with the main config for FileSaveHook
            file_save_config = enhanced_config.copy()
            file_save_config.update(enhanced_config.get("hook_config", {}))
            return FileSaveHook(file_save_config)
        else:
            _logger.error("Unknown hook type: %s", hook_type)
            return None

    def _apply_hook_type_defaults(self, hook_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply hook type-specific default values to hook configuration.

        This method merges hook type defaults with individual hook configuration,
        ensuring that each hook type gets its appropriate default values.

        Args:
            hook_config (Dict[str, Any]): Original hook configuration

        Returns
            Dict[str, Any]: Enhanced configuration with defaults applied
        """
        hook_type = hook_config.get("type", "SummarizationHook")

        # Get hook type defaults from configuration
        hook_type_defaults = self.config.get("hook_type_defaults", {}).get(
            hook_type, {}
        )

        # Create enhanced configuration
        enhanced_config = hook_config.copy()

        # Apply defaults to hook_config if not already specified
        if "hook_config" not in enhanced_config:
            enhanced_config["hook_config"] = {}

        hook_config_section = enhanced_config["hook_config"]

        # Apply defaults for each hook type
        if hook_type == "SummarizationHook":
            defaults = {
                "composer_tool": "OutputSummarizationComposer",
                # Default chunk_size is intentionally large; chunk_size controls
                # chunking, not whether summarization is needed.
                "chunk_size": hook_type_defaults.get("default_chunk_size", 30000),
                "focus_areas": hook_type_defaults.get(
                    "default_focus_areas", "key_findings_and_results"
                ),
                "max_summary_length": hook_type_defaults.get(
                    "default_max_summary_length", 3000
                ),
            }
        # Removed unsupported hook types to avoid confusion
        elif hook_type == "FileSaveHook":
            defaults = {
                "temp_dir": hook_type_defaults.get("default_temp_dir", None),
                "file_prefix": hook_type_defaults.get(
                    "default_file_prefix", "tool_output"
                ),
                "include_metadata": hook_type_defaults.get(
                    "default_include_metadata", True
                ),
                "auto_cleanup": hook_type_defaults.get("default_auto_cleanup", False),
                "cleanup_age_hours": hook_type_defaults.get(
                    "default_cleanup_age_hours", 24
                ),
            }
        else:
            defaults = {}

        # Apply defaults only if not already specified
        for key, default_value in defaults.items():
            if key not in hook_config_section:
                hook_config_section[key] = default_value

        return enhanced_config

    def _is_hook_applicable(
        self, hook: OutputHook, tool_name: str, context: Dict[str, Any]
    ) -> bool:
        """
        Check if a hook is applicable to the current tool.

        Args:
            hook (OutputHook): Hook instance to check
            tool_name (str): Name of the current tool
            context (Dict[str, Any]): Execution context

        Returns
            bool: True if hook is applicable, False otherwise
        """
        # Check tool-specific hooks
        if "tool_name" in hook.config:
            return hook.config["tool_name"] == tool_name

        # Check category-specific hooks
        if "category" in hook.config:
            # This would need to be implemented based on actual tool categorization
            # For now, return True to apply category hooks to all tools
            return True

        # Global hooks apply to all tools
        return True


class FileSaveHook(OutputHook):
    """
    Hook that saves tool outputs to temporary files and returns file information.

    This hook saves the tool output to a temporary file and returns information
    about the file path, data format, and data structure instead of the original output.
    This is useful for handling large outputs or when you need to process outputs
    as files rather than in-memory data.

    Configuration options:
    - temp_dir: Directory to save temporary files (default: system temp)
    - file_prefix: Prefix for generated filenames (default: 'tool_output')
    - include_metadata: Whether to include metadata in the response (default: True)
    - auto_cleanup: Whether to automatically clean up old files (default: False)
    - cleanup_age_hours: Age in hours for auto cleanup (default: 24)
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the FileSaveHook.

        Args:
            config (Dict[str, Any]): Hook configuration including:
                - name: Hook name
                - temp_dir: Directory for temporary files
                - file_prefix: Prefix for filenames
                - include_metadata: Include metadata flag
                - auto_cleanup: Auto cleanup flag
                - cleanup_age_hours: Cleanup age in hours
        """
        super().__init__(config)

        # Set default configuration
        self.temp_dir = config.get("temp_dir", None)
        self.file_prefix = config.get("file_prefix", "tool_output")
        self.include_metadata = config.get("include_metadata", True)
        self.auto_cleanup = config.get("auto_cleanup", False)
        self.cleanup_age_hours = config.get("cleanup_age_hours", 24)

        # Import required modules
        import tempfile
        import os
        from datetime import datetime, timedelta

        self.tempfile = tempfile
        self.os = os
        self.datetime = datetime
        self.timedelta = timedelta

        # Create temp directory if specified
        if self.temp_dir:
            self.os.makedirs(self.temp_dir, exist_ok=True)

    def process(
        self,
        result: Any,
        tool_name: str,
        arguments: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Process the tool output by saving it to a temporary file.

        Args:
            result (Any): The tool output to process
            tool_name (str): Name of the tool that produced the output
            arguments (Dict[str, Any]): Arguments passed to the tool
            context (Dict[str, Any]): Execution context

        Returns
            Dict[str, Any]: Dictionary containing file information:
                - file_path: Path to the saved file
                - data_format: Format of the data (json, text, binary, etc.)
                - data_structure: Structure information about the data
                - file_size: Size of the file in bytes
                - created_at: Timestamp when file was created
                - metadata: Additional metadata (if include_metadata is True)
        """
        try:
            # Determine data format and structure
            data_format, data_structure = self._analyze_data(result)

            # Generate filename
            timestamp = self.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.file_prefix}_{tool_name}_{timestamp}.{data_format}"

            # Save to temporary file
            if self.temp_dir:
                file_path = self.os.path.join(self.temp_dir, filename)
            else:
                # Use system temp directory
                temp_fd, file_path = self.tempfile.mkstemp(
                    suffix=f"_{filename}", prefix=self.file_prefix, dir=self.temp_dir
                )
                self.os.close(temp_fd)

            # Write data to file
            self._write_data_to_file(result, file_path, data_format)

            # Get file size
            file_size = self.os.path.getsize(file_path)

            # Prepare response
            response = {
                "file_path": file_path,
                "data_format": data_format,
                "data_structure": data_structure,
                "file_size": file_size,
                "created_at": self.datetime.now().isoformat(),
                "tool_name": tool_name,
                "original_arguments": arguments,
            }

            # Add metadata if requested
            if self.include_metadata:
                response["metadata"] = {
                    "hook_name": self.name,
                    "hook_type": "FileSaveHook",
                    "processing_time": self.datetime.now().isoformat(),
                    "context": context,
                }

            # Perform auto cleanup if enabled
            if self.auto_cleanup:
                self._cleanup_old_files()

            return response

        except Exception as e:
            # Return error information instead of failing
            return {
                "status": "error",
                "error": f"Failed to save output to file: {str(e)}",
                "original_output": str(result),
                "tool_name": tool_name,
                "hook_name": self.name,
            }

    def _analyze_data(self, data: Any) -> tuple[str, str]:
        """
        Analyze the data to determine its format and structure.

        Args:
            data (Any): The data to analyze

        Returns
            tuple[str, str]: (data_format, data_structure)
        """
        if isinstance(data, dict):
            return "json", f"dict with {len(data)} keys"
        elif isinstance(data, list):
            return "json", f"list with {len(data)} items"
        elif isinstance(data, str):
            if data.strip().startswith("{") or data.strip().startswith("["):
                return "json", "JSON string"
            else:
                return "txt", f"text with {len(data)} characters"
        elif isinstance(data, (int, float)):
            return "json", "numeric value"
        elif isinstance(data, bool):
            return "json", "boolean value"
        else:
            return "bin", f"binary data of type {type(data).__name__}"

    def _write_data_to_file(self, data: Any, file_path: str, data_format: str) -> None:
        """
        Write data to file in the appropriate format.

        Args:
            data (Any): The data to write
            file_path (str): Path to the file
            data_format (str): Format of the data
        """
        if data_format == "json":
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        elif data_format == "txt":
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(str(data))
        else:
            # For binary or other formats, write as string
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(str(data))

    def _cleanup_old_files(self) -> None:
        """
        Clean up old files based on the cleanup_age_hours setting.
        """
        if not self.temp_dir:
            return

        try:
            current_time = self.datetime.now()
            cutoff_time = current_time - self.timedelta(hours=self.cleanup_age_hours)

            for filename in self.os.listdir(self.temp_dir):
                if filename.startswith(self.file_prefix):
                    file_path = self.os.path.join(self.temp_dir, filename)
                    file_time = self.datetime.fromtimestamp(
                        self.os.path.getmtime(file_path)
                    )

                    if file_time < cutoff_time:
                        self.os.remove(file_path)

        except Exception as e:
            # Log error but don't fail the hook
            print(f"Warning: Failed to cleanup old files: {e}")
