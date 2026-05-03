Dbpedia Tools
=============

**Configuration File**: ``dbpedia_tools.json``
**Tool Type**: Local
**Tools Count**: 1

This page contains all tools defined in the ``dbpedia_tools.json`` configuration file.

Available Tools
---------------

**DBpedia_SPARQL_query** (Type: DBpediaSPARQLTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Execute SPARQL queries against DBpedia to retrieve structured knowledge. DBpedia extracts structu...

.. dropdown:: DBpedia_SPARQL_query tool specification

   **Tool Information:**

   * **Name**: ``DBpedia_SPARQL_query``
   * **Type**: ``DBpediaSPARQLTool``
   * **Description**: Execute SPARQL queries against DBpedia to retrieve structured knowledge. DBpedia extracts structured information from Wikipedia and makes it available as linked data. This tool is particularly useful for querying information about people, places, organizations, works, and other entities, especially in humanities and social sciences domains. No API key required.

   **Parameters:**

   * ``sparql`` (string) (required)
     SPARQL query string to execute against DBpedia. Use SPARQL syntax to query entities, relationships, and properties. DBpedia uses different property names than Wikidata (e.g., dbo:abstract, dbo:birthDate, rdfs:label).

   * ``max_results`` (integer) (required)
     Optional result limit override. If not specified, uses the LIMIT clause in the SPARQL query or returns all results.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "DBpedia_SPARQL_query",
          "arguments": {
              "sparql": "example_value",
              "max_results": 10
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
