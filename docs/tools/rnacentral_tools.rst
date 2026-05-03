Rnacentral Tools
================

**Configuration File**: ``rnacentral_tools.json``
**Tool Type**: Local
**Tools Count**: 2

This page contains all tools defined in the ``rnacentral_tools.json`` configuration file.

Available Tools
---------------

**RNAcentral_get_by_accession** (Type: RNAcentralGetTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve a single RNAcentral entry by accession for detailed annotations and source cross-referen...

.. dropdown:: RNAcentral_get_by_accession tool specification

   **Tool Information:**

   * **Name**: ``RNAcentral_get_by_accession``
   * **Type**: ``RNAcentralGetTool``
   * **Description**: Retrieve a single RNAcentral entry by accession for detailed annotations and source cross-references. Use for cross-database ID mapping and metadata.

   **Parameters:**

   * ``accession`` (string) (required)
     RNAcentral accession (e.g., 'URS000075C808').

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "RNAcentral_get_by_accession",
          "arguments": {
              "accession": "example_value"
          }
      }
      result = tu.run(query)


**RNAcentral_search** (Type: RNAcentralSearchTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search aggregated ncRNA records (miRNA, rRNA, lncRNA, etc.) across sources via RNAcentral. Use to...

.. dropdown:: RNAcentral_search tool specification

   **Tool Information:**

   * **Name**: ``RNAcentral_search``
   * **Type**: ``RNAcentralSearchTool``
   * **Description**: Search aggregated ncRNA records (miRNA, rRNA, lncRNA, etc.) across sources via RNAcentral. Use to find accessions, types, species, and descriptions for ncRNA analysis.

   **Parameters:**

   * ``query`` (string) (required)
     Keyword, accession, or sequence-based query (per RNAcentral API).

   * ``page_size`` (integer) (optional)
     Number of records per page (1–100).

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "RNAcentral_search",
          "arguments": {
              "query": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
