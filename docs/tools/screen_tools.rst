Screen Tools
============

**Configuration File**: ``screen_tools.json``
**Tool Type**: Local
**Tools Count**: 1

This page contains all tools defined in the ``screen_tools.json`` configuration file.

Available Tools
---------------

**SCREEN_get_regulatory_elements** (Type: SCREENRESTTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get candidate cis-regulatory elements (cCREs) from SCREEN database for specific genomic regions

.. dropdown:: SCREEN_get_regulatory_elements tool specification

   **Tool Information:**

   * **Name**: ``SCREEN_get_regulatory_elements``
   * **Type**: ``SCREENRESTTool``
   * **Description**: Get candidate cis-regulatory elements (cCREs) from SCREEN database for specific genomic regions

   **Parameters:**

   * ``gene_name`` (string) (required)
     Gene symbol to search for regulatory elements (e.g., BRCA1, TP53)

   * ``element_type`` (string) (optional)
     Type of regulatory element (promoter, enhancer, insulator)

   * ``limit`` (integer) (optional)
     Number of results to return

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "SCREEN_get_regulatory_elements",
          "arguments": {
              "gene_name": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
