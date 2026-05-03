Environment Variables Reference
=================================

ToolUniverse can be configured through environment variables for cache behavior, logging, LLM integration, performance tuning, and more.

.. contents:: Table of Contents
   :local:
   :depth: 2

Quick Reference
---------------

**Most commonly used**:

- ``TOOLUNIVERSE_CACHE_ENABLED`` - Enable/disable caching (default: ``true``)
- ``TOOLUNIVERSE_LOG_LEVEL`` - Set logging level (default: ``INFO``)
- ``NCBI_API_KEY`` - Faster PubMed/NCBI access (3x rate limit increase)

For API keys configuration, see :doc:`../guide/api_keys`.

Cache Configuration
-------------------

Control ToolUniverse's two-tier caching system (in-memory LRU + SQLite persistence).

.. list-table::
   :header-rows: 1
   :widths: 30 15 55

   * - Variable
     - Default
     - Description
   * - ``TOOLUNIVERSE_CACHE_ENABLED``
     - ``true``
     - Master switch for all caching. Set to ``false`` to disable both memory and persistent cache.
   * - ``TOOLUNIVERSE_CACHE_PERSIST``
     - ``true``
     - Enable SQLite persistence. Cached results survive Python restarts.
   * - ``TOOLUNIVERSE_CACHE_PATH``
     - (see below)
     - Full path to SQLite cache file. If unset, uses ``TOOLUNIVERSE_CACHE_DIR``/``tooluniverse_cache.sqlite``
   * - ``TOOLUNIVERSE_CACHE_DIR``
     - ``~/.tooluniverse``
     - Directory for cache file when ``CACHE_PATH`` is not specified.
   * - ``TOOLUNIVERSE_CACHE_MEMORY_SIZE``
     - ``256``
     - Maximum entries in in-memory LRU cache. Increase for batch workflows (e.g., ``5000000`` for millions of entries).
   * - ``TOOLUNIVERSE_CACHE_DEFAULT_TTL``
     - ``None``
     - Time-to-live in seconds for cached entries. ``None`` means no expiration.
   * - ``TOOLUNIVERSE_CACHE_SINGLEFLIGHT``
     - ``true``
     - Deduplicate concurrent identical requests. Prevents redundant API calls when multiple threads request same data.
   * - ``TOOLUNIVERSE_CACHE_ASYNC_PERSIST``
     - ``true``
     - Write to SQLite on background thread for non-blocking I/O. Set to ``false`` for immediate disk persistence.

**Examples**::

   # Disable caching entirely
   export TOOLUNIVERSE_CACHE_ENABLED=false
   
   # Custom cache location with 1-hour expiration
   export TOOLUNIVERSE_CACHE_PATH=/tmp/my_cache.sqlite
   export TOOLUNIVERSE_CACHE_DEFAULT_TTL=3600
   
   # Large-scale batch processing (5M entries in memory)
   export TOOLUNIVERSE_CACHE_MEMORY_SIZE=5000000
   
   # Synchronous writes for critical data
   export TOOLUNIVERSE_CACHE_ASYNC_PERSIST=false

**See also**: :doc:`../guide/cache_system` for complete caching guide.

Logging & Debugging
-------------------

Control log output verbosity and destinations.

.. list-table::
   :header-rows: 1
   :widths: 30 15 55

   * - Variable
     - Default
     - Description
   * - ``TOOLUNIVERSE_LOG_LEVEL``
     - ``INFO``
     - Logging level: ``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``, ``CRITICAL``
   * - ``TOOLUNIVERSE_STDIO_MODE``
     - ``0``
     - Internal flag. Set to ``1`` for STDIO-based MCP servers (redirects logs to stderr).
   * - ``TOOLUNIVERSE_VERBOSE``
     - ``0``
     - Enable verbose output for tool generation and debugging. Set to ``1`` for detailed logs.

**Examples**::

   # Debug mode for troubleshooting
   export TOOLUNIVERSE_LOG_LEVEL=DEBUG
   
   # Verbose tool generation
   export TOOLUNIVERSE_VERBOSE=1

**See also**: :doc:`../guide/logging` for logging configuration.

Loading & Import Control
------------------------

Optimize startup time and memory usage by controlling how tools are loaded.

.. list-table::
   :header-rows: 1
   :widths: 30 15 55

   * - Variable
     - Default
     - Description
   * - ``TOOLUNIVERSE_LAZY_LOADING``
     - ``true``
     - Defer tool loading until first use. Improves startup speed.
   * - ``TOOLUNIVERSE_LIGHT_IMPORT``
     - ``false``
     - Minimal imports on package import. Reduces memory footprint for embedded use.
   * - ``TOOLUNIVERSE_COERCE_TYPES``
     - ``true``
     - Auto-convert parameter types (e.g., string ``"42"`` → integer ``42``) when calling tools. Disable for strict type enforcement.
   * - ``TOOLUNIVERSE_STRICT_VALIDATION``
     - ``false``
     - Raise errors on unknown or extra parameters instead of silently ignoring them.

