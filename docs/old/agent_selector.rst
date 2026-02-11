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
      :link: building_ai_scientists/claude_desktop
      :link-type: doc
      :class-card: platform-card hover-lift
      :shadow: md
      
      **Claude Desktop**
      ^^^
      Desktop app with native MCP integration

   .. grid-item-card::
      :link: building_ai_scientists/claude_code
      :link-type: doc
      :class-card: platform-card hover-lift
      :shadow: md
      
      **Claude Code**
      ^^^
      Code editor for AI scientist development

   .. grid-item-card::
      :link: building_ai_scientists/cursor
      :link-type: doc
      :class-card: platform-card hover-lift
      :shadow: md
      
      **Cursor**
      ^^^
      AI-first code editor with MCP support

   .. grid-item-card::
      :link: building_ai_scientists/windsurf
      :link-type: doc
      :class-card: platform-card hover-lift
      :shadow: md
      
      **Windsurf**
      ^^^
      Agentic IDE with autonomous coding agents

   .. grid-item-card::
      :link: building_ai_scientists/antigravity
      :link-type: doc
      :class-card: platform-card hover-lift
      :shadow: md
      
      **Antigravity**
      ^^^
      Google's free agentic IDE with parallel agents

   .. grid-item-card::
      :link: building_ai_scientists/cline
      :link-type: doc
      :class-card: platform-card hover-lift
      :shadow: md
      
      **Cline**
      ^^^
      VS Code extension with MCP integration

   .. grid-item-card::
      :link: building_ai_scientists/trae
      :link-type: doc
      :class-card: platform-card hover-lift
      :shadow: md
      
      **Trae**
      ^^^
      AI coding assistant with MCP support

   .. grid-item-card::
      :link: building_ai_scientists/opencode
      :link-type: doc
      :class-card: platform-card hover-lift
      :shadow: md
      
      **OpenCode**
      ^^^
      Open-source AI coding platform

   .. grid-item-card::
      :link: building_ai_scientists/gemini_cli
      :link-type: doc
      :class-card: platform-card hover-lift
      :shadow: md
      
      **Gemini CLI**
      ^^^
      Command-line interface with Google Gemini

   .. grid-item-card::
      :link: building_ai_scientists/qwen_code
      :link-type: doc
      :class-card: platform-card hover-lift
      :shadow: md
      
      **Qwen Code**
      ^^^
      Code editor for AI scientist workflows

   .. grid-item-card::
      :link: building_ai_scientists/codex_cli
      :link-type: doc
      :class-card: platform-card hover-lift
      :shadow: md
      
      **Codex CLI**
      ^^^
      Terminal-based interface with OpenAI Codex

   .. grid-item-card::
      :link: building_ai_scientists/chatgpt_api
      :link-type: doc
      :class-card: platform-card hover-lift
      :shadow: md
      
      **ChatGPT API**
      ^^^
      API for programmatic research automation

.. tip:: 🎯 **Guided Setup Available**
   
   Install skills first with ``npx skills add mims-harvard/ToolUniverse``, then ask your AI coding agent **"setup tooluniverse"**. The ``setup-tooluniverse`` skill will walk you through MCP configuration, API keys, and validation step by step.

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
            "args": ["tooluniverse"],
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


- **Setup issues?** Check the :doc:`../help/troubleshooting` guide
- **Questions?** Join our `Slack community <https://join.slack.com/t/tooluniversehq/shared_invite/zt-3dic3eoio-5xxoJch7TLNibNQn5_AREQ>`_
- **Bug reports?** `Create an issue <https://github.com/mims-harvard/ToolUniverse/issues>`_

Quick Links
-----------

.. button-ref:: python_guide
   :color: secondary
   :shadow:
   :expand:

   🐍 **Coding Agent?** Use ToolUniverse directly with Python API

.. button-ref:: ../index
   :color: info
   :shadow:
   :expand:

   🏠 **Back to Home**: Return to main documentation