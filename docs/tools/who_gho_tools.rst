Who Gho Tools
=============

**Configuration File**: ``who_gho_tools.json``
**Tool Type**: Local
**Tools Count**: 2

This page contains all tools defined in the ``who_gho_tools.json`` configuration file.

Available Tools
---------------

**who_gho_get_data** (Type: WHOGHORESTTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve health data from WHO GHO for a specific indicator. Supports filtering by country, year, ...

.. dropdown:: who_gho_get_data tool specification

   **Tool Information:**

   * **Name**: ``who_gho_get_data``
   * **Type**: ``WHOGHORESTTool``
   * **Description**: Retrieve health data from WHO GHO for a specific indicator. Supports filtering by country, year, and other dimensions. Returns actual health statistics and measurements.

   **Parameters:**

   * ``indicator_code`` (string) (required)
     The WHO GHO indicator code (e.g., 'WHOSIS_000001', 'Adult_curr_cig_smoking')

   * ``country_code`` (string) (optional)
     ISO 3-letter country code (e.g., 'USA', 'GBR', 'CHN'). Optional, returns all countries if not specified.

   * ``year`` (integer) (optional)
     Year to filter data (e.g., 2020). Optional, returns all years if not specified.

   * ``top`` (integer) (optional)
     Maximum number of results to return (default: 100, max: 1000)

   * ``skip`` (integer) (optional)
     Number of results to skip for pagination (default: 0)

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "who_gho_get_data",
          "arguments": {
              "indicator_code": "example_value"
          }
      }
      result = tu.run(query)


**who_gho_query_health_data** (Type: WHOGHOQueryTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Answer generic health questions using natural language queries. Automatically searches for releva...

.. dropdown:: who_gho_query_health_data tool specification

   **Tool Information:**

   * **Name**: ``who_gho_query_health_data``
   * **Type**: ``WHOGHOQueryTool``
   * **Description**: Answer generic health questions using natural language queries. Automatically searches for relevant indicators, retrieves health data, and returns formatted answers with actual values. Example: 'smoking rate in USA 2020' returns the actual smoking percentage.

   **Parameters:**

   * ``query`` (string) (required)
     Natural language query (e.g., 'smoking rate in USA', 'diabetes prevalence in China 2020')

   * ``country_code`` (string) (optional)
     ISO 3-letter country code (e.g., 'USA', 'GBR'). Optional, will be extracted from query if not provided.

   * ``year`` (integer) (optional)
     Year for data (e.g., 2020). Optional, will be extracted from query if not provided.

   * ``top`` (integer) (optional)
     Maximum number of results to return (default: 5)

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "who_gho_query_health_data",
          "arguments": {
              "query": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
