"""
Tool Discovery Tools - Standard ToolUniverse tools for discovering and
exploring available tools.

These tools provide efficient ways to discover, list, and explore tools
while minimizing context window usage through progressive disclosure.

Key Features:
- Progressive disclosure: Start with minimal info (names), get details
  when needed
- Agent-friendly: Simple text search (no regex required), natural
  language task discovery
- Workflow-oriented: Tools guide agent through discovery process
- Reduced tool calls: Combined search+detail tools minimize overhead

Tool Categories:
1. Listing Tools: list_tools (unified tool with multiple modes)
   - Use for initial exploration and overview
   - Modes: names, basic, categories, by_category, summary, custom
2. Search Tools: grep_tools, find_tools
   - Use for finding relevant tools
3. Definition Tools: get_tool_info
   - Use for getting detailed information about specific tools
   - Supports description or full definition, single or batch

Recommended Workflow:
1. Start with list_tools(mode="names") or list_tools(mode="categories")
2. Use find_tools (for natural language) or grep_tools
   (for keywords) to find relevant tools
3. Use get_tool_info to get full details
4. Execute tools using execute_tool
"""

import json
import re
from .base_tool import BaseTool
from .tool_registry import register_tool


def _get_tool_category(tool, tool_name, tooluniverse):
    """
    Get the category for a tool, looking it up from tool_category_dicts if not in tool config.

    Args:
        tool: Tool configuration dict
        tool_name: Name of the tool
        tooluniverse: ToolUniverse instance with tool_category_dicts

    Returns:
        str: Category name, or "unknown" if not found
    """
    # First check if category is in tool config
    if isinstance(tool, dict) and "category" in tool:
        category = tool.get("category")
        if category and category != "unknown":
            return category

    # If not found, look up in tool_category_dicts
    if tooluniverse and hasattr(tooluniverse, "tool_category_dicts"):
        for cat_name, tools_in_cat in tooluniverse.tool_category_dicts.items():
            # tools_in_cat can be a list of tool dicts or tool names
            if isinstance(tools_in_cat, list):
                for item in tools_in_cat:
                    if isinstance(item, dict):
                        if item.get("name") == tool_name:
                            return cat_name
                    elif isinstance(item, str):
                        if item == tool_name:
                            return cat_name

    return "unknown"


