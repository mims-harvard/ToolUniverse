MCP Support
===========

**Complete guide to Model Context Protocol (MCP) integration with ToolUniverse**

ToolUniverse provides comprehensive support for the Model Context Protocol (MCP), enabling seamless integration with AI scientists, reasoning models, and agentic systems. This guide covers everything you need to know about using ToolUniverse through MCP.

What is MCP?
------------

The Model Context Protocol (MCP) is a standardized protocol that enables AI scientists to securely connect to external tools and data sources. ToolUniverse implements MCP through the Scientific Model Context Protocol (SMCP), extending standard MCP capabilities with scientific domain expertise.

Why Use MCP?
------------

**Without MCP**:

- Write Python code to call each tool manually
- Manually integrate tools with each AI assistant
- Programming required for every query
- Tools not discoverable by AI assistants
- Separate setup for each application

**With MCP**:

- AI assistants autonomously discover and call tools
- Conversational access to 1000+ scientific tools  
- Non-programmers can leverage scientific databases
- Single setup works across multiple AI assistants (Claude, Cursor, etc.)
- AI can intelligently chain tools based on research questions

**Use MCP when**:

✅ Building AI agent workflows for research  
✅ Enabling conversational scientific data access  
✅ Integrating with Claude Desktop, Cursor, or other AI assistants  
✅ Non-technical users need to query scientific databases  
✅ Want AI to autonomously discover and compose tool sequences

**Use Python API when**:

✅ Writing reproducible analysis scripts  
✅ Building custom applications with programmatic control  
✅ Need fine-grained error handling and control flow  
✅ Batch processing or automated pipelines  
✅ Integration with existing Python codebase

.. seealso::
   For Python API usage, see :doc:`../coding_api` and :doc:`../../getting_started`.

Key Benefits
~~~~~~~~~~~~

- **Standardized Integration**: Connect to any MCP-compatible AI scientist
- **Scientific Tool Access**: Direct access to 1000+ scientific tools
- **Intelligent Discovery**: AI-powered tool search and recommendation
- **Secure Communication**: Standardized protocol ensures secure tool execution
- **Production Ready**: High-performance architecture for real-world applications

MCP Architecture Overview
-------------------------

.. code-block:: text

   AI Scientist (Claude, ChatGPT, Gemini, etc.)
           │
           │ MCP Protocol
           │
   ┌─────────────────┐
   │ ToolUniverse    │ ← MCP Server
   │   MCP Server    │
   └─────────────────┘
           │
           │ Tool Execution
           │
   ┌─────────────────┐
   │ Scientific      │
   │ Tools (1000+)   │
   └─────────────────┘

ToolUniverse MCP Implementation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

ToolUniverse provides three main MCP server implementations:

1. **`tooluniverse-smcp`** - Full-featured server with configurable transport (HTTP, SSE, stdio)
2. **`tooluniverse-smcp-stdio`** - Specialized server for stdio transport (optimized for desktop AI applications)

All servers expose the same comprehensive set of 1000+ scientific tools through the MCP protocol.

Quick Start
-----------

For basic MCP server setup and configuration, see the comprehensive guide in :ref:`mcp-server-functions`.

CLI Options Reference
---------------------

The following are commonly used command-line flags for ToolUniverse MCP servers.

.. code-block:: text

   tooluniverse-smcp [OPTIONS]

   --port INT                     Server port (HTTP/SSE). Default: 8000
   --host TEXT                    Bind host for HTTP/SSE. Default: 0.0.0.0
   --transport [http|stdio|sse]   Transport protocol. Default: http
   --name TEXT                    Server display name
   --max-workers INT              Worker pool size for tool execution
   --verbose                      Enable verbose logs

   # Tool selection
   --categories STR...            Include only these categories
   --exclude-categories STR...    Exclude these categories
   --include-tools STR...         Include only these tool names
   --tools-file PATH              File with one tool name per line
   --include-tool-types STR...    Include only these tool types
   --exclude-tool-types STR...    Exclude these tool types
   --tool-config-files TEXT       Mapping like "custom:/path/to/custom.json"

   # Compact mode
   --compact-mode                 Enable compact mode (only expose core tools)

   # Hooks
   --hooks-enabled                Enable hooks (default: False)
   --hook-type [SummarizationHook|FileSaveHook]
   --hook-config-file PATH        JSON config for hooks

