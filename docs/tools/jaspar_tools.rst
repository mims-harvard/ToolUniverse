Jaspar Tools
============

**Configuration File**: ``jaspar_tools.json``
**Tool Type**: Local
**Tools Count**: 1

This page contains all tools defined in the ``jaspar_tools.json`` configuration file.

Available Tools
---------------

**JASPAR_get_transcription_factors** (Type: JASPARRESTTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get transcription factor binding site matrices from JASPAR

.. dropdown:: JASPAR_get_transcription_factors tool specification

   **Tool Information:**

   * **Name**: ``JASPAR_get_transcription_factors``
   * **Type**: ``JASPARRESTTool``
   * **Description**: Get transcription factor binding site matrices from JASPAR

   **Parameters:**

   * ``collection`` (string) (optional)
     JASPAR collection

   * ``limit`` (integer) (optional)
     Number of results

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "JASPAR_get_transcription_factors",
          "arguments": {
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
