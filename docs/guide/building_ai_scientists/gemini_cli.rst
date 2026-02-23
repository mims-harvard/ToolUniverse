Gemini CLI Setup
================

**Connect ToolUniverse to Google Gemini CLI**

Gemini CLI is Google's open-source AI agent for the terminal with native MCP support.

.. tip:: 🚀 **Fastest setup — no installation needed**

   Open Gemini CLI and paste this single message:

   .. code-block:: text

      Please read https://raw.githubusercontent.com/mims-harvard/ToolUniverse/main/skills/setup-tooluniverse/SKILL.md and follow it to help me set up ToolUniverse.

   Gemini CLI will fetch the setup guide from GitHub and walk you through everything interactively.

Prerequisites
-------------

.. important:: ✅ **What you need:**
   
   - **Node.js 18+** - `Download here <https://nodejs.org/>`_
   - **Gemini CLI** - ``npm install -g @google/gemini-cli``
   - **uv/uvx** - `Install uv <https://docs.astral.sh/uv/>`_

.. seealso:: `Gemini CLI MCP official guide <https://google-gemini.github.io/gemini-cli/docs/tools/mcp-server.html>`_

Setup Steps
-----------

.. card:: Step 1: Configure MCP in Gemini CLI
   :class-card: step-card

   **1.1. Open MCP Configuration**

   Edit (or create) ``~/.gemini/settings.json``:

   **1.2. Add ToolUniverse Configuration**

   Add this to your ``settings.json``:

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

   **1.3. Save the file**

   Gemini CLI reads ``settings.json`` on startup. No server restart is needed.

.. card:: Step 2: Install Agent Skills
   :class-card: step-card

   Install ToolUniverse skills for guided workflows:

   .. code-block:: bash

      npx skills add mims-harvard/ToolUniverse

.. card:: Step 3: Launch and Verify
   :class-card: step-card

   Start the Gemini CLI:

   .. code-block:: bash

      gemini

   Then ask:

   .. code-block:: text

      "List available tools from ToolUniverse"

   Or use the setup skill:

   .. code-block:: text

      "setup tooluniverse"

   You should see ToolUniverse tools available!

.. important:: 🔑 **Configure API Keys**
   
   Many tools require API keys. Set them up for full functionality:
   
   .. button-ref:: ../../api_keys
      :color: primary
      :shadow:
   
      🔐 **API Keys Setup Guide**

Example Queries
---------------

.. tab-set::

   .. tab-item:: Protein Research

      .. code-block:: text

         "Find protein P05067, get its structure from PDB,
         and analyze its interactions"

   .. tab-item:: Drug Safety

      .. code-block:: text

         "Analyze safety profile of aspirin using FDA
         adverse event data"

   .. tab-item:: Literature

      .. code-block:: text

         "Search recent papers about mRNA vaccines,
         summarize findings"

Advanced Configuration
----------------------

.. dropdown:: 🔑 Tool-Specific API Keys
   :animate: fade-in-slide-down

   Add ToolUniverse API keys directly in ``settings.json``:

   .. code-block:: json

      {
        "mcpServers": {
          "tooluniverse": {
            "command": "uvx",
            "args": ["--refresh", "tooluniverse"],
            "env": {
              "PYTHONIOENCODING": "utf-8",
              "NCBI_API_KEY": "your_key",
              "SEMANTIC_SCHOLAR_API_KEY": "your_key"
            }
          }
        }
      }

.. dropdown:: 🎛️ Project-Specific Config
   :animate: fade-in-slide-down

   Place a ``.gemini/settings.json`` in your project directory to use project-scoped MCP settings that override the user-level config.

Troubleshooting
---------------

.. dropdown:: ❌ Tools not found
   :color: danger

   - Ensure ``uvx`` is installed: ``uvx --version``
   - Check that ``settings.json`` is valid JSON
   - Restart Gemini CLI after editing the config

.. dropdown:: ⚠️ Rate limit errors
   :color: warning

   Add API keys in ``settings.json`` ``env`` section (see Advanced Configuration)

Next Steps
----------

- :doc:`../../skills_showcase` - Explore AI agent skills
- :doc:`../../tools/tools_config_index` - Browse 1000+ tools
- :doc:`../../help/troubleshooting` - Get help

.. button-ref:: index
   :color: secondary
   :shadow:
   :expand:

   ← **Back to Platform Selector**

.. seealso::
   - :doc:`../tooluniverse_case_study` - End-to-end example
   - :doc:`../../help/troubleshooting` - Common issues