@register_tool("GrepTools")
class GrepToolsTool(BaseTool):
    """Native grep-like pattern search for tools (simple regex, independent
    from Tool_Finder_Keyword)."""

    def __init__(self, tool_config, tooluniverse=None):
        super().__init__(tool_config)
        self.tooluniverse = tooluniverse

    def run(self, arguments):
        """
        Search tools using simple text matching or regex pattern matching.

        Args:
            arguments (dict): Dictionary containing:
                - pattern (str): Search pattern (text or regex)
                - field (str, optional): Field to search in: "name",
                  "description", "type", "category" (default: "name")
                - search_mode (str, optional): "text" for simple text
                  matching or "regex" for regex (default: "text")
                - categories (list, optional): Optional category filter

        Returns:
            dict: Dictionary with matching tools (name + description)
        """
        if not self.tooluniverse or not hasattr(self.tooluniverse, "all_tool_dict"):
            return {"status": "error", "error": "ToolUniverse not available"}

        pattern = arguments.get("pattern", "")
        field = arguments.get("field", "name")
        # 'text' or 'regex'
        search_mode = arguments.get("search_mode", "text")
        limit = arguments.get("limit", 100)
        offset = arguments.get("offset", 0)
        categories = arguments.get("categories")

        if not pattern:
            return {"status": "error", "error": "pattern parameter is required"}

        matching_tools = []
        for tool_name, tool in self.tooluniverse.all_tool_dict.items():
            # Filter by categories if provided
            if categories:
                tool_category = _get_tool_category(tool, tool_name, self.tooluniverse)
                if tool_category not in categories:
                    continue

            # Search in specified field
            search_text = ""
            if field == "name":
                search_text = tool.get("name", "")
            elif field == "description":
                search_text = tool.get("description", "")
            elif field == "type":
                search_text = tool.get("type", "")
            elif field == "category":
                search_text = _get_tool_category(tool, tool_name, self.tooluniverse)

            # Perform search based on mode
            if search_text:
                matched = False
                if search_mode == "text":
                    # Simple case-insensitive text matching
                    matched = pattern.lower() in search_text.lower()
                elif search_mode == "regex":
                    # Regex pattern matching — case-sensitive by default
                    try:
                        regex = re.compile(pattern)
                        matched = regex.search(search_text)
                    except re.error as e:
                        return {
                            "status": "error",
                            "error": f"Invalid regex pattern: {str(e)}",
                        }
                else:
                    return {
                        "status": "error",
                        "error": (
                            f"Invalid search_mode: {search_mode}. "
                            "Must be 'text' or 'regex'"
                        ),
                    }

                if matched:
                    # tool_name is already shortened (primary identifier)
                    matching_tools.append(
                        {
                            "name": tool_name,
                            "category": _get_tool_category(
                                tool, tool_name, self.tooluniverse
                            ),
                            "type": tool.get("type", "Unknown"),
                            "description": tool.get("description", ""),
                        }
                    )

        # Apply pagination
        total_matches = len(matching_tools)
        if offset > 0 or limit is not None:
            matching_tools = (
                matching_tools[offset : offset + limit]
                if limit is not None
                else matching_tools[offset:]
            )

        has_more = (
            total_matches > 0
            if limit == 0
            else (limit is not None and (offset + len(matching_tools)) < total_matches)
        )
        return {
            "total_matches": total_matches,
            "limit": limit,
            "offset": offset,
            # Feature-R18A-10: limit=0 is a count-probe; has_more should reflect whether
            # there ARE more results (consistent with find_tools behavior).
            # has_more: true at limit=0 correctly signals "there is data if you raise limit".
            "has_more": has_more,
            # Feature-R19A-02: include next_offset so pipelines don't have to recompute
            # offset+len(tools). Feature-23A-02: when limit=0 (count probe) and has_more=True,
            # set next_offset=0 so callers can pass it directly as --offset.
            "next_offset": (offset + len(matching_tools))
            if (has_more and limit != 0)
            else (0 if has_more else None),
            "pattern": pattern,
            "field": field,
            "search_mode": search_mode,
            "tools": matching_tools,
        }


