"""
LLM-based Tool Finder - A tool that uses LLM to find relevant tools based on descriptions.

This tool leverages AgenticTool's LLM functionality to create an intelligent tool finder
that puts only essential tool information (name and description) in the prompt to minimize
context window cost while letting the LLM decide which tools to return based on the query.

Key optimizations:
- Only sends tool name and description to LLM (no parameters, configs, etc.)
- Uses compact formatting to reduce token count
- Caches tool descriptions to avoid repeated processing
- Excludes irrelevant tools from prompt
"""

import json
from datetime import datetime

from .base_tool import BaseTool
from .tool_registry import register_tool
from .agentic_tool import AgenticTool


@register_tool("ToolFinderLLM")
class ToolFinderLLM(BaseTool):
    """
    LLM-based tool finder that uses natural language processing to select relevant tools.

    This class leverages AgenticTool's LLM capabilities to analyze tool descriptions
    and match them with user queries. It's optimized for minimal context window cost
    by only sending essential information (tool name and description) to the LLM,
    providing an intelligent alternative to embedding-based similarity search.

    Cost optimizations:
    - Only includes tool name and description in LLM prompt
    - Uses compact formatting to minimize token usage
    - Excludes unnecessary tool metadata and parameters
    - Implements caching to avoid repeated tool processing
    """

    def __init__(self, tool_config, tooluniverse=None):
        """
        Initialize the LLM-based Tool Finder.

        Args:
            tool_config (dict): Configuration dictionary containing LLM settings and prompts
            tooluniverse: Reference to the ToolUniverse instance containing all tools
        """
        super().__init__(tool_config)
        self.tooluniverse = tooluniverse

        # Extract configuration
        self.name = tool_config.get("name", "ToolFinderLLM")
        self.description = tool_config.get("description", "LLM-based tool finder")

        # Get LLM configuration from tool_config
        configs = tool_config.get("configs", {})
        self.api_type = configs.get("api_type", "CHATGPT")
        self.model_id = configs.get("model_id", "gpt-4o-1120")
        self.temperature = configs.get("temperature", 0.1)
        self.return_json = configs.get("return_json", True)

        # Tool filtering settings
        self.exclude_tools = tool_config.get(
            "exclude_tools",
            tool_config.get("configs", {}).get(
                "exclude_tools",
                ["Tool_RAG", "Tool_Finder", "Finish", "CallAgent", "ToolFinderLLM"],
            ),
        )
        self.include_categories = tool_config.get("include_categories", None)
        self.exclude_categories = tool_config.get("exclude_categories", None)

        # Return format settings - defaults to False if not specified in config
        self.return_list_only = tool_config.get("configs", {}).get(
            "return_list_only", False
        )

        # Initialize the underlying AgenticTool for LLM operations
        self._init_agentic_tool()

        # Cache for tool descriptions
        self._tool_cache = None
        self._cache_timestamp = None

        # Store fallback config for query-time failover
        self._fallback_api_type = configs.get("fallback_api_type")
        self._fallback_model_id = configs.get("fallback_model_id")
        self._fallback_agentic = None

    @staticmethod
    def _extract_llm_response(result):
        """Extract text content from AgenticTool result."""
        if result is None:
            return None
        if isinstance(result, dict) and "result" in result:
            return result["result"]
        return result

    def _try_query_fallback(self, agentic_args):
        """Try fallback LLM backend when primary fails at query time."""
        if not self._fallback_api_type or not self._fallback_model_id:
            return None

        print(
            f"⚠️  Primary LLM failed, trying fallback: "
            f"{self._fallback_api_type}/{self._fallback_model_id}"
        )

        # Lazy-init fallback AgenticTool
        if self._fallback_agentic is None:
            fallback_config = {
                "name": f"{self.name}_fallback",
                "description": "Fallback agentic tool for LLM-based tool selection",
                "type": "AgenticTool",
                "prompt": self._get_tool_selection_prompt(),
                "input_arguments": ["query", "tools_descriptions", "limit"],
                "parameter": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "required": True},
                        "tools_descriptions": {"type": "string", "required": True},
                        "limit": {"type": "integer", "required": True},
                    },
                    "required": ["query", "tools_descriptions", "limit"],
                },
                "configs": {
                    "api_type": self._fallback_api_type,
                    "model_id": self._fallback_model_id,
                    "temperature": self.temperature,
                    "return_json": self.return_json,
                    "return_metadata": False,
                    "validate_api_key": False,
                    "use_global_fallback": False,
                },
            }
            try:
                from .agentic_tool import AgenticTool

                self._fallback_agentic = AgenticTool(fallback_config)
            except Exception as e:
                print(f"❌ Fallback init failed: {e}")
                return None

        try:
            result = self._fallback_agentic.run(agentic_args)
            return self._extract_llm_response(result)
        except Exception as e:
            print(f"❌ Fallback query failed: {e}")
            return None

    def _init_agentic_tool(self):
        """Initialize the underlying AgenticTool for LLM operations."""

        # Create AgenticTool configuration
        agentic_config = {
            "name": f"{self.name}_agentic",
            "description": "Internal agentic tool for LLM-based tool selection",
            "type": "AgenticTool",
            "prompt": self._get_tool_selection_prompt(),
            "input_arguments": ["query", "tools_descriptions", "limit"],
            "parameter": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The user query describing what tools are needed",
                        "required": True,
                    },
                    "tools_descriptions": {
                        "type": "string",
                        "description": "JSON string containing all available tool descriptions",
                        "required": True,
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of tools to return",
                        "required": True,
                    },
                },
                "required": ["query", "tools_descriptions", "limit"],
            },
            "configs": {
                "api_type": self.api_type,
                "model_id": self.model_id,
                "temperature": self.temperature,
                "return_json": self.return_json,
                "return_metadata": False,
            },
        }
        try:
            self.agentic_tool = AgenticTool(agentic_config)
            print(
                f"✅ Successfully initialized {self.name} with LLM model: {self.model_id}"
            )
        except Exception as e:
            print(f"❌ Failed to initialize AgenticTool for {self.name}: {str(e)}")
            raise

    def _get_tool_selection_prompt(self):
        """Get the prompt template for tool selection. Optimized for minimal token usage."""
        return """You are a tool selection assistant. Select the most relevant tools for the user query.

Query: {query}

Tools:
{tools_descriptions}

Select the {limit} most relevant tools. Return JSON:
{{
    "selected_tools": [
        {{
            "name": "tool_name",
            "relevance_score": 0.95,
            "reasoning": "Why relevant"
        }}
    ],
    "total_selected": 1,
    "selection_reasoning": "Overall strategy"
}}

Requirements:
- Only select existing tools from the list
- Rank by relevance (0.0-1.0)
- Prioritize domain-specific tools for specialized queries
- Return requested number or fewer if insufficient relevant tools"""

    def _get_available_tools(self, force_refresh=False):
        """
        Get available tools with their descriptions, with caching.

        Args:
            force_refresh (bool): Whether to force refresh the cache

        Returns
            list: List of tool dictionaries with names and descriptions
        """
        current_time = datetime.now()

        # Use cache if available and not expired (cache for 5 minutes)
        if (
            not force_refresh
            and self._tool_cache is not None
            and self._cache_timestamp is not None
            and (current_time - self._cache_timestamp).seconds < 300
        ):
            return self._tool_cache

        if not self.tooluniverse:
            from .base_tool import tool_error

            print("⚠️ ToolUniverse reference not available")
            return tool_error(
                "ToolUniverse reference not set — tool discovery unavailable",
                error_type="ToolConfigError",
                suggestion="Ensure ToolFinderLLM.tooluniverse is set before calling.",
            )

        try:
            # Get tool names and descriptions
            tool_names, tool_descriptions = self.tooluniverse.refresh_tool_name_desc(
                enable_full_desc=True,
                exclude_names=self.exclude_tools,
                include_categories=self.include_categories,
                exclude_categories=self.exclude_categories,
            )

            # Format tools for LLM
            available_tools = []
            for name, desc in zip(tool_names, tool_descriptions):
                if name not in self.exclude_tools:
                    # name is already shortened (primary identifier)
                    available_tools.append({"name": name, "description": desc})

            # Update cache
            self._tool_cache = available_tools
            self._cache_timestamp = current_time

            print(f"📋 Loaded {len(available_tools)} tools for LLM-based selection")
            return available_tools

        except Exception as e:
            from .base_tool import tool_error

            print(f"❌ Error getting available tools: {str(e)}")
            return tool_error(
                f"Failed to load available tools: {e}",
                error_type="ToolLoadError",
            )

    def _prefilter_tools_by_keywords(self, available_tools, query, max_tools=100):
        """
        Pre-filter tools using keyword matching to reduce context size before LLM processing.

        Args:
            available_tools (list): All available tools
            query (str): User query
            max_tools (int): Maximum number of tools to send to LLM

        Returns
            list: Filtered list of tools
        """
        if len(available_tools) <= max_tools:
            return available_tools

        query_lower = query.lower()
        query_words = set(query_lower.split())

        # Score tools based on keyword matches
        scored_tools = []
        for tool in available_tools:
            name_lower = tool.get("name", "").lower()
            desc_lower = tool.get("description", "").lower()

            # Calculate basic relevance score
            score = 0

            # Exact name matches get high priority
            if query_lower in name_lower:
                score += 10

            # Word matches in name and description
            for word in query_words:
                if len(word) > 2:  # Skip very short words
                    if word in name_lower:
                        score += 3
                    if word in desc_lower:
                        score += 1

            scored_tools.append((score, tool))

        # Sort by score and take top tools
        scored_tools.sort(key=lambda x: x[0], reverse=True)
        filtered_tools = [tool for score, tool in scored_tools[:max_tools]]

        print(
            f"🔍 Pre-filtered from {len(available_tools)} to {len(filtered_tools)} tools using keywords"
        )
        return filtered_tools

    def _format_tools_for_prompt(self, tools):
        """
        Format tools for inclusion in the LLM prompt with minimal information to reduce context cost.
        Only includes name and description to minimize token usage.

        Args:
            tools (list): List of tool dictionaries

        Returns
            str: Compact formatted tool descriptions for the prompt
        """
        formatted_tools = []
        for i, tool in enumerate(tools, 1):
            name = tool.get("name", "Unknown")
            description = tool.get("description", "No description available")

            # Truncate very long descriptions to save tokens
            if len(description) > 150:
                description = description[:150] + "..."

            # Use more compact formatting to save tokens
            formatted_tools.append(f"{i}. {name}: {description}")

        return "\n".join(formatted_tools)

    def find_tools_llm(self, query, limit=5, include_reasoning=False, categories=None):
        """
        Find relevant tools using LLM-based selection.

        Args:
            query (str): User query describing needed functionality
            limit (int): Maximum number of tools to return
            include_reasoning (bool): Whether to include selection reasoning
            categories (list, optional): List of tool categories to filter by

        Returns
            dict: Dictionary containing selected tools and metadata
        """
        try:
            # AUTO-LOAD: If tools not fully loaded, load them now
            # Check if tools are not loaded or only partially loaded (< 100 tools means incomplete)
            if len(self.tooluniverse.all_tool_dict) < 100:
                self.tooluniverse.logger.info(
                    f"Tool_Finder_LLM: Only {len(self.tooluniverse.all_tool_dict)} tools loaded, loading all tools now..."
                )
                # Force full load by clearing filters and loading everything
                self.tooluniverse.load_tools(include_tools=None, tool_type=None)

            # Get available tools
            available_tools = self._get_available_tools()

            if not available_tools:
                return {
                    "success": False,
                    "error": "No tools available for selection",
                    "selected_tools": [],
                    "total_available": 0,
                }

            # Filter by categories if specified
            if categories:
                # Get full tool information for category filtering
                all_tools = self.tooluniverse.return_all_loaded_tools()
                category_filtered_tools = []

                for tool_info in available_tools:
                    tool_name = tool_info["name"]
                    # Find the full tool data to check category
                    for full_tool in all_tools:
                        if full_tool.get("name") == tool_name:
                            tool_category = full_tool.get("category", "unknown")
                            if tool_category in categories:
                                category_filtered_tools.append(tool_info)
                            break

                available_tools = category_filtered_tools

                if not available_tools:
                    return {
                        "success": False,
                        "error": f"No tools available in categories: {categories}",
                        "selected_tools": [],
                        "total_available": 0,
                    }

            # Pre-filter tools to reduce context size for LLM
            available_tools = self._prefilter_tools_by_keywords(
                available_tools, query, max_tools=50
            )

            # Format tools for LLM prompt with minimal information to reduce context cost
            tools_formatted = self._format_tools_for_prompt(available_tools)

            # Prepare arguments for the agentic tool
            agentic_args = {
                "query": query,
                "tools_descriptions": tools_formatted,
                "limit": limit,
            }

            print(f"🤖 Querying LLM to select tools for: '{query[:100]}...'")

            # Call the LLM through AgenticTool (with query-time fallback)
            result = self.agentic_tool.run(agentic_args)
            llm_response = self._extract_llm_response(result)

            # Query-time fallback: if primary returned nothing, try fallback backend
            if llm_response is None or llm_response == "":
                llm_response = self._try_query_fallback(agentic_args)

            # Parse JSON response from LLM
            if isinstance(llm_response, str):
                try:
                    parsed_response = json.loads(llm_response)
                except json.JSONDecodeError as e:
                    print(f"❌ Failed to parse LLM response as JSON: {e}")
                    print(f"Raw response: {llm_response[:500]}...")
                    return {
                        "success": False,
                        "error": f"Invalid JSON response from LLM: {str(e)}",
                        "raw_response": llm_response,
                        "selected_tools": [],
                    }
            elif llm_response is None:
                return {
                    "success": False,
                    "error": "All LLM backends failed",
                    "selected_tools": [],
                }
            else:
                parsed_response = llm_response

            # Extract selected tools
            selected_tools = parsed_response.get("selected_tools", [])
            tool_names = [
                tool.get("name") for tool in selected_tools if tool.get("name")
            ]

            # Get actual tool objects
            if tool_names:
                selected_tool_objects = (
                    self.tooluniverse.get_tool_specification_by_names(tool_names)
                )
                tool_prompts = self.tooluniverse.prepare_tool_prompts(
                    selected_tool_objects
                )
            else:
                selected_tool_objects = []
                tool_prompts = []

            result_dict = {
                "success": True,
                "selected_tools": tool_names,
                "tool_objects": selected_tool_objects,
                "tool_prompts": tool_prompts,
                "total_selected": len(tool_names),
                "total_available": len(available_tools),
                "query": query,
                "limit_requested": limit,
            }

            if include_reasoning:
                result_dict.update(
                    {
                        "selection_details": selected_tools,
                        "selection_reasoning": parsed_response.get(
                            "selection_reasoning", ""
                        ),
                        "llm_response": parsed_response,
                    }
                )

            print(f"✅ Selected {len(tool_names)} tools: {', '.join(tool_names)}")
            return result_dict

        except Exception as e:
            print(f"❌ Error in LLM-based tool selection: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "selected_tools": [],
                "query": query,
            }

    def find_tools(
        self,
        message=None,
        picked_tool_names=None,
        rag_num=5,
        return_call_result=False,
        categories=None,
        return_list_only=None,
    ):
        """
        Find relevant tools based on a message or pre-selected tool names.

        This method matches the interface of the original ToolFinderEmbedding to ensure
        seamless replacement. It uses LLM-based selection instead of embedding similarity.

        Args:
            message (str, optional): Query message to find tools for. Required if picked_tool_names is None.
            picked_tool_names (list, optional): Pre-selected tool names to process. Required if message is None.
            rag_num (int, optional): Number of tools to return after filtering. Defaults to 5.
            return_call_result (bool, optional): If True, returns both prompts and tool names. Defaults to False.
            categories (list, optional): List of tool categories to filter by. Applied before LLM selection.
            return_list_only (bool, optional): If True, returns only a list of tool specifications. Overrides other return options.

        Returns
            str, tuple, or list:
                - If return_list_only is True: List of tool specifications
                - If return_call_result is False: Tool prompts as a formatted string
                - If return_call_result is True: Tuple of (tool_prompts, tool_names)

        Raises:
            AssertionError: If both message and picked_tool_names are None
        """
        # Use class-level configuration if parameter not specified
        if return_list_only is None:
            return_list_only = self.return_list_only

        if picked_tool_names is None:
            assert picked_tool_names is not None or message is not None

            # Use LLM-based tool selection with category filtering
            result = self.find_tools_llm(
                query=message,
                limit=rag_num,
                include_reasoning=False,
                categories=categories,
            )

            if not result["success"]:
                # Return empty results on failure
                if return_list_only:
                    return []  # Return empty list for tool specifications
                elif return_call_result:
                    return "", []
                return ""

            picked_tool_names = result["selected_tools"]

        # Filter out special tools (matching original behavior)
        picked_tool_names_no_special = []
        for tool in picked_tool_names:
            if tool not in self.exclude_tools:
                picked_tool_names_no_special.append(tool)
        picked_tool_names_no_special = picked_tool_names_no_special[:rag_num]
        picked_tool_names = picked_tool_names_no_special[:rag_num]

        # Get tool objects and prepare prompts (needed for both list and other formats)
        picked_tools = self.tooluniverse.get_tool_specification_by_names(
            picked_tool_names
        )
        picked_tools_prompt = self.tooluniverse.prepare_tool_prompts(picked_tools)

        # If only list format is requested, return the tool specifications as a list
        if return_list_only:
            return picked_tools_prompt  # Return list of tool specifications instead of just names

        if return_call_result:
            return picked_tools_prompt, picked_tool_names
        return picked_tools_prompt

    def get_tool_stats(self):
        """Get statistics about available tools."""
        tools = self._get_available_tools(force_refresh=True)

        stats = {
            "total_tools": len(tools),
            "excluded_tools": len(self.exclude_tools),
            "cache_status": "cached" if self._tool_cache is not None else "no_cache",
            "last_updated": (
                self._cache_timestamp.isoformat() if self._cache_timestamp else None
            ),
        }

        return stats

    def _format_as_json(self, result, query, limit, categories, return_call_result):
        """
        Format the find_tools result as a standardized JSON string.

        Args:
            result: Result from find_tools method (either string, list, or tuple)
            query: Original search query
            limit: Requested number of tools
            categories: Requested categories filter
            return_call_result: Whether return_call_result was True

        Returns
            str: JSON formatted search results
        """
        import json

        try:
            if return_call_result and isinstance(result, tuple) and len(result) == 2:
                # Result is (tool_prompts, tool_names) tuple
                tool_prompts, tool_names = result

                # Convert tool prompts to clean tool info format
                tools = []
                for i, tool_name in enumerate(tool_names):
                    if i < len(tool_prompts):
                        tool_prompt = tool_prompts[i]
                        tool_info = {
                            "name": tool_name,
                            "description": tool_prompt.get("description", ""),
                            "type": tool_prompt.get("type", ""),
                            "parameters": tool_prompt.get("parameter", {}),
                            "required": tool_prompt.get("required", []),
                        }
                        tools.append(tool_info)

                return json.dumps(
                    {
                        "query": query,
                        "search_method": "AI-powered (ToolFinderLLM)",
                        "total_matches": len(tools),
                        "categories_filtered": categories,
                        "tools": tools,
                    },
                    indent=2,
                )

            elif isinstance(result, list):
                # Result is already a list of tool prompts
                tools = []
                for tool_prompt in result:
                    if isinstance(tool_prompt, dict):
                        tool_info = {
                            "name": tool_prompt.get("name", ""),
                            "description": tool_prompt.get("description", ""),
                            "type": tool_prompt.get("type", ""),
                            "parameters": tool_prompt.get("parameter", {}),
                            "required": tool_prompt.get("required", []),
                        }
                        tools.append(tool_info)

                return json.dumps(
                    {
                        "query": query,
                        "search_method": "AI-powered (ToolFinderLLM)",
                        "total_matches": len(tools),
                        "categories_filtered": categories,
                        "tools": tools,
                    },
                    indent=2,
                )

            else:
                # Fallback for unexpected result format
                return json.dumps(
                    {
                        "query": query,
                        "search_method": "AI-powered (ToolFinderLLM)",
                        "total_matches": 0,
                        "categories_filtered": categories,
                        "tools": [],
                        "error": f"Unexpected result format: {type(result)}",
                    },
                    indent=2,
                )

        except Exception as e:
            # Error handling
            return json.dumps(
                {
                    "query": query,
                    "search_method": "AI-powered (ToolFinderLLM)",
                    "total_matches": 0,
                    "categories_filtered": categories,
                    "tools": [],
                    "error": f"Formatting error: {str(e)}",
                },
                indent=2,
            )

    def clear_cache(self):
        """Clear the tool cache to force refresh on next access."""
        self._tool_cache = None
        self._cache_timestamp = None
        print("🔄 Tool cache cleared")

    def run(self, arguments):
        """
        Run the tool finder with given arguments following the standard tool interface.

        This method now returns JSON format by default to ensure consistency with other
        search tools and simplify integration with SMCP.

        Args:
            arguments (dict): Dictionary containing:
                - description (str, optional): Query message to find tools for (maps to 'message')
                - limit (int, optional): Number of tools to return (maps to 'rag_num'). Defaults to 5.
                - picked_tool_names (list, optional): Pre-selected tool names to process
                - return_call_result (bool, optional): Whether to return both prompts and names. Defaults to False.
                - return_format (str, optional): 'json' (default) or 'legacy' for old format
                - return_list_only (bool, optional): Whether to return only tool specifications as a list
                - categories (list, optional): List of tool categories to filter by
        """
        import copy

        arguments = copy.deepcopy(arguments)

        # Extract parameters from arguments with defaults
        message = arguments.get("description", None)
        rag_num = arguments.get("limit", 5)
        picked_tool_names = arguments.get("picked_tool_names", None)
        return_call_result = arguments.get("return_call_result", False)
        return_format = arguments.get("return_format", "json")  # Default to JSON format
        return_list_only = arguments.get(
            "return_list_only", None
        )  # Use class default if not specified
        categories = arguments.get("categories", None)

        # Call the find_tools method
        result = self.find_tools(
            message=message,
            picked_tool_names=picked_tool_names,
            rag_num=rag_num,
            return_call_result=return_call_result,
            categories=categories,
            return_list_only=return_list_only,
        )

        # If return_list_only is True, return the list directly
        if return_list_only or (return_list_only is None and self.return_list_only):
            return result

        # If return_format is 'json', convert to standardized JSON format
        if return_format == "json":
            return self._format_as_json(
                result, message, rag_num, categories, return_call_result
            )
        else:
            # Return legacy format (original behavior)
            return result

    # Legacy methods for backward compatibility
    def find_tools_legacy(
        self, query, limit=5, include_reasoning=False, return_format="prompts"
    ):
        """
        Legacy method for finding tools with different parameter names.

        This provides backward compatibility for any code that might use 'query' instead of 'description'.
        """
        return self.run(
            {
                "description": query,
                "limit": limit,
                "return_call_result": return_format == "full",
            }
        )
