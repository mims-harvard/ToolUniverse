Interpro Tools
==============

**Configuration File**: ``interpro_tools.json``
**Tool Type**: Local
**Tools Count**: 3

This page contains all tools defined in the ``interpro_tools.json`` configuration file.

Available Tools
---------------

**InterPro_get_domain_details** (Type: InterProRESTTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get detailed information about a specific InterPro domain entry including description, hierarchy,...

.. dropdown:: InterPro_get_domain_details tool specification

   **Tool Information:**

   * **Name**: ``InterPro_get_domain_details``
   * **Type**: ``InterProRESTTool``
   * **Description**: Get detailed information about a specific InterPro domain entry including description, hierarchy, and member databases.

   **Parameters:**

   * ``accession`` (string) (required)
     InterPro accession ID (e.g., IPR000719, IPR000719)

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "InterPro_get_domain_details",
          "arguments": {
              "accession": "example_value"
          }
      }
      result = tu.run(query)


**InterPro_get_protein_domains** (Type: InterProRESTTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get protein domain annotations from InterPro database using UniProt protein ID. Returns domain fa...

.. dropdown:: InterPro_get_protein_domains tool specification

   **Tool Information:**

   * **Name**: ``InterPro_get_protein_domains``
   * **Type**: ``InterProRESTTool``
   * **Description**: Get protein domain annotations from InterPro database using UniProt protein ID. Returns domain families, signatures, and functional annotations.

   **Parameters:**

   * ``protein_id`` (string) (required)
     UniProt protein ID (e.g., P05067, Q9Y6K9)

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "InterPro_get_protein_domains",
          "arguments": {
              "protein_id": "example_value"
          }
      }
      result = tu.run(query)


**InterPro_search_domains** (Type: InterProRESTTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search InterPro database for protein domains and families by name or accession. Returns matching ...

.. dropdown:: InterPro_search_domains tool specification

   **Tool Information:**

   * **Name**: ``InterPro_search_domains``
   * **Type**: ``InterProRESTTool``
   * **Description**: Search InterPro database for protein domains and families by name or accession. Returns matching domain entries with metadata.

   **Parameters:**

   * ``query`` (string) (required)
     Domain name, accession, or search term (e.g., 'kinase', 'IPR000719')

   * ``size`` (integer) (optional)
     Number of results to return (default: 20, max: 100)

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "InterPro_search_domains",
          "arguments": {
              "query": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
