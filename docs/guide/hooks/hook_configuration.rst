Hook Configuration
==================

**Advanced configuration and customization for hooks**

Configuration Approaches
------------------------

**Simple Configuration (Recommended)**

Use `hook_type` for easy selection:

.. code-block:: python

   from tooluniverse import ToolUniverse

   # Enable default SummarizationHook
   tu = ToolUniverse(hooks_enabled=True)

   # Choose specific hook type
   tu = ToolUniverse(hooks_enabled=True, hook_type='FileSaveHook')

   # Use multiple hooks
   tu = ToolUniverse(hooks_enabled=True, hook_type=['SummarizationHook', 'FileSaveHook'])

**Advanced Configuration**

Use `hook_config` for detailed control:

.. code-block:: python

   hook_config = {
       "hooks": [{
           "name": "my_hook",
           "type": "SummarizationHook",
           "enabled": True,
           "conditions": {"output_length": {"operator": ">", "threshold": 5000}},
           "hook_config": {
               "chunk_size": 30000,
               "focus_areas": "key_findings_and_results"
           }
       }]
   }

   tu = ToolUniverse(hooks_enabled=True, hook_config=hook_config)

**Configuration Precedence**

When both `hook_type` and `hook_config` are provided, `hook_config` takes precedence.

Excluding Tools from Hook Processing
-------------------------------------

**exclude_tools Configuration**

Use `exclude_tools` to prevent specific tools from being processed by hooks. This is useful for excluding tool discovery tools (like Tool_RAG) and other special tools that shouldn't be summarized.

**Default Excluded Tools**

The default configuration excludes these tools:

- `Tool_RAG` - Embedding-based tool finder
- `ToolFinderEmbedding` - Tool discovery tool
- `ToolFinderLLM` - LLM-based tool finder
- `ToolOutputSummarizer` - Hook tool (always excluded)
- `OutputSummarizationComposer` - Hook tool (always excluded)

**Custom Exclude Tools**

.. code-block:: json

   {
     "exclude_tools": [
       "Tool_RAG",
       "ToolFinderEmbedding",
       "MyCustomTool",
       "SpecialTool_*"
     ],
     "hooks": [...]
   }

**Wildcard Patterns**

You can use wildcard patterns to exclude multiple tools:

.. code-block:: json

   {
     "exclude_tools": [
       "Tool_*",      # Excludes all tools starting with "Tool_"
       "Finder*",     # Excludes all tools starting with "Finder"
       "CustomTool_*" # Excludes all tools starting with "CustomTool_"
     ]
   }

**Python Configuration**

.. code-block:: python

   hook_config = {
       "exclude_tools": [
           "Tool_RAG",
           "ToolFinderEmbedding",
           "CustomTool_*"  # Wildcard pattern
       ],
       "hooks": [{
           "name": "summarization_hook",
           "type": "SummarizationHook",
           "enabled": True
       }]
   }

   tu = ToolUniverse(hooks_enabled=True, hook_config=hook_config)

**Why Exclude Tools?**

- **Prevent Recursive Processing**: Hook tools themselves are excluded to avoid infinite loops
- **Performance**: Skip unnecessary processing for tool discovery tools
- **Correctness**: Some tools produce outputs that shouldn't be summarized (e.g., tool lists)

Configuration Structure
-----------------------

**Global Settings**

.. code-block:: json

   {
     "global_settings": {
       "default_timeout": 30,
       "max_hook_depth": 3,
       "enable_hook_caching": true,
       "hook_execution_order": "priority_desc"
     },
     "exclude_tools": [
       "Tool_RAG",
       "ToolFinderEmbedding",
       "ToolFinderLLM"
     ]
   }

**Hook Type Defaults**

.. code-block:: json

   {
     "hook_type_defaults": {
       "SummarizationHook": {
         "default_output_length_threshold": 5000,
         "default_chunk_size": 30000,
         "default_focus_areas": "key_findings_and_results",
         "default_max_summary_length": 3000
       },
       "FileSaveHook": {
         "default_temp_dir": null,
         "default_file_prefix": "tool_output",
         "default_include_metadata": true,
         "default_auto_cleanup": false,
         "default_cleanup_age_hours": 24
       }
     }
   }

**Individual Hook Configuration**

.. code-block:: json

   {
     "hooks": [
       {
         "name": "summarization_hook",
         "type": "SummarizationHook",
         "enabled": true,
         "priority": 1,
         "conditions": {
           "output_length": {
             "operator": ">",
             "threshold": 5000
           }
         },
         "hook_config": {
           "chunk_size": 32000,
           "focus_areas": "key_findings_and_results",
           "max_summary_length": 3000
         }
       }
     ]
   }

Configuration Levels
--------------------

**Global Hooks**

Apply to all tools:

.. code-block:: json

   {
     "hooks": [
       {
         "name": "global_summarization",
         "type": "SummarizationHook",
         "enabled": true,
         "conditions": {
           "output_length": {"operator": ">", "threshold": 10000}
         }
       }
     ]
   }

**Tool-Specific Hooks**

Apply to specific tools:

.. code-block:: json

   {
     "tool_specific_hooks": {
       "UniProt_get_entry_by_accession": {
         "enabled": true,
         "hooks": [
           {
             "name": "protein_summarization",
             "type": "SummarizationHook",
             "enabled": true,
             "conditions": {
               "output_length": {"operator": ">", "threshold": 8000}
             },
             "hook_config": {
               "focus_areas": "protein_function_and_structure",
               "max_summary_length": 3500
             }
           }
         ]
       }
     }
   }