@register_tool("ListTools")
class ListToolsTool(BaseTool):
    """Unified tool listing with multiple modes.

    Note: Defaults to mode='names' to avoid huge outputs when many tools are loaded.
    For getting tool descriptions or detailed information, use the 'get_tool_info' tool instead
    (supports single or batch queries), as modes like 'basic'/'summary' can return
    very large payloads.
    """

    def __init__(self, tool_config, tooluniverse=None):
        super().__init__(tool_config)
        self.tooluniverse = tooluniverse

    def run(self, arguments):
        """
        List tools with configurable output format via mode parameter.

        Args:
            arguments (dict): Dictionary containing:
                - mode (str, optional, default="names"): Output mode
                  - "names": Return only tool names (default, recommended for large tool sets)
                  - "basic": Return name + description (warning: can return very large payloads)
                  - "categories": Return category statistics
                  - "by_category": Return tools grouped by category
                  - "summary": Return name + description + type + has_parameters
                    (warning: can return very large payloads)
                  - "custom": Return user-specified fields
                Note: For getting tool descriptions, use 'get_tool_info' tool instead of
                'basic'/'summary' modes to avoid large payloads.
                - categories (list, optional): Filter by categories
                - fields (list, required for mode="custom"): Fields to include
                - group_by_category (bool, optional): Group by category
                  (mode="names"|"basic"|"summary")
                - brief (bool, optional): Truncate description
                  (mode="basic"|"summary")

        Returns:
            dict: Dictionary with tools in requested format
        """
        if not self.tooluniverse or not hasattr(self.tooluniverse, "all_tool_dict"):
            return {"status": "error", "error": "ToolUniverse not available"}

        mode = arguments.get("mode")
        if not mode:
            mode = "names"

        valid_modes = [
            "names",
            "basic",
            "categories",
            "by_category",
            "summary",
            "custom",
        ]
        if mode not in valid_modes:
            return {
                "status": "error",
                "error": (
                    f"Invalid mode: {mode}. Must be one of: {', '.join(valid_modes)}"
                ),
            }

        categories = arguments.get("categories")
        group_by_category = arguments.get("group_by_category", False)
        brief = arguments.get("brief", False)
        limit = arguments.get("limit")
        offset = arguments.get("offset", 0)

        # Get all tools and filter by categories if provided
        tools = list(self.tooluniverse.all_tool_dict.items())  # Get (name, tool) pairs
        if categories:
            tools = [
                (tool_name, tool)
                for tool_name, tool in tools
                if _get_tool_category(tool, tool_name, self.tooluniverse) in categories
            ]

        try:
            if mode == "names":
                # Return only tool names (use shortened/exposed names for MCP compatibility)
                tool_names = []
                for tool_name, tool in tools:
                    if tool_name:
                        # tool_name is already shortened (primary identifier)
                        tool_names.append(tool_name)

                if group_by_category:
                    # Group by category
                    tools_by_category = {}
                    for tool_name, tool in tools:
                        if tool_name:
                            # tool_name is already shortened (primary identifier)
                            category = _get_tool_category(
                                tool, tool_name, self.tooluniverse
                            )
                            if category not in tools_by_category:
                                tools_by_category[category] = []
                            tools_by_category[category].append(tool_name)

                    # Feature-R10A-02: capture true total BEFORE per-category pagination
                    true_total = sum(len(names) for names in tools_by_category.values())
                    # Feature-22A-07: has_more is True when limit truncates at least one category.
                    _by_cat_has_more = limit is not None and any(
                        len(names) > offset + limit
                        for names in tools_by_category.values()
                    )

                    # Apply pagination to each category if needed
                    if limit is not None or offset > 0:
                        paginated_by_category = {}
                        for cat, names in tools_by_category.items():
                            if offset > 0 or limit is not None:
                                paginated_by_category[cat] = (
                                    names[offset : offset + limit]
                                    if limit is not None
                                    else names[offset:]
                                )
                            else:
                                paginated_by_category[cat] = names
                        tools_by_category = paginated_by_category

                    return {
                        "tools_by_category": tools_by_category,
                        "total_tools": true_total,
                        "limit": limit,
                        "offset": offset,
                        "has_more": _by_cat_has_more,
                    }
                else:
                    # Apply pagination
                    total_count = len(tool_names)
                    if offset > 0 or limit is not None:
                        tool_names = (
                            tool_names[offset : offset + limit]
                            if limit is not None
                            else tool_names[offset:]
                        )

                    # Simple list of names
                    _has_more_names = (
                        total_count > offset
                        if limit == 0
                        else (
                            limit is not None
                            and (offset + len(tool_names)) < total_count
                        )
                    )
                    return {
                        "total_tools": total_count,
                        "limit": limit,
                        "offset": offset,
                        # Feature-R19B-05: limit=0 is a count-probe; has_more should reflect
                        # whether data exists (consistent with grep/find behavior).
                        "has_more": _has_more_names,
                        # Feature-R19A-02: include next_offset for pipeline convenience.
                        # Feature-23A-02: when limit=0 (count probe) and has_more=True,
                        # set next_offset=0 so callers can pass it as --offset.
                        "next_offset": (offset + len(tool_names))
                        if (_has_more_names and limit != 0)
                        else (0 if _has_more_names else None),
                        "tools": tool_names,
                    }

            elif mode == "basic":
                # Return name + description
                tools_info = []
                for tool_name, tool in tools:
                    if tool_name:
                        # Use exposed name from tool config (already shortened during loading)
                        # tool_name is already shortened (primary identifier)
                        description = tool.get("description", "")
                        if brief and len(description) > 100:
                            # Truncate to first sentence or 100 chars
                            sentence_end = description.find(". ")
                            if sentence_end > 0 and sentence_end <= 100:
                                description = description[: sentence_end + 1]
                            else:
                                description = description[:100] + "..."

                        tool_info = {"name": tool_name, "description": description}
                        tools_info.append(tool_info)

                if group_by_category:
                    # Group by category
                    tools_by_category = {}
                    for tool_info in tools_info:
                        tool_name = tool_info["name"]
                        tool = self.tooluniverse.all_tool_dict.get(tool_name)
                        if tool:
                            category = _get_tool_category(
                                tool, tool_name, self.tooluniverse
                            )
                            if category not in tools_by_category:
                                tools_by_category[category] = []
                            tools_by_category[category].append(tool_info)

                    # Feature-R10A-02: capture true total BEFORE per-category pagination
                    true_total = sum(len(infos) for infos in tools_by_category.values())
                    # Feature-22A-07: reflect per-category truncation in has_more.
                    _by_cat_has_more = limit is not None and any(
                        len(infos) > offset + limit
                        for infos in tools_by_category.values()
                    )

                    # Apply pagination to each category if needed
                    if limit is not None or offset > 0:
                        paginated_by_category = {}
                        for cat, infos in tools_by_category.items():
                            if offset > 0 or limit is not None:
                                paginated_by_category[cat] = (
                                    infos[offset : offset + limit]
                                    if limit is not None
                                    else infos[offset:]
                                )
                            else:
                                paginated_by_category[cat] = infos
                        tools_by_category = paginated_by_category

                    return {
                        "tools_by_category": tools_by_category,
                        "total_tools": true_total,
                        "limit": limit,
                        "offset": offset,
                        "has_more": _by_cat_has_more,
                    }
                else:
                    # Apply pagination
                    total_count = len(tools_info)
                    if offset > 0 or limit is not None:
                        tools_info = (
                            tools_info[offset : offset + limit]
                            if limit is not None
                            else tools_info[offset:]
                        )

                    _has_more_basic = (
                        total_count > offset
                        if limit == 0
                        else (
                            limit is not None
                            and (offset + len(tools_info)) < total_count
                        )
                    )
                    return {
                        "total_tools": total_count,
                        "limit": limit,
                        "offset": offset,
                        "has_more": _has_more_basic,
                        # R21A-03: next_offset for pipeline convenience (None at limit=0)
                        "next_offset": (offset + len(tools_info))
                        if (_has_more_basic and limit != 0)
                        else None,
                        "tools": tools_info,
                    }

            elif mode == "categories":
                # Return category statistics
                category_counts = {}
                for tool_name, tool in tools:
                    category = _get_tool_category(tool, tool_name, self.tooluniverse)
                    category_counts[category] = category_counts.get(category, 0) + 1
                # Feature-R12A-09/R12B-04: include summary metadata for machine consumers
                return {
                    "total_categories": len(category_counts),
                    "total_tools": sum(category_counts.values()),
                    "categories": category_counts,
                }

            elif mode == "by_category":
                # Return tools grouped by category (names only)
                tools_by_category = {}
                for tool_name, tool in tools:
                    if tool_name:
                        category = _get_tool_category(
                            tool, tool_name, self.tooluniverse
                        )
                        if category not in tools_by_category:
                            tools_by_category[category] = []
                        tools_by_category[category].append(tool_name)

                # Feature-R10A-02: capture true total BEFORE per-category pagination
                true_total = sum(len(names) for names in tools_by_category.values())
                # Feature-22A-07: has_more is True when limit truncates at least one category.
                _by_cat_has_more = limit is not None and any(
                    len(names) > offset + limit for names in tools_by_category.values()
                )

                # Apply pagination to each category if needed
                if limit is not None or offset > 0:
                    paginated_by_category = {}
                    for cat, names in tools_by_category.items():
                        if offset > 0 or limit is not None:
                            paginated_by_category[cat] = (
                                names[offset : offset + limit]
                                if limit is not None
                                else names[offset:]
                            )
                        else:
                            paginated_by_category[cat] = names
                    tools_by_category = paginated_by_category

                return {
                    "tools_by_category": tools_by_category,
                    "total_tools": true_total,
                    # Feature-R12A-02: clarify that limit/offset apply per-category
                    "per_category_limit": limit,
                    "per_category_offset": offset,
                    "limit": limit,
                    "offset": offset,
                    "has_more": _by_cat_has_more,
                }

            elif mode == "summary":
                # Return name + description + type + has_parameters
                tools_info = []
                for tool_name, tool in tools:
                    if tool_name:
                        # tool_name is already shortened (primary identifier)
                        description = tool.get("description", "")
                        if brief and len(description) > 100:
                            sentence_end = description.find(". ")
                            if sentence_end > 0 and sentence_end <= 100:
                                description = description[: sentence_end + 1]
                            else:
                                description = description[:100] + "..."

                        tool_info = {
                            "name": tool_name,
                            "description": description,
                            "type": tool.get("type", "Unknown"),
                            "has_parameters": bool(tool.get("parameter")),
                        }
                        tools_info.append(tool_info)

                if group_by_category:
                    # Group by category
                    tools_by_category = {}
                    for tool_info in tools_info:
                        tool_name = tool_info["name"]
                        tool = self.tooluniverse.all_tool_dict.get(tool_name)
                        if tool:
                            category = _get_tool_category(
                                tool, tool_name, self.tooluniverse
                            )
                            if category not in tools_by_category:
                                tools_by_category[category] = []
                            tools_by_category[category].append(tool_info)

                    # Feature-R10A-02: capture true total BEFORE per-category pagination
                    true_total = sum(len(infos) for infos in tools_by_category.values())
                    # Feature-22A-07: reflect per-category truncation in has_more.
                    _by_cat_has_more = limit is not None and any(
                        len(infos) > offset + limit
                        for infos in tools_by_category.values()
                    )

                    # Apply pagination to each category if needed
                    if limit is not None or offset > 0:
                        paginated_by_category = {}
                        for cat, infos in tools_by_category.items():
                            if offset > 0 or limit is not None:
                                paginated_by_category[cat] = (
                                    infos[offset : offset + limit]
                                    if limit is not None
                                    else infos[offset:]
                                )
                            else:
                                paginated_by_category[cat] = infos
                        tools_by_category = paginated_by_category

                    return {
                        "tools_by_category": tools_by_category,
                        "total_tools": true_total,
                        "limit": limit,
                        "offset": offset,
                        "has_more": _by_cat_has_more,
                    }
                else:
                    # Apply pagination
                    total_count = len(tools_info)
                    if offset > 0 or limit is not None:
                        tools_info = (
                            tools_info[offset : offset + limit]
                            if limit is not None
                            else tools_info[offset:]
                        )

                    _has_more_summary = (
                        total_count > offset
                        if limit == 0
                        else (
                            limit is not None
                            and (offset + len(tools_info)) < total_count
                        )
                    )
                    return {
                        "total_tools": total_count,
                        "limit": limit,
                        "offset": offset,
                        "has_more": _has_more_summary,
                        # R21A-03: next_offset for pipeline convenience (None at limit=0)
                        "next_offset": (offset + len(tools_info))
                        if (_has_more_summary and limit != 0)
                        else None,
                        "tools": tools_info,
                    }

            elif mode == "custom":
                # Return user-specified fields
                fields = arguments.get("fields", [])
                # Feature-R12A-01: normalize comma-separated strings like "name,type" → ["name", "type"]
                if isinstance(fields, str):
                    fields = [f.strip() for f in fields.split(",") if f.strip()]
                elif isinstance(fields, list):
                    normalized = []
                    for f in fields:
                        if isinstance(f, str) and "," in f:
                            normalized.extend(
                                p.strip() for p in f.split(",") if p.strip()
                            )
                        elif isinstance(f, str) and f.strip():
                            normalized.append(f.strip())
                    fields = normalized
                if not fields:
                    return {
                        "status": "error",
                        "error": ("fields parameter is required for mode='custom'"),
                    }

                tools_info = []
                # Feature-22A-09: track which fields are actually found in at least one tool
                _field_found_count = {
                    field: 0 for field in fields if field != "category"
                }
                for tool_name, tool in tools:
                    if tool_name:
                        tool_info = {}
                        for field in fields:
                            if field == "category":
                                # Special handling for category field
                                tool_info[field] = _get_tool_category(
                                    tool, tool_name, self.tooluniverse
                                )
                            elif field in tool:
                                tool_info[field] = tool[field]
                                _field_found_count[field] += 1
                        tools_info.append(tool_info)
                # Feature-22A-09: fields with zero occurrences across all tools are unknown
                _unknown_fields = [
                    f for f, cnt in _field_found_count.items() if cnt == 0
                ]

                # Apply pagination
                total_count = len(tools_info)
                if offset > 0 or limit is not None:
                    tools_info = (
                        tools_info[offset : offset + limit]
                        if limit is not None
                        else tools_info[offset:]
                    )

                _has_more_custom = (
                    total_count > offset
                    if limit == 0
                    else (
                        limit is not None and (offset + len(tools_info)) < total_count
                    )
                )
                return {
                    "total_tools": total_count,
                    "limit": limit,
                    "offset": offset,
                    "has_more": _has_more_custom,
                    # R21A-03: next_offset for pipeline convenience (None at limit=0)
                    "next_offset": (offset + len(tools_info))
                    if (_has_more_custom and limit != 0)
                    else None,
                    "tools": tools_info,
                    # Feature-22A-09: fields that matched no tool attribute at all
                    "unknown_fields": _unknown_fields if _unknown_fields else None,
                }

        except Exception as e:
            error_msg = f"Error listing tools: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return {
                "status": "error",
                "error": error_msg,
                "error_type": type(e).__name__,
            }


