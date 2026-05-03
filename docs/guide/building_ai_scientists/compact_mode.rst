.. _compact_mode_guide:

Compact Mode Guide
==================

Compact mode exposes only 4-5 core tools instead of 1000+ tools, reducing context window usage by ~99% while maintaining full functionality.

What is Compact Mode?
---------------------

Compact mode is a context window optimization that exposes only 4-5 core discovery tools instead of listing all 1000+ tools. All tools remain accessible through the ``execute_tool`` function.

Why Use Compact Mode?
---------------------

**The Problem**: AI assistants have limited context windows. Listing 1000+ tools consumes significant context space, leaving less room for:

- Your research questions
- Tool outputs and data
- Conversation history
- Analysis and reasoning

**The Solution**: Compact mode exposes only 4-5 discovery tools. The AI uses these to find and execute the specific tools it needs.

**Impact**:

- **99% reduction** in exposed tools (4-5 vs 1000+)
- **Full functionality** - All 1000+ tools still accessible via ``execute_tool``
- **Better AI reasoning** - More context available for analysis
- **Faster responses** - Less token processing overhead

**When to use**:

 **Always recommended** for MCP integration with Claude, Cursor, ChatGPT 
 AI agent workflows with long conversations 
 Complex multi-step research tasks 
 Working with large datasets or outputs

**When to skip**:

 Python API usage (context windows don't apply) 
 Single-use scripts or batch processing 
 When you need to see all available tools at once

Core Tools
----------

Compact mode exposes 4 core discovery tools, plus optionally ``find_tools`` if search is enabled (default):

1. **``list_tools``** - List available tools (names, categories, etc.)
2. **``grep_tools``** - Search tools by text/regex pattern
3. **``get_tool_info``** - Get tool information (description or full definition)
4. **``execute_tool``** - Execute any ToolUniverse tool by name
5. **``find_tools``** - AI-powered tool discovery using natural language queries (optional, enabled by default via ``search_enabled=True``)

Quick Start
-----------

Command Line
~~~~~~~~~~~~

.. code-block:: bash

   # STDIO mode (for Claude Desktop)
   tooluniverse-smcp-stdio --compact-mode

   # HTTP mode
   tooluniverse-smcp-server --compact-mode --port 8000

Claude Desktop Configuration
----------------------------

Add to ``~/Library/Application Support/Claude/claude_desktop_config.json``:

.. code-block:: json

   {
     "mcpServers": {
       "tooluniverse-compact": {
         "command": "python",
         "args": [
           "-m", "tooluniverse.smcp_server",
           "--transport", "stdio",
           "--compact-mode"
         ],
         "env": {
           "FASTMCP_NO_BANNER": "1",
           "PYTHONWARNINGS": "ignore"
         }
       }
     }
   }

Gemini CLI Configuration
------------------------

Add to ``~/.gemini/settings.json`` or project ``.gemini/settings.json``:

.. code-block:: json

   {
     "mcpServers": {
       "tooluniverse": {
         "command": "uv",
         "args": [
           "--directory",
           "/path/to/tooluniverse-env",
           "run",
           "tooluniverse-smcp-stdio",
           "--compact-mode"
         ]
       }
     }
   }

**Why Compact Mode for Gemini CLI?**

- **500 tool limit**: Gemini CLI has a 500 tool limit per MCP server
- **Minimal context usage**: Compact mode exposes only 4-5 tools, well within limits
- **Full functionality**: All 1000+ tools still accessible via ``execute_tool``
- **Progressive disclosure**: Discover tools on demand using ``list_tools``, ``grep_tools``, and ``get_tool_info``

Usage
-----

In Claude Desktop, just configure the server and start using tools. Claude will automatically discover and call them.

**Typical workflow:**
1. Use ``list_tools(mode="names")`` to see available tools
2. Use ``grep_tools(pattern="...")`` to search for tools
3. Use ``get_tool_info(tool_names="...")`` to get details
4. Use ``execute_tool(tool_name="...", arguments={...})`` to execute tools

Comparison
----------

.. list-table::
   :header-rows: 1
   :widths: 30 35 35

   * - Feature
     - Normal Mode
     - Compact Mode
   * - Tools Exposed
     - ~1000 tools
     - 4-5 tools (4 core + find_tools if search enabled)
   * - Context Usage
     - High
     - Low (99% reduction)
   * - Functionality
     - Full
     - Full (via execute_tool)

When to Use
-----------

**Use Compact Mode when:**
- Working with AI agents (Claude Desktop, Gemini CLI, etc.)
- Context window is limited
- Working with Gemini CLI (500 tool limit)
- You want minimal context usage

**Use Normal Mode when:**
- Context window is not a concern
- You want direct access to all tools
- Working with platforms without tool limits

Examples
--------

See ``examples/compact_mode/`` for complete examples.

Related Documentation
---------------------

- :doc:`mcp_support` - General MCP support
- :doc:`claude_desktop` - Claude Desktop integration
- :doc:`gemini_cli` - Gemini CLI integration with profile configuration
