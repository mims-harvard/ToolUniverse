Cline Setup
===========

**Connect ToolUniverse to Cline**

Cline is a VS Code extension that brings AI coding assistance with MCP support.

Prerequisites
-------------

.. important:: ✅ **What you need:**
   
   - **VS Code** - `Download here <https://code.visualstudio.com/>`_
   - **Cline Extension** - `Install from VS Code Marketplace <https://marketplace.visualstudio.com/items?itemName=saoudrizwan.claude-dev>`_
   - **uv/uvx** - `Install uv <https://docs.astral.sh/uv/>`_

.. seealso:: `Cline MCP official guide <https://docs.cline.bot/mcp/configuring-mcp-servers>`_

Setup Steps
-----------

.. card:: Step 1: Configure MCP in Cline
   :class-card: step-card

   **1.1. Open MCP Configuration**

   - Click the **MCP Servers** icon in the Cline top navigation bar
   - Select the **Configure** tab → **Configure MCP Servers**
   - Or edit ``cline_mcp_settings.json`` in VS Code extension globalStorage

   **1.2. Add ToolUniverse Configuration**

   Add this to your MCP config:

   .. code-block:: json

      {
        "mcpServers": {
          "tooluniverse": {
            "command": "uvx",
            "args": ["tooluniverse"],
            "env": {
              "PYTHONIOENCODING": "utf-8"
            }
          }
        }
      }

   **1.3. Reload VS Code**

   Reload VS Code window to load the MCP server.

.. card:: Step 2: Install Agent Skills
   :class-card: step-card

   Install ToolUniverse skills for guided workflows:

   .. code-block:: bash

      npx skills add mims-harvard/ToolUniverse

.. card:: Step 3: Verify Connection
   :class-card: step-card

   Test the integration by asking Cline:

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
