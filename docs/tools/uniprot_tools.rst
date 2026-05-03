Uniprot Tools
=============

**Configuration File**: ``uniprot_tools.json``
**Tool Type**: Local
**Tools Count**: 12

This page contains all tools defined in the ``uniprot_tools.json`` configuration file.

Available Tools
---------------

**UniProt_get_alternative_names_by_accession** (Type: UniProtRESTTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Extract all alternative names (alternativeNames) from UniProtKB entry.

.. dropdown:: UniProt_get_alternative_names_by_accession tool specification

   **Tool Information:**

   * **Name**: ``UniProt_get_alternative_names_by_accession``
   * **Type**: ``UniProtRESTTool``
   * **Description**: Extract all alternative names (alternativeNames) from UniProtKB entry.

   **Parameters:**

   * ``accession`` (string) (required)
     UniProtKB accession, e.g., P05067.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "UniProt_get_alternative_names_by_accession",
          "arguments": {
              "accession": "example_value"
          }
      }
      result = tu.run(query)


**UniProt_get_disease_variants_by_accession** (Type: UniProtRESTTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Extract all variants (feature type = VARIANT) and their related annotations from UniProtKB entry.

.. dropdown:: UniProt_get_disease_variants_by_accession tool specification

   **Tool Information:**

   * **Name**: ``UniProt_get_disease_variants_by_accession``
   * **Type**: ``UniProtRESTTool``
   * **Description**: Extract all variants (feature type = VARIANT) and their related annotations from UniProtKB entry.

   **Parameters:**

   * ``accession`` (string) (required)
     UniProtKB accession, e.g., P05067.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "UniProt_get_disease_variants_by_accession",
          "arguments": {
              "accession": "example_value"
          }
      }
      result = tu.run(query)


**UniProt_get_entry_by_accession** (Type: UniProtRESTTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get the complete JSON entry for a specified UniProtKB accession. WARNING: This tool returns the c...

.. dropdown:: UniProt_get_entry_by_accession tool specification

   **Tool Information:**

   * **Name**: ``UniProt_get_entry_by_accession``
   * **Type**: ``UniProtRESTTool``
   * **Description**: Get the complete JSON entry for a specified UniProtKB accession. WARNING: This tool returns the complete UniProtKB entry, which can be extremely large (40,000+ lines for some entries) and may cause LLM context limits to be exceeded or crashes. For most use cases, consider using more specific extraction tools instead: UniProt_get_function_by_accession, UniProt_get_sequence_by_accession, UniProt_get_recommended_name_by_accession, UniProt_get_organism_by_accession, UniProt_get_subcellular_location_by_accession, UniProt_get_disease_variants_by_accession, or UniProt_get_ptm_processing_by_accession.

   **Parameters:**

   * ``accession`` (string) (required)
     UniProtKB entry accession, e.g., P05067.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "UniProt_get_entry_by_accession",
          "arguments": {
              "accession": "example_value"
          }
      }
      result = tu.run(query)


**UniProt_get_function_by_accession** (Type: UniProtRESTTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Extract functional annotations from UniProtKB entry (Comment type = FUNCTION).

.. dropdown:: UniProt_get_function_by_accession tool specification

   **Tool Information:**

   * **Name**: ``UniProt_get_function_by_accession``
   * **Type**: ``UniProtRESTTool``
   * **Description**: Extract functional annotations from UniProtKB entry (Comment type = FUNCTION).

   **Parameters:**

   * ``accession`` (string) (required)
     UniProtKB accession, e.g., P05067.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "UniProt_get_function_by_accession",
          "arguments": {
              "accession": "example_value"
          }
      }
      result = tu.run(query)


