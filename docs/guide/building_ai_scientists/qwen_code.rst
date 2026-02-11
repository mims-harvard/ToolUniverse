Qwen Code Setup
===============

**Connect ToolUniverse to Qwen Code in 10 minutes**

Overview
--------

Qwen Code integration provides AI-powered development with ToolUniverse's scientific tools ecosystem.

.. grid:: 1 1 3 3
   :gutter: 2

   .. grid-item-card:: ⚡ Setup Time
      :class-card: hover-lift
      :shadow: sm
      
      **10 minutes**

   .. grid-item-card:: 💻 Difficulty
      :class-card: hover-lift
      :shadow: sm
      
      **Moderate**

   .. grid-item-card:: 🎯 Best For
      :class-card: hover-lift
      :shadow: sm
      
      **Code development**

Prerequisites
-------------

.. important:: ✅ **What you need:**
   
   - **Qwen Code** - `Download <https://qwenlm.github.io/>`_
   - **Python 3.10+**
   - **ToolUniverse** - ``pip install tooluniverse``

Setup Steps
-----------

.. card:: Step 1: Install ToolUniverse
   :class-card: step-card completed

   .. code-block:: bash

      pip install tooluniverse

.. card:: Step 2: Configure MCP Server
   :class-card: step-card current

   Add ToolUniverse to Qwen Code's MCP configuration:

   .. code-block:: json

      {
        "mcpServers": {
          "tooluniverse": {
            "command": "python",
            "args": ["-m", "tooluniverse.mcp_integration.smcp_stdio"],
            "env": {"PYTHONIOENCODING": "utf-8"}
          }
        }
      }

.. card:: Step 3: Restart Qwen Code
   :class-card: step-card pending

   Restart the application to load MCP servers.

.. card:: Step 4: Verify Integration
   :class-card: step-card pending

   .. code-block:: text

      "Show available scientific tools"
      "Search PubMed for CRISPR papers"

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

   Verify ToolUniverse is installed:

   .. code-block:: bash

      python -m tooluniverse.mcp_integration.smcp_stdio

Next Steps
----------

.. button-ref:: index
   :color: secondary
   :shadow:
   :expand:

   ← **Back to Platform Selector**
