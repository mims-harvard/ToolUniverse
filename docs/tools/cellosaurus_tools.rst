Cellosaurus Tools
=================

**Configuration File**: ``cellosaurus_tools.json``
**Tool Type**: Local
**Tools Count**: 3

This page contains all tools defined in the ``cellosaurus_tools.json`` configuration file.

Available Tools
---------------

**cellosaurus_get_cell_line_info** (Type: CellosaurusGetCellLineInfoTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get detailed information about a specific cell line using its Cellosaurus accession number (``CVCL_``...).

.. dropdown:: cellosaurus_get_cell_line_info tool specification

   **Tool Information:**

   * **Name**: ``cellosaurus_get_cell_line_info``
   * **Type**: ``CellosaurusGetCellLineInfoTool``
   * **Description**: Get detailed information about a specific cell line using its Cellosaurus accession number (``CVCL_`` format).

   **Parameters:**

   * ``accession`` (string) (required)
     Cellosaurus accession number (must start with ``CVCL_``)

   * ``format`` (string) (required)
     Response format

   * ``fields`` (array) (required)
     Specific fields to retrieve (e.g., ['id', 'ox', 'char']). If not specified, all fields are returned.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "cellosaurus_get_cell_line_info",
          "arguments": {
              "accession": "example_value",
              "format": "example_value",
              "fields": ["item1", "item2"]
          }
      }
      result = tu.run(query)


**cellosaurus_query_converter** (Type: CellosaurusQueryConverterTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Convert natural language queries to Solr syntax for Cellosaurus API searches. Uses semantic simil...

.. dropdown:: cellosaurus_query_converter tool specification

   **Tool Information:**

   * **Name**: ``cellosaurus_query_converter``
   * **Type**: ``CellosaurusQueryConverterTool``
   * **Description**: Convert natural language queries to Solr syntax for Cellosaurus API searches. Uses semantic similarity to map terms to appropriate fields.

   **Parameters:**

   * ``query`` (string) (required)
     Natural language query to convert to Solr syntax (e.g., 'human cancer cells', 'HeLa cells from lung tissue')

   * ``include_explanation`` (boolean) (required)
     Whether to include detailed explanation of the conversion process

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "cellosaurus_query_converter",
          "arguments": {
              "query": "example_value",
              "include_explanation": true
          }
      }
      result = tu.run(query)


**cellosaurus_search_cell_lines** (Type: CellosaurusSearchTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search Cellosaurus cell lines using the /search/cell-line endpoint. Supports Solr query syntax fo...

.. dropdown:: cellosaurus_search_cell_lines tool specification

   **Tool Information:**

   * **Name**: ``cellosaurus_search_cell_lines``
   * **Type**: ``CellosaurusSearchTool``
   * **Description**: Search Cellosaurus cell lines using the /search/cell-line endpoint. Supports Solr query syntax for precise field-based searches.

   **Parameters:**

   * ``q`` (string) (required)
     Search query. Supports Solr syntax for field-specific searches (e.g., 'id:HeLa', 'ox:9606', 'char:cancer'). See https://api.cellosaurus.org/api-fields for available fields.

   * ``offset`` (integer) (required)
     Number of results to skip (for pagination)

   * ``size`` (integer) (required)
     Maximum number of results to return

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "cellosaurus_search_cell_lines",
          "arguments": {
              "q": "example_value",
              "offset": 10,
              "size": 10
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
