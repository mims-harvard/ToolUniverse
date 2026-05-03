Kegg Tools
==========

**Configuration File**: ``kegg_tools.json``
**Tool Type**: Local
**Tools Count**: 5

This page contains all tools defined in the ``kegg_tools.json`` configuration file.

Available Tools
---------------

**kegg_find_genes** (Type: KEGGFindGenes)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Find genes in KEGG database by keyword. Can search across all organisms or within a specific orga...

.. dropdown:: kegg_find_genes tool specification

   **Tool Information:**

   * **Name**: ``kegg_find_genes``
   * **Type**: ``KEGGFindGenes``
   * **Description**: Find genes in KEGG database by keyword. Can search across all organisms or within a specific organism.

   **Parameters:**

   * ``keyword`` (string) (required)
     Search keyword for gene names or descriptions

   * ``organism`` (string) (optional)
     Organism code (e.g., 'hsa' for human, 'mmu' for mouse). Optional - searches all organisms if not specified

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "kegg_find_genes",
          "arguments": {
              "keyword": "example_value"
          }
      }
      result = tu.run(query)


**kegg_get_gene_info** (Type: KEGGGetGeneInfo)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get detailed gene information from KEGG by gene ID. Returns gene data including sequence, functio...

.. dropdown:: kegg_get_gene_info tool specification

   **Tool Information:**

   * **Name**: ``kegg_get_gene_info``
   * **Type**: ``KEGGGetGeneInfo``
   * **Description**: Get detailed gene information from KEGG by gene ID. Returns gene data including sequence, function, and pathway associations.

   **Parameters:**

   * ``gene_id`` (string) (required)
     KEGG gene identifier (e.g., 'hsa:348', 'hsa:3480')

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "kegg_get_gene_info",
          "arguments": {
              "gene_id": "example_value"
          }
      }
      result = tu.run(query)


**kegg_get_pathway_info** (Type: KEGGGetPathwayInfo)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get detailed pathway information from KEGG by pathway ID. Returns pathway data including genes, c...

.. dropdown:: kegg_get_pathway_info tool specification

   **Tool Information:**

   * **Name**: ``kegg_get_pathway_info``
   * **Type**: ``KEGGGetPathwayInfo``
   * **Description**: Get detailed pathway information from KEGG by pathway ID. Returns pathway data including genes, compounds, and reactions.

   **Parameters:**

   * ``pathway_id`` (string) (required)
     KEGG pathway identifier (e.g., 'hsa00010', 'path:hsa00010')

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "kegg_get_pathway_info",
          "arguments": {
              "pathway_id": "example_value"
          }
      }
      result = tu.run(query)


**kegg_list_organisms** (Type: KEGGListOrganisms)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

List all available organisms in the KEGG database. Returns organism codes, names, and descriptions.

.. dropdown:: kegg_list_organisms tool specification

   **Tool Information:**

   * **Name**: ``kegg_list_organisms``
   * **Type**: ``KEGGListOrganisms``
   * **Description**: List all available organisms in the KEGG database. Returns organism codes, names, and descriptions.

   **Parameters:**

   No parameters required.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "kegg_list_organisms",
          "arguments": {
          }
      }
      result = tu.run(query)


**kegg_search_pathway** (Type: KEGGSearchPathway)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search KEGG pathways by keyword. Returns pathway IDs and descriptions matching the search term.

.. dropdown:: kegg_search_pathway tool specification

   **Tool Information:**

   * **Name**: ``kegg_search_pathway``
   * **Type**: ``KEGGSearchPathway``
   * **Description**: Search KEGG pathways by keyword. Returns pathway IDs and descriptions matching the search term.

   **Parameters:**

   * ``keyword`` (string) (required)
     Search keyword for pathway names or descriptions (e.g., 'diabetes', 'metabolism')

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "kegg_search_pathway",
          "arguments": {
              "keyword": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
