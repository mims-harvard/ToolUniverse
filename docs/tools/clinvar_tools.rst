Clinvar Tools
=============

**Configuration File**: ``clinvar_tools.json``
**Tool Type**: Local
**Tools Count**: 3

This page contains all tools defined in the ``clinvar_tools.json`` configuration file.

Available Tools
---------------

**clinvar_get_clinical_significance** (Type: ClinVarGetClinicalSignificance)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get clinical significance information for a variant from ClinVar. Returns pathogenicity classific...

.. dropdown:: clinvar_get_clinical_significance tool specification

   **Tool Information:**

   * **Name**: ``clinvar_get_clinical_significance``
   * **Type**: ``ClinVarGetClinicalSignificance``
   * **Description**: Get clinical significance information for a variant from ClinVar. Returns pathogenicity classification and clinical interpretations.

   **Parameters:**

   * ``variant_id`` (string) (required)
     ClinVar variant ID (e.g., '12345', '123456')

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "clinvar_get_clinical_significance",
          "arguments": {
              "variant_id": "example_value"
          }
      }
      result = tu.run(query)


**clinvar_get_variant_details** (Type: ClinVarGetVariantDetails)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get detailed variant information from ClinVar by variant ID. Returns comprehensive variant data i...

.. dropdown:: clinvar_get_variant_details tool specification

   **Tool Information:**

   * **Name**: ``clinvar_get_variant_details``
   * **Type**: ``ClinVarGetVariantDetails``
   * **Description**: Get detailed variant information from ClinVar by variant ID. Returns comprehensive variant data including clinical significance.

   **Parameters:**

   * ``variant_id`` (string) (required)
     ClinVar variant ID (e.g., '12345', '123456')

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "clinvar_get_variant_details",
          "arguments": {
              "variant_id": "example_value"
          }
      }
      result = tu.run(query)


**clinvar_search_variants** (Type: ClinVarSearchVariants)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search for variants in ClinVar database by gene name, condition, or variant ID. Returns variant i...

.. dropdown:: clinvar_search_variants tool specification

   **Tool Information:**

   * **Name**: ``clinvar_search_variants``
   * **Type**: ``ClinVarSearchVariants``
   * **Description**: Search for variants in ClinVar database by gene name, condition, or variant ID. Returns variant identifiers and basic information.

   **Parameters:**

   * ``gene`` (string) (optional)
     Gene name or symbol (e.g., 'BRCA1', 'BRCA2')

   * ``condition`` (string) (optional)
     Disease or condition name (e.g., 'breast cancer', 'diabetes')

   * ``variant_id`` (string) (optional)
     ClinVar variant ID (e.g., '12345')

   * ``max_results`` (integer) (optional)
     Maximum number of results to return

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "clinvar_search_variants",
          "arguments": {
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
