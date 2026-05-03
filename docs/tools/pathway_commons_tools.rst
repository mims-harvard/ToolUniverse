Pathway Commons Tools
=====================

**Configuration File**: ``pathway_commons_tools.json``
**Tool Type**: Local
**Tools Count**: 2

This page contains all tools defined in the ``pathway_commons_tools.json`` configuration file.

Available Tools
---------------

**pc_get_interactions** (Type: PathwayCommonsTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieves the interaction network (neighborhood) for a specified list of genes. Returns interacti...

.. dropdown:: pc_get_interactions tool specification

   **Tool Information:**

   * **Name**: ``pc_get_interactions``
   * **Type**: ``PathwayCommonsTool``
   * **Description**: Retrieves the interaction network (neighborhood) for a specified list of genes. Returns interactions in Simple Interaction Format (SIF).

   **Parameters:**

   * ``action`` (string) (required)
     The specific action to perform. Must be set to 'get_interaction_graph'.

   * ``gene_list`` (array) (required)
     A list of gene symbols (e.g., ['TP53', 'MDM2']) to query interactions for.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "pc_get_interactions",
          "arguments": {
              "action": "example_value",
              "gene_list": ["item1", "item2"]
          }
      }
      result = tu.run(query)


**pc_search_pathways** (Type: PathwayCommonsTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Searches for biological pathways in Pathway Commons (PC2). Use this tool to find pathways related...

.. dropdown:: pc_search_pathways tool specification

   **Tool Information:**

   * **Name**: ``pc_search_pathways``
   * **Type**: ``PathwayCommonsTool``
   * **Description**: Searches for biological pathways in Pathway Commons (PC2). Use this tool to find pathways related to specific keywords, such as 'p53' or 'apoptosis'.

   **Parameters:**

   * ``action`` (string) (required)
     The specific action to perform. Must be set to 'search_pathways'.

   * ``keyword`` (string) (required)
     The search keyword to identify pathways. Examples include specific genes ('p53'), processes ('apoptosis'), or diseases.

   * ``datasource`` (string) (optional)
     Filter results by the original data source (e.g., 'reactome', 'kegg', 'panther'). This helps narrow down results to specific databases.

   * ``limit`` (integer) (optional)
     The maximum number of pathway results to return. The default is 10.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "pc_search_pathways",
          "arguments": {
              "action": "example_value",
              "keyword": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
