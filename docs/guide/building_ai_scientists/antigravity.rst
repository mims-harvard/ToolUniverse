Antigravity Setup
=================

**Connect ToolUniverse to Antigravity**

Antigravity is Google's free agentic IDE with parallel agent execution and MCP support.

Prerequisites
-------------

.. important:: ✅ **What you need:**
   
   - **Antigravity** - `Download here <https://antigravity.codes/>`_
   - **uv/uvx** - `Install uv <https://docs.astral.sh/uv/>`_

.. seealso:: `Antigravity MCP official guide <https://antigravity.codes/blog/antigravity-mcp-tutorial>`_

Setup Steps
-----------

.. card:: Step 1: Configure MCP in Antigravity
   :class-card: step-card

   **1.1. Open MCP Configuration**

   - Click the **"..."** menu at the top of the Agent panel
   - Select **MCP Servers** → **Manage MCP Servers** → **View raw config**
   - Or edit ``mcp_config.json`` directly

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

   **1.3. Restart Antigravity**

   Close and reopen Antigravity to load the MCP server.

.. card:: Step 2: Install Agent Skills
   :class-card: step-card

   Install ToolUniverse skills for guided workflows:

   .. code-block:: bash

      npx skills add mims-harvard/ToolUniverse

.. card:: Step 3: Verify Connection
   :class-card: step-card

   Test the integration by asking Antigravity:

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
