Server and Stdio Hook Integration
=================================

**Complete Tutorial to using hooks with ToolUniverse servers and stdio interfaces**

Overview
--------

ToolUniverse provides intelligent output processing hooks that can automatically handle large tool outputs through:

- **SummarizationHook**: AI-powered summarization of long outputs
- **FileSaveHook**: File-based archiving with metadata
- **Custom Hooks**: User-defined processing logic

These hooks are available in both server and stdio modes with different default behaviors.

Server Mode (HTTP/SSE)
-----------------------

The server mode provides HTTP and SSE transport with configurable hook support.

Basic Usage
^^^^^^^^^^^^

Start a server with hooks enabled:

.. code-block:: bash

   # Enable hooks with default SummarizationHook
   tooluniverse-smcp-server --hooks-enabled --port 8000

   # Use specific hook type
   tooluniverse-smcp-server --hook-type SummarizationHook --port 8000
   tooluniverse-smcp-server --hook-type FileSaveHook --port 8000

   # Use custom hook configuration
   tooluniverse-smcp-server --hook-config-file hook_config.json --port 8000

Available Parameters
^^^^^^^^^^^^^^^^^^^^

- ``--hooks-enabled``: Enable output processing hooks (default: False)
- ``--hook-type``: Choose hook type (SummarizationHook, FileSaveHook)
- ``--hook-config-file``: Path to custom hook configuration JSON file

Example Configurations
^^^^^^^^^^^^^^^^^^^^^^

**SummarizationHook Configuration:**

.. code-block:: json

   {
     "hooks": [
       {
         "name": "summarization_hook",
         "type": "SummarizationHook",
         "enabled": true,
         "conditions": {
           "output_length": {
             "operator": ">",
             "threshold": 5000
           }
         },
         "hook_config": {
           "chunk_size": 30000,
           "focus_areas": "key_findings_and_results",
           "max_summary_length": 3000
         }
       }
     ]
   }

**FileSaveHook Configuration:**

.. code-block:: json

   {
     "hooks": [
       {
         "name": "file_save_hook",
         "type": "FileSaveHook",
         "enabled": true,
         "conditions": {
           "output_length": {
             "operator": ">",
             "threshold": 1000
           }
         },
         "hook_config": {
           "temp_dir": "/tmp/tooluniverse_outputs",
           "file_prefix": "tool_output",
           "include_metadata": true,
           "auto_cleanup": true,
           "cleanup_age_hours": 24
         }
       }
     ]
   }

Stdio Mode (Desktop AI)
------------------------

The stdio mode is designed for desktop AI applications like Claude Desktop, with hooks enabled by default.

Default Behavior
^^^^^^^^^^^^^^^^^

Stdio mode enables SummarizationHook by default:

.. code-block:: bash

   # Default: hooks enabled with SummarizationHook
   tooluniverse-smcp-stdio

   # Equivalent to:
   tooluniverse-smcp-stdio --hook-type SummarizationHook

Hook Control
^^^^^^^^^^^^

Disable or modify hook behavior:

.. code-block:: bash

   # Disable hooks completely
   tooluniverse-smcp-stdio --no-hooks

   # Use FileSaveHook instead
   tooluniverse-smcp-stdio --hook-type FileSaveHook

   # Use custom configuration
   tooluniverse-smcp-stdio --hook-config-file hook_config.json

Available Parameters
^^^^^^^^^^^^^^^^^^^^

- ``--no-hooks``: Disable output processing hooks (default: enabled)
- ``--hook-type``: Choose hook type (SummarizationHook, FileSaveHook)
- ``--hook-config-file``: Path to custom hook configuration JSON file

Python API Integration
----------------------

Use hooks programmatically with the SMCP class:

Basic Usage
^^^^^^^^^^^

.. code-block:: python

   from tooluniverse import SMCP

   # Enable hooks with default SummarizationHook
   server = SMCP(
       name="My Server",
       hooks_enabled=True
   )

   # Use specific hook type
   server = SMCP(
       name="My Server",
       hooks_enabled=True,
       hook_type="SummarizationHook"
   )

   # Use FileSaveHook
   server = SMCP(
       name="My Server",
       hooks_enabled=True,
       hook_type="FileSaveHook"
   )

Advanced Configuration
^^^^^^^^^^^^^^^^^^^^^^

Use custom hook configurations:

.. code-block:: python

   import json

   # Load custom configuration
   with open('hook_config.json', 'r') as f:
       hook_config = json.load(f)

   server = SMCP(
       name="My Server",
       hooks_enabled=True,
       hook_config=hook_config
   )

   # Or define inline
   hook_config = {
       "hooks": [
           {
               "name": "custom_hook",
               "type": "SummarizationHook",
               "enabled": True,
               "conditions": {
                   "output_length": {
                       "operator": ">",
                       "threshold": 3000
                   }
               },
               "hook_config": {
                   "chunk_size": 2000,
                   "focus_areas": "key_findings_and_results",
                   "max_summary_length": 2000
               }
           }
       ]
   }

   server = SMCP(
       name="My Server",
       hooks_enabled=True,
       hook_config=hook_config
   )

Configuration Precedence
------------------------

When multiple configuration methods are used, the following precedence applies:

1. **hook_config** (highest priority)
2. **hook_type**
3. **hooks_enabled** (lowest priority)

Example:

.. code-block:: python

   # hook_config takes precedence over hook_type
   server = SMCP(
       name="My Server",
       hooks_enabled=True,
       hook_type="SummarizationHook",  # Ignored
       hook_config=custom_config       # Used
   )

Best Practices
---------------

Server Mode
^^^^^^^^^^^

- Use ``--hooks-enabled`` for production servers
- Choose appropriate hook types based on use case
- Use custom configurations for complex requirements
- Monitor hook performance and adjust thresholds

Stdio Mode
^^^^^^^^^^

- Leverage default hook behavior for desktop AI
- Use ``--no-hooks`` only when hooks cause issues
- Consider FileSaveHook for data archiving needs
- Test hook configurations before deployment

Performance Considerations
^^^^^^^^^^^^^^^^^^^^^^^^^^

- **SummarizationHook**: Adds processing time but reduces output size
- **FileSaveHook**: Minimal processing overhead, good for archiving
- **Thresholds**: Set appropriate output length thresholds
- **Chunk Size**: Balance processing efficiency and context preservation

Troubleshooting
---------------

Common Issues
^^^^^^^^^^^^^^

**Hooks Not Triggering:**

- Check output length thresholds
- Verify hook configuration syntax
- Ensure hooks are enabled

**Performance Issues:**

- Adjust chunk sizes
- Increase thresholds
- Use tool-specific configurations

**Configuration Errors:**

- Validate JSON syntax
- Check parameter names
- Verify hook types

Debug Mode
^^^^^^^^^^

Enable verbose logging for troubleshooting:

.. code-block:: bash

   # Server mode
   tooluniverse-smcp-server --hooks-enabled --verbose --port 8000

   # Stdio mode
   tooluniverse-smcp-stdio --hook-type SummarizationHook --verbose

.. seealso::

   - :doc:`index` - Complete hooks system overview
   - :doc:`summarization_hook` - SummarizationHook details
   - :doc:`file_save_hook` - FileSaveHook details
   - :doc:`hook_configuration` - Advanced configuration