**Examples**::

   # Disable lazy loading (load all tools at startup)
   export TOOLUNIVERSE_LAZY_LOADING=false
   
   # Minimal imports for embedded systems
   export TOOLUNIVERSE_LIGHT_IMPORT=true

**When to use**:

- **Lazy loading (default)**: Best for most use cases. Fast startup, tools load on-demand.
- **Eager loading**: Set ``LAZY_LOADING=false`` if you need all tools pre-loaded (e.g., warming cache).
- **Light import**: Embedded systems or when ToolUniverse is imported but not immediately used.

LLM Configuration
-----------------

Configure Large Language Model providers for agentic tools and LLM-powered features.

.. list-table::
   :header-rows: 1
   :widths: 35 15 50

   * - Variable
     - Default
     - Description
   * - ``TOOLUNIVERSE_LLM_DEFAULT_PROVIDER``
     - (none)
     - Default LLM provider: ``openai``, ``azure``, ``gemini``, ``anthropic``
   * - ``TOOLUNIVERSE_LLM_CONFIG_MODE``
     - ``default``
     - LLM configuration mode. Use ``default`` or custom profiles.
   * - ``TOOLUNIVERSE_LLM_TEMPERATURE``
     - (varies)
     - Temperature for LLM sampling (0.0-1.0). Higher = more creative.
   * - ``TOOLUNIVERSE_LLM_MODEL_DEFAULT``
     - (provider default)
     - Default model ID when not task-specific.
   * - ``TOOLUNIVERSE_LLM_MODEL_{TASK}``
     - (none)
     - Task-specific model. ``{TASK}`` = uppercase task name (e.g., ``SUMMARIZATION``, ``EXTRACTION``).

**Examples**::

   # Use OpenAI for all LLM tasks
   export TOOLUNIVERSE_LLM_DEFAULT_PROVIDER=openai
   export TOOLUNIVERSE_LLM_MODEL_DEFAULT=gpt-4o-mini
   
   # Task-specific models
   export TOOLUNIVERSE_LLM_MODEL_SUMMARIZATION=gpt-4o-mini
   export TOOLUNIVERSE_LLM_MODEL_EXTRACTION=gpt-4o
   
   # Adjust temperature
   export TOOLUNIVERSE_LLM_TEMPERATURE=0.2

**Use cases**:

- **Agentic Tools**: Tools that use LLMs internally (e.g., Tool_Finder_LLM, summarization tools)
- **Hooks**: LLM-powered output processing hooks
- **Custom Tools**: Your own tools that leverage LLM capabilities

**See also**: Provider-specific API keys in :doc:`../guide/api_keys`.

Performance & System
--------------------

Tune system resources and performance characteristics.

.. list-table::
   :header-rows: 1
   :widths: 30 15 55

   * - Variable
     - Default
     - Description
   * - ``TOOLUNIVERSE_THREAD_POOL_SIZE``
     - ``20``
     - Thread pool size for HTTP API server concurrent requests.
   * - ``TOOLUNIVERSE_TMPDIR``
     - (system temp)
     - Override temporary directory location. Useful for systems with custom temp partitions.

**Examples**::

   # Increase HTTP API concurrency
   export TOOLUNIVERSE_THREAD_POOL_SIZE=50
   
   # Custom temporary directory
   export TOOLUNIVERSE_TMPDIR=/mnt/fast-ssd/tmp

Development & Tool Generation
------------------------------

Control tool code generation and development workflows.

.. list-table::
   :header-rows: 1
   :widths: 30 15 55

   * - Variable
     - Default
     - Description
   * - ``TOOLUNIVERSE_SKIP_FORMAT``
     - ``0``
     - Skip code formatting during tool generation. Set to ``1`` to speed up generation.
   * - ``TOOLUNIVERSE_FORCE_REGENERATE``
     - ``0``
     - Force regeneration of all tool files even if unchanged. Set to ``1`` for fresh builds.

**Examples**::

   # Fast tool generation (skip formatting)
   export TOOLUNIVERSE_SKIP_FORMAT=1
   
   # Force complete regeneration
   export TOOLUNIVERSE_FORCE_REGENERATE=1

**Use cases**:

- **Development**: When iterating on tool generation scripts
- **CI/CD**: Ensure clean generation in automated builds

Embedding Provider Configuration
---------------------------------

For tu-datastore and semantic search features.

