Geo Tools
=========

**Configuration File**: ``geo_tools.json``
**Tool Type**: Local
**Tools Count**: 3

This page contains all tools defined in the ``geo_tools.json`` configuration file.

Available Tools
---------------

**geo_get_dataset_info** (Type: GEOGetDatasetInfo)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get detailed information about a specific GEO dataset including title, summary, and metadata.

.. dropdown:: geo_get_dataset_info tool specification

   **Tool Information:**

   * **Name**: ``geo_get_dataset_info``
   * **Type**: ``GEOGetDatasetInfo``
   * **Description**: Get detailed information about a specific GEO dataset including title, summary, and metadata.

   **Parameters:**

   * ``dataset_id`` (string) (required)
     GEO dataset ID (e.g., 'GDS1234', 'GSE12345')

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "geo_get_dataset_info",
          "arguments": {
              "dataset_id": "example_value"
          }
      }
      result = tu.run(query)


**geo_get_sample_info** (Type: GEOGetSampleInfo)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get sample information for a GEO dataset including sample characteristics and experimental condit...

.. dropdown:: geo_get_sample_info tool specification

   **Tool Information:**

   * **Name**: ``geo_get_sample_info``
   * **Type**: ``GEOGetSampleInfo``
   * **Description**: Get sample information for a GEO dataset including sample characteristics and experimental conditions.

   **Parameters:**

   * ``dataset_id`` (string) (required)
     GEO dataset ID (e.g., 'GDS1234', 'GSE12345')

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "geo_get_sample_info",
          "arguments": {
              "dataset_id": "example_value"
          }
      }
      result = tu.run(query)


**geo_search_datasets** (Type: GEOSearchDatasets)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search GEO datasets by query terms, organism, study type, or platform. Returns dataset IDs and ba...

.. dropdown:: geo_search_datasets tool specification

   **Tool Information:**

   * **Name**: ``geo_search_datasets``
   * **Type**: ``GEOSearchDatasets``
   * **Description**: Search GEO datasets by query terms, organism, study type, or platform. Returns dataset IDs and basic information.

   **Parameters:**

   * ``query`` (string) (optional)
     Search query terms (e.g., 'cancer', 'diabetes', 'microarray')

   * ``organism`` (string) (optional)
     Organism name (e.g., 'Homo sapiens', 'Mus musculus')

   * ``study_type`` (string) (optional)
     Type of study (e.g., 'Expression profiling by array', 'Expression profiling by high throughput sequencing')

   * ``platform`` (string) (optional)
     Platform used (e.g., 'GPL570', 'GPL96')

   * ``limit`` (integer) (optional)
     Maximum number of results to return

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "geo_search_datasets",
          "arguments": {
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
