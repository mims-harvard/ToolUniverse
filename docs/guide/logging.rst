Logging Tutorial
=============

**Configure and use ToolUniverse's comprehensive logging system**

ToolUniverse provides a robust logging system to help you monitor tool execution, debug issues, and track research workflows.

 Logging Overview
-------------------

ToolUniverse uses Python's standard logging module with enhanced formatting and emoji indicators. The logging system provides:

* **5 Standard Log Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
* **1 Custom Level**: PROGRESS (for workflow tracking)
* **Emoji Indicators**: Visual cues for different message types
* **Flexible Configuration**: Environment variables, programmatic setup, and per-instance control

 Log Levels Explained
-----------------------

Understanding when to use each log level:

DEBUG Level
~~~~~~~~~~~

**When to use**: Detailed diagnostic information for troubleshooting

* Tool loading details
* API request/response data
* Internal state changes
* Parameter validation steps

.. code-block:: python

   from tooluniverse import ToolUniverse
   from tooluniverse.logging_config import setup_logging

   # Enable DEBUG logging
   setup_logging('DEBUG')

   tu = ToolUniverse()
   tu.load_tools()  # Will show detailed tool loading information

**Example output**:

.. code-block:: text

   🔍 DEBUG: Tool files:
   🔍 DEBUG: {
     "opentargets": "/path/to/opentarget_tools.json",
     "pubchem": "/path/to/pubchem_tools.json"
   }

INFO Level (Default)
~~~~~~~~~~~~~~~~~~~~

**When to use**: General information about normal operations

* Tool registration confirmations
* Workflow progress updates
* Configuration changes
* Successful operations

.. code-block:: python

   # INFO is the default level
   tu = ToolUniverse()
   tu.register_custom_tool(MyCustomTool, "my_tool")
   # Output: ℹ️ INFO: Custom tool 'my_tool' registered successfully!

**Example output**:

.. code-block:: text

   ℹ️ INFO: Loading 245 tools from 12 categories
   ℹ️ INFO: Custom tool 'protein_analyzer' registered successfully!

PROGRESS Level (Custom)
~~~~~~~~~~~~~~~~~~~~~~~

**When to use**: Track progress of long-running workflows

* Multi-step research pipelines
* Batch processing operations
* Data collection workflows

.. code-block:: python

   from tooluniverse.logging_config import get_logger

   logger = get_logger('workflow')

   def drug_discovery_pipeline(compounds):
       logger.progress(f"Starting analysis of {len(compounds)} compounds")

       for i, compound in enumerate(compounds):
           logger.progress(f"Processing compound {i+1}/{len(compounds)}: {compound}")
           # ... processing logic ...

       logger.progress("Drug discovery pipeline completed")

**Example output**:

.. code-block:: text

   📈 PROGRESS: Starting analysis of 150 compounds
   📈 PROGRESS: Processing compound 1/150: aspirin
   📈 PROGRESS: Processing compound 2/150: ibuprofen

WARNING Level
~~~~~~~~~~~~~

**When to use**: Something unexpected happened but execution continues

* API rate limiting
* Deprecated tool usage
* Missing optional parameters
* Fallback operations

.. code-block:: python

   # Warnings appear automatically when issues occur
   result = tu.run({
       "name": "NonExistentTool",  # This will trigger a warning
       "arguments": {"query": "test"}
   })

**Example output**:

.. code-block:: text

   ⚠️ WARNING: Tool 'NonExistentTool' not found, similar tools: ['ExistingTool1', 'ExistingTool2']

ERROR Level
~~~~~~~~~~~

**When to use**: Serious problems that prevent specific operations

* Tool execution failures
* API authentication errors
* Invalid parameters
* Network timeouts

**Example output**:

.. code-block:: text

   ❌ ERROR: Failed to execute tool 'PubChem_search': Invalid API key
   ❌ ERROR: OpenTargets query timeout after 30 seconds

CRITICAL Level
~~~~~~~~~~~~~~

**When to use**: Very serious errors that might stop the program

* System-level failures
* Configuration corruption
* Resource exhaustion

**Example output**:

.. code-block:: text

   🚨 CRITICAL: Failed to initialize ToolUniverse: Configuration file corrupted

️ Configuration Methods
------------------------

Method 1: Environment Variable (Recommended)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Set the log level before starting your application:

.. code-block:: bash

   # Linux/macOS
   export TOOLUNIVERSE_LOG_LEVEL=DEBUG
   python your_script.py

   # Windows Command Prompt
   set TOOLUNIVERSE_LOG_LEVEL=DEBUG
   python your_script.py

   # Windows PowerShell
   $env:TOOLUNIVERSE_LOG_LEVEL="DEBUG"
   python your_script.py