.. list-table::
   :header-rows: 1
   :widths: 25 60

   * - Variable
     - Description
   * - ``EMBED_PROVIDER``
     - Embedding provider: ``openai``, ``azure``, ``huggingface``, ``local``
   * - ``EMBED_MODEL``
     - Embedding model name (e.g., ``text-embedding-3-small``)
   * - ``OPENAI_API_KEY``
     - OpenAI API key (if using OpenAI embeddings)
   * - ``HF_TOKEN``
     - Hugging Face token (if using HF embeddings)
   * - ``AZURE_*``
     - Azure-specific configuration variables

**Examples**::

   # OpenAI embeddings
   export EMBED_PROVIDER=openai
   export EMBED_MODEL=text-embedding-3-small
   export OPENAI_API_KEY=sk-...
   
   # Hugging Face embeddings
   export EMBED_PROVIDER=huggingface
   export EMBED_MODEL=sentence-transformers/all-MiniLM-L6-v2
   export HF_TOKEN=hf_...

**See also**: ``tu-datastore`` command in :doc:`cli_tools`.

API Keys
--------

API keys for external scientific databases and services.

For complete API key documentation including:

- Required vs optional keys
- Rate limits and performance benefits
- Configuration methods
- Troubleshooting

See: :doc:`../guide/api_keys`

**Common API keys**::

   # NCBI (3x faster PubMed access)
   NCBI_API_KEY=your_key_here
   
   # Semantic Scholar (no rate limits)
   SEMANTIC_SCHOLAR_API_KEY=your_key_here
   
   # NVIDIA NIM (protein structure prediction)
   NVIDIA_API_KEY=your_key_here
   
   # Many more available - see api_keys.rst

Configuration File Support
--------------------------

You can set environment variables in a ``.env`` file at project root:

**Example .env file**::

   # Cache configuration
   TOOLUNIVERSE_CACHE_ENABLED=true
   TOOLUNIVERSE_CACHE_MEMORY_SIZE=1024
   TOOLUNIVERSE_CACHE_DEFAULT_TTL=3600
   
   # Logging
   TOOLUNIVERSE_LOG_LEVEL=INFO
   
   # API Keys
   NCBI_API_KEY=your_key_here
   SEMANTIC_SCHOLAR_API_KEY=your_key_here
   
   # LLM Configuration
   TOOLUNIVERSE_LLM_DEFAULT_PROVIDER=openai
   OPENAI_API_KEY=sk-...

**To use**:

1. **Automatic**: ToolUniverse automatically loads ``.env`` from current directory
2. **Manual**: Use python-dotenv::

      from dotenv import load_dotenv
      load_dotenv()
      from tooluniverse import ToolUniverse

**See also**: Template at ``.env.template`` in project root.

Precedence Order
----------------

When the same configuration is specified in multiple places, ToolUniverse uses this precedence order (highest to lowest):

1. **Environment variables** (highest priority)
   - Set in shell: ``export TOOLUNIVERSE_CACHE_ENABLED=false``
   - Set in code: ``os.environ["TOOLUNIVERSE_CACHE_ENABLED"] = "false"``

2. **``.env`` file** in current directory
   - Loaded automatically by ToolUniverse

3. **Default values** (lowest priority)
   - Built-in defaults in code

**Example**::

   # .env file
   TOOLUNIVERSE_CACHE_MEMORY_SIZE=512
   
   # Shell export (overrides .env)
   export TOOLUNIVERSE_CACHE_MEMORY_SIZE=1024
   
   # Result: Uses 1024 (environment variable wins)

Platform-Specific Notes
-----------------------

Linux/macOS
~~~~~~~~~~~

Use shell export::

   export TOOLUNIVERSE_CACHE_ENABLED=true
   
Permanent (add to ``~/.bashrc`` or ``~/.zshrc``)::

   echo 'export TOOLUNIVERSE_CACHE_ENABLED=true' >> ~/.bashrc

Windows (PowerShell)
~~~~~~~~~~~~~~~~~~~~

::

   $env:TOOLUNIVERSE_CACHE_ENABLED = "true"
   
Permanent::

   [System.Environment]::SetEnvironmentVariable('TOOLUNIVERSE_CACHE_ENABLED', 'true', 'User')

Windows (Command Prompt)
~~~~~~~~~~~~~~~~~~~~~~~~~

::

   set TOOLUNIVERSE_CACHE_ENABLED=true

Docker
~~~~~~

In Dockerfile::

   ENV TOOLUNIVERSE_CACHE_ENABLED=true \
       TOOLUNIVERSE_LOG_LEVEL=INFO

Or docker-compose.yml::

   services:
     tooluniverse:
       environment:
         - TOOLUNIVERSE_CACHE_ENABLED=true
         - TOOLUNIVERSE_LOG_LEVEL=INFO

Verification
------------

