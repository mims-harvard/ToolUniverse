Gtex Tools
==========

**Configuration File**: ``gtex_tools.json``
**Tool Type**: Local
**Tools Count**: 2

This page contains all tools defined in the ``gtex_tools.json`` configuration file.

Available Tools
---------------

**GTEx_get_expression_summary** (Type: GTExExpressionTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Summarize tissue-specific expression (e.g., median TPM) for a gene across GTEx tissues. Use to pr...

.. dropdown:: GTEx_get_expression_summary tool specification

   **Tool Information:**

   * **Name**: ``GTEx_get_expression_summary``
   * **Type**: ``GTExExpressionTool``
   * **Description**: Summarize tissue-specific expression (e.g., median TPM) for a gene across GTEx tissues. Use to profile baseline expression patterns for targets/biomarkers.

   **Parameters:**

   * ``ensembl_gene_id`` (string) (required)
     Ensembl gene identifier (e.g., 'ENSG00000141510' for TP53).

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "GTEx_get_expression_summary",
          "arguments": {
              "ensembl_gene_id": "example_value"
          }
      }
      result = tu.run(query)


**GTEx_query_eqtl** (Type: GTExEQTLTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Query GTEx single-tissue eQTL associations for a gene. Use to identify regulatory variants (varia...

.. dropdown:: GTEx_query_eqtl tool specification

   **Tool Information:**

   * **Name**: ``GTEx_query_eqtl``
   * **Type**: ``GTExEQTLTool``
   * **Description**: Query GTEx single-tissue eQTL associations for a gene. Use to identify regulatory variants (variantId, pValue, slope) relevant to expression regulation.

   **Parameters:**

   * ``ensembl_gene_id`` (string) (required)
     Ensembl gene identifier (e.g., 'ENSG00000141510').

   * ``page`` (integer) (optional)
     Page number (1-based).

   * ``size`` (integer) (optional)
     Number of records per page (1–100).

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "GTEx_query_eqtl",
          "arguments": {
              "ensembl_gene_id": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
