Set Up ToolUniverse
===================

Open your AI agent and run this single prompt to get started:

.. code-block:: text

   Read https://aiscientist.tools/setup.md and set up ToolUniverse for me.

Your agent will walk you through MCP configuration, API keys, and validation step by step.

Choose your platform
--------------------

.. grid:: 1 1 2 3
   :gutter: 3
   :class-container: platform-grid

   .. grid-item-card::
      :link: claude_desktop
      :link-type: doc
      :class-card: platform-card hover-lift
      :shadow: md

      **Claude Desktop**
      ^^^
      Desktop app with native MCP integration

   .. grid-item-card::
      :link: claude_code
      :link-type: doc
      :class-card: platform-card hover-lift
      :shadow: md

      **Claude Code**
      ^^^
      Terminal-based AI coding agent

   .. grid-item-card::
      :link: cursor
      :link-type: doc
      :class-card: platform-card hover-lift
      :shadow: md

      **Cursor**
      ^^^
      AI-first code editor with MCP support

   .. grid-item-card::
      :link: windsurf
      :link-type: doc
      :class-card: platform-card hover-lift
      :shadow: md

      **Windsurf**
      ^^^
      Agentic IDE with autonomous coding agents

   .. grid-item-card::
      :link: antigravity
      :link-type: doc
      :class-card: platform-card hover-lift
      :shadow: md

      **Antigravity**
      ^^^
      Google's free agentic IDE with parallel agents

   .. grid-item-card::
      :link: cline
      :link-type: doc
      :class-card: platform-card hover-lift
      :shadow: md

      **Cline**
      ^^^
      VS Code extension with MCP integration

   .. grid-item-card::
      :link: trae
      :link-type: doc
      :class-card: platform-card hover-lift
      :shadow: md

      **Trae**
      ^^^
      AI coding assistant with MCP support

   .. grid-item-card::
      :link: opencode
      :link-type: doc
      :class-card: platform-card hover-lift
      :shadow: md

      **OpenCode**
      ^^^
      Open-source AI coding platform

   .. grid-item-card::
      :link: gemini_cli
      :link-type: doc
      :class-card: platform-card hover-lift
      :shadow: md

      **Gemini CLI**
      ^^^
      Command-line interface with Google Gemini

   .. grid-item-card::
      :link: qwen_code
      :link-type: doc
      :class-card: platform-card hover-lift
      :shadow: md

      **Qwen Code**
      ^^^
      Code editor for AI scientist workflows

   .. grid-item-card::
      :link: codex_cli
      :link-type: doc
      :class-card: platform-card hover-lift
      :shadow: md

      **Codex CLI**
      ^^^
      Terminal-based interface with OpenAI Codex

MCP configuration
-----------------

All platforms use the same MCP config snippet:

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

For advanced MCP options, see :doc:`mcp_support`.

Agent skills
------------

Skills are pre-built research workflows that guide your agent through complex tasks. Install all skills with one command:

.. code-block:: bash

   npx skills add mims-harvard/ToolUniverse

Then ask your agent: *"research the drug metformin"*, *"find targets for Alzheimer's disease"*, or *"analyze protein structure for EGFR"*. See the full :doc:`../skills_showcase`.

.. toctree::
   :maxdepth: 1
   :hidden:
   :caption: Platform Setup Guides

   claude_desktop
   claude_code
   cursor
   windsurf
   antigravity
   cline
   trae
   opencode
   gemini_cli
   qwen_code
   codex_cli

.. toctree::
   :maxdepth: 1
   :hidden:
   :caption: MCP & Integration

   mcp_support
   mcpb_introduction
   mcp_name_shortening
   compact_mode