**UniProt_get_isoform_ids_by_accession** (Type: UniProtRESTTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Extract all splice isoform IDs from UniProtKB entry (isoformNames).

.. dropdown:: UniProt_get_isoform_ids_by_accession tool specification

   **Tool Information:**

   * **Name**: ``UniProt_get_isoform_ids_by_accession``
   * **Type**: ``UniProtRESTTool``
   * **Description**: Extract all splice isoform IDs from UniProtKB entry (isoformNames).

   **Parameters:**

   * ``accession`` (string) (required)
     UniProtKB accession, e.g., P05067.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "UniProt_get_isoform_ids_by_accession",
          "arguments": {
              "accession": "example_value"
          }
      }
      result = tu.run(query)


**UniProt_get_organism_by_accession** (Type: UniProtRESTTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Extract the organism scientific name from UniProtKB entry.

.. dropdown:: UniProt_get_organism_by_accession tool specification

   **Tool Information:**

   * **Name**: ``UniProt_get_organism_by_accession``
   * **Type**: ``UniProtRESTTool``
   * **Description**: Extract the organism scientific name from UniProtKB entry.

   **Parameters:**

   * ``accession`` (string) (required)
     UniProtKB accession, e.g., P05067.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "UniProt_get_organism_by_accession",
          "arguments": {
              "accession": "example_value"
          }
      }
      result = tu.run(query)


