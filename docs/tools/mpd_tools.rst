Mpd Tools
=========

**Configuration File**: ``mpd_tools.json``
**Tool Type**: Local
**Tools Count**: 1

This page contains all tools defined in the ``mpd_tools.json`` configuration file.

Available Tools
---------------

**MPD_get_phenotype_data** (Type: MPDRESTTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get mouse phenotype data from Mouse Phenome Database for specific strains and phenotypes

.. dropdown:: MPD_get_phenotype_data tool specification

   **Tool Information:**

   * **Name**: ``MPD_get_phenotype_data``
   * **Type**: ``MPDRESTTool``
   * **Description**: Get mouse phenotype data from Mouse Phenome Database for specific strains and phenotypes

   **Parameters:**

   * ``strain`` (string) (required)
     Mouse strain (e.g., C57BL/6J, BALB/c, DBA/2J)

   * ``phenotype_category`` (string) (optional)
     Phenotype category (behavior, physiology, morphology)

   * ``limit`` (integer) (optional)
     Number of results to return

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "MPD_get_phenotype_data",
          "arguments": {
              "strain": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
