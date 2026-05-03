Gbif Tools
==========

**Configuration File**: ``gbif_tools.json``
**Tool Type**: Local
**Tools Count**: 2

This page contains all tools defined in the ``gbif_tools.json`` configuration file.

Available Tools
---------------

**GBIF_search_occurrences** (Type: GBIFOccurrenceTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve species occurrence records from GBIF with optional filters (taxonKey, country, coordinat...

.. dropdown:: GBIF_search_occurrences tool specification

   **Tool Information:**

   * **Name**: ``GBIF_search_occurrences``
   * **Type**: ``GBIFOccurrenceTool``
   * **Description**: Retrieve species occurrence records from GBIF with optional filters (taxonKey, country, coordinates). Use for distribution mapping, presence-only modeling, and sampling context.

   **Parameters:**

   * ``taxonKey`` (integer) (optional)
     GBIF taxon key to filter occurrences by a specific taxon (from species search).

   * ``country`` (string) (optional)
     ISO 3166-1 alpha-2 country code filter (e.g., 'US', 'CN').

   * ``hasCoordinate`` (boolean) (optional)
     Only return records with valid latitude/longitude coordinates when true.

   * ``limit`` (integer) (optional)
     Maximum number of results to return (1–300).

   * ``offset`` (integer) (optional)
     Result offset for pagination (0-based).

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "GBIF_search_occurrences",
          "arguments": {
          }
      }
      result = tu.run(query)


**GBIF_search_species** (Type: GBIFTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Find taxa by keyword (scientific/common names) in GBIF. Use to resolve organism names to stable t...

.. dropdown:: GBIF_search_species tool specification

   **Tool Information:**

   * **Name**: ``GBIF_search_species``
   * **Type**: ``GBIFTool``
   * **Description**: Find taxa by keyword (scientific/common names) in GBIF. Use to resolve organism names to stable taxon keys (rank, lineage) for downstream biodiversity/occurrence queries.

   **Parameters:**

   * ``query`` (string) (required)
     Search string for species/taxa (supports scientific/common names), e.g., 'Homo', 'Atlantic cod'.

   * ``limit`` (integer) (optional)
     Maximum number of results to return (1–300).

   * ``offset`` (integer) (optional)
     Result offset for pagination (0-based).

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "GBIF_search_species",
          "arguments": {
              "query": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
