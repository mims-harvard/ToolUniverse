Claude Desktop Setup
====================

**Connect ToolUniverse to Claude Desktop App**

Claude Desktop provides a user-friendly interface for scientific research with ToolUniverse's 1000+ tools through the Model Context Protocol (MCP).

Prerequisites
-------------

.. important:: ✅ **What you need:**
   
   - **Claude Desktop App** - `Download here <https://claude.com/download>`_
   - **uv/uvx** - `Install uv <https://docs.astral.sh/uv/>`_

.. seealso:: `Claude Desktop MCP official guide <https://modelcontextprotocol.io/docs/develop/connect-local-servers>`_

Setup Steps
-----------

.. card:: Step 1: Configure MCP Connection
   :class-card: step-card current

   Add ToolUniverse to Claude Desktop's config:

   **1.1. Open Configuration File**

   1. Open **Claude Desktop App**
   2. Go to **Settings** → **Developer** → **Edit Config**
   3. Your default text editor will open the config file

   **1.2. Add ToolUniverse Configuration**

   Add this to your config file:

   .. code-block:: json

      {
        "mcpServers": {
          "tooluniverse": {
            "command": "uvx",
            "args": ["tooluniverse"],
            "env": {"PYTHONIOENCODING": "utf-8"}
          }
        }
      }

   .. dropdown:: 🔧 Alternative: Using pip installation
      :animate: fade-in-slide-down
      :color: info

      If you installed with pip instead of using uvx:

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

   **1.3. Save Configuration**

   Save the file and close your text editor.

.. card:: Step 2: Install Agent Skills
   :class-card: step-card

   Install ToolUniverse skills for guided workflows:

   .. code-block:: bash

      npx skills add mims-harvard/ToolUniverse

   .. dropdown:: 💡 What are Agent Skills?
      :animate: fade-in-slide-down
      :color: primary

      Agent Skills provide Claude with specialized workflows for:

      - Drug discovery research
      - Target identification
      - Disease analysis
      - Literature deep-dive
      - And more!

      **These skills teach Claude how to use ToolUniverse tools effectively.**

.. card:: Step 3: Restart Claude Desktop
   :class-card: step-card pending

   Restart the app to load ToolUniverse:

   1. **Completely quit** Claude Desktop App (don't just close the window)
   2. **Reopen** Claude Desktop App
   3. Wait a few seconds for MCP servers to initialize

   .. tip:: 🔍 **Check if it's loaded:**
      
      Look for a small indicator in Claude Desktop showing MCP servers are connected.

.. card:: Step 4: Verify Integration
   :class-card: step-card pending

   Test that everything works:

   **Try these queries in Claude:**

   .. code-block:: text

      "What scientific tools are available?"

   .. code-block:: text

      "Find protein information for BRCA1"

   .. code-block:: text

      "Search for recent papers about CRISPR"

   .. success:: ✅ **Working?**
      
      Claude should now use ToolUniverse tools to answer your scientific questions!

Example Queries
---------------

Try these queries to explore ToolUniverse capabilities:

.. tab-set::

   .. tab-item:: Drug Research

      .. code-block:: text

         "Find information about aspirin, including its safety profile
         and adverse events from FDA databases"

   .. tab-item:: Protein Analysis

      .. code-block:: text

         "Get comprehensive information about protein P05067,
         including its function, structure, and interactions"

   .. tab-item:: Disease Targets

      .. code-block:: text

         "Find therapeutic targets for Alzheimer's disease
         and rank them by evidence strength"

   .. tab-item:: Literature Search

      .. code-block:: text

         "Search for recent publications about mRNA vaccines
         and summarize key findings"

Demo & Examples
---------------

See ToolUniverse in action with Claude Desktop:

.. button-link:: https://claude.ai/share/ab797b7f-6e6b-46f6-b1d5-5a790b90f42d
   :color: primary
   :shadow:

   🎥 **View Interactive Demo**

Troubleshooting
---------------

.. dropdown:: ❌ Claude doesn't recognize ToolUniverse tools
   :animate: fade-in-slide-down
   :color: danger

   **Solutions:**

   1. Check that you **completely quit and restarted** Claude Desktop (not just closed the window)
   2. Verify the config file syntax is correct (valid JSON)
   3. Check that ``uvx`` is installed: ``uvx --version``
   4. Look at Claude Desktop's developer console for error messages

.. dropdown:: ⚠️ "Too many tools" or context limit errors
   :animate: fade-in-slide-down
   :color: warning

   **Solution:** Load fewer tools by specifying categories.

   Edit your config to use compact mode:

   .. code-block:: json

      {
        "mcpServers": {
          "tooluniverse": {
            "command": "uvx",
            "args": ["tooluniverse", "--compact-mode"],
            "env": {"PYTHONIOENCODING": "utf-8"}
          }
        }
      }

.. dropdown:: 🔧 uvx not found
   :animate: fade-in-slide-down
   :color: info

   **Install uv:**

   .. tab-set::

      .. tab-item:: macOS/Linux

         .. code-block:: bash

            curl -LsSf https://astral.sh/uv/install.sh | sh

      .. tab-item:: Windows

         .. code-block:: powershell

            powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

Advanced Configuration
----------------------

.. dropdown:: 🎛️ Custom Tool Categories
   :animate: fade-in-slide-down
   :color: primary

   Load only specific tool categories:

   .. code-block:: json

      {
        "mcpServers": {
          "tooluniverse": {
            "command": "uvx",
            "args": [
              "tooluniverse",
              "--tool-categories", "uniprot,chembl,opentarget"
            ],
            "env": {"PYTHONIOENCODING": "utf-8"}
          }
        }
      }

.. dropdown:: 🔑 API Keys Configuration
   :animate: fade-in-slide-down
   :color: info

   Add API keys for enhanced performance:

   .. code-block:: json

      {
        "mcpServers": {
          "tooluniverse": {
            "command": "uvx",
            "args": ["tooluniverse"],
            "env": {
              "PYTHONIOENCODING": "utf-8",
              "NCBI_API_KEY": "your_key_here",
              "SEMANTIC_SCHOLAR_API_KEY": "your_key_here"
            }
          }
        }
      }

   See :doc:`../api_keys` for all available keys.

Next Steps
----------

.. grid:: 1 1 2 2
   :gutter: 3

   .. grid-item-card:: 📚 Learn Tool Discovery
      :link: ../finding_tools
      :link-type: doc
      :class-card: hover-lift
      :shadow: md
      
      How to find the right tools for your research

   .. grid-item-card:: 🔗 Build Workflows
      :link: ../scientific_workflows
      :link-type: doc
      :class-card: hover-lift
      :shadow: md
      
      Chain tools into complex research pipelines

   .. grid-item-card:: 🎯 Case Study
      :link: ../tooluniverse_case_study
      :link-type: doc
      :class-card: hover-lift
      :shadow: md
      
      End-to-end drug discovery example

   .. grid-item-card:: 💬 Get Help
      :link: ../../help/troubleshooting
      :link-type: doc
      :class-card: hover-lift
      :shadow: md
      
      Common issues and solutions

.. button-ref:: index
   :color: secondary
   :shadow:
   :expand:

   ← **Back to Platform Selector**

Need Help?
----------

- 💬 **Community**: `Join our Slack <https://join.slack.com/t/tooluniversehq/shared_invite/zt-3dic3eoio-5xxoJch7TLNibNQn5_AREQ>`_
- 🐛 **Issues**: `GitHub Issues <https://github.com/mims-harvard/ToolUniverse/issues>`_
- 📖 **Documentation**: :doc:`../../index`