**UniProt_get_ptm_processing_by_accession** (Type: UniProtRESTTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Extract all PTM and processing sites from UniProtKB entry (feature type = MODIFIED RESIDUE or SIG...

.. dropdown:: UniProt_get_ptm_processing_by_accession tool specification

   **Tool Information:**

   * **Name**: ``UniProt_get_ptm_processing_by_accession``
   * **Type**: ``UniProtRESTTool``
   * **Description**: Extract all PTM and processing sites from UniProtKB entry (feature type = MODIFIED RESIDUE or SIGNAL, etc.).

   **Parameters:**

   * ``accession`` (string) (required)
     UniProtKB accession, e.g., P05067.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "UniProt_get_ptm_processing_by_accession",
          "arguments": {
              "accession": "example_value"
          }
      }
      result = tu.run(query)


**UniProt_get_recommended_name_by_accession** (Type: UniProtRESTTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Extract the recommended protein name (recommendedName) from UniProtKB entry.

.. dropdown:: UniProt_get_recommended_name_by_accession tool specification

   **Tool Information:**

   * **Name**: ``UniProt_get_recommended_name_by_accession``
   * **Type**: ``UniProtRESTTool``
   * **Description**: Extract the recommended protein name (recommendedName) from UniProtKB entry.

   **Parameters:**

   * ``accession`` (string) (required)
     UniProtKB accession, e.g., P05067.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "UniProt_get_recommended_name_by_accession",
          "arguments": {
              "accession": "example_value"
          }
      }
      result = tu.run(query)


**UniProt_get_sequence_by_accession** (Type: UniProtRESTTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Extract the canonical sequence from UniProtKB entry.

.. dropdown:: UniProt_get_sequence_by_accession tool specification

   **Tool Information:**

   * **Name**: ``UniProt_get_sequence_by_accession``
   * **Type**: ``UniProtRESTTool``
   * **Description**: Extract the canonical sequence from UniProtKB entry.

   **Parameters:**

   * ``accession`` (string) (required)
     UniProtKB accession, e.g., P05067.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "UniProt_get_sequence_by_accession",
          "arguments": {
              "accession": "example_value"
          }
      }
      result = tu.run(query)


**UniProt_get_subcellular_location_by_accession** (Type: UniProtRESTTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Extract subcellular localization annotations from UniProtKB entry (Comment type = SUBCELLULAR LOC...

.. dropdown:: UniProt_get_subcellular_location_by_accession tool specification

   **Tool Information:**

   * **Name**: ``UniProt_get_subcellular_location_by_accession``
   * **Type**: ``UniProtRESTTool``
   * **Description**: Extract subcellular localization annotations from UniProtKB entry (Comment type = SUBCELLULAR LOCATION).

   **Parameters:**

   * ``accession`` (string) (required)
     UniProtKB accession, e.g., P05067.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "UniProt_get_subcellular_location_by_accession",
          "arguments": {
              "accession": "example_value"
          }
      }
      result = tu.run(query)


**UniProt_id_mapping** (Type: UniProtRESTTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Map IDs between different databases (e.g., Ensembl to UniProt, Gene Name to UniProt). Supports ba...

.. dropdown:: UniProt_id_mapping tool specification

   **Tool Information:**

   * **Name**: ``UniProt_id_mapping``
   * **Type**: ``UniProtRESTTool``
   * **Description**: Map IDs between different databases (e.g., Ensembl to UniProt, Gene Name to UniProt). Supports batch mapping and async task processing. Use this to convert between different database identifiers.

   **Parameters:**

   * ``ids`` (unknown) (required)
     ID(s) to map. Can be single string or array of strings, e.g., 'ENSG00000141510' or ['MEIOB', 'TP53']

   * ``from_db`` (string) (required)
     Source database. Examples: 'Ensembl', 'Gene_Name', 'RefSeq_Protein', 'PDB', 'EMBL'

   * ``to_db`` (string) (optional)
     Target database (default: 'UniProtKB')

   * ``max_wait_time`` (integer) (optional)
     Maximum time to wait for async task completion in seconds (default: 30)

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "UniProt_id_mapping",
          "arguments": {
              "ids": "example_value",
              "from_db": "example_value"
          }
      }
      result = tu.run(query)


**UniProt_search** (Type: UniProtRESTTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search UniProtKB database with flexible query syntax. Returns protein entries with accession numb...

.. dropdown:: UniProt_search tool specification

   **Tool Information:**

   * **Name**: ``UniProt_search``
   * **Type**: ``UniProtRESTTool``
   * **Description**: Search UniProtKB database with flexible query syntax. Returns protein entries with accession numbers and metadata. Query syntax supports: field searches (gene:TP53, organism_id:9606, reviewed:true), ranges (length:[100 TO 500], mass:[20000 TO 50000]), wildcards (gene:MEIOB*), boolean operators (AND/OR/NOT), and parentheses for grouping. Examples: 'gene:TP53 AND organism_id:9606', 'length:[400 TO 500] AND reviewed:true', 'tissue:brain NOT organism_id:10090'.

   **Parameters:**

   * ``query`` (string) (required)
     Search query using UniProt syntax. Simple: 'MEIOB', 'insulin'. Field searches: 'gene:TP53', 'protein_name:insulin', 'organism_id:9606', 'reviewed:true'. Ranges: 'length:[100 TO 500]', 'mass:[20000 TO 50000]'. Wildcards: 'gene:MEIOB*'. Boolean: 'gene:TP53 AND organism_id:9606', 'tissue:brain OR tissue:liver', 'reviewed:true NOT fragment:true'. Use parentheses for grouping: '(organism_id:9606 OR organism_id:10090) AND gene:TP53'. Note: 'organism:' auto-converts to 'organism_id:'.

   * ``organism`` (string) (optional)
     Optional organism filter. Use common names ('human', 'mouse', 'rat', 'yeast') or taxonomy ID ('9606'). Automatically combined with query using AND. Will not duplicate if organism is already in query.

   * ``limit`` (integer) (optional)
     Maximum number of results to return (default: 25, max: 500). Accepts string or integer.

   * ``min_length`` (integer) (optional)
     Minimum sequence length. Auto-converts to 'length:[min TO *]' range query.

   * ``max_length`` (integer) (optional)
     Maximum sequence length. Auto-converts to 'length:[* TO max]' range query.

   * ``fields`` (array) (optional)
     List of field names to return (e.g., ['accession','gene_primary','length','organism_name']). When specified, returns raw API response with requested fields. Common fields: accession, id, gene_names, gene_primary, protein_name, organism_name, organism_id, length, mass, sequence, reviewed, cc_function. See UniProt API docs for full list. Default (no fields): returns formatted response with accession, id, protein_name, gene_names, organism, length.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "UniProt_search",
          "arguments": {
              "query": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