.. code-block:: python

   # Your script will automatically use the environment setting
   from tooluniverse import ToolUniverse

   tu = ToolUniverse()  # Uses DEBUG level from environment

.. _tooluniverse-logging-configuration:

Method 2: Global Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Set logging level programmatically for all ToolUniverse operations:

.. code-block:: python

   from tooluniverse.logging_config import setup_logging
   from tooluniverse import ToolUniverse

   # Configure logging before creating ToolUniverse instances
   setup_logging('WARNING')  # Only show warnings and errors

   tu = ToolUniverse()
   tu.load_tools()  # Will use WARNING level

Method 3: Per-Instance Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Set different log levels for different ToolUniverse instances:

.. code-block:: python

   from tooluniverse import ToolUniverse

   # Create instances with different log levels
   debug_tu = ToolUniverse(log_level='DEBUG')    # Detailed logging
   quiet_tu = ToolUniverse(log_level='ERROR')    # Only errors

   # Default instance uses global/environment setting
   default_tu = ToolUniverse()

Method 4: Dynamic Level Changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Change log level during execution:

.. code-block:: python

   from tooluniverse.logging_config import set_log_level
   from tooluniverse import ToolUniverse

   tu = ToolUniverse()

   # Start with minimal logging
   set_log_level('ERROR')
   tu.load_tools()  # Quiet loading

   # Enable verbose logging for debugging
   set_log_level('DEBUG')
   result = tu.run({"name": "PubChem_search", "arguments": {"query": "aspirin"}})

   # Return to normal logging
   set_log_level('INFO')

️ Custom Logging in Your Code
-------------------------------

Using ToolUniverse Logger in Your Scripts
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from tooluniverse.logging_config import get_logger

   # Get a logger for your module
   logger = get_logger('my_research_script')

   def analyze_compounds(compound_list):
       logger.info(f"Starting analysis of {len(compound_list)} compounds")

       results = []
       for i, compound in enumerate(compound_list):
           logger.debug(f"Processing {compound}")

           try:
               # Your analysis logic here
               result = perform_analysis(compound)
               results.append(result)
               logger.progress(f"Completed {i+1}/{len(compound_list)} compounds")

           except Exception as e:
               logger.error(f"Failed to analyze {compound}: {e}")
               continue

       logger.info(f"Analysis completed. {len(results)} successful results")
       return results

Convenience Functions
~~~~~~~~~~~~~~~~~~~~~

ToolUniverse provides convenience functions for quick logging:

.. code-block:: python

   from tooluniverse.logging_config import debug, info, warning, error, critical, progress

   # Quick logging without creating logger instances
   info("Starting research workflow")
   debug("Loading configuration from file")
   progress("Processing 25% complete")
   warning("API rate limit approaching")
   error("Tool execution failed")
   critical("System resources exhausted")

 Common Logging Patterns
--------------------------

Research Workflow Logging
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from tooluniverse import ToolUniverse
   from tooluniverse.logging_config import get_logger, setup_logging

   # Setup logging for research workflow
   setup_logging('INFO')
   logger = get_logger('drug_discovery')

   def drug_discovery_workflow(target_disease):
       logger.info(f"🎯 Starting drug discovery for: {target_disease}")

       tu = ToolUniverse()
       tu.load_tools()

       # Step 1: Find disease targets
       logger.progress("Step 1: Identifying disease targets")
       targets_query = {
           "name": "OpenTargets_get_associated_targets_by_disease_name",
           "arguments": {"diseaseName": target_disease, "limit": 10}
       }

       try:
           targets = tu.run(targets_query)
           logger.info(f"✅ Found {len(targets.get('data', []))} targets")
       except Exception as e:
           logger.error(f"❌ Target identification failed: {e}")
           return None

       # Step 2: Find compounds
       logger.progress("Step 2: Searching for compounds")
       # ... more workflow steps ...

       logger.info("🎉 Drug discovery workflow completed successfully")
       return results

Debugging Failed Tools
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from tooluniverse import ToolUniverse
   from tooluniverse.logging_config import setup_logging

   # Enable debug logging to diagnose tool issues
   setup_logging('DEBUG')

   tu = ToolUniverse()
   tu.load_tools()

   # Debug a failing query
   problematic_query = {
       "name": "PubChem_get_compound_info",
       "arguments": {"compound_name": "invalid_compound_name"}
   }

   try:
       result = tu.run(problematic_query)
   except Exception as e:
       # Debug logs will show detailed error information
       print(f"Query failed: {e}")

