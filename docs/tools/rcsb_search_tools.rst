Rcsb Search Tools
=================

**Configuration File**: ``rcsb_search_tools.json``
**Tool Type**: Local
**Tools Count**: 1

This page contains all tools defined in the ``rcsb_search_tools.json`` configuration file.

Available Tools
---------------

**PDB_search_similar_structures** (Type: RCSBSearchTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search for protein structures similar to a given PDB ID or sequence using RCSB PDB structure simi...

.. dropdown:: PDB_search_similar_structures tool specification

   **Tool Information:**

   * **Name**: ``PDB_search_similar_structures``
   * **Type**: ``RCSBSearchTool``
   * **Description**: Search for protein structures similar to a given PDB ID or sequence using RCSB PDB structure similarity search. Supports sequence-based, structure-based, and text-based search. Suitable for antibodies, proteins, and other biologics. Use text search to find PDB IDs by drug name, protein name, or keywords.

   **Parameters:**

   * ``query`` (string) (required)
     PDB ID (e.g., '1ABC'), protein sequence (amino acids), or search text (e.g., drug name, protein name, keyword). For structure search, provide PDB ID. For sequence search, provide amino acid sequence. For text search, provide drug name, protein name, or keyword.

   * ``search_type`` (string) (optional)
     Type of search: 'sequence' for sequence-based similarity search, 'structure' for structure-based similarity search using PDB ID, 'text' for text-based search by name or keyword

   * ``similarity_threshold`` (number) (optional)
     Similarity threshold (0-1). Higher values return more similar structures. Values outside 0-1 will be clamped. For sequence search, this is the identity cutoff. For structure search, this is the structure similarity threshold. Not used for text search.

   * ``max_results`` (integer) (optional)
     Maximum number of results to return (1-100). Values outside this range will be clamped.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "PDB_search_similar_structures",
          "arguments": {
              "query": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
