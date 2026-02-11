OpenCode Setup
==============

**Connect ToolUniverse to OpenCode**

OpenCode is an open-source AI coding platform with MCP integration.

Prerequisites
-------------

.. important:: ✅ **What you need:**
   
   - **OpenCode** - `Download here <https://opencode.ai/>`_
   - **uv/uvx** - `Install uv <https://docs.astral.sh/uv/>`_

.. seealso:: `OpenCode MCP official guide <https://opencode.ai/docs/mcp-servers/>`_

Setup Steps
-----------

.. card:: Step 1: Configure MCP in OpenCode
   :class-card: step-card

   **1.1. Open MCP Configuration**

   - Edit ``opencode.json`` in your project directory
   - Or use ``opencode mcp add`` CLI command

   **1.2. Add ToolUniverse Configuration**

   Add this to your ``opencode.json`` config:

   .. code-block:: json

      {
        "mcp": {
          "tooluniverse": {
            "type": "local",
            "command": ["uvx", "tooluniverse"],
            "environment": {
              "PYTHONIOENCODING": "utf-8"
            }
          }
        }
      }

   **Note**: OpenCode uses ``"mcp"`` key (not ``"mcpServers"``), ``"type": "local"``, ``"command"`` as an array, and ``"environment"`` (not ``"env"``)

   **1.3. Restart OpenCode**

   Close and reopen OpenCode to load the MCP server.

.. card:: Step 2: Install Agent Skills
   :class-card: step-card

   Install ToolUniverse skills for guided workflows:

   .. code-block:: bash

      npx skills add mims-harvard/ToolUniverse

.. card:: Step 3: Verify Connection
   :class-card: step-card

   Test the integration by asking OpenCode:

   .. code-block:: text

      "List available tools from ToolUniverse"

   Or use the setup skill:

   .. code-block:: text

      "setup tooluniverse"

   You should see ToolUniverse tools available!

.. important:: 🔑 **Configure API Keys**
   
   Many tools require API keys. Set them up for full functionality:
   
   .. button-ref:: ../api_keys
      :color: primary
      :shadow:
   
      🔐 **API Keys Setup Guide**

Next Steps
----------

- :doc:`../skills_showcase` - Explore AI agent skills
- :doc:`../../tools/tools_config_index` - Browse 1000+ tools
- :doc:`../../help/troubleshooting` - Get help

.. button-ref:: index
   :color: secondary
   :shadow:
   :expand:

   ← **Back to Platform Selection**
