Boltz Mcp Loader Tools
======================

**Configuration File**: ``boltz_mcp_loader_tools.json``
**Tool Type**: Local
**Tools Count**: 1

This page contains all tools defined in the ``boltz_mcp_loader_tools.json`` configuration file.

Available Tools
---------------

**mcp_auto_loader_boltz** (Type: MCPAutoLoaderTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run Boltz2 docking and affinity prediction using MCP protocol

.. dropdown:: mcp_auto_loader_boltz tool specification

   **Tool Information:**

   * **Name**: ``mcp_auto_loader_boltz``
   * **Type**: ``MCPAutoLoaderTool``
   * **Description**: Run Boltz2 docking and affinity prediction using MCP protocol

   **Parameters:** No parameters required.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "mcp_auto_loader_boltz",
          "arguments": {
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
