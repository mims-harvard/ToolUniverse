Blast Tools
===========

**Configuration File**: ``blast_tools.json``
**Tool Type**: Local
**Tools Count**: 2

This page contains all tools defined in the ``blast_tools.json`` configuration file.

Available Tools
---------------

**BLAST_nucleotide_search** (Type: NCBIBlastTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search nucleotide sequences using NCBI BLAST blastn against nucleotide databases

.. dropdown:: BLAST_nucleotide_search tool specification

   **Tool Information:**

   * **Name**: ``BLAST_nucleotide_search``
   * **Type**: ``NCBIBlastTool``
   * **Description**: Search nucleotide sequences using NCBI BLAST blastn against nucleotide databases

   **Parameters:**

   * ``sequence`` (string) (required)
     DNA sequence to search

   * ``database`` (string) (optional)
     Database (nt, est, etc.)

   * ``expect`` (number) (optional)
     E-value threshold

   * ``hitlist_size`` (integer) (optional)
     Max hits to return

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "BLAST_nucleotide_search",
          "arguments": {
              "sequence": "example_value"
          }
      }
      result = tu.run(query)


**BLAST_protein_search** (Type: NCBIBlastTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search protein sequences using NCBI BLAST blastp against protein databases

.. dropdown:: BLAST_protein_search tool specification

   **Tool Information:**

   * **Name**: ``BLAST_protein_search``
   * **Type**: ``NCBIBlastTool``
   * **Description**: Search protein sequences using NCBI BLAST blastp against protein databases

   **Parameters:**

   * ``sequence`` (string) (required)
     Protein sequence to search

   * ``database`` (string) (optional)
     Database (nr, swissprot, etc.)

   * ``expect`` (number) (optional)
     No description

   * ``hitlist_size`` (integer) (optional)
     No description

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "BLAST_protein_search",
          "arguments": {
              "sequence": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
