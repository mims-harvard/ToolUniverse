Encode Tools
============

**Configuration File**: ``encode_tools.json``
**Tool Type**: Local
**Tools Count**: 2

This page contains all tools defined in the ``encode_tools.json`` configuration file.

Available Tools
---------------

**ENCODE_list_files** (Type: ENCODEFilesTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

List ENCODE files with filters (file_format, output_type, assay). Use to programmatically retriev...

.. dropdown:: ENCODE_list_files tool specification

   **Tool Information:**

   * **Name**: ``ENCODE_list_files``
   * **Type**: ``ENCODEFilesTool``
   * **Description**: List ENCODE files with filters (file_format, output_type, assay). Use to programmatically retrieve downloadable artifact metadata (FASTQ, BAM, bigWig, peaks).

   **Parameters:**

   * ``file_type`` (string) (optional)
     File type filter (e.g., 'fastq', 'bam', 'bigWig').

   * ``assay_title`` (string) (optional)
     Assay filter (e.g., 'ChIP-seq').

   * ``limit`` (integer) (optional)
     Max number of results (1–100).

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "ENCODE_list_files",
          "arguments": {
          }
      }
      result = tu.run(query)


**ENCODE_search_experiments** (Type: ENCODESearchTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search ENCODE functional genomics experiments (e.g., ChIP-seq, ATAC-seq) by assay/target/organism...

.. dropdown:: ENCODE_search_experiments tool specification

   **Tool Information:**

   * **Name**: ``ENCODE_search_experiments``
   * **Type**: ``ENCODESearchTool``
   * **Description**: Search ENCODE functional genomics experiments (e.g., ChIP-seq, ATAC-seq) by assay/target/organism/status. Use to discover datasets and access experiment-level metadata.

   **Parameters:**

   * ``assay_title`` (string) (optional)
     Assay name filter (e.g., 'ChIP-seq', 'ATAC-seq').

   * ``target`` (string) (optional)
     Target filter (e.g., 'CTCF').

   * ``organism`` (string) (optional)
     Organism filter (e.g., 'Homo sapiens', 'Mus musculus').

   * ``status`` (string) (optional)
     Record status filter (default 'released').

   * ``limit`` (integer) (optional)
     Max number of results (1–100).

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "ENCODE_search_experiments",
          "arguments": {
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
