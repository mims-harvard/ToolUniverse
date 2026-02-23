Claude Desktop Setup
====================

**Connect ToolUniverse to Claude Desktop App**

Claude Desktop provides a user-friendly interface for scientific research with ToolUniverse's 1000+ tools through the Model Context Protocol (MCP).

.. seealso:: `Claude Desktop MCP official guide <https://modelcontextprotocol.io/docs/develop/connect-local-servers>`_

Setup Steps
-----------

.. card:: Step 1: Install uv
   :class-card: step-card current

   ``uv`` is the package manager that runs ToolUniverse.

   .. tab-set::

      .. tab-item:: macOS

         .. code-block:: bash

            brew install uv

         .. important::

            On macOS, **Homebrew is the only recommended method** for Claude Desktop.
            The curl installer puts ``uvx`` in ``~/.local/bin/``, which Claude Desktop
            (a GUI app) cannot find, causing a "Failed to spawn" error on first launch.
            If you don't have Homebrew, get it from `brew.sh <https://brew.sh>`_ first.

      .. tab-item:: Windows

         .. code-block:: powershell

            powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

         Then close and reopen PowerShell. Verify: ``uvx --version``

      .. tab-item:: Linux

         .. code-block:: bash

            curl -LsSf https://astral.sh/uv/install.sh | sh
            source "$HOME/.local/bin/env"

         Then verify: ``uvx --version``

   After installing on macOS, verify:

   .. code-block:: bash

      /opt/homebrew/bin/uvx --version    # Apple Silicon
      /usr/local/bin/uvx --version       # Intel Mac

   .. note::

      ``which uvx`` may show ``~/.local/bin/uvx`` if you had a previous uv installation —
      that is fine. Claude Desktop uses the Homebrew path directly, not your shell PATH.
      If needed, run ``brew link uv --overwrite`` to make Homebrew's version the default.

.. card:: Step 2: Add ToolUniverse to Claude Desktop
   :class-card: step-card

   1. Open **Claude Desktop** → **Settings** → **Developer** → **Edit Config**
   2. Your text editor opens ``claude_desktop_config.json``
   3. Replace the file contents with:

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

   4. Save the file.

   .. note::

      ``"--refresh"`` auto-updates ToolUniverse on every launch. If you already have other
      MCP servers in the file, add the ``"tooluniverse": {...}`` block inside your existing
      ``"mcpServers"`` object — don't replace the whole file.

.. card:: Step 3: Restart & Verify
   :class-card: step-card pending

   **Before restarting**, confirm the server starts cleanly in your terminal:

   .. code-block:: bash

      timeout 10 uvx tooluniverse --help

   If that prints usage text, you're good. If it errors, fix it before restarting the app.

   1. **Fully quit** Claude Desktop — **⌘Q** on Mac (closing the window is not enough).
   2. Reopen Claude Desktop.
   3. ⏱️ **Wait up to 60–90 seconds** on first launch — ToolUniverse downloads in the background.
      You can watch the progress: open a terminal and run:

      .. code-block:: bash

         tail -f ~/Library/Logs/Claude/mcp*.log

   4. Look for a 🔨 **hammer icon** at the bottom of the chat input box and click it —
      you should see ``tooluniverse`` listed.

      .. note::

         Don't see a hammer? Check **Settings → Developer → MCP Servers** — this panel
         shows each server's connection status and any error messages. Some versions of
         Claude Desktop show a "Connectors" or integrations panel instead.

   5. Try asking: *"What scientific tools are available?"*

   .. success:: ✅ If ToolUniverse tools appear, you're all set!

.. card:: Step 4: Install Agent Skills (optional but recommended)
   :class-card: step-card pending

   Skills are pre-built research workflows that guide Claude through complex tasks:

   .. code-block:: bash

      npx skills add mims-harvard/ToolUniverse

   .. dropdown:: 💡 What are Agent Skills?
      :animate: fade-in-slide-down
      :color: primary

      Skills teach Claude how to use ToolUniverse's 1200+ tools effectively. Examples:

      - **"Research the drug metformin"** → full drug profile with safety data
      - **"Find protein structures for EGFR"** → retrieves and assesses PDB entries
      - **"What does the literature say about CRISPR?"** → deep literature review

Example Queries
---------------

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

Troubleshooting
---------------

.. dropdown:: ❌ Hammer icon missing / "Failed to spawn" / "ENOENT" error
   :animate: fade-in-slide-down
   :color: danger

   **Cause:** Claude Desktop is a GUI app — it can't find ``uvx`` if it's in ``~/.local/bin``
   (the default location for the shell installer).

   **Fix:** Find your full ``uvx`` path and use it in the config:

   .. code-block:: bash

      which uvx    # macOS / Linux — e.g. /opt/homebrew/bin/uvx or /Users/you/.local/bin/uvx

   .. code-block:: powershell

      where uvx    # Windows

   Then update the ``"command"`` in your config to that full path:

   .. code-block:: json

      {
        "mcpServers": {
          "tooluniverse": {
            "command": "/opt/homebrew/bin/uvx",
            "args": ["--refresh", "tooluniverse"],
            "env": {"PYTHONIOENCODING": "utf-8"}
          }
        }
      }

   Fully quit and reopen Claude Desktop.

   .. tip:: If you installed via **Homebrew** (``brew install uv``), this error won't occur —
      Homebrew places ``uvx`` in a system path Claude Desktop can always find.

   **Check the logs** for the exact error message:

   .. code-block:: bash

      tail -f ~/Library/Logs/Claude/mcp*.log          # macOS

   .. code-block:: powershell

      type "$env:APPDATA\Claude\logs\mcp*.log"         # Windows

.. dropdown:: ❌ Tools not working after config is correct
   :animate: fade-in-slide-down
   :color: danger

   1. Make sure you **fully quit** Claude Desktop (⌘Q / right-click Dock → Quit), not just closed the window.
   2. Check JSON syntax — no trailing commas. Validate at `jsonlint.com <https://jsonlint.com>`_.
   3. Run ``uvx tooluniverse --help`` in your terminal to confirm the package works.
   4. Check logs: ``tail -20 ~/Library/Logs/Claude/mcp*.log``


.. dropdown:: 🔄 Keeping ToolUniverse up to date
   :animate: fade-in-slide-down
   :color: info

   The recommended config uses ``"--refresh"`` so ToolUniverse automatically updates to
   the latest version each time Claude Desktop starts (adds ~1–2 s to startup time):

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

   To update manually instead, remove ``"--refresh"`` from the args and run this in your
   terminal whenever you want to upgrade, then restart Claude Desktop:

   .. code-block:: bash

      uv cache clean tooluniverse

.. dropdown:: 🔑 Adding API keys for more tools
   :animate: fade-in-slide-down
   :color: info

   Add keys to the ``"env"`` block in your config:

   .. code-block:: json

      {
        "mcpServers": {
          "tooluniverse": {
            "command": "uvx",
            "args": ["--refresh", "tooluniverse"],
            "env": {
              "PYTHONIOENCODING": "utf-8",
              "NCBI_API_KEY": "your_key_here",
              "SEMANTIC_SCHOLAR_API_KEY": "your_key_here"
            }
          }
        }
      }

   See :doc:`../api_keys` for all available keys (all are free to obtain).

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

   .. grid-item-card:: 🎯 Case Study
      :link: ../tooluniverse_case_study
      :link-type: doc
      :class-card: hover-lift
      :shadow: md
      
      End-to-end drug discovery example

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
