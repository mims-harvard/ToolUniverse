Emdb Tools
==========

**Configuration File**: ``emdb_tools.json``
**Tool Type**: Local
**Tools Count**: 1

This page contains all tools defined in the ``emdb_tools.json`` configuration file.

Available Tools
---------------

**EMDB_get_structure** (Type: EMDBRESTTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get electron microscopy structure data from EMDB

.. dropdown:: EMDB_get_structure tool specification

   **Tool Information:**

   * **Name**: ``EMDB_get_structure``
   * **Type**: ``EMDBRESTTool``
   * **Description**: Get electron microscopy structure data from EMDB

   **Parameters:**

   * ``emdb_id`` (string) (required)
     EMDB structure ID (e.g., EMD-1234)

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "EMDB_get_structure",
          "arguments": {
              "emdb_id": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
