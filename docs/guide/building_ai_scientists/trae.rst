Trae Setup
==========

**Connect ToolUniverse to Trae**

Trae is an AI coding assistant with MCP support for enhanced tool integration.

Prerequisites
-------------

.. important:: ✅ **What you need:**
   
   - **Trae** - `Download here <https://trae.ai/>`_
   - **uv/uvx** - `Install uv <https://docs.astral.sh/uv/>`_

.. seealso:: `Trae MCP official guide <https://docs.trae.ai/ide/add-mcp-servers>`_

Setup Steps
-----------

.. card:: Step 1: Configure MCP in Trae
   :class-card: step-card

   **1.1. Open MCP Configuration**

   - Press **Ctrl+U** in Trae
   - Go to **AI Management** → **MCP** → **Configure Manually**
   - Or edit ``.trae/mcp.json`` in your project directory

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

   **1.3. Restart Trae**

   Close and reopen Trae to load the MCP server.

.. card:: Step 2: Install Agent Skills
   :class-card: step-card

   Install ToolUniverse skills for guided workflows:

   .. code-block:: bash

      npx skills add mims-harvard/ToolUniverse

.. card:: Step 3: Verify Connection
   :class-card: step-card

   Test the integration by asking Trae:

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
