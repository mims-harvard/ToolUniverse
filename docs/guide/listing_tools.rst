Tool Listing Tutorial
===========================

ToolUniverse provides powerful methods for discovering and exploring the available tools in the system.

Overview
--------

The primary method for tool discovery is ``list_built_in_tools()``, which provides comprehensive information about all available tools. This method supports multiple modes to help you understand tools from different perspectives and access tool data in various formats.

API Reference
~~~~~~~~~~~~~

.. note::
   **For complete Python API documentation**, see :doc:`../api/modules` for commonly used classes and methods, or :doc:`../api/modules` for full API reference.

.. autofunction:: tooluniverse.execute_function.ToolUniverse.list_built_in_tools
   :noindex:

Quick Start
-----------

.. code-block:: python

   from tooluniverse import ToolUniverse

   # Initialize ToolUniverse
   tu = ToolUniverse()

   # List all tools by config categories (default)
   stats = tu.list_built_in_tools()

   # List all tools by implementation types
   type_stats = tu.list_built_in_tools(mode='type')

   # Get all tool names as a list
   tool_names = tu.list_built_in_tools(mode='list_name')

   # Get all tool specifications as a list
   tool_specs = tu.list_built_in_tools(mode='list_spec')

   # Scan all JSON files recursively (not just predefined ones)
   all_tools = tu.list_built_in_tools(mode='list_name', scan_all=True)

Available Modes
---------------

The ``list_built_in_tools()`` method supports several modes for different use cases:

List Name Mode
~~~~~~~~~~~~~~

Returns a simple list of all tool names, sorted alphabetically.

.. code-block:: python

   # Get all tool names as a list
   tool_names = tu.list_built_in_tools(mode='list_name')
   print(f"Found {len(tool_names)} tools")
   print(tool_names[:5])  # First 5 tool names

**Use cases:**
- Quick tool name lookup
- Building tool selection interfaces
- Tool name validation
- Simple tool counting

List Spec Mode
~~~~~~~~~~~~~~

Returns a list of all tool specifications (complete tool configurations).

.. code-block:: python

   # Get all tool specifications
   tool_specs = tu.list_built_in_tools(mode='list_spec')
   print(f"Found {len(tool_specs)} tool specifications")
   
   # Access tool details
   for tool in tool_specs[:3]:
       print(f"Tool: {tool['name']}, Type: {tool['type']}")

**Use cases:**
- Accessing complete tool configurations
- Tool metadata analysis
- Building tool databases
- Tool specification validation

Config Mode (Default)
~~~~~~~~~~~~~~~~~~~~~

The config mode organizes tools by their configuration file categories, representing logical groupings by functionality or data source.

.. code-block:: python

   # Default mode - organize by config file categories
   stats = tu.list_built_in_tools()
   # or explicitly:
   stats = tu.list_built_in_tools(mode='config')

**Use cases:**
- Understanding what data sources are available
- Finding tools by functional area (e.g., clinical trials, drug information, literature search)
- Getting an overview of scientific domains covered

**Example categories:**
- ``fda_drug_label`` - FDA drug labeling tools
- ``clinical_trials`` - Clinical trials data tools
- ``semantic_scholar`` - Academic literature tools
- ``opentarget`` - OpenTargets platform tools
- ``chembl`` - ChEMBL database tools

Type Mode
~~~~~~~~~

The type mode organizes tools by their implementation classes, showing the technical categorization of tools.

.. code-block:: python

   # Organize by tool types/implementation classes
   stats = tu.list_built_in_tools(mode='type')

**Use cases:**
- Understanding the technical architecture
- Finding tools by implementation pattern
- Debugging and development work
- Tool composition and workflow building

**Example types:**
- ``FDADrugLabel`` - FDA drug labeling tool implementations
- ``OpenTarget`` - OpenTargets API tool implementations
- ``ChEMBLTool`` - ChEMBL database tool implementations
- ``MCPAutoLoaderTool`` - MCP client auto-loading tools

Scan All Option
~~~~~~~~~~~~~~~

All modes support the ``scan_all`` parameter to control how tools are discovered:

.. code-block:: python

   # Use predefined tool files (default, faster)
   tools = tu.list_built_in_tools(mode='list_name', scan_all=False)

   # Scan all JSON files in data directory recursively (more comprehensive)
   all_tools = tu.list_built_in_tools(mode='list_name', scan_all=True)

**When to use scan_all=True:**
- Discovering tools not in predefined mappings
- Finding tools in custom or additional JSON files
- Comprehensive tool discovery
- Development and testing

**When to use scan_all=False (default):**
- Production environments (faster)
- Standard tool discovery
- When you only need predefined tools

Return Structure
----------------

The return structure depends on the mode:

**For 'config' and 'type' modes:** Returns a dictionary with comprehensive statistics and information:

