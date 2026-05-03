Health Disparities Tools
========================

**Configuration File**: ``health_disparities_tools.json``
**Tool Type**: Local
**Tools Count**: 2

This page contains all tools defined in the ``health_disparities_tools.json`` configuration file.

Available Tools
---------------

**health_disparities_get_county_rankings_info** (Type: HealthDisparitiesTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get information about County Health Rankings data. County Health Rankings provides county-level h...

.. dropdown:: health_disparities_get_county_rankings_info tool specification

   **Tool Information:**

   * **Name**: ``health_disparities_get_county_rankings_info``
   * **Type**: ``HealthDisparitiesTool``
   * **Description**: Get information about County Health Rankings data. County Health Rankings provides county-level health data. This tool provides information about available datasets and access methods. Note: Data may be available as downloadable files or through their website.

   **Parameters:**

   * ``year`` (integer) (optional)
     Optional year for County Health Rankings data

   * ``state`` (string) (optional)
     Optional state abbreviation (e.g., 'CA', 'NY') to filter by state

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "health_disparities_get_county_rankings_info",
          "arguments": {
          }
      }
      result = tu.run(query)


**health_disparities_get_svi_info** (Type: HealthDisparitiesTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get information about CDC Social Vulnerability Index (SVI) data. SVI data is typically available ...

.. dropdown:: health_disparities_get_svi_info tool specification

   **Tool Information:**

   * **Name**: ``health_disparities_get_svi_info``
   * **Type**: ``HealthDisparitiesTool``
   * **Description**: Get information about CDC Social Vulnerability Index (SVI) data. SVI data is typically available as downloadable CSV files from the CDC ATSDR website. This tool provides information about available SVI datasets and download links. Note: Actual data retrieval may require downloading CSV files.

   **Parameters:**

   * ``year`` (integer) (optional)
     Optional year to filter SVI data (e.g., 2020, 2018, 2016). SVI is released every 2 years.

   * ``geography`` (string) (optional)
     Geographic level: 'county' for county-level, 'tract' for census tract, 'state' for state-level

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "health_disparities_get_svi_info",
          "arguments": {
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
