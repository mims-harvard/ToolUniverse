Gtopdb Tools
============

**Configuration File**: ``gtopdb_tools.json``
**Tool Type**: Local
**Tools Count**: 1

This page contains all tools defined in the ``gtopdb_tools.json`` configuration file.

Available Tools
---------------

**GtoPdb_get_targets** (Type: GtoPdbRESTTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get pharmacological targets from Guide to Pharmacology database

.. dropdown:: GtoPdb_get_targets tool specification

   **Tool Information:**

   * **Name**: ``GtoPdb_get_targets``
   * **Type**: ``GtoPdbRESTTool``
   * **Description**: Get pharmacological targets from Guide to Pharmacology database

   **Parameters:**

   * ``target_type`` (string) (optional)
     Target type

   * ``limit`` (integer) (optional)
     Number of results

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "GtoPdb_get_targets",
          "arguments": {
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
