Compose Tools
=============

**Configuration File**: ``compose_tools.json``
**Tool Type**: Local
**Tools Count**: 6

This page contains all tools defined in the ``compose_tools.json`` configuration file.

Available Tools
---------------

**BiomarkerDiscoveryWorkflow** (Type: ComposeTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Discover and validate biomarkers for a specific disease condition using literature analysis, expr...

.. dropdown:: BiomarkerDiscoveryWorkflow tool specification

   **Tool Information:**

   * **Name**: ``BiomarkerDiscoveryWorkflow``
   * **Type**: ``ComposeTool``
   * **Description**: Discover and validate biomarkers for a specific disease condition using literature analysis, expression data, pathway enrichment, and clinical validation.

   **Parameters:**

   * ``disease_condition`` (string) (required)
     The disease condition to discover biomarkers for (e.g., 'breast cancer', 'Alzheimer's disease')

   * ``sample_type`` (string) (required)
     The type of sample to analyze (e.g., 'blood', 'tissue', 'plasma')

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "BiomarkerDiscoveryWorkflow",
          "arguments": {
              "disease_condition": "example_value",
              "sample_type": "example_value"
          }
      }
      result = tu.run(query)


**ComprehensiveDrugDiscoveryPipeline** (Type: ComposeTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Complete end-to-end drug discovery workflow from disease to optimized candidates. Identifies targ...

.. dropdown:: ComprehensiveDrugDiscoveryPipeline tool specification

   **Tool Information:**

   * **Name**: ``ComprehensiveDrugDiscoveryPipeline``
   * **Type**: ``ComposeTool``
   * **Description**: Complete end-to-end drug discovery workflow from disease to optimized candidates. Identifies targets, discovers lead compounds, screens for ADMET properties, assesses safety, and validates with literature.

   **Parameters:**

   * ``disease_efo_id`` (string) (required)
     The EFO ID of the disease for drug discovery (e.g., 'EFO_0001074' for Alzheimer's disease)

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "ComprehensiveDrugDiscoveryPipeline",
          "arguments": {
              "disease_efo_id": "example_value"
          }
      }
      result = tu.run(query)


**DrugSafetyAnalyzer** (Type: ComposeTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Comprehensive drug safety analysis combining adverse event data, literature review, and molecular...

.. dropdown:: DrugSafetyAnalyzer tool specification

   **Tool Information:**

   * **Name**: ``DrugSafetyAnalyzer``
   * **Type**: ``ComposeTool``
   * **Description**: Comprehensive drug safety analysis combining adverse event data, literature review, and molecular information

   **Parameters:**

   * ``drug_name`` (string) (required)
     Name of the drug to analyze

   * ``patient_sex`` (string) (required)
     Filter by patient sex (optional)

   * ``serious_events_only`` (boolean) (required)
     Focus only on serious adverse events

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "DrugSafetyAnalyzer",
          "arguments": {
              "drug_name": "example_value",
              "patient_sex": "example_value",
              "serious_events_only": true
          }
      }
      result = tu.run(query)


**LiteratureSearchTool** (Type: ComposeTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Comprehensive literature search and summary tool that searches multiple databases (EuropePMC, Ope...

.. dropdown:: LiteratureSearchTool tool specification

   **Tool Information:**

   * **Name**: ``LiteratureSearchTool``
   * **Type**: ``ComposeTool``
   * **Description**: Comprehensive literature search and summary tool that searches multiple databases (EuropePMC, OpenAlex, PubTator) and generates AI-powered summaries of research findings

   **Parameters:**

   * ``research_topic`` (string) (required)
     The research topic or query to search for in the literature

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "LiteratureSearchTool",
          "arguments": {
              "research_topic": "example_value"
          }
      }
      result = tu.run(query)


**ToolGraphGenerationPipeline** (Type: ComposeTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Generates a directed tool relationship graph among provided tool configs using ToolRelationshipDe...

.. dropdown:: ToolGraphGenerationPipeline tool specification

   **Tool Information:**

   * **Name**: ``ToolGraphGenerationPipeline``
   * **Type**: ``ComposeTool``
   * **Description**: Generates a directed tool relationship graph among provided tool configs using ToolRelationshipDetector to infer data-flow compatibility.

   **Parameters:**

   * ``tool_configs`` (array) (required)
     List of tool configuration objects

   * ``max_tools`` (integer) (required)
     Optional max number of tools to process (debug)

   * ``output_path`` (string) (required)
     Path for output graph JSON

   * ``save_intermediate_every`` (integer) (required)
     Checkpoint every N processed pairs

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "ToolGraphGenerationPipeline",
          "arguments": {
              "tool_configs": ["item1", "item2"],
              "max_tools": 10,
              "output_path": "example_value",
              "save_intermediate_every": 10
          }
      }
      result = tu.run(query)


**ToolMetadataGenerationPipeline** (Type: ComposeTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Generates standardized metadata for a batch of ToolUniverse tool configurations by calling ToolMe...

.. dropdown:: ToolMetadataGenerationPipeline tool specification

   **Tool Information:**

   * **Name**: ``ToolMetadataGenerationPipeline``
   * **Type**: ``ComposeTool``
   * **Description**: Generates standardized metadata for a batch of ToolUniverse tool configurations by calling ToolMetadataGenerator, LabelGenerator, and ToolMetadataStandardizer for sources and tags.

   **Parameters:**

   * ``tool_configs`` (array) (required)
     List of raw tool configuration JSON objects to extract and standardize metadata for

   * ``tool_type_mappings`` (object) (required)
     Mapping of simplified toolType (keys) to lists of tool 'type' values belonging to each simplified category (e.g., {'Databases': ['XMLTool']})

   * ``add_existing_tooluniverse_labels`` (boolean) (required)
     Whether to include labels from existing ToolUniverse tools when labeling the metadata configs of the new tools. It is strongly recommended that this is set to true to minimize the number of new labels created and the possibility of redundant labels.

   * ``max_new_tooluniverse_labels`` (integer) (required)
     The maximum number of new ToolUniverse labels to use in the metadata configs of the new tools. The existing ToolUniverse labels will be used first, and then new labels will be created as needed up to this limit. If the limit is reached, the least relevant new labels will be discarded. Please try to use as few new labels as possible to avoid excessive labels.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "ToolMetadataGenerationPipeline",
          "arguments": {
              "tool_configs": ["item1", "item2"],
              "tool_type_mappings": "example_value",
              "add_existing_tooluniverse_labels": true,
              "max_new_tooluniverse_labels": 10
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
