Alphafold Tools
===============

**Configuration File**: ``alphafold_tools.json``
**Tool Type**: Local
**Tools Count**: 3

This page contains all tools defined in the ``alphafold_tools.json`` configuration file.

Available Tools
---------------

**alphafold_get_annotations** (Type: AlphaFoldRESTTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve AlphaFold MUTAGEN annotations for a given UniProt accession. Returns experimental mutage...

.. dropdown:: alphafold_get_annotations tool specification

   **Tool Information:**

   * **Name**: ``alphafold_get_annotations``
   * **Type**: ``AlphaFoldRESTTool``
   * **Description**: Retrieve AlphaFold MUTAGEN annotations for a given UniProt accession. Returns experimental mutagenesis data mapped onto protein structures from UniProt. The qualifier must be a UniProt ACCESSION (e.g., 'P69905'). Note: Not all proteins have MUTAGEN annotations available in the database.

   **Parameters:**

   * ``qualifier`` (string) (required)
     UniProt ACCESSION (e.g., 'P69905'). Must be an accession number, not an entry name.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "alphafold_get_annotations",
          "arguments": {
              "qualifier": "example_value"
          }
      }
      result = tu.run(query)


**alphafold_get_prediction** (Type: AlphaFoldRESTTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve full AlphaFold 3D structure predictions for a given protein. IMPORTANT: The qualifier mu...

.. dropdown:: alphafold_get_prediction tool specification

   **Tool Information:**

   * **Name**: ``alphafold_get_prediction``
   * **Type**: ``AlphaFoldRESTTool``
   * **Description**: Retrieve full AlphaFold 3D structure predictions for a given protein. IMPORTANT: The qualifier must be a UniProt ACCESSION (e.g., 'P69905' for HBA_HUMAN). Do NOT use UniProt entry names like 'HBA_HUMAN' - they will cause API errors. To find UniProt accession from a gene/protein name, use `UniProt_search` (e.g., query='gene:HBA' organism='human') or `UniProt_id_mapping` for ID conversion. Returns residue-level metadata including sequence, per-residue confidence scores (pLDDT), and structure download links (PDB, CIF, PAE). If you already have the accession and want UniProt details, call `UniProt_get_entry_by_accession`. For a quick overview, use `alphafold_get_summary`. For mutation/variant impact, see `alphafold_get_annotations`.

   **Parameters:**

   * ``qualifier`` (string) (required)
     Protein identifier: UniProt ACCESSION (e.g., 'P69905'). Do NOT use entry names like 'HBA_HUMAN'. To find accession from gene name: use `UniProt_search` or `UniProt_id_mapping`.

   * ``sequence_checksum`` (string) (required)
     Optional CRC64 checksum of the UniProt sequence.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "alphafold_get_prediction",
          "arguments": {
              "qualifier": "example_value",
              "sequence_checksum": "example_value"
          }
      }
      result = tu.run(query)


**alphafold_get_summary** (Type: AlphaFoldRESTTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve summary details of AlphaFold 3D models for a given protein. IMPORTANT: The qualifier mus...

.. dropdown:: alphafold_get_summary tool specification

   **Tool Information:**

   * **Name**: ``alphafold_get_summary``
   * **Type**: ``AlphaFoldRESTTool``
   * **Description**: Retrieve summary details of AlphaFold 3D models for a given protein. IMPORTANT: The qualifier must be a UniProt ACCESSION (e.g., 'Q5SWX9' for MEIOB_HUMAN). Do NOT use UniProt entry names like 'MEIOB_HUMAN' - they will cause API errors. To find UniProt accession from a gene/protein name, use `UniProt_search` (e.g., query='gene:MEIOB' organism='human') or `UniProt_id_mapping` for ID conversion. Returns lightweight information such as sequence length, coverage, confidence scores, experimental method, resolution, oligomeric state, and structural entities. For full residue-level 3D predictions with downloadable coordinates, call `alphafold_get_prediction`. For curated variants, see `UniProt_get_disease_variants_by_accession`; for predicted mutation effects, use `alphafold_get_annotations`.

   **Parameters:**

   * ``qualifier`` (string) (required)
     Protein identifier: UniProt ACCESSION (e.g., 'Q5SWX9'). Do NOT use entry names like 'MEIOB_HUMAN'. To find accession from gene name: use `UniProt_search` or `UniProt_id_mapping`.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "alphafold_get_summary",
          "arguments": {
              "qualifier": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
