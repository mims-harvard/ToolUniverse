Compact Mode Tools
==================

**Configuration File**: ``compact_mode_tools.json``
**Tool Type**: Local
**Tools Count**: 4

This page contains all tools defined in the ``compact_mode_tools.json`` configuration file.

Available Tools
---------------

**execute_tool** (Type: ExecuteTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Execute a ToolUniverse tool directly with custom arguments. This is the primary way to run any to...

.. dropdown:: execute_tool tool specification

   **Tool Information:**

   * **Name**: ``execute_tool``
   * **Type**: ``ExecuteTool``
   * **Description**: Execute a ToolUniverse tool directly with custom arguments. This is the primary way to run any tool in the ToolUniverse system. You must get the tool definition first to figure out the arguments to pass.

   **Parameters:**

   * ``tool_name`` (string) (required)
     Name of the tool to execute (e.g., 'example_tool_name')

   * ``arguments`` (object) (optional)
     Tool arguments as a JSON object (dictionary), NOT a JSON string. Pass the parameters required by the target tool as key-value pairs. Example: {"param1": "value1", "param2": 5}. Do NOT use string format like 'param1=value1' or '"{\"param1\":\"value1\"}"'. Must be a proper JSON object.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "execute_tool",
          "arguments": {
              "tool_name": "example_value"
          }
      }
      result = tu.run(query)


**get_tool_info** (Type: GetToolInfo)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get tool information with configurable detail level. Supports single tool (string) or multiple to...

.. dropdown:: get_tool_info tool specification

   **Tool Information:**

   * **Name**: ``get_tool_info``
   * **Type**: ``GetToolInfo``
   * **Description**: Get tool information with configurable detail level. Supports single tool (string) or multiple tools (list). Use detail_level='description' to get only the description field, or detail_level='full' to get complete tool definition including parameter schema.

   **Parameters:**

   * ``tool_names`` (unknown) (required)
     Single tool name (string) or list of tool names (max 20 tools)

   * ``detail_level`` (string) (optional)
     Detail level: 'description' returns only the description field (complete, not truncated), 'full' returns complete tool definition including parameter schema

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "get_tool_info",
          "arguments": {
              "tool_names": "example_value"
          }
      }
      result = tu.run(query)


**grep_tools** (Type: GrepTools)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search tools using simple text matching or regex patterns. Supports both simple text search (defa...

.. dropdown:: grep_tools tool specification

   **Tool Information:**

   * **Name**: ``grep_tools``
   * **Type**: ``GrepTools``
   * **Description**: Search tools using simple text matching or regex patterns. Supports both simple text search (default, agent-friendly) and regex patterns (advanced). Independent from Tool_Finder_Keyword, uses basic text/regex matching without TF-IDF or NLP processing. Fast and simple for pattern searches.

   **Parameters:**

   * ``pattern`` (string) (required)
     Search pattern (text or regex depending on search_mode)

   * ``field`` (string) (optional)
     Field to search in: name, description, type, or category

   * ``search_mode`` (string) (optional)
     Search mode: 'text' for simple case-insensitive text matching (default, agent-friendly), 'regex' for regex pattern matching

   * ``limit`` (integer) (optional)
     Maximum number of tools to return (default: 100)

   * ``offset`` (integer) (optional)
     Number of tools to skip (optional, for pagination, default: 0)

   * ``categories`` (array) (optional)
     Optional list of tool categories to filter by

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "grep_tools",
          "arguments": {
              "pattern": "example_value"
          }
      }
      result = tu.run(query)


**list_tools** (Type: ListTools)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Unified tool listing with multiple modes for different use cases. Supports listing tool names, ba...

.. dropdown:: list_tools tool specification

   **Tool Information:**

   * **Name**: ``list_tools``
   * **Type**: ``ListTools``
   * **Description**: Unified tool listing with multiple modes for different use cases. Supports listing tool names, basic info, categories, grouped by category, summary info, or custom fields. Replaces the previous separate list tools (list_tool_names, list_categories, list_tools_by_category, list_tools_basic, list_tools_by_fields, list_available_tooluniverse_tools).

   **Parameters:**

   * ``mode`` (string) (required)
     Output mode: 'names' (tool names only), 'basic' (name+description), 'categories' (category statistics), 'by_category' (grouped by category), 'summary' (name+description+type+has_parameters), 'custom' (user-specified fields)

   * ``categories`` (array) (optional)
     Optional list of tool categories to filter by (applies to all modes except 'categories')

   * ``fields`` (array) (optional)
     Required for mode='custom'. List of fields to include (e.g., ["name", "type", "category"])

   * ``group_by_category`` (boolean) (optional)
     Whether to group results by category (only for mode='names', 'basic', or 'summary')

   * ``brief`` (boolean) (optional)
     Whether to truncate description to brief (only for mode='basic' or 'summary')

   * ``limit`` (integer) (optional)
     Maximum number of tools to return (optional, for pagination)

   * ``offset`` (integer) (optional)
     Number of tools to skip (optional, for pagination, default: 0)

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "list_tools",
          "arguments": {
              "mode": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
