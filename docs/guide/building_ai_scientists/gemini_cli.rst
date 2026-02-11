Gemini CLI Setup
================

**Connect ToolUniverse to Google Gemini CLI in 10 minutes**

Overview
--------

Gemini CLI integration provides command-line access to Google's Gemini reasoning models with ToolUniverse's scientific tools.

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
      
      **CLI workflows**

Prerequisites
-------------

.. important:: ✅ **What you need:**
   
   - **Gemini CLI** - ``npm install -g @google/generative-ai-cli``
   - **Google AI API Key** - `Get key <https://ai.google.dev>`_
   - **ToolUniverse** - ``pip install tooluniverse``

Setup Steps
-----------

.. card:: Step 1: Install ToolUniverse
   :class-card: step-card completed

   .. code-block:: bash

      pip install tooluniverse

.. card:: Step 2: Start MCP Server
   :class-card: step-card current

   Launch ToolUniverse MCP server:

   .. code-block:: bash

      # Terminal 1: Start MCP server
      tooluniverse-smcp --port 8000

   Keep this terminal open.

.. card:: Step 3: Configure Gemini CLI
   :class-card: step-card pending

   Create Gemini CLI config file ``~/.gemini-cli/config.json``:

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

      export GOOGLE_API_KEY=your_gemini_api_key

.. card:: Step 5: Launch Gemini CLI
   :class-card: step-card pending

   .. code-block:: bash

      # Terminal 2: Start Gemini CLI
      gemini-cli

   .. success:: ✅ **Connected!**
      
      Gemini CLI can now use ToolUniverse tools!

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

.. dropdown:: 🎛️ Custom Port
   :animate: fade-in-slide-down

   Use a different port:

   .. code-block:: bash

      # Server
      tooluniverse-smcp --port 9000

      # Config
      {"mcpServers": {"tooluniverse": {"url": "http://localhost:9000"}}}

.. dropdown:: 🔑 Tool-Specific API Keys
   :animate: fade-in-slide-down

   .. code-block:: bash

      export NCBI_API_KEY=your_key
      export SEMANTIC_SCHOLAR_API_KEY=your_key
      tooluniverse-smcp --port 8000

Troubleshooting
---------------

.. dropdown:: ❌ Connection refused
   :color: danger

   Check MCP server is running:

   .. code-block:: bash

      curl http://localhost:8000/health

.. dropdown:: ⚠️ Rate limit errors
   :color: warning

   Add API keys (see Advanced Configuration)

Next Steps
----------

.. button-ref:: index
   :color: secondary
   :shadow:
   :expand:

   ← **Back to Platform Selector**

.. seealso::
   - :doc:`../tooluniverse_case_study` - End-to-end example with Gemini
   - :doc:`../scientific_workflows` - Research workflows
   - :doc:`../../help/troubleshooting` - Common issues
