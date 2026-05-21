Claude Code
===========

`Claude Code <https://claude.com/claude-code>`_ is Anthropic's terminal-based AI
coding agent. ToolUniverse ships an official Claude Code **plugin** that auto-configures
the MCP server, ~115 specialized research skills, slash commands, and a research
agent — all in two commands.

The plugin is the recommended way to use ToolUniverse with Claude Code. A
manual-MCP fallback is documented at the bottom of this page.


.. _claude-code-plugin-quickstart:

Quickstart — install the plugin
-------------------------------

**Prerequisites** (one-time check):

.. code-block:: bash

   uv --version       # if missing:  curl -LsSf https://astral.sh/uv/install.sh | sh
   claude --version   # if missing:  https://claude.com/claude-code

**Install** (two commands):

.. code-block:: bash

   # 1. Register the ToolUniverse marketplace from GitHub
   claude plugin marketplace add mims-harvard/ToolUniverse

   # 2. Install the plugin
   claude plugin install tooluniverse@tooluniverse

Restart Claude Code. The MCP server auto-starts via ``uvx tooluniverse`` on first use
(~30 s cold start, instant after).

.. note::

   **Pin to a specific version (optional):**

   .. code-block:: bash

      claude plugin marketplace add mims-harvard/ToolUniverse#v1.2.0
      claude plugin install tooluniverse@tooluniverse

   Replace ``v1.2.0`` with any released tag from
   `the releases page <https://github.com/mims-harvard/ToolUniverse/releases>`_.


Verify it worked
----------------

.. code-block:: bash

   claude plugin list
   # Expect to see:  tooluniverse  (enabled)

Inside Claude Code, ask naturally — no command prefix needed; the router skill
auto-dispatches:

.. code-block:: text

   What are the top mutated genes in breast cancer?
   Research the drug metformin.
   Run DESeq2 on my CD4 vs CD14 RNA-seq data in this folder.
   How many indels are in the MDR sample VCF?


What you get
------------

.. list-table::
   :header-rows: 1
   :widths: 22 50 28

   * - Component
     - What it does
     - How to invoke
   * - **MCP server**
     - 1000+ scientific tools via ``find_tools``, ``get_tool_info``, ``execute_tool``
     - Auto-loaded; no action needed
   * - **Slash commands**
     - Discipline-enforcing prompts for common research tasks
     - Type ``/tooluniverse:<command>``
   * - ``/tooluniverse:research``
     - Drive a multi-database investigation inline in this chat — same rigor as the ``researcher`` agent, but stays in your conversation so you see each step and can refine
     - Slash command
   * - ``/tooluniverse:translate-id``
     - Resolve an ID across all relevant namespaces (HGNC ↔ Ensembl ↔ UniProt ↔ NCBI ↔ ChEMBL ↔ PubChem)
     - Slash command
   * - ``/tooluniverse:cross-validate``
     - Verify a claim across 3+ independent databases
     - Slash command
   * - ``/tooluniverse:compare``
     - N-way side-by-side comparison with domain-appropriate columns
     - Slash command
   * - ``/tooluniverse:literature-sweep``
     - Graded mini-review across PubMed + EuropePMC + Semantic Scholar
     - Slash command
   * - ``/tooluniverse:researcher``
     - Same investigation as ``research``, delegated to a forked-context subagent that returns one summary (use when you don't want intermediate tool-call output in your main thread)
     - Slash command
   * - **~115 research skills**
     - Structured workflows for genomics, drug discovery, clinical analysis, statistical modeling, phylogenetics, CRISPR screens, variant interpretation, etc.
     - Auto-activate when the question matches


Update / uninstall
------------------

.. code-block:: bash

   # Update to the latest plugin release
   claude plugin update tooluniverse

   # Refresh the MCP server's tool cache (recommended after updates)
   uv cache clean tooluniverse

   # Restart Claude Code

   # Uninstall
   claude plugin uninstall tooluniverse
   claude plugin marketplace remove tooluniverse


Optional — add API keys
-----------------------

Most tools work without keys. For enhanced access (NCBI, OncoKB, NVIDIA, etc.),
edit the plugin's ``.mcp.json``. Locate the installed plugin directory with:

.. code-block:: bash

   # See plugin component inventory + on-disk location:
   claude plugin details tooluniverse

   # Or find the .mcp.json directly:
   find ~/.claude/plugins -name '.mcp.json' -path '*tooluniverse*'

After install via the GitHub marketplace, the file is typically at:
``~/.claude/plugins/cache/tooluniverse/tooluniverse/<version>/.mcp.json``.

Add keys under the ``env`` block:

.. code-block:: json

   {
     "mcpServers": {
       "tooluniverse": {
         "command": "uvx",
         "args": ["tooluniverse"],
         "env": {
           "PYTHONIOENCODING": "utf-8",
           "NCBI_API_KEY": "your_key",
           "NVIDIA_API_KEY": "your_key",
           "ONCOKB_API_TOKEN": "your_token"
         }
       }
     }
   }

Full API-key reference is in the bundled ``setup-tooluniverse`` skill —
ask Claude Code: *"Show me the ToolUniverse API keys reference."*


Alternative install paths
-------------------------

**Clone + local install (air-gapped / fork):**

.. code-block:: bash

   git clone https://github.com/mims-harvard/ToolUniverse.git
   cd ToolUniverse
   claude plugin marketplace add ./
   claude plugin install tooluniverse@tooluniverse

**Download the release zip (no git needed):**

Grab ``tooluniverse-plugin-vX.Y.Z.zip`` from
`Releases <https://github.com/mims-harvard/ToolUniverse/releases>`_, unzip, then:

.. code-block:: bash

   claude plugin marketplace add /path/to/unzipped-dir
   claude plugin install tooluniverse@tooluniverse


Troubleshooting
---------------

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Symptom
     - Fix
   * - ``marketplace add`` fails with "no marketplace.json"
     - Use ``mims-harvard/ToolUniverse`` (owner/repo), not the plugin subdir.
   * - ``uvx: command not found``
     - Install ``uv`` (see Prerequisites), reopen terminal.
   * - MCP server won't start
     - Test in terminal: ``uvx tooluniverse``. If it fails there, it's a ``uv``/Python issue.
   * - Plugin installs but tools missing
     - Restart Claude Code. First launch downloads the package (~30 s).
   * - ``requires-python >= 3.10``
     - ``uv python install 3.12``
   * - Tools feel outdated
     - ``uv cache clean tooluniverse`` then restart Claude Code.
   * - Skills don't auto-dispatch
     - If you previously installed global ToolUniverse skills (``~/.claude/skills/tooluniverse-*``), remove them: ``rm -rf ~/.claude/skills/tooluniverse-* ~/.claude/skills/setup-tooluniverse``. The plugin includes all skills; global copies interfere with routing.

Still stuck:
`open an issue <https://github.com/mims-harvard/ToolUniverse/issues>`_.


Fallback — manual MCP setup (without the plugin)
------------------------------------------------

If you prefer not to use the plugin (e.g., custom MCP config or non-Claude
clients sharing the same ``.mcp.json``), you can configure Claude Code with the
generic MCP setup. Open Claude Code and run:

.. code-block:: text

   Read https://aiscientist.tools/setup.md and set up ToolUniverse for me.

This walks you through MCP configuration, API keys, and validation step by
step. See also: :doc:`mcp_support` and Anthropic's
`official MCP setup guide <https://docs.anthropic.com/en/docs/claude-code/mcp>`_.
