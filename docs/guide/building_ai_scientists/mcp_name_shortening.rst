==========================================
MCP Tool Name Shortening
==========================================

**Version:** 1.0 
**Status:** Production Ready 

Overview
========

ToolUniverse includes automatic tool name shortening to ensure compatibility with the MCP (Model Context Protocol) 64-character tool name limit. This feature is particularly important for Claude Code and other MCP clients that construct tool names using the pattern ``mcp__{server_name}__{tool_name}``.

The Problem
===========

The MCP standard specifies that tool names must be **maximum 64 characters** long. When tool names exceed this limit, tool calls fail with an API error:

.. code-block:: text

    API Error: 400 {"type":"error","error":{"type":"invalid_request_error",
    "message":"messages.18.content.0.tool_result.content.0.tool_reference.tool_name: 
    String should have at most 64 characters"}}

Name Construction Pattern
--------------------------

MCP clients construct tool names as: ``mcp__{server_name}__{tool_name}``

**With shortened server name:**

- Server name: ``tu`` (2 chars)
- Prefix: ``mcp__tu__`` (9 chars)
- Available space for tool names: 55 characters
- **Result**: All tools fit after automatic shortening

The Solution
============

ToolUniverse implements a two-part solution:

1. **Shortened Server Name**: Use ``tu`` instead of ``tooluniverse`` in MCP configuration
2. **Automatic Name Shortening**: Intelligent word-level truncation when needed

Shortening Algorithm
--------------------

The algorithm intelligently truncates tool names by:

1. **Splitting by underscores** to identify words
2. **Preserving category prefix** (first word): ``FDA``, ``UniProt``, ``euhealthinfo``
3. **Truncating subsequent words**:
 
 - Short words (≤3 chars) kept intact: ``by``, ``get``, ``on``, ``or``, ``for``
 - Medium words (4-6 chars): first 4 chars: ``drug`` → ``drug``
 - Long words (>6 chars): first 4 chars: ``consultation`` → ``cons``

4. **Handling collisions**: Appends numeric suffix if shortened names clash

Examples
--------

.. list-table::
   :header-rows: 1
   :widths: 45 10 40 10

   * - Original Name
     - Length
     - Shortened Name
     - Length
   * - ``FDA_get_info_on_conditions_for_doctor_consultation_by_drug_name``
     - 63
     - ``FDA_get_info_on_cond_for_doct_cons_by_drug_name``
     - 47
   * - ``euhealthinfo_search_diabetes_mellitus_epidemiology_registry``
     - 59
     - ``euhealthinfo_sear_diab_mell_epid_regi``
     - 38
   * - ``UniProt_get_function_by_accession``
     - 34
     - ``UniProt_get_function_by_accession``
     - 34

When to Use This Feature
=========================

 USE in These Scenarios
--------------------------

MCP Integration (Automatic)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**When:**

- Using ToolUniverse through MCP clients (Claude Code, Claude Desktop, etc.)
- Need compliance with 64-character limit

**How:**

- Automatically enabled in SMCP
- No configuration needed
- Works out of the box

**Example MCP Configuration:**

.. code-block:: json

    {
      "mcpServers": {
        "tu": {
          "command": "tooluniverse-smcp-stdio",
          "args": []
        }
      }
    }

Custom MCP Server Implementation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**When:**

- Building your own MCP server using ToolUniverse
- Need to expose tools with shortened names

**Example:**

.. code-block:: python

    from tooluniverse import ToolUniverse

    tu = ToolUniverse(enable_name_shortening=True)
    tu.load_tools()

    # Names are automatically shortened during MCP exposure
    # Access all tool names (already shortened if enable_name_shortening=True)
    for tool_name in tu.all_tool_dict.keys():
        print(tool_name)  # Names fit within MCP length limits automatically

External API Integration with Length Constraints
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**When:**

- Integrating with systems that have tool name length limits
- Need to export tool lists with shorter names
- Building UIs with limited display space

When NOT to Use This Feature
=============================

 DO NOT USE in These Scenarios
---------------------------------

Direct Python API Usage (Default)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**When:**

- Using ToolUniverse directly in Python scripts
- No external length constraints
- Want original descriptive names

**Why Not:**

- Original names are more readable
- No benefit from shortening
- Default behavior (disabled) is correct

**Correct Usage:**

.. code-block:: python

    # DON'T enable shortening unnecessarily
    tu = ToolUniverse()  # Default: enable_name_shortening=False
    tu.run_one_function({
        "name": "FDA_get_drug_info_by_name",
        "arguments": {...}
    })

Internal Tool Development
~~~~~~~~~~~~~~~~~~~~~~~~~

**When:**

- Developing new tools for ToolUniverse
- Writing tool configurations
- Creating tool documentation

**Why Not:**

- Tools should always use full descriptive names
- Shortening is only for external exposure
- Tool implementations don't need shortened names

Tool Discovery and Search
~~~~~~~~~~~~~~~~~~~~~~~~~

**When:**

- Searching for tools by name
- Browsing available tools
- Generating tool documentation

**Why Not:**

- Original names are more meaningful
- Shortened names may be ambiguous
- Discovery should use full descriptive names

Usage Guide
===========

For MCP Users (Automatic)
--------------------------

If you're using ToolUniverse through MCP (Claude Desktop, Claude Code, etc.), name shortening is **automatically enabled**. No configuration needed!

**Update your MCP configuration:**

.. code-block:: json

    {
      "mcpServers": {
        "tu": {
          "command": "tooluniverse-smcp-stdio",
          "args": []
        }
      }
    }

.. important::
   The key ``"tu"`` in the configuration becomes the MCP server name in the prefix ``mcp__tu__``. Change this from ``"tooluniverse"`` to ``"tu"`` to save 10 characters for tool names!

For Python API Users (Opt-in)
------------------------------

If you're using ToolUniverse directly in Python:

.. code-block:: python

    from tooluniverse import ToolUniverse

    # Enable name shortening during initialization
    tu = ToolUniverse(enable_name_shortening=True)
    tu.load_tools()

    # Name shortening is applied automatically during MCP server exposure
    # When enable_name_shortening=True, tool names are shortened to fit MCP limits
    long_name = "FDA_get_info_on_conditions_for_doctor_consultation_by_drug_name"

    # Execute tools using their full original name — ToolUniverse handles resolution
    tu.run_one_function({"name": long_name, "arguments": {}})

API Reference
=============

ToolUniverse Constructor
------------------------

.. code-block:: python

    ToolUniverse(
        ...,
        enable_name_shortening: bool = False
    )

**Parameters:**

- ``enable_name_shortening`` (bool): Enable automatic name shortening. Default: ``False``

**Example:**

.. code-block:: python

    tu = ToolUniverse(enable_name_shortening=True)


run_one_function()
------------------

Execute a tool function. Automatically accepts both shortened and original names when shortening is enabled.

.. code-block:: python

    tu.run_one_function(function_call_json: dict, ...) -> dict

**Behavior:**

- Accepts both shortened and original names when ``enable_name_shortening=True``
- Transparently resolves shortened → original
- Executes with original name

**Example:**

.. code-block:: python

    tu = ToolUniverse(enable_name_shortening=True)
    tu.load_tools()

    # Both names work identically (transparent resolution):
    result1 = tu.run_one_function({
        "name": "FDA_get_info_on_conditions_for_doctor_consultation_by_drug_name",
        "arguments": {"drug_name": "aspirin"}
    })

    result2 = tu.run_one_function({
        "name": "FDA_get_info_on_cond_for_doct_cons_by_drug_name",
        "arguments": {"drug_name": "aspirin"}
    })

    # result1 == result2 (transparent resolution!)

How It Works
============

Data Flow
---------

When you use ToolUniverse with MCP:

1. **User Configuration**: Set server key as ``"tu"`` in MCP config
2. **SMCP Startup**: Automatically enables shortening
3. **Tool Exposure**: Each tool name shortened and cached
4. **MCP Registration**: Tools registered with shortened names (e.g., ``mcp__tu__FDA_get_info_on_cond_for_doct_cons_by_drug_name``)
5. **User Calls Tool**: MCP client sends full MCP name
6. **FastMCP Processing**: Strips prefix, passes shortened name
7. **Transparent Resolution**: ToolUniverse resolves shortened → original
8. **Execution**: Tool executes with original name
9. **Result**: Returns to user

Key Insight
-----------

.. note::
   **MCP clients see ONLY shortened names**, but **ToolUniverse internally uses ONLY original names**. Resolution happens transparently in ``run_one_function()``, making the shortening completely invisible to users!

Limitations
===========

Known Limitations
-----------------

1. **Maximum 999 Collisions per Base Name**
 
 - Collision handling uses numeric suffixes (``_2``, ``_3``, ..., ``_999``)
 - Extremely unlikely in practice

2. **Shortened Names May Be Ambiguous**
 
 - Different full names may shorten to similar results
 - Collision handling adds suffixes to ensure uniqueness

3. **No Shortening for Query Methods**
 
 - Methods like ``get_tool_info()`` still use original names
 - No concrete use case for shortened names in queries yet

4. **Fixed Shortening Algorithm**
 
 - Algorithm is deterministic and not customizable per-tool
 - Designed to preserve meaning while maximizing uniqueness

Edge Cases Handled
------------------

 Collision handling - Numeric suffixes added 
 Very short names - Returned unchanged 
 Already at limit - Returned unchanged 
 Non-ASCII characters - Handled correctly 
 Empty strings - Handled gracefully 
 Repeated calls - Cached for consistency 

Performance
===========

Time Complexity
---------------

- **First shortening:** O(n) where n = name length (~0.001ms)
- **Cached lookup:** O(1) (~0.0001ms)
- **Resolution:** O(1) dict lookup (~0.0001ms)

Space Complexity
----------------

- **Per mapping:** ~50 bytes
- **1000 tools:** ~50KB memory
- **Negligible overhead**

Benchmark Results
-----------------

.. list-table::
   :header-rows: 1
   :widths: 50 25 25

   * - Operation
     - Time
     - Memory
   * - Shorten tool name (first call)
     - 0.001ms
     - 50 bytes
   * - Shorten tool name (cached)
     - 0.0001ms
     - 0 bytes
   * - Resolve shortened to original
     - 0.0001ms
     - 0 bytes
   * - Total overhead (1000 tools)
     - <1ms
     - <50KB

Migration Guide
===============

For MCP Users
-------------

**Before:**

.. code-block:: json

    {
      "mcpServers": {
        "tooluniverse": {
          "command": "tooluniverse-smcp-stdio"
        }
      }
    }

**After:**

.. code-block:: json

    {
      "mcpServers": {
        "tu": {
          "command": "tooluniverse-smcp-stdio"
        }
      }
    }

.. critical::
   Change the JSON key from ``"tooluniverse"`` to ``"tu"`` in your configuration!

For Python API Users
--------------------

**No changes required!** Name shortening is opt-in and disabled by default.

**To enable:**

.. code-block:: python

    # Old way (still works):
    tu = ToolUniverse()

    # New way (with shortening):
    tu = ToolUniverse(enable_name_shortening=True)

Testing and Validation
=======================

Run Tests
---------

.. code-block:: bash

    pytest tests/test_tool_name_shortening.py --no-cov -v

Expected Output
---------------

.. code-block:: text

    ======================= 13 passed, 13 warnings in 0.97s ========================

Validate MCP Compatibility
---------------------------

.. code-block:: python

    from tooluniverse import ToolUniverse

    tu = ToolUniverse(enable_name_shortening=True)
    tu.load_tools()

    # Verify all tools fit within MCP prefix + name limits
    mcp_prefix = "mcp__tu__"
    for tool_name in tu.all_tool_dict.keys():
        full_mcp_name = mcp_prefix + tool_name
        assert len(full_mcp_name) <= 64, f"Too long: {full_mcp_name}"

Troubleshooting
===============

Tool Not Found Errors
---------------------

If you get "tool not found" errors with shortened names:

1. Ensure ``enable_name_shortening=True`` was passed during initialization
2. The tool was loaded (``tu.load_tools()`` called)
3. The shortened name was generated via ``get_exposed_name()``

Names Still Too Long
--------------------

If shortened names still exceed your limit:

1. Adjust ``max_length`` parameter in ``get_exposed_name()``
2. Consider using a shorter server name in MCP configuration
3. Check if collision handling added a suffix

Summary
=======

Key Takeaways
-------------

1. **Automatic for MCP** - Works out of the box, no configuration
2. **Opt-in for Python** - Enable only when needed
3. **Transparent execution** - Both names work, resolution automatic
4. **Simple implementation** - 380 lines, well-tested
5. **Production ready** - All tests passing, validated with real tools

 When to Use
--------------

- **MCP integration** (automatic)
- **Custom MCP servers** (opt-in)
- **External systems with name length limits**
- **Testing and validation**

 When NOT to Use
------------------

- **Direct Python API** (no constraints)
- **Internal tool development** (use full names)
- **Tool discovery and search** (full names clearer)
- **Systems without length constraints**

See Also
========

- :doc:`mcp_support` - Complete MCP integration guide
- :doc:`../../api/tooluniverse` - ToolUniverse API reference
- :doc:`../tool_caller` - Tool execution documentation

.. note::
   For complete technical details, see ``NAME_SHORTENING_REPORT.md`` in the repository root.
