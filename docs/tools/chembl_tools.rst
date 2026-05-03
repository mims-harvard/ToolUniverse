Chembl Tools
============

**Configuration File**: ``chembl_tools.json``
**Tool Type**: Local
**Tools Count**: 1

This page contains all tools defined in the ``chembl_tools.json`` configuration file.

Available Tools
---------------

**ChEMBL_search_similar_molecules** (Type: ChEMBLTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search for molecules similar to a given SMILES, chembl_id, or compound or drug name, using the Ch...

.. dropdown:: ChEMBL_search_similar_molecules tool specification

   **Tool Information:**

   * **Name**: ``ChEMBL_search_similar_molecules``
   * **Type**: ``ChEMBLTool``
   * **Description**: Search for molecules similar to a given SMILES, chembl_id, or compound or drug name, using the ChEMBL Web Services. Note: This tool is designed for small molecule compounds only. Biologics (antibodies, proteins, oligonucleotides, etc.) do not have SMILES structures and cannot be used for similarity search. For biologics similarity search, use BLAST_protein_search (requires amino acid sequence) or UniProt_search. For small molecules, use PubChem_search_compounds_by_similarity (requires SMILES input).

   **Parameters:**

   * ``query`` (string) (required)
     SMILES string, chembl_id, or compound or drug name. Note: Only small molecule compounds are supported. Biologics (antibodies, proteins, etc.) will return an error as they lack SMILES structures.

   * ``similarity_threshold`` (integer) (required)
     Similarity threshold (0–100).

   * ``max_results`` (integer) (required)
     Maximum number of results to return.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "ChEMBL_search_similar_molecules",
          "arguments": {
              "query": "example_value",
              "similarity_threshold": 10,
              "max_results": 10
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
