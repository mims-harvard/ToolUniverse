Remap Tools
===========

**Configuration File**: ``remap_tools.json``
**Tool Type**: Local
**Tools Count**: 1

This page contains all tools defined in the ``remap_tools.json`` configuration file.

Available Tools
---------------

**ReMap_get_transcription_factor_binding** (Type: ReMapRESTTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get transcription factor binding sites from ReMap database for specific genes and cell types

.. dropdown:: ReMap_get_transcription_factor_binding tool specification

   **Tool Information:**

   * **Name**: ``ReMap_get_transcription_factor_binding``
   * **Type**: ``ReMapRESTTool``
   * **Description**: Get transcription factor binding sites from ReMap database for specific genes and cell types

   **Parameters:**

   * ``gene_name`` (string) (required)
     Gene symbol (e.g., BRCA1, TP53, MYC)

   * ``cell_type`` (string) (optional)
     Cell type (e.g., HepG2, K562, MCF-7)

   * ``limit`` (integer) (optional)
     Number of results to return

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "ReMap_get_transcription_factor_binding",
          "arguments": {
              "gene_name": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
