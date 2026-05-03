Paleobiology Tools
==================

**Configuration File**: ``paleobiology_tools.json``
**Tool Type**: Local
**Tools Count**: 1

This page contains all tools defined in the ``paleobiology_tools.json`` configuration file.

Available Tools
---------------

**Paleobiology_get_fossils** (Type: PaleobiologyRESTTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get fossil records from Paleobiology Database

.. dropdown:: Paleobiology_get_fossils tool specification

   **Tool Information:**

   * **Name**: ``Paleobiology_get_fossils``
   * **Type**: ``PaleobiologyRESTTool``
   * **Description**: Get fossil records from Paleobiology Database

   **Parameters:**

   * ``taxon`` (string) (required)
     Taxon name

   * ``limit`` (integer) (optional)
     Number of results

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "Paleobiology_get_fossils",
          "arguments": {
              "taxon": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
