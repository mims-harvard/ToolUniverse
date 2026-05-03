FileSaveHook
============

**File-based output processing and archiving**

The FileSaveHook saves tool outputs to temporary files and returns file information instead of the original output. This is ideal for handling large outputs or when you need to process outputs as files.

Overview
--------

**What it does:**
- Saves tool outputs to temporary files
- Analyzes data format and structure automatically
- Returns file metadata (path, size, format, structure)
- Supports automatic cleanup of old files

**When to use:**
- Very large outputs that exceed memory limits
- Processing outputs as files for external tools
- Archiving tool outputs for later analysis
- Reducing memory usage in long-running processes

Quick Start
-----------

**Simple Usage**

.. code-block:: python

   from tooluniverse import ToolUniverse

   # Enable FileSaveHook
   tu = ToolUniverse(hooks_enabled=True, hook_type='FileSaveHook')
   tu.load_tools(['uniprot'])

   result = tu.run({
       "name": "UniProt_get_entry_by_accession",
       "arguments": {"accession": "P05067"}
   })

   # Result contains file information
   print(f"File path: {result['file_path']}")
   print(f"Data format: {result['data_format']}")
   print(f"File size: {result['file_size']} bytes")

**Advanced Configuration**

.. code-block:: python

   hook_config = {
       "hooks": [{
           "name": "file_save_hook",
           "type": "FileSaveHook",
           "enabled": True,
           "conditions": {
               "output_length": {
                   "operator": ">",
                   "threshold": 1000
               }
           },
           "hook_config": {
               "temp_dir": "/tmp/my_outputs",
               "file_prefix": "my_tool_output",
               "include_metadata": True,
               "auto_cleanup": True,
               "cleanup_age_hours": 12
           }
       }]
   }

   tu = ToolUniverse(hooks_enabled=True, hook_config=hook_config)

Configuration Options
---------------------

**Temp Directory**
- Directory where files are saved
- Default: System temporary directory
- Use absolute paths for custom locations

**File Prefix**
- Prefix for generated filenames
- Default: "tool_output"
- Helps organize files by purpose

**Include Metadata**
- Whether to include file metadata in response
- Default: True
- Provides file information and context

**Auto Cleanup**
- Automatically remove old files
- Default: False
- Helps manage disk space

**Cleanup Age Hours**
- Age threshold for automatic cleanup
- Default: 24 hours
- Files older than this are removed

Data Format Detection
---------------------

The hook automatically detects and handles different data types:

**JSON Data**
- Dictionaries, lists, JSON strings
- Saved as `.json` files
- Structure: "dict with X keys", "list with X items"

**Text Data**
- Plain text, strings
- Saved as `.txt` files
- Structure: "text", "string"

**Binary Data**
- Non-text data
- Saved as `.bin` files
- Structure: "binary", "data"

**Other Formats**
- Custom data types
- Saved with appropriate extensions
- Structure: "custom", "unknown"

Examples
--------

**Large Dataset Processing**

.. code-block:: python

   # Process large protein database entries
   tu = ToolUniverse(hooks_enabled=True, hook_type='FileSaveHook')
   tu.load_tools(['uniprot'])

   result = tu.run({
       "name": "UniProt_get_entry_by_accession",
       "arguments": {"accession": "P05067"}
   })

   # File information for external processing
   print(f"Dataset saved to: {result['file_path']}")
   print(f"Format: {result['data_format']}")
   print(f"Size: {result['file_size']} bytes")

   # Process with external tools
   import subprocess
   external_result = subprocess.run([
       'external_analysis_tool', '--input', result['file_path']
   ], capture_output=True, text=True)

**Custom Directory and Cleanup**

.. code-block:: python

   # Configure custom directory with auto-cleanup
   hook_config = {
       "hooks": [{
           "name": "file_save_hook",
           "type": "FileSaveHook",
           "enabled": True,
           "hook_config": {
               "temp_dir": "/tmp/research_outputs",
               "file_prefix": "research_data",
               "auto_cleanup": True,
               "cleanup_age_hours": 6
           }
       }]
   }

   tu = ToolUniverse(hooks_enabled=True, hook_config=hook_config)

   # Files will be saved to /tmp/research_outputs/
   # and automatically cleaned up after 6 hours

**External Tool Integration**

.. code-block:: python

   # Save output and process with external tool
   tu = ToolUniverse(hooks_enabled=True, hook_type='FileSaveHook')
   tu.load_tools(['europepmc'])

   result = tu.run({
       "name": "EuropePMC_search_publications",
       "arguments": {"query": "machine learning drug discovery"}
   })

   # Process with external analysis tool
   import subprocess
   external_output = subprocess.run([
       'your_external_tool', '--input', result['file_path']
   ], capture_output=True, text=True)

Troubleshooting
---------------

**File Permission Errors**
- Ensure directory exists and is writable
- Check file permissions and ownership
- Use absolute paths for temp directories

**Memory Issues**
- Use FileSaveHook for large outputs
- Enable auto-cleanup for temporary files
- Monitor disk space usage

**Hook Not Triggering**
- Check trigger conditions and thresholds
- Verify hook configuration and enabled status
- Review hook priority settings

**Performance Problems**
- Use tool-specific hooks instead of global hooks
- Set appropriate thresholds to avoid unnecessary processing
- Monitor hook execution times

**Debugging**

Enable detailed logging for hook operations:

.. code-block:: python

   import logging
   logging.basicConfig(level=logging.DEBUG)

   # Hook operations will be logged in detail
   tu = ToolUniverse(hooks_enabled=True, hook_config=config)

**Validation**

Verify hook configuration:

.. code-block:: python

   # Check hook configuration
   hook_manager = tu.hook_manager
   for hook in hook_manager.hooks:
       print(f"Hook: {hook.name}")
       print(f"Enabled: {hook.enabled}")
       print(f"Type: {hook.config.get('type')}")
       print(f"Conditions: {hook.config.get('conditions')}")

Next Steps
----------

.. seealso::

   - :doc:`summarization_hook` - AI-powered output summarization
   - :doc:`hook_configuration` - Advanced configuration options
   - :doc:`index` - Complete hooks system overview
   - :doc:`../tool_composition` - Chain tools into workflows
