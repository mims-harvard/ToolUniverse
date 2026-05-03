Regulomedb Tools
================

**Configuration File**: ``regulomedb_tools.json``
**Tool Type**: Local
**Tools Count**: 1

This page contains all tools defined in the ``regulomedb_tools.json`` configuration file.

Available Tools
---------------

**RegulomeDB_query_variant** (Type: RegulomeDBRESTTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Query RegulomeDB for regulatory variant annotations using rsID

.. dropdown:: RegulomeDB_query_variant tool specification

   **Tool Information:**

   * **Name**: ``RegulomeDB_query_variant``
   * **Type**: ``RegulomeDBRESTTool``
   * **Description**: Query RegulomeDB for regulatory variant annotations using rsID

   **Parameters:**

   * ``rsid`` (string) (required)
     dbSNP rsID (e.g., rs123456)

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "RegulomeDB_query_variant",
          "arguments": {
              "rsid": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
