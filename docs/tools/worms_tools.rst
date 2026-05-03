Worms Tools
===========

**Configuration File**: ``worms_tools.json``
**Tool Type**: Local
**Tools Count**: 1

This page contains all tools defined in the ``worms_tools.json`` configuration file.

Available Tools
---------------

**WoRMS_search_species** (Type: WoRMSRESTTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search marine species in World Register of Marine Species

.. dropdown:: WoRMS_search_species tool specification

   **Tool Information:**

   * **Name**: ``WoRMS_search_species``
   * **Type**: ``WoRMSRESTTool``
   * **Description**: Search marine species in World Register of Marine Species

   **Parameters:**

   * ``query`` (string) (required)
     Species name or search term

   * ``limit`` (integer) (optional)
     Number of results

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "WoRMS_search_species",
          "arguments": {
              "query": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