**Category-Specific Hooks**

Apply to tool categories:

.. code-block:: json

   {
     "category_hooks": {
       "uniprot": {
         "enabled": true,
         "hooks": [
           {
             "name": "protein_file_save",
             "type": "FileSaveHook",
             "enabled": true,
             "conditions": {
               "output_length": {"operator": ">", "threshold": 5000}
             },
             "hook_config": {
               "file_prefix": "protein_data",
               "auto_cleanup": true
             }
           }
         ]
       }
     }
   }

Condition Types
---------------

**Output Length Conditions**

.. code-block:: json

   {
     "conditions": {
       "output_length": {
         "operator": ">",
         "threshold": 5000
       }
     }
   }

**Available Operators:**
- `>`: Greater than
- `>=`: Greater than or equal
- `<`: Less than
- `<=`: Less than or equal
- `==`: Equal to
- `!=`: Not equal to

**Tool Name Conditions**

.. code-block:: json

   {
     "conditions": {
       "tool_name": {
         "operator": "==",
         "value": "UniProt_get_entry_by_accession"
       }
     }
   }

**Multiple Conditions**

.. code-block:: json

   {
     "conditions": {
       "output_length": {
         "operator": ">",
         "threshold": 5000
       },
       "tool_name": {
         "operator": "!=",
         "value": "ToolOutputSummarizer"
       }
     }
   }

Performance Optimization
------------------------

**Tool-Specific Configuration**

Use tool-specific hooks for better performance:

.. code-block:: json

   {
     "tool_specific_hooks": {
       "UniProt_get_entry_by_accession": {
         "enabled": true,
         "hooks": [
           {
             "name": "protein_hook",
             "type": "SummarizationHook",
             "enabled": true,
             "conditions": {
               "output_length": {"operator": ">", "threshold": 8000}
             }
           }
         ]
       }
     }
   }

**Appropriate Thresholds**

Set thresholds to avoid unnecessary processing:

.. code-block:: json

   {
     "conditions": {
       "output_length": {
         "operator": ">",
         "threshold": 10000
       }
     }
   }

**Caching Configuration**

Enable caching for better performance:

.. code-block:: json

   {
     "global_settings": {
       "enable_hook_caching": true
     }
   }

**Excluding Tools**

Exclude tool discovery and special tools:

.. code-block:: json

   {
     "exclude_tools": [
       "Tool_RAG",
       "ToolFinderEmbedding",
       "ToolFinderLLM"
     ]
   }

This prevents unnecessary processing and avoids recursive hook calls.

**Auto-Cleanup**

Enable auto-cleanup for file-based hooks:

.. code-block:: json

   {
     "hook_config": {
       "auto_cleanup": true,
       "cleanup_age_hours": 12
     }
   }

Best Practices
---------------

**Configuration Management**

1. **Start Simple**: Use `hook_type` for basic needs
2. **Gradual Complexity**: Add `hook_config` for specific requirements
3. **Test Incrementally**: Test each configuration change
4. **Document Settings**: Keep track of custom configurations

**Performance Tips**

1. **Use Tool-Specific Hooks**: More efficient than global hooks
2. **Set Appropriate Thresholds**: Avoid unnecessary processing
3. **Enable Caching**: Reduce redundant operations
4. **Monitor Resource Usage**: Track memory and disk usage
5. **Exclude Unnecessary Tools**: Use `exclude_tools` to skip tool discovery tools

**Error Handling**

1. **Validate Configurations**: Check JSON syntax and structure
2. **Handle Missing Tools**: Ensure required tools are available
3. **Graceful Degradation**: Provide fallback options
4. **Logging**: Enable detailed logging for debugging

**Security Considerations**

1. **File Permissions**: Ensure proper file access controls
2. **Temporary Files**: Use secure temporary directories
3. **Data Privacy**: Consider sensitive data handling
4. **Cleanup**: Regular cleanup of temporary files

Troubleshooting
---------------

**Configuration Validation**

.. code-block:: python

   # Validate hook configuration
   import json

   try:
       with open('hook_config.json', 'r') as f:
           config = json.load(f)
       print("Configuration is valid JSON")
   except (FileNotFoundError, json.JSONDecodeError) as e:
       print(f"Error: {e}")

**Debug Configuration**

.. code-block:: python

   # Check hook configuration
   hook_manager = tu.hook_manager
   for hook in hook_manager.hooks:
       print(f"Hook: {hook.name}")
       print(f"Enabled: {hook.enabled}")
       print(f"Type: {hook.config.get('type')}")
       print(f"Conditions: {hook.config.get('conditions')}")

**Common Issues**

**Hook Not Triggering**
- Check threshold settings
- Verify hook is enabled
- Confirm tool name matching
- Review condition parameters
- Check if tool is in `exclude_tools` list (excluded tools won't trigger hooks)

**Performance Problems**
- Use tool-specific hooks
- Set appropriate thresholds
- Enable caching
- Monitor resource usage

**File Permission Errors**
- Check directory permissions
- Use absolute paths
- Verify file access rights

Next Steps
----------

.. seealso::

   - :doc:`summarization_hook` - AI-powered output summarization
   - :doc:`file_save_hook` - File-based output processing
   - :doc:`index` - Complete hooks system overview
   - :doc:`../tool_composition` - Chain tools into workflows