@register_tool("GetToolInfo")
class GetToolInfoTool(BaseTool):
    """Get tool information with configurable detail level. Supports single or batch tool queries."""

    def __init__(self, tool_config, tooluniverse=None):
        super().__init__(tool_config)
        self.tooluniverse = tooluniverse

    def run(self, arguments):
        """
        Get tool information with configurable detail level.

        Args:
            arguments (dict): Dictionary containing:
                - tool_names (str | list): Single tool name (string) or list of tool names
                - detail_level (str, optional): "description" or "full". Default: "full"
                  - "description": Returns only the description field (complete, not truncated)
                  - "full": Returns complete tool definition including parameter schema

        Returns:
            dict: Dictionary with tool information
            - Single tool: Direct tool info object
            - Batch tools: {"tools": [...], "total_requested": N, "total_found": M}
        """
        import time

        start_time = time.time()

        if not self.tooluniverse:
            return {"status": "error", "error": "ToolUniverse not available"}

        tool_names = arguments.get("tool_names")
        if not tool_names:
            return {"status": "error", "error": "tool_names parameter is required"}

        detail_level = arguments.get("detail_level", "full")
        if detail_level not in ["description", "full"]:
            return {
                "status": "error",
                "error": (
                    f"Invalid detail_level: {detail_level}. "
                    "Must be 'description' or 'full'"
                ),
            }

        # Normalize tool_names to list
        if isinstance(tool_names, str):
            tool_names = [tool_names]
            is_single = True
        elif isinstance(tool_names, list):
            is_single = False
        else:
            return {"status": "error", "error": "tool_names must be a string or list"}

        try:
            if detail_level == "description":
                # Return only description for each tool
                results = []
                for tool_name in tool_names:
                    tool_config = self.tooluniverse.all_tool_dict.get(tool_name)
                    if not tool_config:
                        # tool_name is already shortened (primary identifier)
                        results.append({"name": tool_name, "error": "not found"})
                    else:
                        # tool_name is already shortened (primary identifier)
                        results.append(
                            {
                                "name": tool_name,
                                "category": _get_tool_category(
                                    tool_config, tool_name, self.tooluniverse
                                ),
                                "description": tool_config.get("description", ""),
                            }
                        )

                # Return single tool directly, or batch format
                if is_single:
                    return results[0]
                else:
                    found_count = sum(1 for r in results if "error" not in r)
                    return {
                        "total_requested": len(tool_names),
                        "total_found": found_count,
                        "tools": results,
                    }

            else:  # detail_level == "full"
                # Use existing methods for full definitions
                if is_single:
                    # Single tool: use tool_specification
                    tool_config = self.tooluniverse.tool_specification(
                        tool_names[0], return_prompt=False
                    )
                    if not tool_config:
                        return {
                            "status": "error",
                            "error": f"Tool '{tool_names[0]}' not found",
                        }
                    return tool_config
                else:
                    # Batch: use get_tool_specification_by_names
                    tools_definitions = (
                        self.tooluniverse.get_tool_specification_by_names(tool_names)
                    )

                    # Handle tools not found
                    found_names = {
                        tool.get("name") for tool in tools_definitions if tool
                    }
                    missing_tools = [
                        {"name": name, "error": "not found"}
                        for name in tool_names
                        if name not in found_names
                    ]

                    # Combine found and missing tools
                    all_tools = tools_definitions + missing_tools

                    return {
                        "total_requested": len(tool_names),
                        "total_found": len(tools_definitions),
                        "tools": all_tools,
                    }

        except Exception as e:
            elapsed = time.time() - start_time
            error_msg = f"Error getting tool info: {str(e)}"
            self.logger.error(f"{error_msg} (elapsed: {elapsed:.2f}s)", exc_info=True)
            return {
                "status": "error",
                "error": error_msg,
                "error_type": type(e).__name__,
                "elapsed_seconds": round(elapsed, 2),
            }
        except KeyboardInterrupt:
            # Handle interruption gracefully
            elapsed = time.time() - start_time
            error_msg = "Tool info retrieval was interrupted"
            self.logger.warning(f"{error_msg} (elapsed: {elapsed:.2f}s)")
            return {
                "status": "error",
                "error": error_msg,
                "error_type": "InterruptedError",
                "elapsed_seconds": round(elapsed, 2),
            }


