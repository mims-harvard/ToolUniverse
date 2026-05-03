"""
Extended Hook Types for ToolUniverse

This module demonstrates how to extend the hook system with additional
hook types beyond summarization. It shows the pattern for creating
new hook types while maintaining compatibility with the existing system.
"""

import re
import json
from typing import Dict, Any, List
from .output_hook import OutputHook


class FilteringHook(OutputHook):
    """
    Hook for filtering sensitive or unwanted content from tool outputs.

    This hook can be used to:
    - Remove sensitive information (emails, phones, SSNs)
    - Filter inappropriate content
    - Sanitize data before display

    Args:
        config (Dict[str, Any]): Hook configuration containing filter settings
        tooluniverse: Optional ToolUniverse instance (not used for filtering)
    """

    def __init__(self, config: Dict[str, Any], tooluniverse=None):
        """
        Initialize the filtering hook with configuration.

        Args:
            config (Dict[str, Any]): Hook configuration
            tooluniverse: ToolUniverse instance (optional, not used)
        """
        super().__init__(config)
        hook_config = config.get("hook_config", {})

        # Filter configuration
        self.filter_patterns = hook_config.get("filter_patterns", [])
        self.replacement_text = hook_config.get("replacement_text", "[REDACTED]")
        self.preserve_structure = hook_config.get("preserve_structure", True)
        self.log_filtered_items = hook_config.get("log_filtered_items", False)

        # Compile regex patterns for efficiency
        self.compiled_patterns = []
        for pattern in self.filter_patterns:
            try:
                compiled = re.compile(pattern, re.IGNORECASE)
                self.compiled_patterns.append(compiled)
            except re.error as e:
                print(f"Warning: Invalid regex pattern '{pattern}': {e}")

    def process(
        self,
        result: Any,
        tool_name: str,
        arguments: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        """
        Apply filtering to the tool output.

        Args:
            result (Any): The tool output to filter
            tool_name (str): Name of the tool that produced the output
            arguments (Dict[str, Any]): Arguments passed to the tool
            context (Dict[str, Any]): Additional context information

        Returns
            Any: The filtered output, or original output if filtering fails
        """
        try:
            if not self.compiled_patterns:
                return result

            output_str = result if isinstance(result, str) else str(result)
            filtered_output = output_str
            filtered_count = 0

            # Apply each filter pattern
            for pattern in self.compiled_patterns:
                matches = pattern.findall(filtered_output)
                if matches:
                    filtered_count += len(matches)
                    if self.log_filtered_items:
                        print(
                            f"🔒 Filtered {len(matches)} items matching pattern: {pattern.pattern}"
                        )

                    filtered_output = pattern.sub(
                        self.replacement_text, filtered_output
                    )

            if filtered_count > 0:
                print(
                    f"🔒 FilteringHook: Filtered {filtered_count} sensitive items from {tool_name} output"
                )

            return filtered_output

        except Exception as e:
            print(f"Error in filtering hook: {str(e)}")
            return result


class FormattingHook(OutputHook):
    """
    Hook for formatting and beautifying tool outputs.

    This hook can be used to:
    - Pretty-print JSON/XML outputs
    - Format text with proper indentation
    - Standardize output formats

    Args:
        config (Dict[str, Any]): Hook configuration containing formatting settings
        tooluniverse: Optional ToolUniverse instance (not used for formatting)
    """

    def __init__(self, config: Dict[str, Any], tooluniverse=None):
        """
        Initialize the formatting hook with configuration.

        Args:
            config (Dict[str, Any]): Hook configuration
            tooluniverse: ToolUniverse instance (optional, not used)
        """
        super().__init__(config)
        hook_config = config.get("hook_config", {})

        # Formatting configuration
        self.indent_size = hook_config.get("indent_size", 2)
        self.sort_keys = hook_config.get("sort_keys", True)
        self.ensure_ascii = hook_config.get("ensure_ascii", False)
        self.max_line_length = hook_config.get("max_line_length", 100)
        self.pretty_print = hook_config.get("pretty_print", True)

    def process(
        self,
        result: Any,
        tool_name: str,
        arguments: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        """
        Apply formatting to the tool output.

        Args:
            result (Any): The tool output to format
            tool_name (str): Name of the tool that produced the output
            arguments (Dict[str, Any]): Arguments passed to the tool
            context (Dict[str, Any]): Additional context information

        Returns
            Any: The formatted output, or original output if formatting fails
        """
        try:
            if isinstance(result, dict):
                return self._format_json(result)
            elif isinstance(result, str):
                return self._format_text(result)
            elif isinstance(result, list):
                return self._format_list(result)
            else:
                return result

        except Exception as e:
            print(f"Error in formatting hook: {str(e)}")
            return result

    def _format_json(self, data: Dict[str, Any]) -> str:
        """Format JSON data with pretty printing."""
        if self.pretty_print:
            return json.dumps(
                data,
                indent=self.indent_size,
                sort_keys=self.sort_keys,
                ensure_ascii=self.ensure_ascii,
            )
        return json.dumps(data, ensure_ascii=self.ensure_ascii)

    def _format_text(self, text: str) -> str:
        """Format plain text with line wrapping."""
        if len(text) <= self.max_line_length:
            return text

        # Simple line wrapping
        lines = []
        current_line = ""

        for word in text.split():
            if len(current_line + " " + word) <= self.max_line_length:
                current_line += (" " + word) if current_line else word
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word

        if current_line:
            lines.append(current_line)

        return "\n".join(lines)

    def _format_list(self, data: List[Any]) -> str:
        """Format list data."""
        if self.pretty_print:
            formatted_items = []
            for i, item in enumerate(data):
                if isinstance(item, dict):
                    formatted_items.append(f"{i + 1}. {self._format_json(item)}")
                else:
                    formatted_items.append(f"{i + 1}. {str(item)}")
            return "\n".join(formatted_items)
        return str(data)


class ValidationHook(OutputHook):
    """
    Hook for validating tool outputs against schemas or rules.

    This hook can be used to:
    - Validate JSON against schemas
    - Check required fields
    - Ensure data quality

    Args:
        config (Dict[str, Any]): Hook configuration containing validation settings
        tooluniverse: Optional ToolUniverse instance (not used for validation)
    """

    def __init__(self, config: Dict[str, Any], tooluniverse=None):
        """
        Initialize the validation hook with configuration.

        Args:
            config (Dict[str, Any]): Hook configuration
            tooluniverse: ToolUniverse instance (optional, not used)
        """
        super().__init__(config)
        hook_config = config.get("hook_config", {})

        # Validation configuration
        self.validation_schema = hook_config.get("validation_schema", None)
        self.strict_mode = hook_config.get("strict_mode", True)
        self.error_action = hook_config.get("error_action", "warn")  # warn, fix, fail
        self.required_fields = hook_config.get("required_fields", [])

    def process(
        self,
        result: Any,
        tool_name: str,
        arguments: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        """
        Apply validation to the tool output.

        Args:
            result (Any): The tool output to validate
            tool_name (str): Name of the tool that produced the output
            arguments (Dict[str, Any]): Arguments passed to the tool
            context (Dict[str, Any]): Additional context information

        Returns
            Any: The validated output, or original output if validation fails
        """
        try:
            validation_result = self._validate_output(result)

            if validation_result["valid"]:
                if validation_result["warnings"]:
                    print(
                        f"✅ ValidationHook: {tool_name} output validated with warnings"
                    )
                else:
                    print(
                        f"✅ ValidationHook: {tool_name} output validated successfully"
                    )
                return result
            else:
                if self.error_action == "fail":
                    print(f"❌ ValidationHook: {tool_name} output validation failed")
                    return result
                elif self.error_action == "fix":
                    fixed_result = self._fix_output(result, validation_result["errors"])
                    print(
                        f"🔧 ValidationHook: Fixed {tool_name} output based on validation errors"
                    )
                    return fixed_result
                else:  # warn
                    print(f"⚠️ ValidationHook: {tool_name} output has validation issues")
                    return result

        except Exception as e:
            print(f"Error in validation hook: {str(e)}")
            return result

    def _validate_output(self, result: Any) -> Dict[str, Any]:
        """Validate the output against configured rules."""
        validation_result = {"valid": True, "errors": [], "warnings": []}

        # Check required fields for dict outputs
        if isinstance(result, dict) and self.required_fields:
            for field in self.required_fields:
                if field not in result:
                    validation_result["errors"].append(
                        f"Missing required field: {field}"
                    )
                    validation_result["valid"] = False

        # Add schema validation here if needed
        # This would integrate with jsonschema or similar libraries

        return validation_result

    def _fix_output(self, result: Any, errors: List[str]) -> Any:
        """Attempt to fix validation errors."""
        # Simple fixes for common issues
        if isinstance(result, dict):
            fixed_result = result.copy()

            for error in errors:
                if "Missing required field" in error:
                    field_name = error.split(": ")[1]
                    fixed_result[field_name] = None  # Add missing field with None value

            return fixed_result

        return result


class LoggingHook(OutputHook):
    """
    Hook for logging tool outputs and execution details.

    This hook can be used to:
    - Log all tool outputs
    - Track execution metrics
    - Audit tool usage

    Args:
        config (Dict[str, Any]): Hook configuration containing logging settings
        tooluniverse: Optional ToolUniverse instance (not used for logging)
    """

    def __init__(self, config: Dict[str, Any], tooluniverse=None):
        """
        Initialize the logging hook with configuration.

        Args:
            config (Dict[str, Any]): Hook configuration
            tooluniverse: ToolUniverse instance (optional, not used)
        """
        super().__init__(config)
        hook_config = config.get("hook_config", {})

        # Logging configuration
        self.log_level = hook_config.get("log_level", "INFO")
        self.log_format = hook_config.get(
            "log_format", "detailed"
        )  # simple, detailed, json
        self.log_file = hook_config.get("log_file", None)
        self.max_log_size = hook_config.get("max_log_size", 1000)  # characters

    def process(
        self,
        result: Any,
        tool_name: str,
        arguments: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        """
        Log the tool output and execution details.

        Args:
            result (Any): The tool output to log
            tool_name (str): Name of the tool that produced the output
            arguments (Dict[str, Any]): Arguments passed to the tool
            context (Dict[str, Any]): Additional context information

        Returns
            Any: The original output (logging doesn't modify the output)
        """
        try:
            log_entry = self._create_log_entry(result, tool_name, arguments, context)
            self._write_log(log_entry)

        except Exception as e:
            print(f"Error in logging hook: {str(e)}")

        # Logging hook always returns the original result unchanged
        return result

    def _create_log_entry(
        self,
        result: Any,
        tool_name: str,
        arguments: Dict[str, Any],
        context: Dict[str, Any],
    ) -> str:
        """Create a log entry for the tool execution."""
        if self.log_format == "simple":
            return f"Tool: {tool_name} | Args: {arguments} | Output length: {len(str(result))}"
        elif self.log_format == "json":
            return json.dumps(
                {
                    "tool_name": tool_name,
                    "arguments": arguments,
                    "output_length": len(str(result)),
                    "timestamp": context.get("execution_time", "unknown"),
                    "output_preview": str(result)[: self.max_log_size],
                }
            )
        else:  # detailed
            return f"""
Tool Execution Log:
==================
Tool: {tool_name}
Arguments: {arguments}
Execution Time: {context.get("execution_time", "unknown")}
Output Length: {len(str(result))} characters
Output Preview: {str(result)[: self.max_log_size]}{"..." if len(str(result)) > self.max_log_size else ""}
==================
"""

    def _write_log(self, log_entry: str):
        """Write the log entry to the configured destination."""
        if self.log_file:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(log_entry + "\n")
        else:
            print(f"📝 Log: {log_entry}")


# Hook type registry for easy extension
HOOK_TYPE_REGISTRY = {
    "SummarizationHook": "SummarizationHook",  # Import from parent module
    "FilteringHook": FilteringHook,
    "FormattingHook": FormattingHook,
    "ValidationHook": ValidationHook,
    "LoggingHook": LoggingHook,
}
