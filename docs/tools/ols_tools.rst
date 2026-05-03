Ols Tools
=========

**Configuration File**: ``ols_tools.json``
**Tool Type**: Local
**Tools Count**: 7

This page contains all tools defined in the ``ols_tools.json`` configuration file.

Available Tools
---------------

**ols_find_similar_terms** (Type: OLSTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Find similar terms using LLM-based similarity

.. dropdown:: ols_find_similar_terms tool specification

   **Tool Information:**

   * **Name**: ``ols_find_similar_terms``
   * **Type**: ``OLSTool``
   * **Description**: Find similar terms using LLM-based similarity

   **Parameters:**

   * ``operation`` (string) (required)
     The operation to perform (find_similar_terms)

   * ``term_iri`` (string) (required)
     The IRI of the term to find similar terms for

   * ``ontology`` (string) (required)
     The ontology ID

   * ``size`` (integer) (optional)
     Number of similar terms to return (default: 10)

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "ols_find_similar_terms",
          "arguments": {
              "operation": "example_value",
              "term_iri": "example_value",
              "ontology": "example_value"
          }
      }
      result = tu.run(query)


**ols_get_ontology_info** (Type: OLSTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get detailed information about an ontology

.. dropdown:: ols_get_ontology_info tool specification

   **Tool Information:**

   * **Name**: ``ols_get_ontology_info``
   * **Type**: ``OLSTool``
   * **Description**: Get detailed information about an ontology

   **Parameters:**

   * ``operation`` (string) (required)
     The operation to perform (get_ontology_info)

   * ``ontology_id`` (string) (required)
     The ID of the ontology to retrieve

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "ols_get_ontology_info",
          "arguments": {
              "operation": "example_value",
              "ontology_id": "example_value"
          }
      }
      result = tu.run(query)


**ols_get_term_ancestors** (Type: OLSTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get ancestor terms of a specific term in an ontology

.. dropdown:: ols_get_term_ancestors tool specification

   **Tool Information:**

   * **Name**: ``ols_get_term_ancestors``
   * **Type**: ``OLSTool``
   * **Description**: Get ancestor terms of a specific term in an ontology

   **Parameters:**

   * ``operation`` (string) (required)
     The operation to perform (get_term_ancestors)

   * ``term_iri`` (string) (required)
     The IRI of the term to retrieve ancestors for

   * ``ontology`` (string) (required)
     The ontology ID

   * ``include_obsolete`` (boolean) (optional)
     Include obsolete terms (default: false)

   * ``size`` (integer) (optional)
     Number of results to return (default: 20)

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "ols_get_term_ancestors",
          "arguments": {
              "operation": "example_value",
              "term_iri": "example_value",
              "ontology": "example_value"
          }
      }
      result = tu.run(query)


**ols_get_term_children** (Type: OLSTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get child terms of a specific term in an ontology

.. dropdown:: ols_get_term_children tool specification

   **Tool Information:**

   * **Name**: ``ols_get_term_children``
   * **Type**: ``OLSTool``
   * **Description**: Get child terms of a specific term in an ontology

   **Parameters:**

   * ``operation`` (string) (required)
     The operation to perform (get_term_children)

   * ``term_iri`` (string) (required)
     The IRI of the term to retrieve children for

   * ``ontology`` (string) (required)
     The ontology ID

   * ``include_obsolete`` (boolean) (optional)
     Include obsolete terms (default: false)

   * ``size`` (integer) (optional)
     Number of results to return (default: 20)

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "ols_get_term_children",
          "arguments": {
              "operation": "example_value",
              "term_iri": "example_value",
              "ontology": "example_value"
          }
      }
      result = tu.run(query)


**ols_get_term_info** (Type: OLSTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get detailed information about a specific term in OLS

.. dropdown:: ols_get_term_info tool specification

   **Tool Information:**

   * **Name**: ``ols_get_term_info``
   * **Type**: ``OLSTool``
   * **Description**: Get detailed information about a specific term in OLS

   **Parameters:**

   * ``operation`` (string) (required)
     The operation to perform (get_term_info)

   * ``id`` (string) (required)
     The ID or IRI of the term to retrieve

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "ols_get_term_info",
          "arguments": {
              "operation": "example_value",
              "id": "example_value"
          }
      }
      result = tu.run(query)


**ols_search_ontologies** (Type: OLSTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search for ontologies in OLS

.. dropdown:: ols_search_ontologies tool specification

   **Tool Information:**

   * **Name**: ``ols_search_ontologies``
   * **Type**: ``OLSTool``
   * **Description**: Search for ontologies in OLS

   **Parameters:**

   * ``operation`` (string) (required)
     The operation to perform (search_ontologies)

   * ``search`` (string) (optional)
     Search query for ontologies (optional)

   * ``page`` (integer) (optional)
     Page number (default: 0)

   * ``size`` (integer) (optional)
     Number of results per page (default: 20)

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "ols_search_ontologies",
          "arguments": {
              "operation": "example_value"
          }
      }
      result = tu.run(query)


**ols_search_terms** (Type: OLSTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search for terms in OLS (Ontology Lookup Service)

.. dropdown:: ols_search_terms tool specification

   **Tool Information:**

   * **Name**: ``ols_search_terms``
   * **Type**: ``OLSTool``
   * **Description**: Search for terms in OLS (Ontology Lookup Service)

   **Parameters:**

   * ``operation`` (string) (required)
     The operation to perform (search_terms)

   * ``query`` (string) (required)
     The search query for terms

   * ``rows`` (integer) (optional)
     Number of results to return (default: 10)

   * ``ontology`` (string) (optional)
     Filter by specific ontology (optional)

   * ``exact_match`` (boolean) (optional)
     Search for exact matches only (default: false)

   * ``include_obsolete`` (boolean) (optional)
     Include obsolete terms (default: false)

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "ols_search_terms",
          "arguments": {
              "operation": "example_value",
              "query": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