.. code-block:: text

   tooluniverse-smcp-stdio [OPTIONS]

   --name TEXT                    Server display name
   --categories STR...            Include only these categories
   --include-tools STR...         Include only these tool names
   --tools-file PATH              File with one tool name per line
   --include-tool-types STR...    Include only these tool types
   --exclude-tool-types STR...    Exclude these tool types
   --compact-mode                 Enable compact mode (only expose core tools)
   --hooks                        Enable hooks (default: disabled for stdio)
   --hook-type [SummarizationHook|FileSaveHook]
   --hook-config-file PATH        JSON config for hooks

Configuration
-------------

All MCP servers support configuration through command-line arguments. See the CLI Options Reference above for available configuration options.

Configuration Files
-------------------

Example tools file (one tool per line, lines starting with # are comments):

.. code-block:: text

   # tools.txt
   OpenTargets_get_associated_targets_by_disease_efoId
   Tool_Finder_LLM
   ChEMBL_search_similar_molecules
   # Tool_Finder_Keyword

Example hook config file:

.. code-block:: json

   {
     "SummarizationHook": {
       "max_tokens": 2048,
       "summary_style": "concise"
     },
     "FileSaveHook": {
       "output_dir": "/tmp/tu_outputs",
       "filename_template": "{tool}_{timestamp}.json"
     }
   }

Client Integration Examples
---------------------------

Python MCP client (conceptual) connecting to HTTP server:

.. code-block:: python

   import requests

   # Discover tools
   tools = requests.get("http://127.0.0.1:8000/mcp/tools").json()

   # Execute a tool
   payload = {
       "name": "UniProt_get_entry_by_accession",
       "arguments": {"accession": "P04637"}
   }
   result = requests.post("http://127.0.0.1:8000/mcp/run", json=payload).json()
   print(result)

JavaScript MCP client (conceptual) against HTTP server:

.. code-block:: javascript

   const fetch = require('node-fetch');

   async function run() {
     const toolsResp = await fetch('http://127.0.0.1:8000/mcp/tools');
     const tools = await toolsResp.json();
     console.log('Tools:', tools.length);

     const resp = await fetch('http://127.0.0.1:8000/mcp/run', {
       method: 'POST',
       headers: { 'Content-Type': 'application/json' },
       body: JSON.stringify({
         name: 'UniProt_get_entry_by_accession',
         arguments: { accession: 'P04637' }
       })
     });
   const result = await resp.json();
   console.log(result);
 }
  run();



Claude Desktop stdio registration (example):

.. code-block:: json

   {
     "mcpServers": {
       "tooluniverse": {
         "command": "tooluniverse-smcp-stdio",
         "args": ["--categories", "uniprot", "ChEMBL", "opentarget", "--hooks", "--hook-type", "SummarizationHook"]
       }
     }
   }

MCP Server Configuration
-------------------------

Transport Options
~~~~~~~~~~~~~~~~~

ToolUniverse MCP servers support multiple transport protocols:

**HTTP Transport** (Default)
   - Best for web-based applications and remote access
   - Supports RESTful API endpoints
   - Configurable host and port

**STDIO Transport**
   - Optimized for desktop AI applications
   - Direct process communication
   - Lower latency for local applications

**Server-Sent Events (SSE)**
   - Real-time streaming capabilities
   - Suitable for interactive applications
   - Supports long-running operations

Tool Selection
~~~~~~~~~~~~~~~

Configure which tools are available through the MCP server. For detailed configuration options including category-based loading, tool-specific loading, and type-based filtering, see :ref:`category-based-loading`, :ref:`tool-specific-loading`, and :ref:`type-based-filtering`.

Advanced Configuration
~~~~~~~~~~~~~~~~~~~~~~~

Hook Configuration
^^^^^^^^^^^^^^^^^^^

Enable intelligent output processing hooks for MCP servers. For comprehensive hook configuration including SummarizationHook and FileSaveHook, see :ref:`hook-configuration`.

.. seealso::
   **Detailed Guide**: :doc:`../hooks/server_stdio_hooks` - Complete hook integration tutorial

Performance Tuning
^^^^^^^^^^^^^^^^^^

Optimize server performance for your use case. For detailed performance configuration options, see :ref:`server-configuration`.

AI Scientist Integration
------------------------

ToolUniverse MCP servers are compatible with major AI scientists and platforms:

Claude Desktop
~~~~~~~~~~~~~~

Integrate ToolUniverse with Claude Desktop for powerful desktop-based scientific research.

.. seealso::
   For complete Claude Desktop integration, see :doc:`claude_desktop`

   **Tutorial**: :doc:`../../tutorials/aiscientists/MCP_for_Claude` - Step-by-step Claude Desktop setup

ChatGPT API
~~~~~~~~~~~

Connect ToolUniverse to ChatGPT API for programmatic AI-scientist workflows.

.. seealso::
   For ChatGPT API integration, see :doc:`chatgpt_api`

Gemini CLI
~~~~~~~~~~

Use ToolUniverse with Gemini CLI for command-line scientific research.

.. seealso::
   For Gemini CLI integration, see :doc:`gemini_cli`

   **Tutorial**: :doc:`../../tutorials/aiscientists/MCP_for_Gemini_CLI` - Complete Gemini CLI setup guide

Claude Code
~~~~~~~~~~~

Integrate ToolUniverse with Claude Code for IDE-based scientific development.

.. seealso::
   For Claude Code integration, see :doc:`claude_code`

Qwen Code
~~~~~~~~~

Connect ToolUniverse to Qwen Code for terminal-based scientific workflows.

.. seealso::
   For Qwen Code integration, see :doc:`qwen_code`

GPT Codex CLI
~~~~~~~~~~~~~

Use ToolUniverse with GPT Codex CLI for advanced command-line research capabilities.

.. seealso::
   For GPT Codex CLI integration, see :doc:`codex_cli`

MCP Protocol Details
--------------------

Tool Discovery
~~~~~~~~~~~~~~

MCP clients can discover available tools through the standard MCP protocol. For detailed tool discovery methods and examples, see :ref:`mcp-server-integration`.

Tool Execution
~~~~~~~~~~~~~~

Execute tools through the MCP protocol. For comprehensive tool execution patterns and MCP client examples, see :ref:`mcp-client-integration`.

Error Handling
~~~~~~~~~~~~~~

MCP provides standardized error handling. For detailed error handling patterns and troubleshooting, see :ref:`error-handling-validation`.

MCP Server Management
---------------------

Server Status
~~~~~~~~~~~~~

Monitor MCP server status and health. For server management commands and status monitoring, see :ref:`discovery-commands`.

Logging and Debugging
~~~~~~~~~~~~~~~~~~~~~

Enable comprehensive logging for debugging. For detailed logging configuration and debugging options, see :ref:`tooluniverse-logging-configuration`.

Performance Monitoring
~~~~~~~~~~~~~~~~~~~~~~~

Monitor MCP server performance. For performance monitoring and optimization, see :ref:`performance-optimization`.

Troubleshooting
---------------

Common Issues
~~~~~~~~~~~~~~

**MCP Server Not Starting**
   - Check if port is available
   - Verify ToolUniverse installation
   - Check server logs for error messages

**Tools Not Available**
   - Verify tool categories are loaded
   - Check tool names are correct
   - Ensure tools are not excluded

**Connection Issues**
   - Verify transport protocol matches client expectations
   - Check firewall settings for HTTP transport
   - Ensure proper authentication for remote connections

**Performance Issues**
   - Increase worker threads
   - Enable caching for repeated tool calls
   - Use specific tool categories instead of loading all tools

For comprehensive troubleshooting guide, see :ref:`troubleshooting`.

Debug Commands
~~~~~~~~~~~~~~

Useful debugging commands and validation methods. For complete debugging command reference, see :ref:`discovery-commands`.

Best Practices
--------------

Security
~~~~~~~~

- Use HTTPS in production environments
- Implement proper authentication and authorization
- Regularly update ToolUniverse and MCP dependencies
- Monitor server logs for suspicious activity

Performance
~~~~~~~~~~

- Load only necessary tool categories
- Use appropriate worker thread counts
- Enable caching for frequently used tools
- Monitor server metrics and adjust configuration

Reliability
~~~~~~~~~~~

- Implement proper error handling in MCP clients
- Use retry mechanisms for transient failures
- Monitor server health and restart if needed
- Keep backup configurations for critical deployments

For detailed best practices and production deployment guidance, see :ref:`performance-optimization`.

Related Documentation
--------------------

Core MCP Components
~~~~~~~~~~~~~~~~~~~

- :doc:`../tool_caller` - Tool execution engine and MCP server implementation
- :doc:`../loading_tools` - Tool loading and MCP server configuration
- :doc:`../interaction_protocol` - ToolUniverse interaction protocol and MCP schema
- :doc:`../../api/modules` - Complete API documentation

AI Agent Platform Setup
~~~~~~~~~~~~~~~~~~~~~~~

- :doc:`index` - Platform setup guide
- :doc:`claude_desktop` - Claude Desktop setup
- :doc:`chatgpt_api` - ChatGPT API setup
- :doc:`gemini_cli` - Gemini CLI setup
- :doc:`claude_code` - Claude Code setup
- :doc:`qwen_code` - Qwen Code setup
- :doc:`codex_cli` - Codex CLI setup

MCP Tutorials and Guides
~~~~~~~~~~~~~~~~~~~~~~~~

- :doc:`../../tutorials/aiscientists/MCP_Server_Tutorial` - Converting tools to MCP servers
- :doc:`../../tutorials/aiscientists/MCP_for_Claude` - Claude Desktop MCP integration
- :doc:`../../tutorials/aiscientists/MCP_for_Gemini_CLI` - Gemini CLI MCP integration
- :doc:`../../tutorials/aiscientists/adding_mcp_tools` - Adding MCP tools to ToolUniverse
- :doc:`../../tutorials/addtools/mcp_tool_registration_en` - MCP tool registration tutorial

Advanced Features
~~~~~~~~~~~~~~~~~

- :doc:`compact_mode` - Optimize context window usage by exposing only core tools
- :doc:`../hooks/server_stdio_hooks` - Output processing hooks for MCP servers
- :doc:`../scientific_workflows` - Building complex workflows with MCP
- :doc:`../tool_composition` - Composing tools for advanced research
- :doc:`../streaming_tools` - Streaming support for MCP tools

MCP Tools and Examples
~~~~~~~~~~~~~~~~~~~~~~

- :doc:`../../tools/mcp_client_tools_example` - MCP client tools example
- :doc:`../../tools/expert_feedback_tools` - Expert feedback MCP tools
- :doc:`../../tools/txagent_client_tools` - TXAgent client MCP tools

Examples and Tutorials
~~~~~~~~~~~~~~~~~~~~~~

- :doc:`../examples` - Practical MCP usage examples
- :doc:`index` - Comprehensive tutorials for MCP integration with AI systems

API Reference
~~~~~~~~~~~~~

- :doc:`../../api/modules` - Complete API documentation

External Resources
~~~~~~~~~~~~~~~~~~

- `Model Context Protocol Specification <https://modelcontextprotocol.io/>`_
- `MCP GitHub Repository <https://github.com/modelcontextprotocol>`_
- `ToolUniverse GitHub Repository <https://github.com/tooluniverse/tooluniverse>`_

Summary
-------

ToolUniverse's MCP support provides a powerful, standardized way to integrate scientific tools with AI scientists. The SMCP implementation extends standard MCP capabilities with scientific domain expertise, making it easy to build sophisticated AI-scientist workflows.

Key takeaways:

- **Easy Integration**: Simple setup with major AI scientists
- **Comprehensive Tools**: Access to 1000+ scientific tools through MCP
- **Flexible Configuration**: Multiple transport options and tool selection
- **Production Ready**: High-performance, secure, and reliable
- **Extensive Documentation**: Complete guides for all major AI platforms

Start with the :doc:`index` guide to connect ToolUniverse to your AI agent platform.
