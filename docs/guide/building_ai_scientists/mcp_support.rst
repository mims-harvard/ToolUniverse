MCP Support
===========

ToolUniverse runs as a `Model Context Protocol <https://modelcontextprotocol.io/>`_ server, exposing 1000+ scientific tools to any MCP-compatible AI client.

For platform-specific setup, see :doc:`index`.

Server Commands
---------------

Two server executables are available:

``tooluniverse-smcp``
   Full-featured server with configurable transport (HTTP, SSE, stdio).

``tooluniverse-smcp-stdio``
   Optimized for desktop AI clients (Claude Desktop, Cursor, etc.) via stdio.

CLI Options
-----------

.. code-block:: text

   tooluniverse-smcp [OPTIONS]

   --port INT                     Server port (HTTP/SSE). Default: 8000
   --host TEXT                    Bind host. Default: 0.0.0.0
   --transport [http|stdio|sse]   Transport protocol. Default: http
   --name TEXT                    Server display name
   --max-workers INT              Worker pool size
   --verbose                      Enable verbose logs

   # Tool selection
   --categories STR...            Include only these categories
   --exclude-categories STR...    Exclude these categories
   --include-tools STR...         Include only these tool names
   --tools-file PATH              File with one tool name per line
   --include-tool-types STR...    Include only these tool types
   --exclude-tool-types STR...    Exclude these tool types
   --tool-config-files TEXT       Mapping like "custom:/path/to/custom.json"

   # Compact mode
   --compact-mode                 Expose only core tools (reduces context usage)

   # Hooks
   --hooks-enabled                Enable output processing hooks
   --hook-type [SummarizationHook|FileSaveHook]
   --hook-config-file PATH        JSON config for hooks

.. code-block:: text

   tooluniverse-smcp-stdio [OPTIONS]

   --name TEXT                    Server display name
   --categories STR...            Include only these categories
   --include-tools STR...         Include only these tool names
   --tools-file PATH              File with one tool name per line
   --include-tool-types STR...    Include only these tool types
   --exclude-tool-types STR...    Exclude these tool types
   --compact-mode                 Expose only core tools
   --hooks                        Enable hooks
   --hook-type [SummarizationHook|FileSaveHook]
   --hook-config-file PATH        JSON config for hooks

Configuration Files
-------------------

**Tools file** — one tool name per line, ``#`` for comments:

.. code-block:: text

   # tools.txt
   OpenTargets_get_associated_targets_by_disease_efoId
   Tool_Finder_LLM
   ChEMBL_search_similar_molecules

Pass with ``--tools-file tools.txt``.

**Hook config file**:

.. code-block:: json

   {
     "SummarizationHook": {
       "max_tokens": 2048,
       "summary_style": "concise"
     },
     "FileSaveHook": {
       "output_dir": "/tmp/tu_outputs",
       "filename_template": "{tool}_{timestamp}.json"
     }
   }

Pass with ``--hook-config-file hooks.json``.

Python Client Example
---------------------

.. code-block:: python

   import requests

   tools = requests.get("http://127.0.0.1:8000/mcp/tools").json()

   result = requests.post("http://127.0.0.1:8000/mcp/run", json={
       "name": "UniProt_get_entry_by_accession",
       "arguments": {"accession": "P04637"}
   }).json()

Advanced Features
-----------------

- :doc:`compact_mode` — reduce context window usage by exposing only core tools
- :doc:`../hooks/server_stdio_hooks` — AI-powered output summarization and file saving
- :doc:`../python_guide` — use tools directly via the Python API instead of MCP