.. code-block:: python

   {
       'categories': {
           'category_name': {
               'count': int,          # Number of tools in this category
               'tools': list          # List of tool names (only in 'type' mode)
           },
           # ... more categories
       },
       'total_categories': int,        # Total number of categories
       'total_tools': int,            # Total number of unique tools
       'mode': str,                   # The mode used ('config' or 'type')
       'summary': str                 # Human-readable summary
   }

**For 'list_name' mode:** Returns a sorted list of tool names:

.. code-block:: python

   ['ADMETAI_predict_BBB_penetrance', 'ADMETAI_predict_CYP_interactions', ...]

**For 'list_spec' mode:** Returns a list of tool specification dictionaries:

.. code-block:: python

   [
       {
           'name': 'ADMETAI_predict_BBB_penetrance',
           'type': 'ADMETAITool',
           'description': 'Predicts blood-brain barrier penetrance...',
           'parameter': {...}
       },
       ...
   ]

Accessing Tool Information
--------------------------

After getting the statistics, you can access detailed information about tools:

.. code-block:: python

   # Get statistics
   stats = tu.list_built_in_tools(mode='type')

   # Access category information
   categories = stats['categories']
   total_tools = stats['total_tools']

   # For type mode, get tools in a specific category
   if 'FDADrugLabel' in categories:
       fda_tools = categories['FDADrugLabel']['tools']
       print(f"Found {len(fda_tools)} FDA drug label tools:")
       for tool in fda_tools[:5]:  # Show first 5
           print(f"  - {tool}")

Practical Examples
------------------

Example 1: Finding Tools by Data Source
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from tooluniverse import ToolUniverse

   tu = ToolUniverse()

   # List tools by config categories to see data sources
   stats = tu.list_built_in_tools(mode='config')

   print(f"Available data sources: {len(stats['categories'])}")
   print(f"Total tools available: {stats['total_tools']}")

   # Find categories related to drug information
   drug_categories = [cat for cat in stats['categories'].keys()
                     if 'drug' in cat.lower() or 'fda' in cat.lower()]
   print(f"Drug-related categories: {drug_categories}")

Example 2: Understanding Tool Implementation Types
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # List tools by implementation type
   type_stats = tu.list_built_in_tools(mode='type')

   # Find the most common tool types
   sorted_types = sorted(type_stats['categories'].items(),
                        key=lambda x: x[1]['count'],
                        reverse=True)

   print("Top 5 tool types by count:")
   for tool_type, info in sorted_types[:5]:
       print(f"  {tool_type}: {info['count']} tools")

       # Show some example tools for this type
       if 'tools' in info:
           examples = info['tools'][:3]
           for example in examples:
               print(f"    - {example}")

Example 3: Comparing Both Modes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Compare different modes
   config_stats = tu.list_built_in_tools(mode='config')
   type_stats = tu.list_built_in_tools(mode='type')
   tool_names = tu.list_built_in_tools(mode='list_name')
   tool_specs = tu.list_built_in_tools(mode='list_spec')

   print(f"Config mode: {config_stats['total_categories']} categories")
   print(f"Type mode: {type_stats['total_categories']} types")
   print(f"Tool names: {len(tool_names)} tools")
   print(f"Tool specs: {len(tool_specs)} specifications")

   # Compare predefined vs scan_all
   predefined_tools = tu.list_built_in_tools(mode='list_name', scan_all=False)
   all_tools = tu.list_built_in_tools(mode='list_name', scan_all=True)
   
   print(f"Predefined tools: {len(predefined_tools)}")
   print(f"All tools (scan_all): {len(all_tools)}")
   print(f"Additional tools found: {len(all_tools) - len(predefined_tools)}")

   # Find which implementation types are most diverse
   for tool_type, info in type_stats['categories'].items():
       if info['count'] > 10:  # Focus on types with many tools
           print(f"{tool_type}: {info['count']} implementations")

Filtering and Selection
-----------------------

While ``list_built_in_tools()`` shows all available tools, you can filter tools using other methods:

.. autofunction:: tooluniverse.execute_function.ToolUniverse.select_tools
   :noindex:

.. autofunction:: tooluniverse.execute_function.ToolUniverse.refresh_tool_name_desc
   :noindex:

.. code-block:: python

   # Load tools first
   tu.load_tools()

   # Select tools from specific categories
   selected_tools = tu.select_tools(
       include_categories=['opentarget', 'chembl'],
       exclude_names=['tool_to_exclude']
   )

   # Get filtered tool names and descriptions
   tool_names, tool_descs = tu.refresh_tool_name_desc(
       include_categories=['fda_drug_label'],
       exclude_categories=['deprecated_tools']
   )

Working Without Loading Tools
-----------------------------

One key advantage of ``list_built_in_tools()`` is that it works **before** calling ``load_tools()``:

.. code-block:: python

   # You can explore available tools immediately after initialization
   tu = ToolUniverse()
   
   # All these work without loading tools first
   tool_names = tu.list_built_in_tools(mode='list_name')
   tool_specs = tu.list_built_in_tools(mode='list_spec')
   stats = tu.list_built_in_tools(mode='config')
   
   # Only then load tools if needed
   tu.load_tools()