Check if environment variables are set correctly:

**Python**::

   import os
   print(os.getenv("TOOLUNIVERSE_CACHE_ENABLED"))  # Should print 'true' or 'false'

**Shell**::

   echo $TOOLUNIVERSE_CACHE_ENABLED  # Linux/macOS
   echo %TOOLUNIVERSE_CACHE_ENABLED%  # Windows CMD
   $env:TOOLUNIVERSE_CACHE_ENABLED   # Windows PowerShell

**Using tooluniverse-doctor**::

   tooluniverse-doctor --check-keys

Troubleshooting
---------------

Environment variable not taking effect
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Possible causes**:

1. Variable set after importing ToolUniverse
   - **Solution**: Set environment variables *before* ``from tooluniverse import ToolUniverse``

2. Typo in variable name
   - **Solution**: Variable names are case-sensitive. Use exactly as documented.

3. Value format incorrect
   - **Solution**: Boolean values should be ``true``/``false`` (lowercase). Numbers should be unquoted.

4. Cached Python import
   - **Solution**: Restart Python interpreter to reload environment

Values not persisting
~~~~~~~~~~~~~~~~~~~~~

**Problem**: Variables reset after terminal closes.

**Solution**: Add to shell configuration file:

- Bash: ``~/.bashrc`` or ``~/.bash_profile``
- Zsh: ``~/.zshrc``
- Fish: ``~/.config/fish/config.fish``

See Also
--------

- :doc:`cli_tools` - Command-line tools reference
- :doc:`../guide/api_keys` - API keys configuration
- :doc:`../guide/cache_system` - Caching system guide
- :doc:`../guide/logging` - Logging configuration
- :doc:`../help/troubleshooting` - Troubleshooting guide
- :doc:`../guide/python_guide` - Installation and Python API guide

Complete Variable List
----------------------

**Quick reference table** of all documented environment variables:

.. list-table::
   :header-rows: 1
   :widths: 40 15 45

   * - Variable
     - Default
     - Category
   * - ``TOOLUNIVERSE_CACHE_ENABLED``
     - true
     - Cache
   * - ``TOOLUNIVERSE_CACHE_PERSIST``
     - true
     - Cache
   * - ``TOOLUNIVERSE_CACHE_PATH``
     - (dynamic)
     - Cache
   * - ``TOOLUNIVERSE_CACHE_DIR``
     - ~/.tooluniverse
     - Cache
   * - ``TOOLUNIVERSE_CACHE_MEMORY_SIZE``
     - 256
     - Cache
   * - ``TOOLUNIVERSE_CACHE_DEFAULT_TTL``
     - None
     - Cache
   * - ``TOOLUNIVERSE_CACHE_SINGLEFLIGHT``
     - true
     - Cache
   * - ``TOOLUNIVERSE_CACHE_ASYNC_PERSIST``
     - true
     - Cache
   * - ``TOOLUNIVERSE_LOG_LEVEL``
     - INFO
     - Logging
   * - ``TOOLUNIVERSE_STDIO_MODE``
     - 0
     - Logging
   * - ``TOOLUNIVERSE_VERBOSE``
     - 0
     - Logging
   * - ``TOOLUNIVERSE_LAZY_LOADING``
     - true
     - Loading
   * - ``TOOLUNIVERSE_LIGHT_IMPORT``
     - false
     - Loading
   * - ``TOOLUNIVERSE_COERCE_TYPES``
     - true
     - Loading
   * - ``TOOLUNIVERSE_STRICT_VALIDATION``
     - false
     - Loading
   * - ``TOOLUNIVERSE_LLM_DEFAULT_PROVIDER``
     - (none)
     - LLM
   * - ``TOOLUNIVERSE_LLM_CONFIG_MODE``
     - default
     - LLM
   * - ``TOOLUNIVERSE_LLM_TEMPERATURE``
     - (varies)
     - LLM
   * - ``TOOLUNIVERSE_LLM_MODEL_DEFAULT``
     - (provider default)
     - LLM
   * - ``TOOLUNIVERSE_LLM_MODEL_{TASK}``
     - (none)
     - LLM
   * - ``TOOLUNIVERSE_THREAD_POOL_SIZE``
     - 20
     - Performance
   * - ``TOOLUNIVERSE_TMPDIR``
     - (system temp)
     - Performance
   * - ``TOOLUNIVERSE_SKIP_FORMAT``
     - 0
     - Development
   * - ``TOOLUNIVERSE_FORCE_REGENERATE``
     - 0
     - Development
   * - ``EMBED_PROVIDER``
     - (none)
     - Embeddings
   * - ``EMBED_MODEL``
     - (none)
     - Embeddings
   * - API keys
     - (various)
     - See :doc:`../guide/api_keys`
