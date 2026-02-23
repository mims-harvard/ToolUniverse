Choose AI Agent Platform
==============================

**Connect ToolUniverse to your favorite AI agent**

Select your platform to get started with step-by-step setup instructions:

Platforms
---------

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
      Code editor for AI scientist development

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

   .. grid-item-card::
      :link: chatgpt_api
      :link-type: doc
      :class-card: platform-card hover-lift
      :shadow: md
      
      **ChatGPT API**
      ^^^
      API for programmatic research automation

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
   chatgpt_api

.. tip:: 🚀 **Instant guided setup — works with any agent, no pre-installation needed**

   Open your AI agent and paste this single message:

   .. code-block:: text

      Please read https://raw.githubusercontent.com/mims-harvard/ToolUniverse/main/skills/setup-tooluniverse/SKILL.md and follow it to help me set up ToolUniverse.

   Your agent will fetch the interactive setup guide from GitHub and walk you through MCP configuration, API keys, and validation step by step — no setup required beforehand.

   Or, install skills first with ``npx skills add mims-harvard/ToolUniverse``, then ask your agent **"setup tooluniverse"**.

Common Setup Steps
------------------

All platforms follow this general pattern:

.. card:: Step 1: Add MCP Configuration
   :class-card: step-card

   Add ToolUniverse to your MCP config file (location varies by platform):

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

.. card:: Step 2: Install Agent Skills
   :class-card: step-card

   Install ToolUniverse skills for guided workflows:

   .. code-block:: bash

      npx skills add mims-harvard/ToolUniverse

.. card:: Step 3: Verify MCP Connection
   :class-card: step-card

   Check if the MCP connector is working by asking your AI agent:

   .. code-block:: text

      "List available tools from ToolUniverse"

   Or use the setup skill for interactive verification:

   .. code-block:: text

      "setup tooluniverse"

.. important:: 🔑 **Configure API Keys for Full Capabilities**
   
   Many tools require API keys to function. Set up your API keys to unlock the full power of ToolUniverse:
   
   .. button-ref:: ../api_keys
      :color: primary
      :shadow:
   
      🔐 **API Keys Setup Guide**: Configure access to scientific databases and services

Getting Help
------------


- **Setup issues?** Check the :doc:`../../help/troubleshooting` guide
- **Questions?** Join our `Slack community <https://join.slack.com/t/tooluniversehq/shared_invite/zt-3dic3eoio-5xxoJch7TLNibNQn5_AREQ>`_
- **Bug reports?** `Create an issue <https://github.com/mims-harvard/ToolUniverse/issues>`_

Quick Links
-----------

.. button-ref:: ../python_guide
   :color: secondary
   :shadow:
   :expand:

   🐍 **Coding Agent?** Use ToolUniverse directly with Python API

.. button-ref:: ../../index
   :color: info
   :shadow:
   :expand:

   🏠 **Back to Home**: Return to main documentation

.. toctree::
   :maxdepth: 1
   :hidden:
   :caption: MCP & Integration

   mcp_support
   mcpb_introduction
   mcp_name_shortening
   compact_mode
