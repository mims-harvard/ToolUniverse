Tool Caller Tutorial
==================

The Tool Caller is ToolUniverse's execution engine that handles tool instantiation, validation, and execution. It uses dynamic loading to efficiently manage hundreds of tools without loading them all at startup.

Python API Usage
----------------

ToolUniverse provides three ways to call tools through its Python API:

1. **Direct Import** (Simplest)
2. **Dynamic Access** (Convenient)  
3. **JSON Format** (Most Flexible)

Direct Import
~~~~~~~~~~~~~

Import and call tools directly:

.. code-block:: python

    from tooluniverse.tools import UniProt_get_entry_by_accession
    
    result = UniProt_get_entry_by_accession(accession="P05067")
    print(result)

Dynamic Access
~~~~~~~~~~~~~~

Access tools through the ToolUniverse instance:

.. code-block:: python

    from tooluniverse import ToolUniverse
    
    tu = ToolUniverse()
    result = tu.tools.UniProt_get_entry_by_accession(accession="P05067")
    print(result)

JSON Format (Recommended)
~~~~~~~~~~~~~~~~~~~~~~~~~

Use the ``run()`` method for maximum flexibility:

.. code-block:: python

    from tooluniverse import ToolUniverse
    
    tu = ToolUniverse()
    
    # Single tool call
    result = tu.run({
        "name": "UniProt_get_entry_by_accession",
        "arguments": {"accession": "P05067"}
    })
    
    # Multiple tool calls
    results = tu.run([
        {
            "name": "UniProt_get_entry_by_accession",
            "arguments": {"accession": "P05067"}
        },
        {
            "name": "OpenTargets_get_associated_targets_by_disease_efoId",
            "arguments": {"efoId": "EFO_0000249"}
        }
    ])
    
    print(results)

The ``run()`` method is recommended because it:
- Supports both single and multiple tool calls
- Provides better error handling
- Works with AI agent integration formats
- Handles dynamic tool loading automatically

Error Handling
--------------

The Tool Caller provides comprehensive error handling and validation:

.. code-block:: python

    from tooluniverse import ToolUniverse
    
    tu = ToolUniverse()
    
    # Example: Invalid tool name
    try:
        result = tu.run({
            "name": "nonexistent_tool",
            "arguments": {"param": "value"}
        })
    except Exception as e:
        print(f"Tool execution failed: {e}")
    
    # Example: Missing required parameter
    result = tu.run({
        "name": "UniProt_get_entry_by_accession",
        "arguments": {"wrong_param": "value"}  # Missing required 'accession'
    })
    # Returns: "Invalid function call: Missing required parameter: accession"

Tool Execution Flow
-------------------

The Tool Caller follows this systematic process:

1. **Parse Request**: Extract tool name and arguments
2. **Validate Tool**: Check if tool exists and is available
3. **Validate Arguments**: Ensure arguments match tool's parameter schema
4. **Load Tool**: Dynamically load tool if not cached
5. **Execute**: Call the tool's ``run()`` method
6. **Return Result**: Format and return the output

Performance Features
--------------------

**Dynamic Loading**: Tools are loaded only when first requested and cached for subsequent calls, minimizing memory usage.

**Thread Safety**: Multiple tools can execute concurrently without conflicts.

**Caching**: Loaded tools are cached to improve performance for repeated calls.

MCP Server Integration
----------------------

ToolUniverse provides MCP (Model Context Protocol) server capabilities for AI agent integration. This allows AI agents to discover and execute tools through a standardized protocol.

SMCP Server Overview
~~~~~~~~~~~~~~~~~~~~

The SMCP (Scientific Model Context Protocol) server extends standard MCP with scientific domain expertise and intelligent tool discovery.

Key Features:
- **Scientific Tool Integration**: Access to 1000+ specialized tools
- **AI-Powered Tool Discovery**: Multi-tiered intelligent search system
- **Full MCP Protocol Support**: Complete implementation of MCP specification
- **High-Performance Architecture**: Production-ready features

Server Setup
~~~~~~~~~~~~

