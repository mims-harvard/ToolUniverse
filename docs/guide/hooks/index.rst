Post-processing Tool Outputs
============================

**Intelligent output processing for ToolUniverse**

The ToolUniverse Hooks system provides automatic post-processing of tool outputs. Use hooks to summarize long results, save large outputs to files, and customize behavior per tool or workflow.

What are Hooks?
---------------

Hooks are post-processing functions that automatically transform tool outputs before they're returned to you. They're designed to:

- **Summarize long outputs**: Use AI to condense lengthy results into key insights
- **Save large datasets**: Store massive outputs as files with metadata
- **Customize processing**: Apply different logic based on tool type or output size
- **Improve performance**: Reduce memory usage and processing time

Quick Start
-----------

**Enable hooks with one line:**

.. code-block:: python

   from tooluniverse import ToolUniverse
   
   # Enable default SummarizationHook
   tu = ToolUniverse(hooks_enabled=True)
   tu.load_tools()
   
   # Run tools - outputs are automatically processed
   result = tu.run({
       "name": "OpenTargets_get_target_gene_ontology_by_ensemblID",
       "arguments": {"ensemblId": "ENSG00000012048"}
   })

**Choose different hook types:**

.. code-block:: python

   # Use FileSaveHook for large outputs
   tu = ToolUniverse(hooks_enabled=True, hook_type='FileSaveHook')
   
   # Use custom configuration
   tu = ToolUniverse(hooks_enabled=True, hook_config=my_config)

Hook Types
----------

**SummarizationHook** - AI-powered summarization
   Automatically summarizes long tool outputs using advanced AI models. Preserves key findings while reducing length.

**FileSaveHook** - File-based processing
   Saves large outputs to disk with metadata. Returns file information instead of the original output.

**Custom Hooks** - User-defined processing
   Create your own hooks for specialized processing needs.

When to Use Hooks
-----------------

**Use SummarizationHook when:**
- Tool outputs are too long to read efficiently
- You need quick insights from detailed data
- Working with literature search results
- Processing large scientific datasets

**Note:** Some tools (like Tool_RAG, ToolFinderEmbedding) are automatically excluded from hook processing to prevent information missing. You can customize excluded tools using the `exclude_tools` configuration option.

**Use FileSaveHook when:**
- Outputs exceed memory limits
- You need to process outputs as files
- Archiving results for later analysis
- Integrating with external tools

**Use Custom Hooks when:**
- You have specific processing requirements
- Standard hooks don't meet your needs
- You need specialized data transformations

Performance Impact
------------------

Hooks add processing overhead but provide significant benefits:

- **SummarizationHook**: 2-5x processing time, 50-80% output reduction
- **FileSaveHook**: Minimal overhead, significant memory savings
- **Custom Hooks**: Depends on implementation

The trade-off is usually worth it for large outputs that benefit from processing.

.. toctree::
   :maxdepth: 1
   :hidden:
   :caption: Hook Topics

   summarization_hook
   file_save_hook
   hook_configuration
   server_stdio_hooks

**Topic summaries**

- :doc:`summarization_hook`: Automatically condenses long tool outputs into concise, high-signal summaries. Useful for literature results, large datasets, and multi-step workflows.
- :doc:`file_save_hook`: Saves large outputs to disk with metadata for later processing and sharing. Ideal for heavy payloads, audit trails, and external pipelines.
- :doc:`hook_configuration`: Configure which hooks run, when they trigger, and how they behave. Supports thresholds, per-tool rules, and advanced options.
- :doc:`server_stdio_hooks`: How to use hooks in server (HTTP/SSE) and stdio modes. Covers CLI flags, Python API, defaults, and best practices.

Examples
--------

**Complete Hook Example:**

A comprehensive example demonstrating all hook functionality is available at:

.. code-block:: bash

   # Run all hook examples
   python examples/hooks_example.py

**Example Features:**

- **Basic Usage**: Simple SummarizationHook and FileSaveHook examples
- **Advanced Configuration**: Custom settings and tool-specific hooks
- **Performance Testing**: Comparison between different hook configurations
- **Error Handling**: Graceful degradation and error recovery