Batch Processing with Progress Tracking
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from tooluniverse import ToolUniverse
   from tooluniverse.logging_config import get_logger

   logger = get_logger('batch_processor')
   tu = ToolUniverse()
   tu.load_tools()

   def process_compound_batch(compounds):
       logger.info(f"🚀 Starting batch processing of {len(compounds)} compounds")

       results = []
       errors = []

       for i, compound in enumerate(compounds):
           logger.progress(f"Processing {i+1}/{len(compounds)}: {compound}")

           query = {
               "name": "PubChem_get_compound_info",
               "arguments": {"compound_name": compound}
           }

           try:
               result = tu.run(query)
               results.append(result)
               logger.debug(f"✅ Successfully processed {compound}")
           except Exception as e:
               errors.append((compound, str(e)))
               logger.warning(f"⚠️ Failed to process {compound}: {e}")

       logger.info(f"📊 Batch complete: {len(results)} successful, {len(errors)} failed")
       return results, errors

 Best Practices
-----------------

Choose Appropriate Log Levels
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* **Production**: Use INFO or WARNING to reduce noise
* **Development**: Use DEBUG for detailed diagnostics
* **CI/CD**: Use ERROR to only show failures
* **Demonstrations**: Use PROGRESS to show workflow steps

.. code-block:: python

   import os
   from tooluniverse.logging_config import setup_logging

   # Environment-based logging configuration
   if os.getenv('ENVIRONMENT') == 'production':
       setup_logging('WARNING')
   elif os.getenv('ENVIRONMENT') == 'development':
       setup_logging('DEBUG')
   else:
       setup_logging('INFO')  # Default

Structure Your Log Messages
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use consistent formatting for better readability:

.. code-block:: python

   logger = get_logger('workflow')

   # Good: Clear, actionable messages
   logger.info("🎯 Starting protein analysis workflow")
   logger.progress("Step 1/5: Loading protein sequences")
   logger.error("❌ PubChem API returned 404 for compound 'xyz123'")

   # Avoid: Vague or uninformative messages
   logger.info("Processing")  # Too vague
   logger.debug("Data: " + str(huge_dict))  # Too much data

Log Important Context
~~~~~~~~~~~~~~~~~~~~~

Include relevant details for debugging:

.. code-block:: python

   logger = get_logger('tool_executor')

   def execute_tool_safely(tool_name, arguments):
       logger.debug(f"Executing tool: {tool_name}")
       logger.debug(f"Arguments: {arguments}")

       try:
           result = tu.run({"name": tool_name, "arguments": arguments})
           logger.info(f"✅ Tool '{tool_name}' completed successfully")
           return result
       except Exception as e:
           logger.error(f"❌ Tool '{tool_name}' failed: {e}")
           logger.debug(f"Full traceback:", exc_info=True)  # Include stack trace in debug
           raise

 Troubleshooting Logging
--------------------------

Common Issues and Solutions
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Issue**: No log messages appearing

.. code-block:: python

   # Solution: Check if logging is configured
   from tooluniverse.logging_config import setup_logging
   setup_logging('DEBUG')  # Ensure logging is enabled

**Issue**: Too many log messages

.. code-block:: python

   # Solution: Increase log level to reduce verbosity
   from tooluniverse.logging_config import set_log_level
   set_log_level('WARNING')  # Only warnings and errors

**Issue**: Log messages not showing emoji

.. code-block:: python

   # This is normal in some terminals. The logging still works,
   # just without emoji indicators. No action needed.

**Issue**: Want to disable all logging

.. code-block:: python

   # Solution: Set to CRITICAL level
   from tooluniverse.logging_config import setup_logging
   setup_logging('CRITICAL')

Check Current Log Level
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from tooluniverse.logging_config import get_logger

   logger = get_logger()
   current_level = logger.getEffectiveLevel()
   print(f"Current log level: {current_level}")

   # Level numbers: DEBUG=10, INFO=20, PROGRESS=25, WARNING=30, ERROR=40, CRITICAL=50

 Log Output Examples
---------------------

Here's what different log levels look like in practice:

.. code-block:: text

   🔍 DEBUG: Tool files loaded from: /path/to/tools/
   🔍 DEBUG: Validating parameters for PubChem_search
   ℹ️ INFO: Loading 245 tools from 12 categories
   📈 PROGRESS: Processing compound 15/100: caffeine
   ⚠️ WARNING: API rate limit reached, waiting 2 seconds
   ❌ ERROR: OpenTargets query failed: Connection timeout
   🚨 CRITICAL: Failed to initialize tool registry

 Next Steps
-------------

Now that you understand ToolUniverse logging:

* ** Workflows** → :doc:`scientific_workflows` - Apply logging to scientific workflows
* ** Extend Tools** → :doc:`../expand_tooluniverse/index` - Add logging to custom tools
* ** Troubleshooting** → :doc:`../help/troubleshooting` - Debug common logging issues

.. tip::
   **Pro tip**: Start with INFO level for normal use, switch to DEBUG when investigating issues, and use PROGRESS for long-running workflows to track execution progress!
