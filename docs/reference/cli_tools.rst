CLI Tools Reference
===================

ToolUniverse provides several command-line tools for server management, diagnostics, and data management.

.. contents:: Table of Contents
   :local:
   :depth: 2

MCP Server Commands
-------------------

tooluniverse-smcp
~~~~~~~~~~~~~~~~~

Start the Scientific Model Context Protocol (SMCP) server with HTTP/SSE transport.

**Usage**::

   tooluniverse-smcp [OPTIONS]

**Common Options**:

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Option
     - Default
     - Description
   * - ``--host``
     - 127.0.0.1
     - Server host address
   * - ``--port``
     - 8000
     - Server port
   * - ``--compact-mode``
     - False
     - Enable compact tool names (40% shorter)
   * - ``--categories``
     - all
     - Load specific tool categories only
   * - ``--hooks-enabled``
     - False
     - Enable output processing hooks
   * - ``--load``
     - None
     - Load space configuration (preset/workspace)

**Examples**::

   # Start server with all tools (default: localhost:8000)
   tooluniverse-smcp
   
   # Start with compact mode (recommended for AI assistants)
   tooluniverse-smcp --compact-mode
   
   # Start with specific categories only
   tooluniverse-smcp --categories uniprot ChEMBL opentarget
   
   # Start with custom port
   tooluniverse-smcp --port 3001
   
   # Load workspace configuration
   tooluniverse-smcp --load "community/proteomics-toolkit"

**See also**: :doc:`../guide/building_ai_scientists/mcp_support` for detailed MCP integration guide

tooluniverse-smcp-stdio
~~~~~~~~~~~~~~~~~~~~~~~

Start SMCP server with STDIO transport for desktop AI applications (Claude Desktop, Cursor, etc.).

**Usage**::

   tooluniverse-smcp-stdio [OPTIONS]

**Common Options**: Same as ``tooluniverse-smcp`` except transport-related options.

**Examples**::

   # Claude Desktop configuration (in claude_desktop_config.json)
   {
     "mcpServers": {
       "tooluniverse": {
         "command": "tooluniverse-smcp-stdio",
         "args": ["--compact-mode"]
       }
     }
   }

**See also**: :doc:`../guide/building_ai_scientists/claude_desktop`

tooluniverse-smcp-server
~~~~~~~~~~~~~~~~~~~~~~~~

Alias for ``tooluniverse-smcp`` - starts HTTP/SSE server.

**Usage**::

   tooluniverse-smcp-server [OPTIONS]

This command is identical to ``tooluniverse-smcp`` and provided for compatibility.

tooluniverse-http-api
~~~~~~~~~~~~~~~~~~~~~

Start HTTP API server for ToolUniverse class methods.

**Usage**::

   tooluniverse-http-api [OPTIONS]

**Options**:

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Option
     - Default
     - Description
   * - ``--host``
     - 127.0.0.1
     - Server host address
   * - ``--port``
     - 8080
     - Server port
   * - ``--workers``
     - 4
     - Number of worker processes

**See also**: :doc:`../guide/http_api`

Diagnostic Tools
----------------

tooluniverse-doctor
~~~~~~~~~~~~~~~~~~~

Health check tool that diagnoses ToolUniverse installation and tool availability.

**Usage**::

   tooluniverse-doctor [OPTIONS]

**Options**:

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Option
     - Default
     - Description
   * - ``--verbose``
     - False
     - Show detailed diagnostic information
   * - ``--check-keys``
     - False
     - Verify API key configuration

**What it checks**:

- ✅ ToolUniverse installation and imports
- ✅ Tool loading status (available vs unavailable)
- ✅ Missing dependencies for specific tools
- ✅ API key configuration (with ``--check-keys``)

**Example Output**::

   🔍 Checking ToolUniverse health...
   
   📊 Total tools: 1195
   ✅ Available: 1150
   ❌ Unavailable: 45
   
   ⚠️  Unavailable tools:
   
     ❌ BioBERT_ner
        Error: No module named 'transformers'
        Fix: pip install transformers
   
   💡 Bulk fix command:
      pip install transformers torch biopython

**Use cases**:

- After fresh installation to verify setup
- Debugging tool loading issues
- Before important analyses to ensure all needed tools are available
- Identifying missing optional dependencies

Data Management Tools
---------------------

tu-datastore
~~~~~~~~~~~~

Manage local searchable datastores for building custom tool collections with semantic search.

**Usage**::

   tu-datastore COMMAND [OPTIONS]

**Commands**:

build
^^^^^

Build or extend a collection from JSON documents.

**Usage**::

   tu-datastore build --collection NAME --docs-json PATH [OPTIONS]

**Options**:

.. list-table::
   :header-rows: 1
   :widths: 25 60

   * - Option
     - Description
   * - ``--collection``
     - Collection name (required)
   * - ``--docs-json``
     - Path to JSON file with documents (required)
   * - ``--db``
     - Optional path to SQLite database (default: ~/.tooluniverse/embeddings/<name>.db)
   * - ``--provider``
     - Embedding provider: openai, azure, huggingface, local
   * - ``--model``
     - Embedding model name
   * - ``--overwrite``
     - Rebuild FAISS index if exists

**Example**::

   tu-datastore build \
     --collection my_research \
     --docs-json ./documents.json \
     --provider openai \
     --model text-embedding-3-small

quickbuild
^^^^^^^^^^

Build a collection from a folder of text files (.txt/.md).

