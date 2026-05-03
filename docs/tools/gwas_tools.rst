Gwas Tools
==========

**Configuration File**: ``gwas_tools.json``
**Tool Type**: Local
**Tools Count**: 13

This page contains all tools defined in the ``gwas_tools.json`` configuration file.

Available Tools
---------------

**GWAS_search_associations_by_gene** (Type: GWASGeneSearch)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search GWAS Catalog associations by gene name (returns strongest risk allele and p-value fields).

.. dropdown:: GWAS_search_associations_by_gene tool specification

   **Tool Information:**

   * **Name**: ``GWAS_search_associations_by_gene``
   * **Type**: ``GWASGeneSearch``
   * **Description**: Search GWAS Catalog associations by gene name (returns strongest risk allele and p-value fields).

   **Parameters:**

   * ``gene_name`` (string) (required)
     Gene symbol (e.g., BRCA1).

   * ``size`` (integer) (optional)
     Max associations to return.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "GWAS_search_associations_by_gene",
          "arguments": {
              "gene_name": "example_value"
          }
      }
      result = tu.run(query)


**gwas_get_association_by_id** (Type: GWASAssociationByID)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get a specific GWAS association by its unique identifier.

.. dropdown:: gwas_get_association_by_id tool specification

   **Tool Information:**

   * **Name**: ``gwas_get_association_by_id``
   * **Type**: ``GWASAssociationByID``
   * **Description**: Get a specific GWAS association by its unique identifier.

   **Parameters:**

   * ``association_id`` (string) (required)
     GWAS association identifier

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "gwas_get_association_by_id",
          "arguments": {
              "association_id": "example_value"
          }
      }
      result = tu.run(query)


**gwas_get_associations_for_snp** (Type: GWASAssociationsForSNP)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get all associations for a specific SNP with optional sorting.

.. dropdown:: gwas_get_associations_for_snp tool specification

   **Tool Information:**

   * **Name**: ``gwas_get_associations_for_snp``
   * **Type**: ``GWASAssociationsForSNP``
   * **Description**: Get all associations for a specific SNP with optional sorting.

   **Parameters:**

   * ``rs_id`` (string) (required)
     dbSNP rs identifier

   * ``sort`` (string) (optional)
     Sort field (e.g., 'p_value', 'or_value')

   * ``direction`` (string) (optional)
     Sort direction ('asc' or 'desc')

   * ``size`` (integer) (optional)
     Number of results to return per page

   * ``page`` (integer) (optional)
     Page number for pagination

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "gwas_get_associations_for_snp",
          "arguments": {
              "rs_id": "example_value"
          }
      }
      result = tu.run(query)


**gwas_get_associations_for_study** (Type: GWASAssociationsForStudy)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get all associations for a specific study, sorted by p-value.

.. dropdown:: gwas_get_associations_for_study tool specification

   **Tool Information:**

   * **Name**: ``gwas_get_associations_for_study``
   * **Type**: ``GWASAssociationsForStudy``
   * **Description**: Get all associations for a specific study, sorted by p-value.

   **Parameters:**

   * ``accession_id`` (string) (required)
     Study accession identifier

   * ``size`` (integer) (optional)
     Number of results to return per page

   * ``page`` (integer) (optional)
     Page number for pagination

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "gwas_get_associations_for_study",
          "arguments": {
              "accession_id": "example_value"
          }
      }
      result = tu.run(query)


**gwas_get_associations_for_trait** (Type: GWASAssociationsForTrait)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get all associations for a specific trait, sorted by p-value (most significant first).

.. dropdown:: gwas_get_associations_for_trait tool specification

   **Tool Information:**

   * **Name**: ``gwas_get_associations_for_trait``
   * **Type**: ``GWASAssociationsForTrait``
   * **Description**: Get all associations for a specific trait, sorted by p-value (most significant first).

   **Parameters:**

   * ``efo_trait`` (string) (required)
     EFO trait identifier or name

   * ``size`` (integer) (optional)
     Number of results to return per page

   * ``page`` (integer) (optional)
     Page number for pagination

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "gwas_get_associations_for_trait",
          "arguments": {
              "efo_trait": "example_value"
          }
      }
      result = tu.run(query)


**gwas_get_snp_by_id** (Type: GWASSNPByID)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get a specific GWAS SNP by its rs ID.

.. dropdown:: gwas_get_snp_by_id tool specification

   **Tool Information:**

   * **Name**: ``gwas_get_snp_by_id``
   * **Type**: ``GWASSNPByID``
   * **Description**: Get a specific GWAS SNP by its rs ID.

   **Parameters:**

   * ``rs_id`` (string) (required)
     dbSNP rs identifier

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "gwas_get_snp_by_id",
          "arguments": {
              "rs_id": "example_value"
          }
      }
      result = tu.run(query)


**gwas_get_snps_for_gene** (Type: GWASSNPsForGene)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get all SNPs mapped to a specific gene.

.. dropdown:: gwas_get_snps_for_gene tool specification

   **Tool Information:**

   * **Name**: ``gwas_get_snps_for_gene``
   * **Type**: ``GWASSNPsForGene``
   * **Description**: Get all SNPs mapped to a specific gene.

   **Parameters:**

   * ``mapped_gene`` (string) (required)
     Gene name or symbol

   * ``size`` (integer) (optional)
     Number of results to return per page

   * ``page`` (integer) (optional)
     Page number for pagination

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "gwas_get_snps_for_gene",
          "arguments": {
              "mapped_gene": "example_value"
          }
      }
      result = tu.run(query)