Python Configuration
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from tooluniverse.smcp import SMCP

   # Create a basic MCP server
   server = SMCP(
       name="Scientific Research Server",
       tool_categories=["uniprot", "opentarget", "ChEMBL"],
       search_enabled=True,
       max_workers=10
   )

   # Start the server
   server.run_simple(
       transport="http",
       host="localhost",
       port=8000
   )

Command Line Setup
^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   # Start MCP server with specific configuration
   tooluniverse-smcp \
       --port 8000 \
       --host 0.0.0.0 \
       --categories "uniprot" "opentarget" "ChEMBL" \
       --max-workers 10 \
       --verbose

   # List all available tools
   tooluniverse-smcp --list-tools

   # List available categories
   tooluniverse-smcp --list-categories

MCP Client Integration
~~~~~~~~~~~~~~~~~~~~~~

Python MCP Client Examples
^^^^^^^^^^^^^^^^^^^^^^^^^^^

**STDIO Client:**

.. code-block:: python

   from mcp.client.stdio import stdio_client
   from mcp.client.session import ClientSession
   from mcp import StdioServerParameters
   import asyncio

   async def connect_to_tooluniverse():
       # Create stdio server parameters
       server_params = StdioServerParameters(
           command="tooluniverse-smcp-stdio",
           args=[]
       )

       # Create stdio client transport
       async with stdio_client(server_params) as (read, write):
           # Create client session
           async with ClientSession(read, write) as session:
               # Initialize the session
               await session.initialize()

               # List available tools
               tools_result = await session.list_tools()
               print(f"Available tools: {len(tools_result.tools)}")

               # Call a tool
               result = await session.call_tool(
                   "UniProt_get_entry_by_accession",
                   {"accession": "P05067"}
               )

               return result

   # Run the client
   result = asyncio.run(connect_to_tooluniverse())

**HTTP Client:**

.. code-block:: python

   from mcp.client.session import ClientSession
   from mcp.client.streamable_http import streamablehttp_client
   import asyncio

   async def connect_via_http():
       # Connect to HTTP MCP server
       async with streamablehttp_client("http://localhost:8000/mcp") as (read, write, get_session_id):
           async with ClientSession(read, write) as session:
               await session.initialize()

               # List available tools
               tools_result = await session.list_tools()
               print(f"Available tools: {len(tools_result.tools)}")

               # Call a tool
               result = await session.call_tool(
                   "UniProt_get_entry_by_accession",
                   {"accession": "P05067"}
               )

               return result

   # Run the client
   result = asyncio.run(connect_via_http())

cURL Client Examples
^^^^^^^^^^^^^^^^^^^^^

You can also interact with ToolUniverse MCP servers directly using cURL commands:

.. code-block:: bash

   # List available tools
   curl -X POST http://localhost:8000/mcp \
     -H "Content-Type: application/json" \
     -H "Accept: application/json, text/event-stream" \
     -d '{
       "jsonrpc": "2.0",
       "id": 1,
       "method": "tools/list",
       "params": {}
     }'

   # Call a tool
   curl -X POST http://localhost:8000/mcp \
     -H "Content-Type: application/json" \
     -H "Accept: application/json, text/event-stream" \
     -d '{
       "jsonrpc": "2.0",
       "id": 2,
       "method": "tools/call",
       "params": {
         "name": "UniProt_get_entry_by_accession",
         "arguments": {
           "accession": "P05067"
         }
       }
     }'

Important Notes for MCP Clients
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

1. **Required Headers**: ToolUniverse MCP servers use the streamable-http protocol, which requires:
   - `Content-Type: application/json`
   - `Accept: application/json, text/event-stream`

2. **JSON-RPC 2.0 Format**: All requests must follow the JSON-RPC 2.0 specification with:
   - `jsonrpc: "2.0"`
   - `id`: Unique request identifier
   - `method`: The MCP method to call
   - `params`: Method parameters

3. **Tool Arguments**: When calling tools, arguments must match the tool's parameter schema exactly.

.. seealso::
   For detailed MCP server setup and usage, see :doc:`building_ai_scientists/mcp_support`

.. seealso::

   :doc:`../api/modules` - Complete API reference
