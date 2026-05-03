Obis Tools
==========

**Configuration File**: ``obis_tools.json``
**Tool Type**: Local
**Tools Count**: 2

This page contains all tools defined in the ``obis_tools.json`` configuration file.

Available Tools
---------------

**OBIS_search_occurrences** (Type: OBISOccurrenceTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve marine species occurrence records (with coordinates/time) from OBIS using flexible filte...

.. dropdown:: OBIS_search_occurrences tool specification

   **Tool Information:**

   * **Name**: ``OBIS_search_occurrences``
   * **Type**: ``OBISOccurrenceTool``
   * **Description**: Retrieve marine species occurrence records (with coordinates/time) from OBIS using flexible filters. Use for ocean biodiversity distribution analyses.

   **Parameters:**

   * ``scientificname`` (string) (optional)
     Scientific name filter to restrict occurrences.

   * ``areaid`` (string) (optional)
     Area identifier filter (per OBIS API).

   * ``size`` (integer) (optional)
     Number of records to return (1–100).

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "OBIS_search_occurrences",
          "arguments": {
          }
      }
      result = tu.run(query)


**OBIS_search_taxa** (Type: OBISTaxaTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Resolve marine taxa in OBIS by scientific name to obtain standardized identifiers (AphiaID), rank...

.. dropdown:: OBIS_search_taxa tool specification

   **Tool Information:**

   * **Name**: ``OBIS_search_taxa``
   * **Type**: ``OBISTaxaTool``
   * **Description**: Resolve marine taxa in OBIS by scientific name to obtain standardized identifiers (AphiaID), ranks, and names. Use before querying marine occurrences.

   **Parameters:**

   * ``scientificname`` (string) (required)
     Scientific name query (e.g., 'Gadus').

   * ``size`` (integer) (optional)
     Number of records to return (1–100).

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "OBIS_search_taxa",
          "arguments": {
              "scientificname": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
