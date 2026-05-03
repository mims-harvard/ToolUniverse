Hpa Tools
=========

**Configuration File**: ``hpa_tools.json``
**Tool Type**: Local
**Tools Count**: 14

This page contains all tools defined in the ``hpa_tools.json`` configuration file.

Available Tools
---------------

**HPA_generic_search** (Type: HPASearchTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Generic search tool for Human Protein Atlas. Allows custom search queries and retrieval of specif...

.. dropdown:: HPA_generic_search tool specification

   **Tool Information:**

   * **Name**: ``HPA_generic_search``
   * **Type**: ``HPASearchTool``
   * **Description**: Generic search tool for Human Protein Atlas. Allows custom search queries and retrieval of specific columns.

   **Parameters:**

   * ``search_query`` (string) (required)
     Search term for the query

   * ``columns`` (string) (optional)
     Comma-separated list of columns to retrieve. Defaults to 'g,gs,gd'. Common options: 'g' (Gene), 'gs' (Synonym), 'e' (Ensembl), 'u' (UniProt), 'pe' (Protein existence), 's' (Subcellular location), 'scml' (Main location), 'scal' (Addl location), 'rnat' (RNA tissue specificity), 'rnatsm' (RNA tissue nTPM), 'rnablm' (RNA blood nTPM), 'rnascm' (RNA single cell nTPM).

   * ``format`` (string) (optional)
     Response format (json or tsv). Defaults to 'json'.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "HPA_generic_search",
          "arguments": {
              "search_query": "example_value"
          }
      }
      result = tu.run(query)


**HPA_get_biological_processes_by_gene** (Type: HPAGetBiologicalProcessTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get biological process information for a gene, with special focus on key processes like apoptosis...

.. dropdown:: HPA_get_biological_processes_by_gene tool specification

   **Tool Information:**

   * **Name**: ``HPA_get_biological_processes_by_gene``
   * **Type**: ``HPAGetBiologicalProcessTool``
   * **Description**: Get biological process information for a gene, with special focus on key processes like apoptosis, cell cycle, etc.

   **Parameters:**

   * ``gene_name`` (string) (required)
     Gene name or gene symbol, e.g., 'TP53', 'CDK1', 'CASP3', etc.

   * ``filter_processes`` (boolean) (required)
     Whether to filter and focus on specific biological processes (apoptosis, cell cycle, transcription regulation, etc.), defaults to true.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "HPA_get_biological_processes_by_gene",
          "arguments": {
              "gene_name": "example_value",
              "filter_processes": true
          }
      }
      result = tu.run(query)


**HPA_get_cancer_prognostics_by_gene** (Type: HPAGetCancerPrognosticsTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve prognostic value of a gene across various cancer types, indicating if its expression lev...

.. dropdown:: HPA_get_cancer_prognostics_by_gene tool specification

   **Tool Information:**

   * **Name**: ``HPA_get_cancer_prognostics_by_gene``
   * **Type**: ``HPAGetCancerPrognosticsTool``
   * **Description**: Retrieve prognostic value of a gene across various cancer types, indicating if its expression level correlates with patient survival outcomes.

   **Parameters:**

   * ``ensembl_id`` (string) (required)
     Ensembl Gene ID of the gene to check, e.g., 'ENSG00000141510' for TP53, 'ENSG00000012048' for BRCA1.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "HPA_get_cancer_prognostics_by_gene",
          "arguments": {
              "ensembl_id": "example_value"
          }
      }
      result = tu.run(query)


**HPA_get_comparative_expression_by_gene_and_cellline** (Type: HPAGetComparativeExpressionTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Compare the expression level differences of a gene between a specific cell line and healthy tissu...

.. dropdown:: HPA_get_comparative_expression_by_gene_and_cellline tool specification

   **Tool Information:**

   * **Name**: ``HPA_get_comparative_expression_by_gene_and_cellline``
   * **Type**: ``HPAGetComparativeExpressionTool``
   * **Description**: Compare the expression level differences of a gene between a specific cell line and healthy tissues using gene name and cell line name.

   **Parameters:**

   * ``gene_name`` (string) (required)
     Gene name or gene symbol, e.g., 'TP53', 'BRCA1', 'EGFR', etc.

   * ``cell_line`` (string) (required)
     Cell line name, supported cell lines include: ishikawa, hela, mcf7, a549, hepg2, jurkat, pc3, rh30, siha, u251.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "HPA_get_comparative_expression_by_gene_and_cellline",
          "arguments": {
              "gene_name": "example_value",
              "cell_line": "example_value"
          }
      }
      result = tu.run(query)


