"""
Tool Defaults Configuration

This module provides structured default configurations for tool metadata,
including MCP annotations and future extensible fields.

Design Principles:
- Python code for efficiency (no runtime file I/O)
- Structured dataclass for type safety and extensibility
- Multi-level override system (default → type → category → tool)
- Same level as default_config.py in the module hierarchy
"""

from dataclasses import dataclass, field
from typing import Dict, Optional
import os

# =============================================================================
# MCP Tool Annotations Defaults
# =============================================================================


@dataclass
class ToolAnnotations:
    """
    Tool annotation values for MCP protocol.

    Attributes
    ----------
    readOnlyHint : bool
        Whether the tool only reads data (default: True for database queries)
    destructiveHint : bool
        Whether the tool may modify/delete data (default: False)
    """

    readOnlyHint: bool = True
    destructiveHint: bool = False
    # Future extensibility:
    # idempotentHint: bool = True
    # openWorldHint: bool = False


# =============================================================================
# Tool Defaults Configuration
# =============================================================================


@dataclass
class ToolDefaultsConfig:
    """
    Structured configuration for tool defaults.

    Supports multi-level overrides:
    1. default_annotations: Base defaults for all tools
    2. tool_type_overrides: Override by tool class type (e.g., "AgenticTool")
    3. category_overrides: Override by tool category (e.g., "agents")

    Tool-specific overrides are handled via tool_config fields.
    """

    # Default annotations for all tools
    default_annotations: ToolAnnotations = field(default_factory=ToolAnnotations)

    # Override by tool type (e.g., "AgenticTool", "ComposeTool", "PackageTool")
    tool_type_overrides: Dict[str, ToolAnnotations] = field(default_factory=dict)

    # Override by category (e.g., "agents", "compose")
    category_overrides: Dict[str, ToolAnnotations] = field(default_factory=dict)


# =============================================================================
# Global Configuration Instance
# =============================================================================

TOOL_DEFAULTS = ToolDefaultsConfig(
    # Base defaults: most tools are read-only database queries
    default_annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False),
    # Tool type overrides
    tool_type_overrides={
        "ComposeTool": ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=False,  # Composition tools may modify state
        ),
        "PythonCodeExecutor": ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=True,  # Code execution may have side effects
        ),
    },
    # Category overrides
    category_overrides={
        "compose": ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=False,
        ),
        "python_executor": ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=True,
        ),
    },
)


# =============================================================================
# Public API Functions
# =============================================================================


def get_tool_defaults() -> ToolDefaultsConfig:
    """
    Get the tool defaults configuration.

    Returns
    -------
    ToolDefaultsConfig
        Structured configuration with defaults and overrides
    """
    return TOOL_DEFAULTS


def get_default_annotations() -> Dict[str, bool]:
    """
    Get default tool annotations as a dictionary.

    Returns
    -------
    dict
        Dictionary with readOnlyHint and destructiveHint
    """
    default = TOOL_DEFAULTS.default_annotations
    return {
        "readOnlyHint": default.readOnlyHint,
        "destructiveHint": default.destructiveHint,
    }


def get_annotations_for_tool(
    tool_type: Optional[str] = None,
    category: Optional[str] = None,
    tool_config: Optional[Dict] = None,
    update_config: bool = False,
) -> Dict[str, bool]:
    """
    Get annotations for a specific tool with multi-level override support.

    If tool_config is provided, tool_type and category will be automatically
    extracted from it if not explicitly provided. Category will also be derived
    from source_file if not present.

    Override priority (highest to lowest):
    1. tool_config.mcp_annotations or tool_config.readOnlyHint/destructiveHint
    2. category_overrides[category]
    3. tool_type_overrides[tool_type]
    4. default_annotations

    Parameters
    ----------
    tool_type : str, optional
        Tool class type (e.g., "AgenticTool"). If None and tool_config provided,
        will be extracted from tool_config["type"]
    category : str, optional
        Tool category (e.g., "agents"). If None and tool_config provided,
        will be derived from tool_config
    tool_config : dict, optional
        Tool configuration with potential overrides. If provided, tool_type and
        category will be auto-extracted if not explicitly provided.
    update_config : bool, default False
        If True and tool_config is provided, will update tool_config["mcp_annotations"]
        in-place with the computed annotations.

    Returns
    -------
    dict
        Dictionary with readOnlyHint and destructiveHint
    """
    config = TOOL_DEFAULTS

    # Auto-extract from tool_config if provided
    if tool_config:
        if tool_type is None:
            tool_type = tool_config.get("type")
        if category is None:
            category = tool_config.get("category") or _derive_category_from_config(
                tool_config
            )

    # Start with defaults
    annotations = {
        "readOnlyHint": config.default_annotations.readOnlyHint,
        "destructiveHint": config.default_annotations.destructiveHint,
    }

    # Apply tool type override
    if tool_type and tool_type in config.tool_type_overrides:
        override = config.tool_type_overrides[tool_type]
        annotations["readOnlyHint"] = override.readOnlyHint
        annotations["destructiveHint"] = override.destructiveHint

    # Apply category override (higher priority than type)
    if category and category in config.category_overrides:
        override = config.category_overrides[category]
        annotations["readOnlyHint"] = override.readOnlyHint
        annotations["destructiveHint"] = override.destructiveHint

    # Apply tool-specific override (highest priority)
    if tool_config:
        if "mcp_annotations" in tool_config:
            tool_override = tool_config["mcp_annotations"]
            if "readOnlyHint" in tool_override:
                annotations["readOnlyHint"] = tool_override["readOnlyHint"]
            if "destructiveHint" in tool_override:
                annotations["destructiveHint"] = tool_override["destructiveHint"]

        # Also support top-level fields
        if "readOnlyHint" in tool_config:
            annotations["readOnlyHint"] = tool_config["readOnlyHint"]
        if "destructiveHint" in tool_config:
            annotations["destructiveHint"] = tool_config["destructiveHint"]

    # Update config if requested
    if update_config and tool_config:
        tool_config["mcp_annotations"] = annotations

    return annotations


def _derive_category_from_config(tool_config: Dict) -> Optional[str]:
    """
    Derive category from tool config by looking up in default_config.

    Since tools are only loaded if they exist in default_config.default_tool_files,
    we can directly look up the category from there by matching the source_file path.

    Parameters
    ----------
    tool_config : dict
        Tool configuration dictionary

    Returns
    -------
    str or None
        Category name if found in default_config, None otherwise
    """
    # First check explicit category in config
    category = tool_config.get("category")
    if category:
        return category

    # Look up category from default_config.default_tool_files
    source_file = tool_config.get("source_file", "")
    if source_file:
        from .default_config import default_tool_files

        # Normalize the source_file path for comparison
        source_file_normalized = os.path.normpath(source_file)

        # Search for matching file path in default_tool_files
        for cat_name, file_path in default_tool_files.items():
            file_path_normalized = os.path.normpath(file_path)
            # Match by full path or just filename
            if source_file_normalized == file_path_normalized or os.path.basename(
                source_file_normalized
            ) == os.path.basename(file_path_normalized):
                return cat_name

    return None


def add_annotations_to_tool_config(tool_config: Dict) -> Dict:
    """
    Add MCP annotations to a tool config in-place.

    This is a convenience wrapper around get_annotations_for_tool with update_config=True.

    Parameters
    ----------
    tool_config : dict
        Tool configuration dictionary (will be modified in-place)

    Returns
    -------
    dict
        The same tool_config dictionary with annotations added
    """
    get_annotations_for_tool(tool_config=tool_config, update_config=True)
    return tool_config
