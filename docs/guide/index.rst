Tutorial Navigation
===================


This comprehensive tutorial takes you from basic concepts to advanced AI scientist workflows, with everything you need to democratize AI agents for scientific discovery.

Choose the section that matches your current needs:

💡 **For Python API documentation**, see the dedicated :doc:`../api/modules` section.

💡 **For MCP integration and server setup**, see the comprehensive :doc:`building_ai_scientists/mcp_support` guide.

Core Concepts
-------------

* **⚙️ Loading Tools** → :doc:`loading_tools` - Complete tutorial to loading tools with Python API and MCP terminal commands
* **📋 Listing Tools** → :doc:`listing_tools` - Discover and filter tools by capability, domain, and IO
* **🔧 Tool Caller** → :doc:`tool_caller` - Primary execution engine with dynamic loading, validation, and MCP server integration
* **🔗 Tool Composition** → :doc:`tool_composition` - Chain ToolUniverse's 1000+ tools into powerful scientific workflows using Tool Composer
* **🐍 Coding API** → :doc:`coding_api` - Import and call tools like normal Python functions with type safety
* **🔬 Scientific Workflows** → :doc:`scientific_workflows` - Real-world research scenarios: drug discovery, safety analysis, literature review
* **📡 MCP Support** → :doc:`building_ai_scientists/mcp_support` - Model Context Protocol integration and server setup
* **✂️ MCP Name Shortening** → :doc:`building_ai_scientists/mcp_name_shortening` - Automatic tool name shortening for MCP 64-character limit compatibility
* **📦 MCPB Support** → :doc:`building_ai_scientists/mcpb_introduction` - Standalone executable bundle for Claude Desktop and other clients
* **🌐 HTTP API** → :doc:`http_api` - Remote access via HTTP/REST with auto-updating server and minimal client dependencies
* **📦 Compact Mode** → :doc:`building_ai_scientists/compact_mode` - Optimize context window usage by exposing only core tools (4 tools) while maintaining full functionality
* **🔊 Streaming Tools** → :doc:`streaming_tools` - Real-time streaming output and custom tool integration
* **📝 Logging** → :doc:`logging` - Comprehensive logging configuration and debugging
* **🗃️ Result Caching** → :doc:`cache_system` - Configure in-memory and persistent caches for tool results
* **🔗 Interaction Protocol** → :doc:`interaction_protocol` - Understanding tool interaction patterns

Tool Discovery & Usage
----------------------

* **🔍 Tool Discovery** → :doc:`finding_tools` - Tutorial to ToolUniverse's three tool finder methods: keyword, LLM, and embedding search
* **📚 Tools Overview** → :doc:`tools` - Comprehensive overview of all available tools

AI Agent Platform Setup
-----------------------

* **🤖 Platform Setup** → :doc:`building_ai_scientists/index` - Connect ToolUniverse to your AI agent

  * **🖥️ Claude Desktop** → :doc:`building_ai_scientists/claude_desktop` - Claude Desktop app setup
  * **💻 Claude Code** → :doc:`building_ai_scientists/claude_code` - Claude Code editor setup
  * **🔮 Gemini CLI** → :doc:`building_ai_scientists/gemini_cli` - Gemini command-line setup
  * **🧠 Qwen Code** → :doc:`building_ai_scientists/qwen_code` - Qwen Code editor setup
  * **⚡ Codex CLI** → :doc:`building_ai_scientists/codex_cli` - Codex terminal setup
  * **🎯 ChatGPT API** → :doc:`building_ai_scientists/chatgpt_api` - ChatGPT API setup

LLM Providers
-------------

* **🚀 vLLM Support** → :doc:`vllm_support` - Use self-hosted LLM models with vLLM for high-performance inference
* **🌐 OpenRouter Support** → :doc:`openrouter_support` - Access multiple LLM providers through OpenRouter API

Advanced Features
-----------------

* **🔗 Hooks System** → :doc:`hooks/index` - Intelligent output processing with AI-powered hooks

  * **🤖 SummarizationHook** → :doc:`hooks/summarization_hook` - AI-powered output summarization
  * **💾 FileSaveHook** → :doc:`hooks/file_save_hook` - File-based output processing and archiving
  * **⚙️ Hook Configuration** → :doc:`hooks/hook_configuration` - Advanced configuration and customization
  * **🖥️ Server & Stdio Hooks** → :doc:`hooks/server_stdio_hooks` - Using hooks with server and stdio interfaces

.. tip::
   **New to ToolUniverse?** Check out the "Start Here" section on the :doc:`../index` page for a recommended learning path.

Tool Collections
----------------

Specialized tool collections for specific research domains:

* **🏥 Clinical Guidelines** → :doc:`clinical_guidelines_tools` - Search and extract clinical practice guidelines from NICE, WHO, PubMed, and 5 other authoritative sources
* **📖 Literature Search** → :doc:`literature_search_tools_tutorial` - Comprehensive literature search across PubMed, arXiv, bioRxiv, and academic databases
* **⚙️ Space Configurations** → :doc:`toolspace` - Pre-configured tool collections for protein research, genomics, bioinformatics, structural biology, cheminformatics, disease research, drug discovery, literature search, and clinical research. Load directly from GitHub or customize for your needs.
