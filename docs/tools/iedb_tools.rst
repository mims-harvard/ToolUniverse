Iedb Tools
==========

**Configuration File**: ``iedb_tools.json``
**Tool Type**: Local
**Tools Count**: 1

This page contains all tools defined in the ``iedb_tools.json`` configuration file.

Available Tools
---------------

**iedb_search_epitopes** (Type: IEDBTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Searches for immune epitopes in the Immune Epitope Database (IEDB). Use this tool to find specifi...

.. dropdown:: iedb_search_epitopes tool specification

   **Tool Information:**

   * **Name**: ``iedb_search_epitopes``
   * **Type**: ``IEDBTool``
   * **Description**: Searches for immune epitopes in the Immune Epitope Database (IEDB). Use this tool to find specific epitope structures, such as linear peptides, involved in immune responses.

   **Parameters:**

   * ``action`` (string) (required)
     The specific action to perform. Must be set to 'search_epitopes'.

   * ``query`` (string) (optional)
     Sequence fragment or pattern to search for within the epitope's linear sequence. For example, use 'KVF' to find epitopes containing that sequence.

   * ``structure_type`` (string) (optional)
     The chemical type of the epitope structure. Common values include 'Linear peptide', 'Discontinuous peptide', or 'Non-peptidic'.

   * ``limit`` (integer) (optional)
     The maximum number of epitope results to return. The default is 10.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "iedb_search_epitopes",
          "arguments": {
              "action": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
