Cursor Setup
============

**Connect ToolUniverse to Cursor**

Cursor is an AI-first code editor with native MCP support. Follow these steps to integrate ToolUniverse.

Prerequisites
-------------

.. important:: ✅ **What you need:**
   
   - **Cursor** - `Download here <https://cursor.com/>`_
   - **uv/uvx** - `Install uv <https://docs.astral.sh/uv/>`_

.. seealso:: `Cursor MCP official guide <https://docs.cursor.com/context/model-context-protocol>`_

Setup Steps
-----------

.. card:: Step 1: Configure MCP in Cursor
   :class-card: step-card

   **1.1. Open MCP Settings**

   - In Cursor, go to **Settings** → **MCP** → **Add new global MCP server**
   - Or edit ``~/.cursor/mcp.json`` directly

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

   **1.3. Restart Cursor**

   Close and reopen Cursor to load the MCP server.

.. card:: Step 2: Install Agent Skills
   :class-card: step-card

   Install ToolUniverse skills for guided workflows:

   .. code-block:: bash

      npx skills add mims-harvard/ToolUniverse

.. card:: Step 3: Verify Connection
   :class-card: step-card

   Test the integration by asking Cursor:

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
