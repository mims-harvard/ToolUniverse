Umls Tools
==========

**Configuration File**: ``umls_tools.json``
**Tool Type**: Local
**Tools Count**: 5

This page contains all tools defined in the ``umls_tools.json`` configuration file.

Available Tools
---------------

**icd_search_codes** (Type: UMLSRESTTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search for ICD-10 or ICD-11 codes using UMLS. Returns matching codes with descriptions. Requires ...

.. dropdown:: icd_search_codes tool specification

   **Tool Information:**

   * **Name**: ``icd_search_codes``
   * **Type**: ``UMLSRESTTool``
   * **Description**: Search for ICD-10 or ICD-11 codes using UMLS. Returns matching codes with descriptions. Requires free UMLS API key (register at https://uts.nlm.nih.gov/uts/). Set UMLS_API_KEY environment variable.

   **Parameters:**

   * ``query`` (string) (required)
     Search query (disease name, condition, or ICD code)

   * ``version`` (string) (optional)
     ICD version to search (ICD10CM for US clinical modification, ICD10 for international, ICD11 for ICD-11)

   * ``pageNumber`` (integer) (optional)
     Page number for pagination (default: 1)

   * ``pageSize`` (integer) (optional)
     Number of results per page (default: 25, max: 25)

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "icd_search_codes",
          "arguments": {
              "query": "example_value"
          }
      }
      result = tu.run(query)


**loinc_search_codes** (Type: UMLSRESTTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search for LOINC (Logical Observation Identifiers Names and Codes) codes using UMLS. Returns matc...

.. dropdown:: loinc_search_codes tool specification

   **Tool Information:**

   * **Name**: ``loinc_search_codes``
   * **Type**: ``UMLSRESTTool``
   * **Description**: Search for LOINC (Logical Observation Identifiers Names and Codes) codes using UMLS. Returns matching codes with descriptions. Requires free UMLS API key (register at https://uts.nlm.nih.gov/uts/). Set UMLS_API_KEY environment variable.

   **Parameters:**

   * ``query`` (string) (required)
     Search query (test name, component, or LOINC code)

   * ``pageNumber`` (integer) (optional)
     Page number for pagination (default: 1)

   * ``pageSize`` (integer) (optional)
     Number of results per page (default: 25, max: 25)

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "loinc_search_codes",
          "arguments": {
              "query": "example_value"
          }
      }
      result = tu.run(query)


**snomed_search_concepts** (Type: UMLSRESTTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search for SNOMED CT concepts using UMLS. Returns matching concepts with descriptions. Requires f...

.. dropdown:: snomed_search_concepts tool specification

   **Tool Information:**

   * **Name**: ``snomed_search_concepts``
   * **Type**: ``UMLSRESTTool``
   * **Description**: Search for SNOMED CT concepts using UMLS. Returns matching concepts with descriptions. Requires free UMLS API key (register at https://uts.nlm.nih.gov/uts/). Set UMLS_API_KEY environment variable.

   **Parameters:**

   * ``query`` (string) (required)
     Search query (concept name or SNOMED CT code)

   * ``pageNumber`` (integer) (optional)
     Page number for pagination (default: 1)

   * ``pageSize`` (integer) (optional)
     Number of results per page (default: 25, max: 25)

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "snomed_search_concepts",
          "arguments": {
              "query": "example_value"
          }
      }
      result = tu.run(query)


**umls_get_concept_details** (Type: UMLSRESTTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get detailed information about a UMLS concept by its CUI (Concept Unique Identifier). Returns con...

.. dropdown:: umls_get_concept_details tool specification

   **Tool Information:**

   * **Name**: ``umls_get_concept_details``
   * **Type**: ``UMLSRESTTool``
   * **Description**: Get detailed information about a UMLS concept by its CUI (Concept Unique Identifier). Returns concept details, atoms, definitions, relations, and mappings to other terminologies. Requires free UMLS API key (register at https://uts.nlm.nih.gov/uts/). Set UMLS_API_KEY environment variable.

   **Parameters:**

   * ``cui`` (string) (required)
     UMLS Concept Unique Identifier (CUI, e.g., 'C0004096')

   * ``pageNumber`` (integer) (optional)
     Page number for pagination (default: 1)

   * ``pageSize`` (integer) (optional)
     Number of results per page (default: 25)

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "umls_get_concept_details",
          "arguments": {
              "cui": "example_value"
          }
      }
      result = tu.run(query)


**umls_search_concepts** (Type: UMLSRESTTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search for concepts in UMLS (Unified Medical Language System) using concept names or terms. UMLS ...

.. dropdown:: umls_search_concepts tool specification

   **Tool Information:**

   * **Name**: ``umls_search_concepts``
   * **Type**: ``UMLSRESTTool``
   * **Description**: Search for concepts in UMLS (Unified Medical Language System) using concept names or terms. UMLS provides access to multiple medical terminologies including SNOMED CT, ICD-10, ICD-11, LOINC, RxNorm, and more. Requires free UMLS API key (register at https://uts.nlm.nih.gov/uts/). Set UMLS_API_KEY environment variable.

   **Parameters:**

   * ``query`` (string) (required)
     Search query (concept name or term)

   * ``sabs`` (string) (optional)
     Source abbreviation(s) to filter by (e.g., 'SNOMEDCT_US', 'ICD10CM', 'LOINC', 'RXNORM'). Comma-separated for multiple sources. Optional, searches all sources if not specified.

   * ``pageNumber`` (integer) (optional)
     Page number for pagination (default: 1)

   * ``pageSize`` (integer) (optional)
     Number of results per page (default: 25, max: 25)

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "umls_search_concepts",
          "arguments": {
              "query": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
