Codex CLI Setup
===============

**Connect ToolUniverse to OpenAI Codex CLI**

Codex CLI is OpenAI's locally-running AI coding agent with native MCP support via stdio.

.. tip:: 🚀 **Fastest setup — no installation needed**

   Open Codex CLI and paste this single message:

   .. code-block:: text

      Please read https://raw.githubusercontent.com/mims-harvard/ToolUniverse/main/skills/setup-tooluniverse/SKILL.md and follow it to help me set up ToolUniverse.

   Codex CLI will fetch the setup guide from GitHub and walk you through everything interactively.

Prerequisites
-------------

.. important:: ✅ **What you need:**
   
   - **Node.js 18+** - `Download here <https://nodejs.org/>`_
   - **Codex CLI** - ``npm install -g @openai/codex``
   - **OpenAI API Key** - `Get key <https://platform.openai.com/api-keys>`_
   - **uv/uvx** - `Install uv <https://docs.astral.sh/uv/>`_

.. seealso:: `Codex CLI MCP official guide <https://developers.openai.com/codex/mcp/>`_

Setup Steps
-----------

.. card:: Step 1: Configure MCP in Codex CLI
   :class-card: step-card

   **Option A — CLI command (quickest):**

   .. code-block:: bash

      codex mcp add tooluniverse -- uvx tooluniverse

   **Option B — Edit config directly:**

   Open ``~/.codex/config.toml`` and add:

   .. code-block:: toml

      [mcp_servers.tooluniverse]
      command = "uvx"
      args = ["tooluniverse"]

      [mcp_servers.tooluniverse.env]
      PYTHONIOENCODING = "utf-8"

   .. note::
      Codex CLI uses **TOML format** (not JSON) and the ``mcp_servers`` key (not ``mcpServers``).
      You can also scope config to a project with ``.codex/config.toml`` in a trusted project directory.

.. card:: Step 2: Set OpenAI API Key
   :class-card: step-card

   .. code-block:: bash

      export OPENAI_API_KEY=your_key

.. card:: Step 3: Install Agent Skills
   :class-card: step-card

   Install ToolUniverse skills for guided workflows:

   .. code-block:: bash

      npx skills add mims-harvard/ToolUniverse

.. card:: Step 4: Launch and Verify
   :class-card: step-card

   .. code-block:: bash

      codex

   In the TUI, run ``/mcp`` to confirm ToolUniverse is connected, then ask:

   .. code-block:: text

      "List available tools from ToolUniverse"

   Or use the setup skill:

   .. code-block:: text

      "setup tooluniverse"

.. important:: 🔑 **Configure API Keys**
   
   Many tools require API keys. Set them up for full functionality:
   
   .. button-ref:: ../../api_keys
      :color: primary
      :shadow:
   
      🔐 **API Keys Setup Guide**

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

Advanced Configuration
----------------------

.. dropdown:: 🔑 Tool-Specific API Keys
   :animate: fade-in-slide-down

   Add ToolUniverse API keys in ``config.toml``:

   .. code-block:: toml

      [mcp_servers.tooluniverse]
      command = "uvx"
      args = ["tooluniverse"]

      [mcp_servers.tooluniverse.env]
      PYTHONIOENCODING = "utf-8"
      NCBI_API_KEY = "your_key"
      SEMANTIC_SCHOLAR_API_KEY = "your_key"

.. dropdown:: 🎛️ Project-Scoped Config
   :animate: fade-in-slide-down

   Place ``.codex/config.toml`` in a trusted project directory to scope MCP servers per project (project config merges with ``~/.codex/config.toml``).

Troubleshooting
---------------

.. dropdown:: ❌ MCP server not found
   :color: danger

   - Ensure ``uvx`` is installed: ``uvx --version``
   - Verify TOML syntax with a linter
   - Run ``/mcp`` in the Codex TUI to inspect server status

.. dropdown:: ⚠️ Context limit errors
   :color: warning

   Disable ToolUniverse when not needed:

   .. code-block:: toml

      [mcp_servers.tooluniverse]
      enabled = false

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
