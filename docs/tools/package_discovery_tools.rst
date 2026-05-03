Package Discovery Tools
=======================

**Configuration File**: ``package_discovery_tools.json``
**Tool Type**: Local
**Tools Count**: 1

This page contains all tools defined in the ``package_discovery_tools.json`` configuration file.

Available Tools
---------------

**dynamic_package_discovery** (Type: DynamicPackageDiscovery)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Dynamically searches PyPI and evaluates packages based on requirements

.. dropdown:: dynamic_package_discovery tool specification

   **Tool Information:**

   * **Name**: ``dynamic_package_discovery``
   * **Type**: ``DynamicPackageDiscovery``
   * **Description**: Dynamically searches PyPI and evaluates packages based on requirements

   **Parameters:**

   * ``requirements`` (string) (required)
     Description of what the package should do

   * ``functionality`` (string) (optional)
     Specific functionality needed

   * ``constraints`` (object) (optional)
     Constraints (python version, license, etc.)

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "dynamic_package_discovery",
          "arguments": {
              "requirements": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
