Tutorial Navigation
===================

**Python API:** :doc:`../api/modules` | **MCP setup:** :doc:`building_ai_scientists/mcp_support`

Core Concepts
-------------

* **Loading Tools** → :doc:`loading_tools` - Complete tutorial to loading tools with Python API and MCP terminal commands
* **Listing Tools** → :doc:`listing_tools` - Discover and filter tools by capability, domain, and IO
* **Tool Caller** → :doc:`tool_caller` - Primary execution engine with dynamic loading, validation, and MCP server integration
* **Tool Composition** → :doc:`tool_composition` - Chain ToolUniverse's 1000+ tools into powerful scientific workflows using Tool Composer
* **Coding API** → :doc:`coding_api` - Import and call tools like normal Python functions with type safety
* **Scientific Workflows** → :doc:`scientific_workflows` - Real-world research scenarios: drug discovery, safety analysis, literature review
* **MCP Support** → :doc:`building_ai_scientists/mcp_support` - Model Context Protocol integration and server setup
* **MCP Name Shortening** → :doc:`building_ai_scientists/mcp_name_shortening` - Automatic tool name shortening for MCP 64-character limit compatibility
* **MCPB Support** → :doc:`building_ai_scientists/mcpb_introduction` - Standalone executable bundle for Claude Desktop and other clients
* **HTTP API** → :doc:`http_api` - Remote access via HTTP/REST with auto-updating server and minimal client dependencies
* **Compact Mode** → :doc:`building_ai_scientists/compact_mode` - Optimize context window usage by exposing only core tools (4 tools) while maintaining full functionality
* **Streaming Tools** → :doc:`streaming_tools` - Real-time streaming output and custom tool integration
* **Logging** → :doc:`logging` - Comprehensive logging configuration and debugging
* **Result Caching** → :doc:`cache_system` - Configure in-memory and persistent caches for tool results
* **Interaction Protocol** → :doc:`interaction_protocol` - Understanding tool interaction patterns

Tool Discovery & Usage
----------------------

* **Tool Discovery** → :doc:`finding_tools` - Tutorial to ToolUniverse's three tool finder methods: keyword, LLM, and embedding search
* **Tools Overview** → :doc:`tools` - Comprehensive overview of all available tools

AI Agent Platform Setup
-----------------------

* **Platform Setup** → :doc:`building_ai_scientists/index` - Connect ToolUniverse to your AI agent

LLM Providers
-------------

* **vLLM Support** → :doc:`vllm_support` - Use self-hosted LLM models with vLLM for high-performance inference
* **OpenRouter Support** → :doc:`openrouter_support` - Access multiple LLM providers through OpenRouter API

Advanced Features
-----------------

* **Hooks System** → :doc:`hooks/index` - Intelligent output processing with AI-powered hooks

  * **SummarizationHook** → :doc:`hooks/summarization_hook` - AI-powered output summarization
  * **FileSaveHook** → :doc:`hooks/file_save_hook` - File-based output processing and archiving
  * **Hook Configuration** → :doc:`hooks/hook_configuration` - Advanced configuration and customization
  * **Server & Stdio Hooks** → :doc:`hooks/server_stdio_hooks` - Using hooks with server and stdio interfaces

Tool Collections
----------------

Specialized tool collections for specific research domains:

* **Clinical Guidelines** → :doc:`clinical_guidelines_tools` - Search and extract clinical practice guidelines from NICE, WHO, PubMed, and 5 other authoritative sources
* **Literature Search** → :doc:`literature_search_tools_tutorial` - Comprehensive literature search across PubMed, arXiv, bioRxiv, and academic databases
* **Profile & Workspace** → :doc:`toolspace` - Configure which tools to load, cache settings, LLM providers, and hooks via profile.yaml. Includes ``life-science.yaml``, a ready-made profile covering all life science and general tools.
* **tu CLI** → :doc:`tu_cli` - Discover and execute tools from the shell without an MCP server.
