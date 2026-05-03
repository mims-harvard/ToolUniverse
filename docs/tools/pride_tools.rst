Pride Tools
===========

**Configuration File**: ``pride_tools.json``
**Tool Type**: Local
**Tools Count**: 1

This page contains all tools defined in the ``pride_tools.json`` configuration file.

Available Tools
---------------

**PRIDE_search_proteomics** (Type: PRIDERESTTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search PRIDE proteomics database for experiments

.. dropdown:: PRIDE_search_proteomics tool specification

   **Tool Information:**

   * **Name**: ``PRIDE_search_proteomics``
   * **Type**: ``PRIDERESTTool``
   * **Description**: Search PRIDE proteomics database for experiments

   **Parameters:**

   * ``query`` (string) (required)
     Search query

   * ``page_size`` (integer) (optional)
     Results per page

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "PRIDE_search_proteomics",
          "arguments": {
              "query": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
