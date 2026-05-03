Gnomad Tools
============

**Configuration File**: ``gnomad_tools.json``
**Tool Type**: Local
**Tools Count**: 1

This page contains all tools defined in the ``gnomad_tools.json`` configuration file.

Available Tools
---------------

**gnomad_get_gene_constraints** (Type: gnomADGetGeneConstraints)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get gene constraint metrics from gnomAD. Returns pLI, LOEUF, and other constraint scores for genes.

.. dropdown:: gnomad_get_gene_constraints tool specification

   **Tool Information:**

   * **Name**: ``gnomad_get_gene_constraints``
   * **Type**: ``gnomADGetGeneConstraints``
   * **Description**: Get gene constraint metrics from gnomAD. Returns pLI, LOEUF, and other constraint scores for genes.

   **Parameters:**

   * ``gene_symbol`` (string) (required)
     Gene symbol (e.g., 'BRCA1', 'TP53')

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "gnomad_get_gene_constraints",
          "arguments": {
              "gene_symbol": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
