Nhanes Tools
============

**Configuration File**: ``nhanes_tools.json``
**Tool Type**: Local
**Tools Count**: 2

This page contains all tools defined in the ``nhanes_tools.json`` configuration file.

Available Tools
---------------

**nhanes_get_dataset_info** (Type: NHANESTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get information about NHANES (National Health and Nutrition Examination Survey) datasets. NHANES ...

.. dropdown:: nhanes_get_dataset_info tool specification

   **Tool Information:**

   * **Name**: ``nhanes_get_dataset_info``
   * **Type**: ``NHANESTool``
   * **Description**: Get information about NHANES (National Health and Nutrition Examination Survey) datasets. NHANES data is typically available as downloadable files (SAS, XPT formats) from the CDC website. This tool provides information about available datasets, years, and download links. Note: Actual data retrieval may require downloading and converting files.

   **Parameters:**

   * ``year`` (string) (optional)
     NHANES cycle/year (e.g., '2017-2018', '2015-2016', '2013-2014')

   * ``component`` (string) (optional)
     Optional component type to filter datasets

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "nhanes_get_dataset_info",
          "arguments": {
          }
      }
      result = tu.run(query)


**nhanes_search_datasets** (Type: NHANESTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search for NHANES datasets by keyword. Returns information about matching datasets including down...

.. dropdown:: nhanes_search_datasets tool specification

   **Tool Information:**

   * **Name**: ``nhanes_search_datasets``
   * **Type**: ``NHANESTool``
   * **Description**: Search for NHANES datasets by keyword. Returns information about matching datasets including download links. Note: NHANES data files are typically in SAS/XPT format and may require conversion tools.

   **Parameters:**

   * ``search_term`` (string) (optional)
     Search term to find datasets (e.g., 'glucose', 'blood pressure', 'diabetes')

   * ``year`` (string) (optional)
     Optional NHANES cycle to filter (e.g., '2017-2018')

   * ``limit`` (integer) (optional)
     Maximum number of results (default: 20)

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "nhanes_search_datasets",
          "arguments": {
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
