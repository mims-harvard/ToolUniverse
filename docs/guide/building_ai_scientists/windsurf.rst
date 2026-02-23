Windsurf Setup
==============

**Connect ToolUniverse to Windsurf**

Windsurf is an agentic IDE with autonomous coding agents and MCP support.

Prerequisites
-------------

.. important:: ✅ **What you need:**
   
   - **Windsurf** - `Download here <https://windsurf.com/>`_
   - **uv/uvx** - `Install uv <https://docs.astral.sh/uv/>`_

.. seealso:: `Windsurf MCP official guide <https://docs.windsurf.com/windsurf/cascade/mcp>`_

Setup Steps
-----------

.. card:: Step 1: Configure MCP in Windsurf
   :class-card: step-card

   **1.1. Open MCP Configuration**

   - Click the **MCPs icon** in the top-right of the Cascade panel
   - Or go to **Windsurf Settings** → **Cascade** → **MCP Servers**
   - Or edit ``~/.codeium/windsurf/mcp_config.json`` directly

   **1.2. Add ToolUniverse Configuration**

   Add this to your MCP config:

   .. code-block:: json

      {
        "mcpServers": {
          "tooluniverse": {
            "command": "uvx",
            "args": ["--refresh", "tooluniverse"],
            "env": {
              "PYTHONIOENCODING": "utf-8"
            }
          }
        }
      }

   **1.3. Restart Windsurf**

   Close and reopen Windsurf to load the MCP server.

.. card:: Step 2: Install Agent Skills
   :class-card: step-card

   Install ToolUniverse skills for guided workflows:

   .. code-block:: bash

      npx skills add mims-harvard/ToolUniverse

.. card:: Step 3: Verify Connection
   :class-card: step-card

   Test the integration by asking Windsurf:

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
