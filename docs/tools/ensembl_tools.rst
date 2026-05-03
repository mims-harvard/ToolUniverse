Ensembl Tools
=============

**Configuration File**: ``ensembl_tools.json``
**Tool Type**: Local
**Tools Count**: 3

This page contains all tools defined in the ``ensembl_tools.json`` configuration file.

Available Tools
---------------

**ensembl_get_sequence** (Type: EnsemblGetSequence)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get DNA sequence for a gene, transcript, or genomic region. Returns sequence in FASTA format.

.. dropdown:: ensembl_get_sequence tool specification

   **Tool Information:**

   * **Name**: ``ensembl_get_sequence``
   * **Type**: ``EnsemblGetSequence``
   * **Description**: Get DNA sequence for a gene, transcript, or genomic region. Returns sequence in FASTA format.

   **Parameters:**

   * ``sequence_id`` (string) (required)
     Ensembl gene/transcript ID or genomic region (e.g., 'ENSG00000139618' or '1:1000000-2000000')

   * ``type`` (string) (optional)
     Sequence type: 'genomic', 'cds', 'cdna', 'peptide'

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "ensembl_get_sequence",
          "arguments": {
              "sequence_id": "example_value"
          }
      }
      result = tu.run(query)


**ensembl_get_variants** (Type: EnsemblGetVariants)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get genetic variants in a genomic region. Returns SNP and indel information.

.. dropdown:: ensembl_get_variants tool specification

   **Tool Information:**

   * **Name**: ``ensembl_get_variants``
   * **Type**: ``EnsemblGetVariants``
   * **Description**: Get genetic variants in a genomic region. Returns SNP and indel information.

   **Parameters:**

   * ``region`` (string) (required)
     Genomic region in format 'chromosome:start-end' (e.g., '13:32315086-32400268')

   * ``species`` (string) (optional)
     Species name

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "ensembl_get_variants",
          "arguments": {
              "region": "example_value"
          }
      }
      result = tu.run(query)


**ensembl_lookup_gene** (Type: EnsemblLookupGene)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Lookup gene information by Ensembl gene ID or symbol. Returns gene details including location, de...

.. dropdown:: ensembl_lookup_gene tool specification

   **Tool Information:**

   * **Name**: ``ensembl_lookup_gene``
   * **Type**: ``EnsemblLookupGene``
   * **Description**: Lookup gene information by Ensembl gene ID or symbol. Returns gene details including location, description, and external references.

   **Parameters:**

   * ``gene_id`` (string) (required)
     Ensembl gene ID or symbol (e.g., 'ENSG00000139618' or 'BRCA1')

   * ``species`` (string) (optional)
     Species name required for gene symbols (default 'homo_sapiens')

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "ensembl_lookup_gene",
          "arguments": {
              "gene_id": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
