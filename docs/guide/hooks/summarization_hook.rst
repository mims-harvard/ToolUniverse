SummarizationHook
=================

**AI-powered intelligent summarization of long tool outputs**

The SummarizationHook automatically summarizes long tool outputs using advanced AI models, preserving key findings and results while reducing length.

Overview
--------

**What it does:**
- Analyzes tool outputs and identifies key information
- Uses AI models to create concise summaries
- Preserves important technical details and findings
- Reduces output length while maintaining relevance

**When to use:**
- Large datasets from scientific databases
- Complex research results and literature
- Long-form tool outputs that exceed memory limits
- When you need quick insights from detailed data

Quick Start
-----------

**Simple Usage**

.. code-block:: python

   from tooluniverse import ToolUniverse

   # Enable SummarizationHook (default)
   tu = ToolUniverse(hooks_enabled=True)

   # Or explicitly specify
   tu = ToolUniverse(hooks_enabled=True, hook_type='SummarizationHook')

   tu.load_tools(['uniprot'])

   result = tu.run({
       "name": "UniProt_get_entry_by_accession",
       "arguments": {"accession": "P05067"}
   })

   # Result is automatically summarized
   print(f"Summary length: {len(str(result))} characters")

**Advanced Configuration**

.. code-block:: python

   hook_config = {
       "exclude_tools": [
           "Tool_RAG",
           "ToolFinderEmbedding"
       ],
       "hooks": [{
           "name": "protein_summarization",
           "type": "SummarizationHook",
           "enabled": True,
           "conditions": {
               "output_length": {
                   "operator": ">",
                   "threshold": 8000
               }
           },
           "hook_config": {
                   "chunk_size": 30000,
               "focus_areas": "protein_function_and_structure",
               "max_summary_length": 3500
           }
       }]
   }

   tu = ToolUniverse(hooks_enabled=True, hook_config=hook_config)

Configuration Options
---------------------

**Chunk Size**
- Controls the size of chunks for processing
- Default: 30000 characters
- Range: 10000-50000 characters recommended for optimal performance

**Focus Areas**
- Specifies what to focus on during summarization
- Default: "key_findings_and_results"

**Maximum Summary Length**
- Limits the length of the final summary
- Default: 3000 characters

**Excluding Tools**

Use `exclude_tools` to prevent specific tools from being summarized:

.. code-block:: python

   hook_config = {
       "exclude_tools": [
           "Tool_RAG",           # Exact match
           "ToolFinderEmbedding", # Exact match
           "CustomTool_*"         # Wildcard pattern
       ],
       "hooks": [...]
   }

This is particularly useful for excluding tool discovery tools that shouldn't be processed by hooks.

**Focus Areas Options**

General Focus Areas:
- `key_findings_and_results`: General key findings and results
- `consolidate_and_prioritize`: Merging multiple summaries
- `technical_details`: Technical specifications and details
- `main_conclusions`: Main conclusions and outcomes

Domain-Specific Focus Areas:
- `protein_function_and_structure`: Protein-specific information
- `compound_properties_and_activity`: Chemical compound data
- `key_findings_and_relevance`: Literature search results
- `clinical_significance_and_drug_interactions`: Clinical data
- `methodology_and_results`: Research methodology and findings

Examples
--------

**Scientific Literature Analysis**

.. code-block:: python

   # Summarize literature search results
   tu = ToolUniverse(hooks_enabled=True)
   tu.load_tools(['europepmc'])

   result = tu.run({
       "name": "EuropePMC_search_publications",
       "arguments": {
           "query": "CRISPR gene editing therapeutic applications",
           "resultType": "core"
       }
   })

   # Get AI-powered summary of research findings
   print("Research Summary:")
   print(result)

**Protein Data Summarization**

.. code-block:: python

   # Configure for protein data
   protein_config = {
       'tool_specific_hooks': {
           'UniProt_get_entry_by_accession': {
               'enabled': True,
               'hooks': [{
                   'name': 'protein_summarization',
                   'type': 'SummarizationHook',
                   'enabled': True,
                   'conditions': {
                       'output_length': {
                           'operator': '>',
                           'threshold': 8000
                       }
                   },
                   'hook_config': {
                       'focus_areas': 'protein_function_and_structure',
                       'max_summary_length': 3500
                   }
               }]
           }
       }
   }

   tu = ToolUniverse(hooks_enabled=True, hook_config=protein_config)

   # Execute protein tool
   result = tu.run({
       "name": "UniProt_get_entry_by_accession",
       "arguments": {"accession": "P05067"}
   })

   # Result will be summarized focusing on protein function and structure

**Compound Analysis Summarization**

.. code-block:: python

   # Configure for compound analysis
   compound_config = {
       'tool_specific_hooks': {
           'ChEMBL_search_compounds': {
               'enabled': True,
               'hooks': [{
                   'name': 'compound_summarization',
                   'type': 'SummarizationHook',
                   'enabled': True,
                   'conditions': {
                       'output_length': {
                           'operator': '>',
                           'threshold': 7000
                       }
                   },
                   'hook_config': {
                       'focus_areas': 'compound_properties_and_activity',
                       'max_summary_length': 3000
                   }
               }]
           }
       }
   }

   tu = ToolUniverse(hooks_enabled=True, hook_config=compound_config)

   # Execute compound search
   result = tu.run({
       "name": "ChEMBL_search_compounds",
       "arguments": {
           "compound_name": "aspirin",
           "limit": 100
       }
   })

   # Result will be summarized focusing on compound properties and activity

Troubleshooting
---------------

**Summarization Not Triggering**
- Check threshold settings: Ensure output exceeds threshold
- Verify hook is enabled: Check `enabled` field
- Confirm tool name matching: Ensure exact tool name match
- Review conditions: Check all condition parameters

**Poor Summarization Quality**
- Adjust focus areas: Use more specific focus areas
- Modify chunk size: Smaller chunks may provide better context
- Increase max summary length: Allow more detailed summaries
- Check query context: Ensure original query is captured

**Performance Issues**
- Increase thresholds: Process fewer outputs
- Optimize chunk sizes: Balance processing time and quality
- Use tool-specific hooks: More efficient than global hooks
- Enable caching: Reduce redundant processing

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

   - :doc:`file_save_hook` - File-based output processing
   - :doc:`hook_configuration` - Advanced configuration options
   - :doc:`index` - Complete hooks system overview
   - :doc:`../tool_composition` - Chain tools into workflows
