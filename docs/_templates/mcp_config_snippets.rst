.. This file contains reusable MCP configuration snippets.
   Include these snippets in documentation to maintain consistency.
   
   Usage:
   .. include:: ../_templates/mcp_config_snippets.rst
      :start-after: .. _mcp-basic-config:
      :end-before: .. _mcp-custom-port:

.. _mcp-basic-config:

**Basic MCP Configuration (Default)**

.. code-block:: json

   {
     "mcpServers": {
       "tooluniverse": {
         "command": "tooluniverse-smcp-stdio",
         "args": ["--compact-mode"],
         "timeout": 600
       }
     }
   }

.. _mcp-custom-port:

**Custom Port Configuration (HTTP Server)**

.. code-block:: json

   {
     "mcpServers": {
       "tooluniverse": {
         "command": "tooluniverse-smcp",
         "args": ["--port", "8001", "--compact-mode"],
         "timeout": 600
       }
     }
   }

.. _mcp-stdio-config:

**STDIO Configuration (Claude Desktop)**

For Claude Desktop, use STDIO transport:

.. code-block:: json

   {
     "mcpServers": {
       "tooluniverse": {
         "command": "tooluniverse-smcp-stdio",
         "args": ["--compact-mode"]
       }
     }
   }

**Configuration file location**:

- **macOS**: ``~/Library/Application Support/Claude/claude_desktop_config.json``
- **Windows**: ``%APPDATA%\Claude\claude_desktop_config.json``
- **Linux**: ``~/.config/Claude/claude_desktop_config.json``

.. _mcp-multiple-instances:

**Multiple Server Instances**

Run multiple ToolUniverse instances with different configurations:

.. code-block:: json

   {
     "mcpServers": {
       "tooluniverse-default": {
         "command": "tooluniverse-smcp",
         "args": ["--port", "8000", "--compact-mode"],
         "timeout": 600
       },
       "tooluniverse-proteomics": {
         "command": "tooluniverse-smcp",
         "args": [
           "--port", "8001",
           "--load", "community/proteomics-toolkit",
           "--compact-mode"
         ],
         "timeout": 600
       }
     }
   }

.. _mcp-with-hooks:

**Configuration with Hooks**

Enable output processing hooks:

.. code-block:: json

   {
     "mcpServers": {
       "tooluniverse": {
         "command": "tooluniverse-smcp-stdio",
         "args": [
           "--compact-mode",
           "--hooks-enabled",
           "--hook-type", "SummarizationHook"
         ]
       }
     }
   }

.. _mcp-workspace-config:

**Workspace Configuration**

Load a workspace/space configuration:

.. code-block:: json

   {
     "mcpServers": {
       "tooluniverse": {
         "command": "tooluniverse-smcp-stdio",
         "args": [
           "--compact-mode",
           "--load", "community/drug-discovery"
         ]
       }
     }
   }

.. _mcp-category-filter:

**Category Filtering**

Load only specific tool categories:

.. code-block:: json

   {
     "mcpServers": {
       "tooluniverse": {
         "command": "tooluniverse-smcp-stdio",
         "args": [
           "--compact-mode",
           "--categories", "uniprot", "chembl", "opentarget"
         ]
       }
     }
   }

.. _mcp-fast-startup:

**Fast Startup Configuration**

Optimize for faster startup (300s timeout, minimal loading):

.. code-block:: json

   {
     "mcpServers": {
       "tooluniverse": {
         "command": "tooluniverse-smcp-stdio",
         "args": ["--compact-mode"],
         "timeout": 300
       }
     }
   }

.. _mcp-debug-mode:

**Debug Mode**

Enable debug logging:

.. code-block:: bash

   # Set environment variable before starting
   export TOOLUNIVERSE_LOG_LEVEL=DEBUG
   tooluniverse-smcp-stdio --compact-mode

Or in configuration:

.. code-block:: json

   {
     "mcpServers": {
       "tooluniverse": {
         "command": "tooluniverse-smcp-stdio",
         "args": ["--compact-mode", "--debug"],
         "env": {
           "TOOLUNIVERSE_LOG_LEVEL": "DEBUG"
         }
       }
     }
   }

.. _mcp-standard-settings:

**Standard Settings Reference**

Common MCP server configuration options:

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Setting
     - Default
     - Description
   * - ``command``
     - (required)
     - CLI command to start server: ``tooluniverse-smcp`` or ``tooluniverse-smcp-stdio``
   * - ``args``
     - ``[]``
     - Command-line arguments array
   * - ``timeout``
     - 600
     - Timeout in seconds (600s = 10 minutes)
   * - ``--compact-mode``
     - false
     - Enable compact tool names (recommended)
   * - ``--port``
     - 8000
     - Port number (HTTP server only)
   * - ``--host``
     - 127.0.0.1
     - Host address (HTTP server only)
   * - ``--categories``
     - all
     - Comma-separated list of tool categories to load
   * - ``--load``
     - (none)
     - Load workspace/space configuration
   * - ``--hooks-enabled``
     - false
     - Enable output processing hooks

.. _mcp-troubleshooting:

**Common Issues**

**Server won't start**:
- Check if port is already in use: ``lsof -i :8000``
- Try a different port: ``--port 8001``
- Verify ToolUniverse is installed: ``pip show tooluniverse``

**Timeout errors**:
- Increase timeout value: ``"timeout": 900``
- Use category filtering to load fewer tools
- Enable fast startup mode

**Tools not loading**:
- Run health check: ``tooluniverse-doctor``
- Check for missing dependencies
- Review server logs for errors

See :doc:`../help/troubleshooting` for more solutions.
