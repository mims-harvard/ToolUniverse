Wikipathways Tools
==================

**Configuration File**: ``wikipathways_tools.json``
**Tool Type**: Local
**Tools Count**: 2

This page contains all tools defined in the ``wikipathways_tools.json`` configuration file.

Available Tools
---------------

**WikiPathways_get_pathway** (Type: WikiPathwaysGetTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Fetch pathway content by WPID (JSON/GPML). Use to programmatically access pathway nodes/edges/met...

.. dropdown:: WikiPathways_get_pathway tool specification

   **Tool Information:**

   * **Name**: ``WikiPathways_get_pathway``
   * **Type**: ``WikiPathwaysGetTool``
   * **Description**: Fetch pathway content by WPID (JSON/GPML). Use to programmatically access pathway nodes/edges/metadata for enrichment reporting or network visualization.

   **Parameters:**

   * ``wpid`` (string) (required)
     WikiPathways identifier (e.g., 'WP254').

   * ``format`` (string) (optional)
     Response format: 'json' for structured, 'gpml' for GPML XML.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "WikiPathways_get_pathway",
          "arguments": {
              "wpid": "example_value"
          }
      }
      result = tu.run(query)


**WikiPathways_search** (Type: WikiPathwaysSearchTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Text search across community-curated pathways (disease, metabolic, signaling). Use to discover re...

.. dropdown:: WikiPathways_search tool specification

   **Tool Information:**

   * **Name**: ``WikiPathways_search``
   * **Type**: ``WikiPathwaysSearchTool``
   * **Description**: Text search across community-curated pathways (disease, metabolic, signaling). Use to discover relevant pathways for a topic/gene set and obtain WPIDs for retrieval/visualization.

   **Parameters:**

   * ``query`` (string) (required)
     Free-text query (keywords, gene symbols, processes), e.g., 'p53', 'glycolysis'.

   * ``organism`` (string) (optional)
     Organism filter (scientific name), e.g., 'Homo sapiens'.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "WikiPathways_search",
          "arguments": {
              "query": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
