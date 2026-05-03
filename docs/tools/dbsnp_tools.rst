Dbsnp Tools
===========

**Configuration File**: ``dbsnp_tools.json``
**Tool Type**: Local
**Tools Count**: 3

This page contains all tools defined in the ``dbsnp_tools.json`` configuration file.

Available Tools
---------------

**dbsnp_get_frequencies** (Type: dbSNPGetFrequencies)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get allele frequencies for a variant from dbSNP. Returns population-specific allele frequency data.

.. dropdown:: dbsnp_get_frequencies tool specification

   **Tool Information:**

   * **Name**: ``dbsnp_get_frequencies``
   * **Type**: ``dbSNPGetFrequencies``
   * **Description**: Get allele frequencies for a variant from dbSNP. Returns population-specific allele frequency data.

   **Parameters:**

   * ``rsid`` (string) (required)
     dbSNP rsID (e.g., 'rs12345', '12345')

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "dbsnp_get_frequencies",
          "arguments": {
              "rsid": "example_value"
          }
      }
      result = tu.run(query)


**dbsnp_get_variant_by_rsid** (Type: dbSNPGetVariantByRsID)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get variant information from dbSNP by rsID. Returns genomic coordinates, alleles, and basic varia...

.. dropdown:: dbsnp_get_variant_by_rsid tool specification

   **Tool Information:**

   * **Name**: ``dbsnp_get_variant_by_rsid``
   * **Type**: ``dbSNPGetVariantByRsID``
   * **Description**: Get variant information from dbSNP by rsID. Returns genomic coordinates, alleles, and basic variant information.

   **Parameters:**

   * ``rsid`` (string) (required)
     dbSNP rsID (e.g., 'rs12345', '12345')

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "dbsnp_get_variant_by_rsid",
          "arguments": {
              "rsid": "example_value"
          }
      }
      result = tu.run(query)


**dbsnp_search_by_gene** (Type: dbSNPSearchByGene)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search for variants in a specific gene. Returns variants associated with the gene symbol.

.. dropdown:: dbsnp_search_by_gene tool specification

   **Tool Information:**

   * **Name**: ``dbsnp_search_by_gene``
   * **Type**: ``dbSNPSearchByGene``
   * **Description**: Search for variants in a specific gene. Returns variants associated with the gene symbol.

   **Parameters:**

   * ``gene_symbol`` (string) (required)
     Gene symbol (e.g., 'BRCA1', 'TP53', 'APOE')

   * ``limit`` (integer) (optional)
     Maximum number of results to return

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "dbsnp_search_by_gene",
          "arguments": {
              "gene_symbol": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