**HPA_get_comprehensive_gene_details_by_ensembl_id** (Type: HPAGetGenePageDetailsTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get detailed in-depth information from gene page using Ensembl Gene ID, including image URLs, ant...

.. dropdown:: HPA_get_comprehensive_gene_details_by_ensembl_id tool specification

   **Tool Information:**

   * **Name**: ``HPA_get_comprehensive_gene_details_by_ensembl_id``
   * **Type**: ``HPAGetGenePageDetailsTool``
   * **Description**: Get detailed in-depth information from gene page using Ensembl Gene ID, including image URLs, antibody data, protein expression, and comprehensive information. This is the core tool for retrieving all images (tissue immunohistochemistry, subcellular immunofluorescence).

   **Parameters:**

   * ``ensembl_id`` (string) (required)
     Ensembl Gene ID, e.g., 'ENSG00000064787' (BCAS1), 'ENSG00000141510' (TP53), etc. Usually obtained through HPA_search_genes_by_query tool.

   * ``include_images`` (boolean) (required)
     Whether to include image URL information (immunofluorescence, cell line images, etc.), defaults to true.

   * ``include_antibodies`` (boolean) (required)
     Whether to include detailed antibody information (validation status, Western blot data, etc.), defaults to true.

   * ``include_expression`` (boolean) (required)
     Whether to include detailed expression data (tissue specificity, subcellular localization, etc.), defaults to true.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "HPA_get_comprehensive_gene_details_by_ensembl_id",
          "arguments": {
              "ensembl_id": "example_value",
              "include_images": true,
              "include_antibodies": true,
              "include_expression": true
          }
      }
      result = tu.run(query)


**HPA_get_contextual_biological_process_analysis** (Type: HPAGetContextualBiologicalProcessTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Analyze a gene's biological processes in the context of a specific tissue or cell line by integra...

.. dropdown:: HPA_get_contextual_biological_process_analysis tool specification

   **Tool Information:**

   * **Name**: ``HPA_get_contextual_biological_process_analysis``
   * **Type**: ``HPAGetContextualBiologicalProcessTool``
   * **Description**: Analyze a gene's biological processes in the context of a specific tissue or cell line by integrating functional annotation with expression data to determine functional relevance.

   **Parameters:**

   * ``gene_name`` (string) (required)
     Gene name or symbol, e.g., 'TP53', 'EGFR', 'BRCA1'.

   * ``context_name`` (string) (required)
     Name of the tissue or cell line to provide context, e.g., 'brain', 'liver', 'hela', 'mcf7'.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "HPA_get_contextual_biological_process_analysis",
          "arguments": {
              "gene_name": "example_value",
              "context_name": "example_value"
          }
      }
      result = tu.run(query)


**HPA_get_disease_expression_by_gene_tissue_disease** (Type: HPAGetDiseaseExpressionTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Compare the expression level of a gene in specific disease state versus healthy state using gene ...

.. dropdown:: HPA_get_disease_expression_by_gene_tissue_disease tool specification

   **Tool Information:**

   * **Name**: ``HPA_get_disease_expression_by_gene_tissue_disease``
   * **Type**: ``HPAGetDiseaseExpressionTool``
   * **Description**: Compare the expression level of a gene in specific disease state versus healthy state using gene name, tissue type, and disease name.

   **Parameters:**

   * ``gene_name`` (string) (required)
     Gene name or gene symbol, e.g., 'TP53', 'BRCA1', 'KRAS', etc.

   * ``tissue_type`` (string) (required)
     Tissue type, e.g., 'brain', 'breast', 'colon', 'lung', etc., optional parameter.

   * ``disease_name`` (string) (required)
     Disease name, supported diseases include: brain_cancer, breast_cancer, colon_cancer, lung_cancer, liver_cancer, prostate_cancer, kidney_cancer, pancreatic_cancer, stomach_cancer, ovarian_cancer.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "HPA_get_disease_expression_by_gene_tissue_disease",
          "arguments": {
              "gene_name": "example_value",
              "tissue_type": "example_value",
              "disease_name": "example_value"
          }
      }
      result = tu.run(query)


**HPA_get_gene_basic_info_by_ensembl_id** (Type: HPAGetGeneJSONTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get gene basic information and expression data from Human Protein Atlas using Ensembl Gene ID. En...

.. dropdown:: HPA_get_gene_basic_info_by_ensembl_id tool specification

   **Tool Information:**

   * **Name**: ``HPA_get_gene_basic_info_by_ensembl_id``
   * **Type**: ``HPAGetGeneJSONTool``
   * **Description**: Get gene basic information and expression data from Human Protein Atlas using Ensembl Gene ID. Enhanced version now uses efficient JSON API.

   **Parameters:**

   * ``ensembl_id`` (string) (required)
     Ensembl Gene ID, e.g., 'ENSG00000134057', 'ENSG00000141510', etc.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "HPA_get_gene_basic_info_by_ensembl_id",
          "arguments": {
              "ensembl_id": "example_value"
          }
      }
      result = tu.run(query)