**Usage**::

   tu-datastore quickbuild --name NAME --from-folder PATH [OPTIONS]

**Example**::

   tu-datastore quickbuild \
     --name my_notes \
     --from-folder ~/Documents/research/ \
     --provider openai \
     --model text-embedding-3-small

search
^^^^^^

Query an existing collection.

**Usage**::

   tu-datastore search --collection NAME --query TEXT [OPTIONS]

**Options**:

.. list-table::
   :header-rows: 1
   :widths: 25 60

   * - Option
     - Description
   * - ``--collection``
     - Collection name (required)
   * - ``--query``
     - Search query text (required)
   * - ``--method``
     - Search method: keyword, embedding, hybrid (default: hybrid)
   * - ``--top-k``
     - Number of results to return (default: 10)
   * - ``--alpha``
     - Hybrid mix weight (default: 0.5)

**Example**::

   tu-datastore search \
     --collection my_research \
     --query "protein folding mechanisms" \
     --method hybrid \
     --top-k 5

sync-hf
^^^^^^^

Upload/download datastore artifacts to/from Hugging Face.

**Upload Usage**::

   tu-datastore sync-hf upload --collection NAME [OPTIONS]

**Upload Options**:

.. list-table::
   :header-rows: 1
   :widths: 25 60

   * - Option
     - Description
   * - ``--collection``
     - Collection name (required)
   * - ``--repo``
     - HF dataset repo ID (default: <username>/<collection>)
   * - ``--private``
     - Make dataset private (default: True)
   * - ``--tool-json``
     - Path(s) to tool JSON file(s) to include

**Download Usage**::

   tu-datastore sync-hf download --repo REPO --collection NAME [OPTIONS]

**Example**::

   # Upload to Hugging Face
   tu-datastore sync-hf upload \
     --collection my_research \
     --repo myusername/my-research-tools \
     --private
   
   # Download from Hugging Face
   tu-datastore sync-hf download \
     --repo myusername/my-research-tools \
     --collection my_research \
     --include-tools

add-tool
^^^^^^^^

Register a tool JSON in ``~/.tooluniverse/data/user_tools`` for auto-loading.

**Usage**::

   tu-datastore add-tool PATH [OPTIONS]

**Options**:

.. list-table::
   :header-rows: 1
   :widths: 25 60

   * - Option
     - Description
   * - ``json_file``
     - Path to tool JSON file (required)
   * - ``--name``
     - Custom filename (default: source filename)
   * - ``--overwrite``
     - Overwrite if file exists

**Example**::

   tu-datastore add-tool ./my_custom_tool.json --name custom_tool.json

**Use case**: Create custom tools that will be automatically loaded by ToolUniverse without modifying the installation.

Expert Feedback Tools
---------------------

tooluniverse-expert-feedback
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Start the human expert feedback MCP server for validation workflows.

**Usage**::

   tooluniverse-expert-feedback

This starts an MCP server that provides tools for collecting human expert feedback on scientific analyses.

**See also**: Remote tools documentation

tooluniverse-expert-feedback-web
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Start the web interface for human expert feedback system.

**Usage**::

   tooluniverse-expert-feedback-web

Opens a web interface where human experts can review and validate scientific tool outputs.

Utility Commands
----------------

generate-mcp-tools
~~~~~~~~~~~~~~~~~~

Generate MCP tool configurations from ToolUniverse tool definitions.

**Usage**::

   generate-mcp-tools [OPTIONS]

This tool helps convert ToolUniverse tool specifications into MCP-compatible format for custom integrations.

.. note::
   This is an advanced tool for developers extending ToolUniverse. Most users should use the built-in MCP servers instead.

Environment Variables
---------------------

CLI tools respect these environment variables:

**Embedding Configuration** (for tu-datastore):

- ``EMBED_PROVIDER`` - Embedding provider (openai, azure, huggingface, local)
- ``EMBED_MODEL`` - Embedding model name
- ``OPENAI_API_KEY`` - OpenAI API key (if using OpenAI embeddings)
- ``HF_TOKEN`` - Hugging Face token (if using HF embeddings)

**See also**: :doc:`environment_variables` for complete reference

Troubleshooting
---------------

Server won't start
~~~~~~~~~~~~~~~~~~

**Problem**: Server fails to start or exits immediately.

**Solutions**:

1. Check if port is already in use::

      lsof -i :8000  # Check if port 8000 is busy
      
2. Run health check::

      tooluniverse-doctor
      
3. Try different port::

      tooluniverse-smcp --port 8001

Tools not loading
~~~~~~~~~~~~~~~~~

**Problem**: ``tooluniverse-doctor`` shows many unavailable tools.

**Solution**: Install missing dependencies::

   # Install all optional dependencies
   pip install tooluniverse[all]
   
   # Or follow the specific installation instructions from doctor output

Command not found
~~~~~~~~~~~~~~~~~

**Problem**: CLI commands are not recognized.

**Solution**: Ensure ToolUniverse is installed correctly::

   pip install --upgrade tooluniverse
   
   # Verify installation
   python -c "from tooluniverse import ToolUniverse; print('OK')"

See Also
--------

- :doc:`../installation` - Installation instructions
- :doc:`../guide/building_ai_scientists/mcp_support` - MCP integration guide
- :doc:`../help/troubleshooting` - Troubleshooting guide
- :doc:`environment_variables` - Environment variables reference
- :doc:`../guide/api_keys` - API keys configuration
