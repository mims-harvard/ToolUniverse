Cdc Tools
=========

**Configuration File**: ``cdc_tools.json``
**Tool Type**: Local
**Tools Count**: 2

This page contains all tools defined in the ``cdc_tools.json`` configuration file.

Available Tools
---------------

**cdc_data_get_dataset** (Type: CDCRESTTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve data from a specific CDC dataset on Data.CDC.gov. Requires a dataset ID (view ID) which ...

.. dropdown:: cdc_data_get_dataset tool specification

   **Tool Information:**

   * **Name**: ``cdc_data_get_dataset``
   * **Type**: ``CDCRESTTool``
   * **Description**: Retrieve data from a specific CDC dataset on Data.CDC.gov. Requires a dataset ID (view ID) which can be found using cdc_data_search_datasets.

   **Parameters:**

   * ``dataset_id`` (string) (required)
     Dataset ID (view ID) from Data.CDC.gov (e.g., 'p5x4-u35c')

   * ``limit`` (integer) (optional)
     Maximum number of rows to return (default: 100, max: 50000)

   * ``offset`` (integer) (optional)
     Number of rows to skip for pagination (default: 0)

   * ``where_clause`` (string) (optional)
     Optional SoQL WHERE clause for filtering (e.g., "year = '2020'")

   * ``order_by`` (string) (optional)
     Optional column name to order by (e.g., 'year')

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "cdc_data_get_dataset",
          "arguments": {
              "dataset_id": "example_value"
          }
      }
      result = tu.run(query)


**cdc_data_search_datasets** (Type: CDCRESTTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search for datasets on Data.CDC.gov (CDC's Socrata-based open data portal). Returns a list of ava...

.. dropdown:: cdc_data_search_datasets tool specification

   **Tool Information:**

   * **Name**: ``cdc_data_search_datasets``
   * **Type**: ``CDCRESTTool``
   * **Description**: Search for datasets on Data.CDC.gov (CDC's Socrata-based open data portal). Returns a list of available datasets matching search criteria. Use this to discover datasets before querying data.

   **Parameters:**

   * ``search_query`` (string) (optional)
     Search term to find datasets (e.g., 'mortality', 'vaccination', 'covid')

   * ``category`` (string) (optional)
     Optional category filter (e.g., 'Health', 'Public Safety')

   * ``limit`` (integer) (optional)
     Maximum number of datasets to return (default: 50, max: 1000)

   * ``offset`` (integer) (optional)
     Number of results to skip for pagination (default: 0)

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "cdc_data_search_datasets",
          "arguments": {
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
