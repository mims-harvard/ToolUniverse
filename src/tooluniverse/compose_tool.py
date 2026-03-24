"""
ComposeTool - A tool that composes other tools using custom code logic.
Supports intelligent dependency management with automatic tool loading.
"""

import json
import copy
import traceback
import os
import importlib.util
import re
from datetime import datetime
from typing import Set
from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("ComposeTool")
class ComposeTool(BaseTool):
    """
    A flexible tool that can compose other tools using custom code logic.
    Supports both inline composition_code and external Python files.
    Features intelligent dependency management with automatic tool loading.
    """

    def __init__(self, tool_config, tooluniverse=None):
        """
        Initialize the ComposeTool.

        Args:
            tool_config (dict): Tool configuration containing composition code or file reference
            tooluniverse (ToolUniverse): Reference to the ToolUniverse instance
        """
        super().__init__(tool_config)
        self.tool_config = tool_config
        self.name = tool_config.get("name", "unnamed_compose_tool")
        self.tooluniverse = tooluniverse

        # Configuration for dependency handling
        self.auto_load_dependencies = tool_config.get("auto_load_dependencies", True)
        self.required_tools = tool_config.get(
            "required_tools", []
        )  # Explicitly specified dependencies
        self.fail_on_missing_tools = tool_config.get("fail_on_missing_tools", False)

        # Check if using external file or inline code
        self.composition_file = tool_config.get("composition_file")
        self.composition_function = tool_config.get("composition_function", "compose")

        if self.composition_file:
            # Load code from external file
            self.composition_code = self._load_code_from_file()
        else:
            # Use inline code (existing behavior)
            composition_code_raw = tool_config.get("composition_code", "")
            if isinstance(composition_code_raw, list):
                self.composition_code = "\n".join(composition_code_raw)
            else:
                self.composition_code = composition_code_raw

        # Extract tool dependencies from code
        self.discovered_dependencies = self._discover_tool_dependencies()

    def _discover_tool_dependencies(self):
        """
        Automatically discover tool dependencies from composition code.

        Returns
            set: Set of tool names that this composition calls
        """
        dependencies = set()

        if not self.composition_code:
            return dependencies

        # Look for call_tool patterns: call_tool('ToolName', ...)
        call_tool_pattern = r"call_tool\s*\(\s*['\"]([^'\"]+)['\"]"
        matches = re.findall(call_tool_pattern, self.composition_code)
        dependencies.update(matches)

        # Look for tooluniverse.run_one_function patterns
        run_function_pattern = r"tooluniverse\.run_one_function\s*\(\s*\{\s*['\"]name['\"]:\s*['\"]([^'\"]+)['\"]"
        matches = re.findall(run_function_pattern, self.composition_code)
        dependencies.update(matches)

        return dependencies

    def _get_tool_category_mapping(self):
        """
        Create a mapping from tool names to their categories.

        Returns
            dict: Mapping of tool names to category names
        """
        tool_to_category = {}

        if not self.tooluniverse:
            return tool_to_category

        # Check all tool files to build mapping
        for category, file_path in self.tooluniverse.tool_files.items():
            try:
                from .execute_function import read_json_list

                tools_in_category = read_json_list(file_path)
                for tool in tools_in_category:
                    tool_name = tool.get("name")
                    if tool_name:
                        tool_to_category[tool_name] = category
            except Exception as e:
                print(f"Warning: Could not read tool file {file_path}: {e}")

        return tool_to_category

    def _load_missing_dependencies(self, missing_tools: Set[str]):
        """
        Automatically load missing tool dependencies.

        Args:
            missing_tools (set): Set of missing tool names

        Returns
            tuple: (successfully_loaded, failed_to_load)
        """
        if not self.tooluniverse or not self.auto_load_dependencies:
            return set(), missing_tools

        tool_to_category = self._get_tool_category_mapping()
        categories_to_load = set()
        successfully_loaded = set()
        failed_to_load = set()

        # Determine which categories need to be loaded
        for tool_name in missing_tools:
            category = tool_to_category.get(tool_name)
            if category:
                categories_to_load.add(category)
            else:
                failed_to_load.add(tool_name)

        # Load the required categories
        for category in categories_to_load:
            try:
                print(
                    f"🔄 Auto-loading category '{category}' for ComposeTool '{self.name}'"
                )
                self.tooluniverse.load_tools(tool_type=[category])

                # Check which tools from this category are now available
                for tool_name in missing_tools:
                    # Check both callable_functions and all_tool_dict
                    if (
                        tool_name in self.tooluniverse.callable_functions
                        or tool_name in self.tooluniverse.all_tool_dict
                    ):
                        successfully_loaded.add(tool_name)

            except Exception as e:
                print(f"❌ Failed to auto-load category '{category}': {e}")

        failed_to_load = missing_tools - successfully_loaded

        if successfully_loaded:
            print(
                f"✅ Successfully auto-loaded tools: {', '.join(successfully_loaded)}"
            )
        if failed_to_load:
            print(f"❌ Failed to load tools: {', '.join(failed_to_load)}")

        return successfully_loaded, failed_to_load

    def _load_code_from_file(self):
        """
        Load composition code from external Python file.

        Returns
            str: The composition code as a string
        """
        if not self.composition_file:
            return ""

        # Resolve file path relative to the tool configuration file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(current_dir, "compose_scripts", self.composition_file)

        try:
            # Load the Python file as a module
            spec = importlib.util.spec_from_file_location("compose_module", file_path)
            compose_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(compose_module)

            # Get the composition function
            if hasattr(compose_module, self.composition_function):
                compose_func = getattr(compose_module, self.composition_function)
                # Extract the function code
                import inspect

                return inspect.getsource(compose_func)
            else:
                raise AttributeError(
                    f"Function '{self.composition_function}' not found in {self.composition_file}"
                )

        except Exception as e:
            print(f"Error loading composition file {self.composition_file}: {e}")
            return f"# Error loading file: {e}\nresult = {{'error': 'Failed to load composition code'}}"

    def run(self, arguments, stream_callback=None):
        """
        Execute the composed tool with custom code logic.

        Args:
            arguments (dict): Input arguments for the composition
            stream_callback (callable, optional): Callback function for streaming output

        Returns
            Any: Result from the composition execution
        """
        if not self.tooluniverse:
            return {
                "status": "error",
                "error": "ToolUniverse reference is required for ComposeTool",
            }

        if not self.composition_code:
            return {"status": "error", "error": "No composition code provided"}

        # Check for missing dependencies
        all_dependencies = self.discovered_dependencies.union(set(self.required_tools))
        missing_tools = set()

        for tool_name in all_dependencies:
            # Check both callable_functions and all_tool_dict
            if (
                tool_name not in self.tooluniverse.callable_functions
                and tool_name not in self.tooluniverse.all_tool_dict
            ):
                missing_tools.add(tool_name)

        # Handle missing dependencies
        if missing_tools:
            if self.auto_load_dependencies:
                print(
                    f"🔍 ComposeTool '{self.name}' detected missing dependencies: {', '.join(missing_tools)}"
                )
                successfully_loaded, still_missing = self._load_missing_dependencies(
                    missing_tools
                )

                if still_missing:
                    if self.fail_on_missing_tools:
                        return {
                            "status": "error",
                            "error": f"Required tools not available: {', '.join(still_missing)}",
                            "missing_tools": list(still_missing),
                            "auto_loaded": list(successfully_loaded),
                        }
                    else:
                        print(
                            f"⚠️  Continuing execution despite missing tools: {', '.join(still_missing)}"
                        )
            else:
                if self.fail_on_missing_tools:
                    return {
                        "status": "error",
                        "error": f"Required tools not available: {', '.join(missing_tools)}",
                        "missing_tools": list(missing_tools),
                        "auto_load_disabled": True,
                    }
                else:
                    print(
                        f"⚠️  ComposeTool '{self.name}' has missing dependencies but continuing: {', '.join(missing_tools)}"
                    )

        try:
            if self.composition_file:
                # Execute function from external file
                return self._execute_from_file(arguments, stream_callback)
            else:
                # Execute inline code (existing behavior)
                return self._execute_inline_code(arguments, stream_callback)

        except Exception as e:
            error_msg = f"Error in ComposeTool '{self.name}': {str(e)}"
            traceback.print_exc()  # Print full stack trace
            print(f"\033[91m{error_msg}\033[0m")

            return {
                "status": "error",
                "error": error_msg,
                "traceback": traceback.format_exc(),
            }

    def _emit_stream_chunk(self, chunk, stream_callback):
        """
        Emit a stream chunk if callback is provided.

        Args:
            chunk (str): The chunk to emit
            stream_callback (callable, optional): Callback function for streaming output
        """
        if stream_callback and chunk:
            try:
                stream_callback(chunk)
            except Exception as e:
                print(f"Error in stream callback: {e}")

    def _create_event_emitter(self, stream_callback):
        """
        Create an event emitter function for the compose script.

        Args:
            stream_callback (callable, optional): Callback function for streaming output

        Returns
            callable: Event emitter function
        """

        def emit_event(event_type, data=None):
            """Emit an event via stream callback"""
            if stream_callback:
                event = {
                    "type": event_type,
                    "timestamp": datetime.now().isoformat(),
                    "data": data or {},
                }
                self._emit_stream_chunk(json.dumps(event), stream_callback)

        return emit_event

    def _execute_from_file(self, arguments, stream_callback=None):
        """
        Execute composition code from external file.

        Args:
            arguments (dict): Input arguments
            stream_callback (callable, optional): Callback function for streaming output

        Returns
            Any: Result from the composition execution
        """
        # Resolve file path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(current_dir, "compose_scripts", self.composition_file)

        # Load the Python file as a module
        spec = importlib.util.spec_from_file_location("compose_module", file_path)
        compose_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(compose_module)

        # Get the composition function
        compose_func = getattr(compose_module, self.composition_function)

        # Import memory manager
        from .memory_manager import memory_manager

        # Execute the function with backward-compatible parameters
        import inspect

        sig = inspect.signature(compose_func)
        params = list(sig.parameters.keys())

        # Build arguments based on function signature
        call_args = {
            "arguments": arguments,
            "tooluniverse": self.tooluniverse,
            "call_tool": self._call_tool,
        }

        # Add optional parameters if the function accepts them
        if "stream_callback" in params:
            call_args["stream_callback"] = stream_callback
        if "emit_event" in params:
            call_args["emit_event"] = self._create_event_emitter(stream_callback)
        if "memory_manager" in params:
            call_args["memory_manager"] = memory_manager

        # Call with only the parameters the function expects
        return compose_func(**{k: v for k, v in call_args.items() if k in params})

    def _execute_inline_code(self, arguments, stream_callback=None):
        """
        Execute inline composition code (existing behavior).

        Args:
            arguments (dict): Input arguments
            stream_callback (callable, optional): Callback function for streaming output

        Returns
            Any: Result from the composition execution
        """
        # Initialize execution context
        context = {
            "arguments": arguments,
            "tooluniverse": self.tooluniverse,
            "call_tool": self._call_tool,
            "json": json,
            "copy": copy,
            "result": None,  # The code should set this variable
        }

        # Execute the composition code
        exec_globals = {"__builtins__": __builtins__, **context}

        exec(self.composition_code, exec_globals)

        # Return the result variable set by the code
        return exec_globals.get(
            "result", {"error": "No result variable set in composition code"}
        )

    def _call_tool(self, tool_name, arguments):
        """
        Helper function to call other tools from within composition code.

        Args:
            tool_name (str): Name of the tool to call
            arguments (dict): Arguments to pass to the tool

        Returns
            Any: Result from the tool execution
        """
        # Check if tool is available (check both callable_functions and all_tool_dict)
        if (
            tool_name not in self.tooluniverse.callable_functions
            and tool_name not in self.tooluniverse.all_tool_dict
        ):
            if self.auto_load_dependencies:
                # Try to load the tool
                missing_tools = {tool_name}
                successfully_loaded, still_missing = self._load_missing_dependencies(
                    missing_tools
                )

                if (
                    tool_name in still_missing
                    and tool_name not in self.tooluniverse.all_tool_dict
                ):
                    return f"Invalid function call: Function name {tool_name} not found in loaded tools."
            else:
                return f"Invalid function call: Function name {tool_name} not found in loaded tools."

        function_call = {"name": tool_name, "arguments": arguments}

        result = self.tooluniverse.run_one_function(function_call)

        # Ensure consistent result format for backward compatibility
        if isinstance(result, str):
            # If result is a string, it might be an error message or JSON string
            try:
                import json

                parsed_result = json.loads(result)
                if isinstance(parsed_result, dict):
                    return parsed_result
                else:
                    return {"result": parsed_result}
            except (json.JSONDecodeError, TypeError):
                # If it's not JSON, treat as normal string result
                return {"result": result}
        elif isinstance(result, dict):
            return result
        else:
            # For other types, wrap in a standard format
            return {"result": result}
