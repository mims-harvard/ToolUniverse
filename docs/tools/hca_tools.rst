Hca Tools
=========

**Configuration File**: ``hca_tools.json``
**Tool Type**: Local
**Tools Count**: 2

This page contains all tools defined in the ``hca_tools.json`` configuration file.

Available Tools
---------------

**hca_get_file_manifest** (Type: HCATool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieves a list of downloadable files for a specific Human Cell Atlas (HCA) project identified b...

.. dropdown:: hca_get_file_manifest tool specification

   **Tool Information:**

   * **Name**: ``hca_get_file_manifest``
   * **Type**: ``HCATool``
   * **Description**: Retrieves a list of downloadable files for a specific Human Cell Atlas (HCA) project identified by its Project ID.

   **Parameters:**

   * ``action`` (string) (required)
     The specific action to perform. Must be set to 'get_file_manifest'.

   * ``project_id`` (string) (required)
     The unique UUID of the project (entryId) for which to retrieve files. This ID is typically obtained from the 'hca_search_projects' tool.

   * ``limit`` (integer) (optional)
     The maximum number of files to list. The default is 10.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "hca_get_file_manifest",
          "arguments": {
              "action": "example_value",
              "project_id": "example_value"
          }
      }
      result = tu.run(query)


**hca_search_projects** (Type: HCATool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Searches for single-cell projects in the Human Cell Atlas (HCA) Data Coordination Platform (DCP)....

.. dropdown:: hca_search_projects tool specification

   **Tool Information:**

   * **Name**: ``hca_search_projects``
   * **Type**: ``HCATool``
   * **Description**: Searches for single-cell projects in the Human Cell Atlas (HCA) Data Coordination Platform (DCP). This tool allows filtering projects based on specific organs and disease states.

   **Parameters:**

   * ``action`` (string) (required)
     The specific action to perform. Must be set to 'search_projects'.

   * ``organ`` (string) (optional)
     The organ to filter projects by. Examples include 'heart', 'liver', 'brain', 'kidney'. This field is optional.

   * ``disease`` (string) (optional)
     The disease state to filter by. Examples include 'normal', 'cancer', 'covid-19'. This field is optional.

   * ``limit`` (integer) (optional)
     The maximum number of projects to return. The default is 10. Use this to control the size of the result set.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "hca_search_projects",
          "arguments": {
              "action": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
