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
   * - ``/tooluniverse:tu-translate-id``
     - Resolve an ID across all relevant namespaces (HGNC ↔ Ensembl ↔ UniProt ↔ NCBI ↔ ChEMBL ↔ PubChem)
     - Slash command
   * - ``/tooluniverse:tu-cross-validate``
     - Verify a claim across 3+ independent databases
     - Slash command
   * - ``/tooluniverse:tu-compare``
     - N-way side-by-side comparison with domain-appropriate columns
     - Slash command
   * - ``/tooluniverse:tu-literature-sweep``
     - Graded mini-review across PubMed + EuropePMC + Semantic Scholar
     - Slash command
   * - ``/tooluniverse:researcher``
     - Autonomous forked-context research agent for complex multi-database questions
     - Slash command
   * - **~115 research skills**
     - Structured workflows for genomics, drug discovery, clinical analysis, statistical modeling, phylogenetics, CRISPR screens, variant interpretation, etc.
     - Auto-activate when the question matches


Run a data-analysis question (BixBench-style)
---------------------------------------------

The plugin is built for exactly this pattern: you have a data folder
(RNA-seq counts + metadata, a VCF, a methylation table, a BUSCO ortholog
zip, etc.) and a specific scientific question. The plugin's router auto-loads
the matching skill, which already encodes the right pipeline.

Step-by-step:

1. ``cd`` into your data directory:

   .. code-block:: bash

      cd ~/my_research_project/

   The folder can contain anything: ``counts.csv``, ``coldata.csv``,
   ``CapsuleData-XXX/*.csv``, ``Swarm_2.csv``, ``ZF_AgeRelated_CpG_noMT_Final.csv``,
   ``scogs_animals.zip``, etc.

2. Start Claude Code: ``claude``

3. Ask in plain language. The router skill detects the topic from the wording
   and the file extensions in the folder, then dispatches to the right
   sub-skill (115 cover RNA-seq DE, gene enrichment, phylogenetics, methylation,
   variant interpretation, clinical-trial AE analysis, CRISPR screens,
   single-cell, statistical modeling, image analysis, etc.):

   .. code-block:: text

      Run DESeq2 differential expression on this RNA-seq data
      (CD4 vs CD14 immune cells). Apply padj<0.05, |LFC|>0.5, baseMean>10
      with apeglm shrinkage. How many DEGs are upregulated?

4. The agent computes the analysis with the plugin's deterministic helper
   scripts (so results are reproducible), and reports the answer with a
   sensitivity table showing alternative method choices (e.g., shrunk vs
   unshrunk, padj-only vs padj+LFC) when the result depends on them.

**Reproducibility.** The plugin's analysis skills include "RULE ZERO": if a
canonical executed Jupyter notebook (``*_executed.ipynb``) ships with the
data folder, the agent reads its outputs and cites them — preserving the
exact published values rather than risking floating-point drift from library
version changes. This is the recommended mode when you have access to the
authors' analysis bundle.

**Closed-book mode (no notebook).** When only raw data is present, the
agent runs the full pipeline from scratch using bundled scripts:
``r_deseq2_wrapper.py``, ``gseapy_enrichment_runner.py``, ``enrichgo_runner.py``,
``methylation_density.py``, ``logistic_regression_or.py``,
``r_natural_spline_regression.py``, ``phykit_dvmc_runner.py``, etc. Each
emits multiple parameter variants so the agent (and you) can see how
sensitive the answer is to method choices.

**Iterating with the agent.** Unlike single-shot benchmark mode, Claude
Code is conversational — you can refine after seeing the first answer:

   .. code-block:: text

      You: How many DEGs at padj<0.05?
      Agent: 1,131 (with apeglm shrinkage; 1,615 without)
      You: Use the unshrunken count, and now also intersect with the
           genes that are DE in the cisplatin treatment.
      Agent: 525 genes are DE in both contrasts (padj<0.05, unshrunken).


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