@register_tool("ExecuteTool")
class ExecuteToolTool(BaseTool):
    """Execute a ToolUniverse tool directly with custom arguments."""

    def __init__(self, tool_config, tooluniverse=None):
        super().__init__(tool_config)
        self.tooluniverse = tooluniverse

    def run(self, arguments):
        """
        Execute a ToolUniverse tool directly with custom arguments.

        Args:
            arguments (dict): Dictionary containing:
                - tool_name (str): Name of the tool to execute
                - arguments (dict|str): Arguments to pass to the tool.
                  Accepts:
                  1) JSON object/dict: {"param1": "value1", "param2": 5}
                  2) JSON string that parses to object:
                     "{\"param1\": \"value1\", \"param2\": 5}"

        Returns:
            dict or str: Tool execution result. If result is already a dict,
                        return as-is. If it's a string (JSON), parse and
                        return as dict.
        """
        if not self.tooluniverse:
            return {"status": "error", "error": "ToolUniverse not available"}

        tool_name = arguments.get("tool_name")
        tool_arguments = arguments.get("arguments")

        # Validate tool_name
        if not tool_name or (isinstance(tool_name, str) and not tool_name.strip()):
            error_msg = "tool_name parameter is required and cannot be empty"
            if hasattr(self, "logger"):
                self.logger.error(f"execute_tool: {error_msg}")
            return {
                "status": "error",
                "error": error_msg,
                "error_type": "ValidationError",
            }

        # Normalize arguments
        if tool_arguments is None:
            parsed_args = {}
        elif isinstance(tool_arguments, dict):
            parsed_args = tool_arguments
        elif isinstance(tool_arguments, str):
            try:
                parsed_args = json.loads(tool_arguments)
            except (json.JSONDecodeError, ValueError):
                error_msg = (
                    "arguments string must be valid JSON that parses to an object. "
                    f"Received: {repr(tool_arguments)[:100]}. "
                    'Example: "{\\"param1\\": \\"value1\\", \\"param2\\": 5}".'
                )
                if hasattr(self, "logger"):
                    self.logger.error(f"{tool_name}: {error_msg}")
                return {
                    "status": "error",
                    "error": error_msg,
                    "error_type": "ValidationError",
                }

            if not isinstance(parsed_args, dict):
                error_msg = (
                    "arguments JSON string must decode to an object (dictionary), "
                    f"got {type(parsed_args).__name__}. "
                    'Example: "{\\"param1\\": \\"value1\\", \\"param2\\": 5}".'
                )
                if hasattr(self, "logger"):
                    self.logger.error(f"{tool_name}: {error_msg}")
                return {
                    "status": "error",
                    "error": error_msg,
                    "error_type": "ValidationError",
                }
        else:
            # Provide helpful error message with examples
            received_type = type(tool_arguments).__name__
            error_msg = (
                f"arguments must be a JSON object (dictionary) or JSON object string, not a {received_type}. "
                f"Received: {repr(tool_arguments)[:100]}. "
                f'Example of correct format: {{"param1": "value1", "param2": 5}}. '
                'JSON string also accepted: "{\\"param1\\": \\"value1\\", \\"param2\\": 5}".'
            )
            if hasattr(self, "logger"):
                self.logger.error(f"{tool_name}: {error_msg}")
            return {
                "status": "error",
                "error": error_msg,
                "error_type": "ValidationError",
            }

        # Directly use tooluniverse.run_one_function - it handles everything
        function_call = {"name": tool_name, "arguments": parsed_args}
        result = self.tooluniverse.run_one_function(function_call)

        # Convert result to dict if it's a JSON string
        if isinstance(result, str):
            try:
                result = json.loads(result)
            except (json.JSONDecodeError, ValueError):
                # If it's not valid JSON, return as string wrapped in dict
                return {"result": result}

        # Return as dict (FastMCP will serialize if needed)
        return result if isinstance(result, dict) else {"result": result}
