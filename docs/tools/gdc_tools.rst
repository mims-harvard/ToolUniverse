Gdc Tools
=========

**Configuration File**: ``gdc_tools.json``
**Tool Type**: Local
**Tools Count**: 2

This page contains all tools defined in the ``gdc_tools.json`` configuration file.

Available Tools
---------------

**GDC_list_files** (Type: GDCFilesTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

List GDC files filtered by data_type and other fields. Use to identify downloadable artifacts (e....

.. dropdown:: GDC_list_files tool specification

   **Tool Information:**

   * **Name**: ``GDC_list_files``
   * **Type**: ``GDCFilesTool``
   * **Description**: List GDC files filtered by data_type and other fields. Use to identify downloadable artifacts (e.g., expression quantification) for analysis pipelines.

   **Parameters:**

   * ``data_type`` (string) (optional)
     Data type filter (e.g., 'Gene Expression Quantification').

   * ``size`` (integer) (optional)
     Number of results (1–100).

   * ``offset`` (integer) (optional)
     Offset for pagination (0-based).

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "GDC_list_files",
          "arguments": {
          }
      }
      result = tu.run(query)


**GDC_search_cases** (Type: GDCCasesTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search cancer cohort cases in NCI GDC by project and filters. Use to retrieve case-level metadata...

.. dropdown:: GDC_search_cases tool specification

   **Tool Information:**

   * **Name**: ``GDC_search_cases``
   * **Type**: ``GDCCasesTool``
   * **Description**: Search cancer cohort cases in NCI GDC by project and filters. Use to retrieve case-level metadata for cohort construction and downstream file queries.

   **Parameters:**

   * ``project_id`` (string) (optional)
     GDC project identifier (e.g., 'TCGA-BRCA').

   * ``size`` (integer) (optional)
     Number of results (1–100).

   * ``offset`` (integer) (optional)
     Offset for pagination (0-based).

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "GDC_search_cases",
          "arguments": {
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
