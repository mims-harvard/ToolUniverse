.. |logo| image:: _static/logo.png
   :height: 32
   :alt: ToolUniverse Logo

|logo| ToolUniverse Documentation
=================================

.. raw:: html

   <div align="center">

.. image:: https://img.shields.io/badge/Website-aiscientist.tools-brightgreen.svg?logo=google-chrome
   :alt: Website
   :target: https://aiscientist.tools

.. image:: https://img.shields.io/pypi/v/tooluniverse.svg?label=PyPI&logo=pypi
   :alt: PyPI
   :target: https://pypi.org/project/tooluniverse

.. image:: https://img.shields.io/badge/GitHub-ToolUniverse-black.svg?logo=github
   :alt: GitHub
   :target: https://github.com/mims-harvard/ToolUniverse

.. image:: https://img.shields.io/badge/Slack-Join_Community-purple.svg?logo=slack
   :alt: Slack
   :target: https://join.slack.com/t/tooluniversehq/shared_invite/zt-3dic3eoio-5xxoJch7TLNibNQn5_AREQ

.. raw:: html

   </div>

.. raw:: html

   <div align="center">
   
   <a href="https://aiscientist.tools">
   <img src="https://img.shields.io/badge/Visit_Website-AIScientist.Tools-4285F4?style=for-the-badge&logo=google-chrome&logoColor=white" alt="Visit Website">
   </a>
   
   <br><br>
   
   <a href="https://join.slack.com/t/tooluniversehq/shared_invite/zt-3dic3eoio-5xxoJch7TLNibNQn5_AREQ">
   <img src="https://img.shields.io/badge/Join_Slack_Community-Get_Help_&_Connect-FF6B6B?style=for-the-badge&logo=slack&logoColor=white" alt="Join Slack Community">
   </a>
   <a href="wechat_community.html">
   <img src="https://img.shields.io/badge/Join_WeChat_Group-Community_&_Discussion-07C160?style=for-the-badge&logo=wechat&logoColor=white" alt="Join WeChat Group">
   </a>
   
   <br><br>
   
   <a href="https://www.linkedin.com/in/tooluniverse-at-harvard-b9aa88385/">
   <img src="https://img.shields.io/badge/Follow_on_LinkedIn-Professional_Updates-0077B5?style=for-the-badge&logo=linkedin&logoColor=white" alt="Follow on LinkedIn">
   </a>
   <a href="https://x.com/ScientistTools">
   <img src="https://img.shields.io/badge/Follow_on_X-Latest_Updates-000000?style=for-the-badge&logo=x&logoColor=white" alt="Follow on X">
   </a>
   
   </div>

Democratizing AI Scientists for Science
---------------------------

ToolUniverse is a unified ecosystem that transforms any large language model (LLM)—open or closed—into a powerful AI scientist. By standardizing how LLMs identify and call tools, it integrates over 1000 scientific resources, including machine learning models, datasets, APIs, and analysis packages.

With its **AI-Tool Interaction Protocol**, ToolUniverse provides a common interface for seamless communication between LLMs and tools, ensuring compatibility across platforms such as GPT, Claude, Gemini, and open-source models.

🚀 Start Here
-------------

**New to ToolUniverse?** Follow this path:

1. **Quickstart** (5 min) → :doc:`quickstart`
   
   Try your first query without reading lengthy docs

2. **Getting Started** (30 min) → :doc:`getting_started`
   
   Step-by-step tutorial covering core concepts

3. **Choose Your Integration** → :doc:`guide/building_ai_scientists/index`
   
   Connect to Claude, ChatGPT, Gemini, or use Python API

**Already familiar?** Jump to:

- :doc:`guide/index` - Complete feature guide
- :doc:`tools/tools_config_index` - Browse 1000+ tools
- :doc:`help/troubleshooting` - Fix issues
- :doc:`reference/cli_tools` - Command-line tools reference

