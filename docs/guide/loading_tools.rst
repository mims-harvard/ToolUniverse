Tool Loading Tutorial
==================

**Complete Tutorial to loading and managing tools in ToolUniverse**

This Tutorial covers two main approaches to load and access ToolUniverse tools: Python API using ``load_tools()`` method and MCP (Model Context Protocol) server using terminal commands.

Python API: Using load_tools()
---------------------------------

The ``load_tools()`` method is the primary way to load tools when using ToolUniverse programmatically in Python.

.. note::
   **For complete Python API documentation**, see :doc:`../api/modules` for the full API reference.

.. autofunction:: tooluniverse.execute_function.ToolUniverse.load_tools
 :noindex:

Basic Usage
~~~~~~~~~~~

Load all available tools:

.. code-block:: python

   from tooluniverse import ToolUniverse

   # Initialize ToolUniverse
   tu = ToolUniverse()

   # Load all tools from all categories
   tu.load_tools()

   # Check how many tools were loaded
   print(f"Loaded {len(tu.all_tools)} tools")

   # List first 5 tools
   tool_names = tu.list_built_in_tools(mode='list_name')
   for tool in tool_names[:5]:
       print(f"  • {tool}")

Selective Tool Loading
~~~~~~~~~~~~~~~~~~~~~~

Load specific tool categories:

.. code-block:: python

   # Load only specific categories
   tu.load_tools(tool_type=["uniprot", "ChEMBL", "opentarget"])

   # Load tools but exclude certain categories
   tu.load_tools(exclude_categories=["mcp_auto_loader", "special_tools"])

Load specific tools by name:

.. code-block:: python

   # Load only specific tools
   tu.load_tools(include_tools=[
       "UniProt_get_entry_by_accession",
       "ChEMBL_get_molecule_by_chembl_id",
       "OpenTargets_get_associated_targets_by_disease_efoId"
   ])

   # Load tools from a file
   tu.load_tools(tools_file="/path/to/tool_names.txt")

Advanced Filtering
~~~~~~~~~~~~~~~~~~

Filter by tool types:

.. code-block:: python

   # Include only specific tool types
   tu.load_tools(include_tool_types=["OpenTarget", "ChEMBLTool"])

   # Exclude specific tool types
   tu.load_tools(exclude_tool_types=["ToolFinderEmbedding", "Unknown"])

Exclude specific tools:

.. code-block:: python

   # Load all tools except specific ones
   tu.load_tools(exclude_tools=["problematic_tool", "slow_tool"])

Load Additional Configurations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Add custom tool configuration files:

.. code-block:: python

   # Load additional config files
   tu.load_tools(tool_config_files={
       "custom_tools": "/path/to/custom_tools.json",
       "local_analysis": "/path/to/local_tools.json"
   })

Note: tool_config_files is a dictionary of tool category names and the path to the tool configuration file,
but it does not mean that the tool is loaded.
You need to load the tool with tool_type or include_tools or include_tool_types.

Combined Parameters
~~~~~~~~~~~~~~~~~~~

Combine multiple loading options:

.. code-block:: python

   tu.load_tools(
       tool_type=["uniprot", "ChEMBL", "custom"],              # Load specific categories
       exclude_tools=["problematic_tool"],            # Exclude specific tools
       exclude_tool_types=["Unknown"],                # Exclude tool types
       tool_config_files={                           # Add custom tools
           "custom": "/path/to/custom.json"
       }
   )

.. _mcp-server-functions:

MCP Server Functions
-------------------------------------------

ToolUniverse provides two main MCP server functions for different use cases:

.. seealso::
   For a comprehensive MCP overview, detailed configuration, best practices, and troubleshooting, see :doc:`building_ai_scientists/mcp_support`.

1. **`tooluniverse-smcp`** - Full-featured server with configurable transport (HTTP, SSE, stdio)
2. **`tooluniverse-smcp-stdio`** - Specialized server for stdio transport (for desktop AI applications)

Both functions expose the same 1000+ scientific tools through the Model Context Protocol (MCP), but with different transport configurations and argument handling.

tooluniverse-smcp Function
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The `tooluniverse-smcp` function is the main entry point for ToolUniverse's SMCP server, providing full configurability for different deployment scenarios.

Basic Server Startup
^^^^^^^^^^^^^^^^^^^^

Start a basic MCP server with all tools:

.. code-block:: bash

   # Start server on default port 7000
   tooluniverse-smcp

   # Start server on specific port
   tooluniverse-smcp --port 8000

   # Start with custom server name
   tooluniverse-smcp --name "My ToolUniverse Server" --port 8000

.. _hook-configuration:

Hook Configuration
^^^^^^^^^^^^^^^^^^

Enable intelligent output processing hooks:

.. code-block:: bash

   # Enable hooks with default SummarizationHook
   tooluniverse-smcp --hooks-enabled --port 8000

   # Use specific hook type
   tooluniverse-smcp --hook-type SummarizationHook --port 8000
   tooluniverse-smcp --hook-type FileSaveHook --port 8000

   # Use custom hook configuration
   tooluniverse-smcp --hook-config-file /path/to/hook_config.json --port 8000

Available Hook Types
^^^^^^^^^^^^^^^^^^^^

- **SummarizationHook**: AI-powered summarization of long outputs
- **FileSaveHook**: Save outputs to files with metadata

For detailed hook configuration, see :doc:`hooks/index`.

Transport Configuration
^^^^^^^^^^^^^^^^^^^^^^^

Different transport protocols:

.. code-block:: bash

   # HTTP transport (default)
   tooluniverse-smcp --transport http --port 8000

   # STDIO transport (for desktop apps)
   tooluniverse-smcp --transport stdio

   # Server-Sent Events transport
   tooluniverse-smcp --transport sse --port 8000

.. _category-based-loading:

Category-Based Loading
^^^^^^^^^^^^^^^^^^^^^^

Load only specific tool categories:

.. code-block:: bash

   # Load specific categories
   tooluniverse-smcp --categories uniprot ChEMBL opentarget --port 8000

   # Load all except certain categories
   tooluniverse-smcp --exclude-categories mcp_auto_loader special_tools --port 8000

.. _tool-specific-loading:

Tool-Specific Loading
^^^^^^^^^^^^^^^^^^^^^

Load specific tools by name:

.. code-block:: bash

   # Load only specific tools
   tooluniverse-smcp --include-tools "UniProt_get_entry_by_accession" "ChEMBL_get_molecule_by_chembl_id" --port 8000

   # Load tools from a file
   tooluniverse-smcp --tools-file "/path/to/tool_names.txt" --port 8000

.. _type-based-filtering:

Type-Based Filtering
^^^^^^^^^^^^^^^^^^^^

Filter by tool types:

.. code-block:: bash

   # Include only specific tool types
   tooluniverse-smcp --include-tool-types "OpenTarget" "ToolFinderEmbedding" --port 8000

   # Exclude specific tool types
   tooluniverse-smcp --exclude-tool-types "ToolFinderLLM" "Unknown" --port 8000

.. _server-configuration:

Server Configuration
^^^^^^^^^^^^^^^^^^^^

Advanced server configuration:

.. code-block:: bash

   # Configure server parameters
   tooluniverse-smcp \
       --port 8000 \
       --host 0.0.0.0 \
       --max-workers 10 \
       --transport http \
       --verbose

.. _discovery-commands:

Discovery Commands
^^^^^^^^^^^^^^^^^^

List available categories and tools:

.. code-block:: bash

   # List all available categories
   tooluniverse-smcp --list-categories

   # List all available tools
   tooluniverse-smcp --list-tools

Custom Configuration Files
^^^^^^^^^^^^^^^^^^^^^^^^^^

Load additional tool configurations:

.. code-block:: bash

   # Load custom config files
   tooluniverse-smcp --tool-config-files "custom:/path/to/custom_tools.json" --port 8000

tooluniverse-smcp-stdio Function
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The `tooluniverse-smcp-stdio` function is specifically designed for stdio transport, making it ideal for Claude Desktop integration and other desktop AI applications. **By default, this function enables output processing hooks for intelligent post-processing of tool outputs.**

Basic Stdio Server Startup
^^^^^^^^^^^^^^^^^^^^^^^^^^

Start a stdio server with default settings (hooks enabled):

.. code-block:: bash

   # Start stdio server with default SummarizationHook enabled
   tooluniverse-smcp-stdio

   # Start with specific categories
   tooluniverse-smcp-stdio --categories uniprot ChEMBL opentarget

Hook Configuration
^^^^^^^^^^^^^^^^^^

The stdio server supports intelligent output processing hooks:

.. code-block:: bash

   # Disable hooks (default is enabled)
   tooluniverse-smcp-stdio --no-hooks

   # Use FileSaveHook instead of SummarizationHook
   tooluniverse-smcp-stdio --hook-type FileSaveHook

   # Use custom hook configuration
   tooluniverse-smcp-stdio --hook-config-file /path/to/hook_config.json

Available Hook Types
^^^^^^^^^^^^^^^^^^^^

- **SummarizationHook** (default): AI-powered summarization of long outputs
- **FileSaveHook**: Save outputs to files with metadata

For detailed hook configuration, see :doc:`hooks/index`.


️ Practical Examples
----------------------

Research Workflow Setup
~~~~~~~~~~~~~~~~~~~~~~~

Setting up for scientific research:

.. code-block:: python

   # Python approach
   from tooluniverse import ToolUniverse

   tu = ToolUniverse()

   # Load tools for drug discovery research
   tu.load_tools(tool_type=[
       "uniprot",        # Protein information
       "ChEMBL",         # Chemical data
       "opentarget",     # Target-disease associations
       "pubchem",        # Chemical compounds
       "fda_drug_adverse_event"  # Safety data
   ])

   # Ready for research queries
   result = tu.run({
       "name": "UniProt_get_entry_by_accession",
       "arguments": {"accession": "P04637"}  # p53 protein
   })

.. code-block:: bash

   # MCP server approach (run_smcp_server)
   tooluniverse-smcp \
       --categories uniprot ChEMBL opentarget pubchem fda_drug_adverse_event \
       --port 8000 \
       --name "Drug Discovery Server"

   # Or stdio server approach (run_stdio_server) with hooks enabled by default
   tooluniverse-smcp-stdio \
       --categories uniprot ChEMBL opentarget pubchem fda_drug_adverse_event \
       --name "Drug Discovery Tools"

   # Stdio server with FileSaveHook for data archiving
   tooluniverse-smcp-stdio \
       --categories uniprot ChEMBL opentarget pubchem fda_drug_adverse_event \
       --hook-type FileSaveHook \
       --name "Drug Discovery Tools with File Archiving"


️ File Formats
----------------

Tool Names File Format
~~~~~~~~~~~~~~~~~~~~~~

Create a text file with one tool name per line:

.. code-block:: text

   # my_tools.txt - Lines starting with # are comments
   OpenTargets_get_associated_targets_by_disease_efoId
   Tool_Finder_LLM
   ChEMBL_search_similar_molecules

   # You can add comments anywhere
   Tool_Finder_Keyword
