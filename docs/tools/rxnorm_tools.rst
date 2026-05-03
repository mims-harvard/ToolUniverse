Rxnorm Tools
============

**Configuration File**: ``rxnorm_tools.json``
**Tool Type**: Local
**Tools Count**: 1

This page contains all tools defined in the ``rxnorm_tools.json`` configuration file.

Available Tools
---------------

**RxNorm_get_drug_names** (Type: RxNormTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get RXCUI (RxNorm Concept Unique Identifier) and all associated names (generic names, brand names...

.. dropdown:: RxNorm_get_drug_names tool specification

   **Tool Information:**

   * **Name**: ``RxNorm_get_drug_names``
   * **Type**: ``RxNormTool``
   * **Description**: Get RXCUI (RxNorm Concept Unique Identifier) and all associated names (generic names, brand names, synonyms, etc.) for a drug by its name. This tool uses the RxNorm API from the U.S. National Library of Medicine (NLM) to standardize drug names.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug to search for (e.g., 'ibuprofen', 'aspirin', 'acetaminophen'). Can be a generic name, brand name, or any drug name variant.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "RxNorm_get_drug_names",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