**gwas_get_studies_for_trait** (Type: GWASStudiesForTrait)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get studies for a specific trait with optional filters for cohort, GxE interactions, and summary ...

.. dropdown:: gwas_get_studies_for_trait tool specification

   **Tool Information:**

   * **Name**: ``gwas_get_studies_for_trait``
   * **Type**: ``GWASStudiesForTrait``
   * **Description**: Get studies for a specific trait with optional filters for cohort, GxE interactions, and summary statistics.

   **Parameters:**

   * ``efo_trait`` (string) (optional)
     EFO trait identifier or name

   * ``disease_trait`` (string) (optional)
     Disease trait name

   * ``cohort`` (string) (optional)
     Cohort name (e.g., 'UKB' for UK Biobank)

   * ``gxe`` (boolean) (optional)
     Filter for Gene-by-Environment interaction studies

   * ``full_pvalue_set`` (boolean) (optional)
     Filter for studies with full summary statistics

   * ``size`` (integer) (optional)
     Number of results to return per page

   * ``page`` (integer) (optional)
     Page number for pagination

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "gwas_get_studies_for_trait",
          "arguments": {
          }
      }
      result = tu.run(query)


**gwas_get_study_by_id** (Type: GWASStudyByID)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get a specific GWAS study by its unique identifier.

.. dropdown:: gwas_get_study_by_id tool specification

   **Tool Information:**

   * **Name**: ``gwas_get_study_by_id``
   * **Type**: ``GWASStudyByID``
   * **Description**: Get a specific GWAS study by its unique identifier.

   **Parameters:**

   * ``study_id`` (string) (required)
     GWAS study identifier

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "gwas_get_study_by_id",
          "arguments": {
              "study_id": "example_value"
          }
      }
      result = tu.run(query)


**gwas_get_variants_for_trait** (Type: GWASVariantsForTrait)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get all variants associated with a specific trait with pagination support.

.. dropdown:: gwas_get_variants_for_trait tool specification

   **Tool Information:**

   * **Name**: ``gwas_get_variants_for_trait``
   * **Type**: ``GWASVariantsForTrait``
   * **Description**: Get all variants associated with a specific trait with pagination support.

   **Parameters:**

   * ``efo_trait`` (string) (required)
     EFO trait identifier or name

   * ``size`` (integer) (optional)
     Number of results to return per page

   * ``page`` (integer) (optional)
     Page number for pagination

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "gwas_get_variants_for_trait",
          "arguments": {
              "efo_trait": "example_value"
          }
      }
      result = tu.run(query)


**gwas_search_associations** (Type: GWASAssociationSearch)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search for GWAS associations by various criteria including EFO trait, rs ID, accession ID, with s...

.. dropdown:: gwas_search_associations tool specification

   **Tool Information:**

   * **Name**: ``gwas_search_associations``
   * **Type**: ``GWASAssociationSearch``
   * **Description**: Search for GWAS associations by various criteria including EFO trait, rs ID, accession ID, with sorting and pagination support.

   **Parameters:**

   * ``efo_trait`` (string) (optional)
     EFO trait identifier or name

   * ``rs_id`` (string) (optional)
     dbSNP rs identifier

   * ``accession_id`` (string) (optional)
     Study accession identifier

   * ``sort`` (string) (optional)
     Sort field (e.g., 'p_value', 'or_value')

   * ``direction`` (string) (optional)
     Sort direction ('asc' or 'desc')

   * ``size`` (integer) (optional)
     Number of results to return

   * ``page`` (integer) (optional)
     Page number for pagination

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "gwas_search_associations",
          "arguments": {
          }
      }
      result = tu.run(query)


**gwas_search_snps** (Type: GWASSNPSearch)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search for GWAS single nucleotide polymorphisms (SNPs) by rs ID or mapped gene.

.. dropdown:: gwas_search_snps tool specification

   **Tool Information:**

   * **Name**: ``gwas_search_snps``
   * **Type**: ``GWASSNPSearch``
   * **Description**: Search for GWAS single nucleotide polymorphisms (SNPs) by rs ID or mapped gene.

   **Parameters:**

   * ``rs_id`` (string) (optional)
     dbSNP rs identifier

   * ``mapped_gene`` (string) (optional)
     Gene name or symbol

   * ``size`` (integer) (optional)
     Number of results to return

   * ``page`` (integer) (optional)
     Page number for pagination

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "gwas_search_snps",
          "arguments": {
          }
      }
      result = tu.run(query)


**gwas_search_studies** (Type: GWASStudySearch)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search for GWAS studies by various criteria including EFO trait, disease trait, cohort, GxE inter...

.. dropdown:: gwas_search_studies tool specification

   **Tool Information:**

   * **Name**: ``gwas_search_studies``
   * **Type**: ``GWASStudySearch``
   * **Description**: Search for GWAS studies by various criteria including EFO trait, disease trait, cohort, GxE interactions, and summary statistics availability.

   **Parameters:**

   * ``efo_trait`` (string) (optional)
     EFO trait identifier or name

   * ``disease_trait`` (string) (optional)
     Disease trait name

   * ``cohort`` (string) (optional)
     Cohort name (e.g., 'UKB' for UK Biobank)

   * ``gxe`` (boolean) (optional)
     Filter for Gene-by-Environment interaction studies

   * ``full_pvalue_set`` (boolean) (optional)
     Filter for studies with full summary statistics

   * ``size`` (integer) (optional)
     Number of results to return

   * ``page`` (integer) (optional)
     Page number for pagination

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "gwas_search_studies",
          "arguments": {
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
