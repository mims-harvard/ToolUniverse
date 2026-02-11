Codex CLI Setup
===============

**Connect ToolUniverse to OpenAI Codex CLI in 10 minutes**

Overview
--------

Codex CLI integration provides terminal-based access to OpenAI's reasoning with ToolUniverse's scientific tools.

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
      
      **Terminal workflows**

Prerequisites
-------------

.. important:: ✅ **What you need:**
   
   - **Codex CLI** - ``npm install -g @openai/codex-cli``
   - **OpenAI API Key** - `Get key <https://platform.openai.com/api-keys>`_
   - **ToolUniverse** - ``pip install tooluniverse``

Setup Steps
-----------

.. card:: Step 1: Install ToolUniverse
   :class-card: step-card completed

   .. code-block:: bash

      pip install tooluniverse

.. card:: Step 2: Start MCP Server
   :class-card: step-card current

   .. code-block:: bash

      tooluniverse-smcp --port 8000

.. card:: Step 3: Configure Codex CLI
   :class-card: step-card pending

   .. code-block:: json

      {
        "mcpServers": {
          "tooluniverse": {
            "url": "http://localhost:8000"
          }
        }
      }

.. card:: Step 4: Set API Key
   :class-card: step-card pending

   .. code-block:: bash

      export OPENAI_API_KEY=your_key

.. card:: Step 5: Launch Codex CLI
   :class-card: step-card pending

   .. code-block:: bash

      codex-cli

Example Queries
---------------

.. tab-set::

   .. tab-item:: Quick Search

      .. code-block:: text

         "Find recent papers about protein folding"

   .. tab-item:: Data Analysis

      .. code-block:: text

         "Get disease targets for diabetes,
         rank by evidence strength"

Troubleshooting
---------------

.. dropdown:: ❌ MCP server unreachable
   :color: danger

   Check server status:

   .. code-block:: bash

      curl http://localhost:8000/health

Next Steps
----------

.. button-ref:: index
   :color: secondary
   :shadow:
   :expand:

   ← **Back to Platform Selector**
