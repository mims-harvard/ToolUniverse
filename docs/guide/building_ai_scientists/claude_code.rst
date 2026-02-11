Claude Code Setup
=================

**Connect ToolUniverse to Claude Code in 10 minutes**

Overview
--------

Claude Code integration combines Anthropic's reasoning model with ToolUniverse's 1000+ scientific tools in a development-focused environment.

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
      
      **Development workflows**

Prerequisites
-------------

.. important:: ✅ **What you need:**
   
   - **Claude Code CLI** - Install via: ``npm install -g @anthropics/claude-code``
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

   Add ToolUniverse MCP server to Claude Code:

   .. code-block:: bash

      claude mcp add --transport stdio tooluniverse -- tooluniverse-smcp-stdio --compact-mode

   .. dropdown:: 💡 What does this do?
      :animate: fade-in-slide-down
      :color: info

      - ``--transport stdio``: Uses standard input/output for communication
      - ``tooluniverse``: Server name
      - ``tooluniverse-smcp-stdio``: ToolUniverse's MCP stdio server
      - ``--compact-mode``: Loads essential tools (prevents context overflow)

.. card:: Step 3: Install Agent Skills (Optional)
   :class-card: step-card pending

   .. code-block:: bash

      npx skills add mims-harvard/ToolUniverse

.. card:: Step 4: Start Claude Code
   :class-card: step-card pending

   Launch Claude Code with ToolUniverse:

   .. code-block:: bash

      claude

.. card:: Step 5: Verify Integration
   :class-card: step-card pending

   Test in Claude Code:

   .. code-block:: text

      "List available ToolUniverse tools"
      "Find protein P05067 function"

   .. success:: ✅ **Working!**
      
      Claude Code can now access scientific tools!

Example Workflows
-----------------

.. tab-set::

   .. tab-item:: Drug Discovery

      .. code-block:: text

         "Search ChEMBL for compounds similar to aspirin,
         then analyze their ADMET properties"

   .. tab-item:: Code Generation

      .. code-block:: text

         "Write a Python script that:
         1. Searches PubMed for COVID-19 papers
         2. Extracts key findings
         3. Saves to CSV"

   .. tab-item:: Data Analysis

      .. code-block:: text

         "Get gene expression data for BRCA1 from GTEx,
         analyze tissue specificity, create visualization"

Advanced Configuration
----------------------

.. dropdown:: 🎛️ Load Specific Tool Categories
   :animate: fade-in-slide-down
   :color: primary

   .. code-block:: bash

      claude mcp add --transport stdio tooluniverse -- \
        tooluniverse-smcp-stdio \
        --tool-categories uniprot,chembl,opentarget

.. dropdown:: 🔑 API Keys
   :animate: fade-in-slide-down
   :color: info

   Set environment variables:

   .. code-block:: bash

      export NCBI_API_KEY=your_key
      export SEMANTIC_SCHOLAR_API_KEY=your_key

Troubleshooting
---------------

.. dropdown:: ❌ MCP server not found
   :color: danger

   Reinstall ToolUniverse:

   .. code-block:: bash

      pip install --upgrade tooluniverse

.. dropdown:: ⚠️ Too many tools warning
   :color: warning

   Use ``--compact-mode`` flag (see Step 2)

Next Steps
----------

.. button-ref:: index
   :color: secondary
   :shadow:
   :expand:

   ← **Back to Platform Selector**

.. seealso::
   - :doc:`../finding_tools` - Tool discovery
   - :doc:`../scientific_workflows` - Workflow patterns
   - :doc:`../../help/troubleshooting` - Common issues