.. important::
   **🔍 Looking for specific tools?**
   
   ToolUniverse has 3 specialized search tools to find what you need:
   
   - **Tool_Finder_Keyword** - Fast keyword search ("protein structure", "drug interactions")
   - **Tool_Finder_LLM** - Natural language search ("find tools for analyzing gene expression")
   - **Tool_Finder** - Semantic embedding search (most powerful, finds by meaning)
   
   → See :doc:`tutorials/finding_tools` for detailed guide on finding and using tools.


Building your AI Scientists
---------------------------

Transform any LLM/Reasoning Model/Agent into a powerful research scientist with ToolUniverse's comprehensive integration guides:

📖 **Complete Tutorial**: `Building AI Scientists Overview <guide/building_ai_scientists/index.html>`_


- **Claude Desktop**: `Claude Desktop Integration <guide/building_ai_scientists/claude_desktop.html>`_
- **Claude Code**: `Claude Code Integration <guide/building_ai_scientists/claude_code.html>`_
- **Gemini CLI**: `Gemini CLI Integration <guide/building_ai_scientists/gemini_cli.html>`_
- **Qwen Code**: `Qwen Code Integration <guide/building_ai_scientists/qwen_code.html>`_
- **Codex CLI**: `Codex CLI Integration <guide/building_ai_scientists/codex_cli.html>`_
- **ChatGPT API**: `ChatGPT API Integration <guide/building_ai_scientists/chatgpt_api.html>`_

🌍 Ecosystem & Community
------------------------
**Open Science**

- Open-source ecosystem encouraging community contributions
- Standardized tool specifications for agentic AI
- Integration with heterogeneous scientific workflows

**Join the Community**

- **Web Service**: `aiscientist.tools <https://aiscientist.tools>`_
- **GitHub Repository**: `mims-harvard/ToolUniverse <https://github.com/mims-harvard/ToolUniverse>`_
- **Report Issues**: `GitHub Issues <https://github.com/mims-harvard/ToolUniverse/issues>`_
- **Discussions**: `Join our Slack community <https://join.slack.com/t/tooluniversehq/shared_invite/zt-3dic3eoio-5xxoJch7TLNibNQn5_AREQ>`_

📚 Documentation Structure
-------------------------

.. toctree::
   :maxdepth: 1
   :caption: 🚀 Getting Started

   quickstart
   installation
   api_keys
   getting_started

.. toctree::
   :maxdepth: 3
   :caption: 🤖 Building AI Scientists

   guide/building_ai_scientists/index

.. toctree::
   :maxdepth: 1
   :caption: 💡 Use ToolUniverse

   guide/index
   guide/interaction_protocol
   guide/loading_tools
   guide/listing_tools
   tutorials/finding_tools
   guide/tool_caller
   guide/building_ai_scientists/mcp_support
   guide/building_ai_scientists/mcpb_introduction
   guide/compact_mode
   guide/toolspace
   guide/coding_api
   tutorials/tooluniverse_case_study
   tutorials/agentic_tools_tutorial
   tutorials/literature_search_tools_tutorial
   tutorials/literature_search_web_ui_tutorial
   guide/clinical_guidelines_tools
   guide/tool_composition
   guide/scientific_workflows
   tutorials/expert_feedback
   guide/hooks/index
   guide/cache_system
   guide/examples
   guide/logging
   guide/openrouter_support
   guide/streaming_tools
   guide/tools
   guide/vllm_support
   wechat_community
   tutorials/make_your_data_agent_searchable
   tutorials/visualization_tutorial

.. toctree::
   :maxdepth: 3
   :caption: 🔨 Add Tools to ToolUniverse

   expand_tooluniverse/index
   expand_tooluniverse/quick_start
   expand_tooluniverse/local_tools/index
   expand_tooluniverse/remote_tools/index
   expand_tooluniverse/contributing/index
   expand_tooluniverse/architecture

.. toctree::
   :maxdepth: 1
   :caption: 🔧 Tools

   tools/tools_config_index
   tools/remote_tools


.. toctree::
   :maxdepth: 1
   :caption: 🔌 API

   api/modules

.. toctree::
   :maxdepth: 1
   :caption: ❓ Reference

   reference/cli_tools
   reference/environment_variables
   glossary
   reference/data_sources
   help/index
   expand_tooluniverse/reference/index
   about/index