**HPA_get_gene_tsv_data_by_ensembl_id** (Type: HPAGetGeneXMLTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get detailed gene data in TSV format from Human Protein Atlas using Ensembl Gene ID (backward com...

.. dropdown:: HPA_get_gene_tsv_data_by_ensembl_id tool specification

   **Tool Information:**

   * **Name**: ``HPA_get_gene_tsv_data_by_ensembl_id``
   * **Type**: ``HPAGetGeneXMLTool``
   * **Description**: Get detailed gene data in TSV format from Human Protein Atlas using Ensembl Gene ID (backward compatibility tool).

   **Parameters:**

   * ``ensembl_id`` (string) (required)
     Ensembl Gene ID, e.g., 'ENSG00000134057', 'ENSG00000141510', etc.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "HPA_get_gene_tsv_data_by_ensembl_id",
          "arguments": {
              "ensembl_id": "example_value"
          }
      }
      result = tu.run(query)


**HPA_get_protein_interactions_by_gene** (Type: HPAGetProteinInteractionsTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Fetch known protein-protein interaction partners for a given gene from Human Protein Atlas database.

.. dropdown:: HPA_get_protein_interactions_by_gene tool specification

   **Tool Information:**

   * **Name**: ``HPA_get_protein_interactions_by_gene``
   * **Type**: ``HPAGetProteinInteractionsTool``
   * **Description**: Fetch known protein-protein interaction partners for a given gene from Human Protein Atlas database.

   **Parameters:**

   * ``gene_name`` (string) (required)
     Official gene symbol, e.g., 'EGFR', 'TP53', 'BRCA1', etc.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "HPA_get_protein_interactions_by_gene",
          "arguments": {
              "gene_name": "example_value"
          }
      }
      result = tu.run(query)


**HPA_get_rna_expression_by_source** (Type: HPAGetRnaExpressionBySourceTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get RNA expression level (nTPM) for a gene in a specific biological source using optimized column...

.. dropdown:: HPA_get_rna_expression_by_source tool specification

   **Tool Information:**

   * **Name**: ``HPA_get_rna_expression_by_source``
   * **Type**: ``HPAGetRnaExpressionBySourceTool``
   * **Description**: Get RNA expression level (nTPM) for a gene in a specific biological source using optimized columns parameter. Supports tissue, blood, brain, and single_cell source types with comprehensive source mappings.

   **Parameters:**

   * ``gene_name`` (string) (required)
     Gene name or gene symbol, e.g., 'GFAP', 'TP53', 'BRCA1', etc.

   * ``source_type`` (string) (required)
     The type of biological source. Choose from: 'tissue', 'blood', 'brain', 'single_cell'.

   * ``source_name`` (string) (required)
     The specific name of the biological source, e.g., 'liver', 'heart_muscle', 't_cell', 'hepatocytes', 'cerebellum'. Must be a valid name from the comprehensive HPA columns mapping.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "HPA_get_rna_expression_by_source",
          "arguments": {
              "gene_name": "example_value",
              "source_type": "example_value",
              "source_name": "example_value"
          }
      }
      result = tu.run(query)


**HPA_get_rna_expression_in_specific_tissues** (Type: HPAGetRnaExpressionByTissueTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Query RNA expression levels (nTPM) for a specific gene in one or more user-specified tissues with...

.. dropdown:: HPA_get_rna_expression_in_specific_tissues tool specification

   **Tool Information:**

   * **Name**: ``HPA_get_rna_expression_in_specific_tissues``
   * **Type**: ``HPAGetRnaExpressionByTissueTool``
   * **Description**: Query RNA expression levels (nTPM) for a specific gene in one or more user-specified tissues with precise tissue matching.

   **Parameters:**

   * ``ensembl_id`` (string) (required)
     Ensembl Gene ID for the gene, e.g., 'ENSG00000141510' for TP53.

   * ``tissue_names`` (array) (required)
     List of tissue names to query, e.g., ['brain', 'liver', 'heart muscle', 'kidney']. Case-insensitive matching is supported.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "HPA_get_rna_expression_in_specific_tissues",
          "arguments": {
              "ensembl_id": "example_value",
              "tissue_names": ["item1", "item2"]
          }
      }
      result = tu.run(query)


**HPA_get_subcellular_location** (Type: HPAGetSubcellularLocationTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get annotated subcellular locations for a protein using optimized columns parameter. Retrieves bo...

.. dropdown:: HPA_get_subcellular_location tool specification

   **Tool Information:**

   * **Name**: ``HPA_get_subcellular_location``
   * **Type**: ``HPAGetSubcellularLocationTool``
   * **Description**: Get annotated subcellular locations for a protein using optimized columns parameter. Retrieves both main and additional subcellular locations efficiently.

   **Parameters:**

   * ``gene_name`` (string) (required)
     Gene name or gene symbol, e.g., 'CCNB1', 'TP53', 'EGFR', etc.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "HPA_get_subcellular_location",
          "arguments": {
              "gene_name": "example_value"
          }
      }
      result = tu.run(query)


**HPA_search_genes_by_query** (Type: HPASearchGenesTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search for matching genes by gene name, keywords, or cell line names and return Ensembl ID list. ...

.. dropdown:: HPA_search_genes_by_query tool specification

   **Tool Information:**

   * **Name**: ``HPA_search_genes_by_query``
   * **Type**: ``HPASearchGenesTool``
   * **Description**: Search for matching genes by gene name, keywords, or cell line names and return Ensembl ID list. This is the entry tool for many HPA query workflows.

   **Parameters:**

   * ``search_query`` (string) (required)
     Gene name, alias, keyword, or cell line name to search for, e.g., 'EGFR', 'TP53', or 'MCF7'.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "HPA_search_genes_by_query",
          "arguments": {
              "search_query": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
