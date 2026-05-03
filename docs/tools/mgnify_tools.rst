Mgnify Tools
============

**Configuration File**: ``mgnify_tools.json``
**Tool Type**: Local
**Tools Count**: 2

This page contains all tools defined in the ``mgnify_tools.json`` configuration file.

Available Tools
---------------

**MGnify_list_analyses** (Type: MGnifyAnalysesTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

List analyses associated with a study accession (taxonomic/functional outputs). Use to enumerate ...

.. dropdown:: MGnify_list_analyses tool specification

   **Tool Information:**

   * **Name**: ``MGnify_list_analyses``
   * **Type**: ``MGnifyAnalysesTool``
   * **Description**: List analyses associated with a study accession (taxonomic/functional outputs). Use to enumerate available processed results for programmatic retrieval.

   **Parameters:**

   * ``study_accession`` (string) (required)
     MGnify study accession (e.g., 'MGYS00000001').

   * ``size`` (integer) (optional)
     Number of records per page (1–100).

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "MGnify_list_analyses",
          "arguments": {
              "study_accession": "example_value"
          }
      }
      result = tu.run(query)


**MGnify_search_studies** (Type: MGnifyStudiesTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search MGnify metagenomics/microbiome studies by biome/keyword. Use to discover study accessions ...

.. dropdown:: MGnify_search_studies tool specification

   **Tool Information:**

   * **Name**: ``MGnify_search_studies``
   * **Type**: ``MGnifyStudiesTool``
   * **Description**: Search MGnify metagenomics/microbiome studies by biome/keyword. Use to discover study accessions and attributes for downstream analyses and downloads.

   **Parameters:**

   * ``biome`` (string) (optional)
     Biome identifier (e.g., 'root:Host-associated').

   * ``search`` (string) (optional)
     Keyword to search in study titles/descriptions.

   * ``size`` (integer) (optional)
     Number of records per page (1–100).

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "MGnify_search_studies",
          "arguments": {
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
