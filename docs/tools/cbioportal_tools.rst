Cbioportal Tools
================

**Configuration File**: ``cbioportal_tools.json``
**Tool Type**: Local
**Tools Count**: 2

This page contains all tools defined in the ``cbioportal_tools.json`` configuration file.

Available Tools
---------------

**cBioPortal_get_cancer_studies** (Type: CBioPortalRESTTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get list of cancer studies from cBioPortal

.. dropdown:: cBioPortal_get_cancer_studies tool specification

   **Tool Information:**

   * **Name**: ``cBioPortal_get_cancer_studies``
   * **Type**: ``CBioPortalRESTTool``
   * **Description**: Get list of cancer studies from cBioPortal

   **Parameters:**

   * ``limit`` (integer) (optional)
     Number of studies to return

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "cBioPortal_get_cancer_studies",
          "arguments": {
          }
      }
      result = tu.run(query)


**cBioPortal_get_mutations** (Type: CBioPortalRESTTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get mutation data for specific genes in a cancer study

.. dropdown:: cBioPortal_get_mutations tool specification

   **Tool Information:**

   * **Name**: ``cBioPortal_get_mutations``
   * **Type**: ``CBioPortalRESTTool``
   * **Description**: Get mutation data for specific genes in a cancer study

   **Parameters:**

   * ``study_id`` (string) (required)
     Cancer study ID

   * ``gene_list`` (string) (required)
     Comma-separated gene symbols

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "cBioPortal_get_mutations",
          "arguments": {
              "study_id": "example_value",
              "gene_list": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
