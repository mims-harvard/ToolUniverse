Qwen Code Setup
===============

**Connect ToolUniverse to Qwen Code**

Qwen Code integration provides AI-powered development with ToolUniverse's scientific tools ecosystem.

Prerequisites
-------------

.. important:: ✅ **What you need:**
   
   - **Qwen Code** - `GitHub <https://github.com/QwenLM/qwen-code>`_
   - **uv/uvx** - `Install uv <https://docs.astral.sh/uv/>`_

.. seealso:: `Qwen Code MCP official guide <https://qwenlm.github.io/qwen-code-docs/en/developers/tools/mcp-server/>`_

Setup Steps
-----------

.. card:: Step 1: Configure MCP in Qwen Code
   :class-card: step-card

   **1.1. Open MCP Configuration**

   Edit (or create) ``~/.qwen/settings.json``:

   **1.2. Add ToolUniverse Configuration**

   Add this to your ``settings.json``:

   .. code-block:: json

      {
        "mcpServers": {
          "tooluniverse": {
            "command": "uvx",
            "args": ["--refresh", "tooluniverse"],
            "env": {"PYTHONIOENCODING": "utf-8"}
          }
        }
      }

   **1.3. Restart Qwen Code**

   Restart the application to load MCP servers.

.. card:: Step 2: Install Agent Skills
   :class-card: step-card

   Install ToolUniverse skills for guided workflows:

   .. code-block:: bash

      npx skills add mims-harvard/ToolUniverse

.. card:: Step 3: Verify Integration
   :class-card: step-card

   .. code-block:: text

      "Show available scientific tools"
      "Search PubMed for CRISPR papers"

.. important:: 🔑 **Configure API Keys**
   
   Many tools require API keys. Set them up for full functionality:
   
   .. button-ref:: ../../api_keys
      :color: primary
      :shadow:
   
      🔐 **API Keys Setup Guide**

Example Workflows
-----------------

.. tab-set::

   .. tab-item:: Code Generation

      .. code-block:: text

         "Write Python code to analyze protein sequences
         from UniProt and visualize results"

   .. tab-item:: Data Pipeline

      .. code-block:: text

         "Create a pipeline: fetch disease targets,
         get protein structures, analyze druggability"

Troubleshooting
---------------

.. dropdown:: ❌ Tools not available
   :color: danger

   - Ensure ``uvx`` is installed: ``uvx --version``
   - Check that ``settings.json`` is valid JSON
   - Restart Qwen Code after editing the config

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
