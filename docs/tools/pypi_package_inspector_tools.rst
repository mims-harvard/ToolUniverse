Pypi Package Inspector Tools
============================

**Configuration File**: ``pypi_package_inspector_tools.json``
**Tool Type**: Local
**Tools Count**: 1

This page contains all tools defined in the ``pypi_package_inspector_tools.json`` configuration file.

Available Tools
---------------

**PyPIPackageInspector** (Type: PyPIPackageInspector)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Extracts comprehensive package information from PyPI and GitHub for quality evaluation. Provides ...

.. dropdown:: PyPIPackageInspector tool specification

   **Tool Information:**

   * **Name**: ``PyPIPackageInspector``
   * **Type**: ``PyPIPackageInspector``
   * **Description**: Extracts comprehensive package information from PyPI and GitHub for quality evaluation. Provides detailed metrics on popularity (downloads, stars, forks), maintenance (release frequency, recent activity), documentation quality, Python version compatibility, and security indicators. Returns an overall quality score (0-100) with breakdown by category.

   **Parameters:**

   * ``package_name`` (string) (required)
     Name of the Python package to inspect on PyPI (e.g., 'requests', 'numpy', 'pandas')

   * ``include_github`` (boolean) (optional)
     Whether to fetch GitHub repository statistics (stars, forks, issues, last push). Requires package to have GitHub URL in metadata.

   * ``include_downloads`` (boolean) (optional)
     Whether to fetch download statistics from pypistats.org (downloads per day/week/month)

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "PyPIPackageInspector",
          "arguments": {
              "package_name": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
