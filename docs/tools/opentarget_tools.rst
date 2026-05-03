Opentarget Tools
================

**Configuration File**: ``opentarget_tools.json``
**Tool Type**: Local
**Tools Count**: 54

This page contains all tools defined in the ``opentarget_tools.json`` configuration file.

Available Tools
---------------

**OpenTargets_drug_pharmacogenomics_data** (Type: OpenTarget)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve pharmacogenomics data for a specific drug, including evidence levels and genotype annota...

.. dropdown:: OpenTargets_drug_pharmacogenomics_data tool specification

   **Tool Information:**

   * **Name**: ``OpenTargets_drug_pharmacogenomics_data``
   * **Type**: ``OpenTarget``
   * **Description**: Retrieve pharmacogenomics data for a specific drug, including evidence levels and genotype annotations.

   **Parameters:**

   * ``chemblId`` (string) (required)
     The ChEMBL ID of the drug.

   * ``page`` (object) (optional)
     Pagination options.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "OpenTargets_drug_pharmacogenomics_data",
          "arguments": {
              "chemblId": "example_value"
          }
      }
      result = tu.run(query)


**OpenTargets_get_approved_indications_by_drug_chemblId** (Type: OpenTarget)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve detailed information about multiple drugs using a list of ChEMBL IDs.

.. dropdown:: OpenTargets_get_approved_indications_by_drug_chemblId tool specification

   **Tool Information:**

   * **Name**: ``OpenTargets_get_approved_indications_by_drug_chemblId``
   * **Type**: ``OpenTarget``
   * **Description**: Retrieve detailed information about multiple drugs using a list of ChEMBL IDs.

   **Parameters:**

   * ``chemblId`` (string) (required)
     The ChEMBL ID of the drug.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "OpenTargets_get_approved_indications_by_drug_chemblId",
          "arguments": {
              "chemblId": "example_value"
          }
      }
      result = tu.run(query)


**OpenTargets_get_associated_diseases_by_drug_chemblId** (Type: OpenTarget)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve the list of diseases associated with a specific drug chemblId based on clinical trial da...

.. dropdown:: OpenTargets_get_associated_diseases_by_drug_chemblId tool specification

   **Tool Information:**

   * **Name**: ``OpenTargets_get_associated_diseases_by_drug_chemblId``
   * **Type**: ``OpenTarget``
   * **Description**: Retrieve the list of diseases associated with a specific drug chemblId based on clinical trial data or post-marketed drugs.

   **Parameters:**

   * ``chemblId`` (string) (required)
     The ChEMBL ID of the drug.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "OpenTargets_get_associated_diseases_by_drug_chemblId",
          "arguments": {
              "chemblId": "example_value"
          }
      }
      result = tu.run(query)


**OpenTargets_get_associated_drugs_by_disease_efoId** (Type: OpenTarget)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve known drugs associated with a specific disease by disease efoId.

.. dropdown:: OpenTargets_get_associated_drugs_by_disease_efoId tool specification

   **Tool Information:**

   * **Name**: ``OpenTargets_get_associated_drugs_by_disease_efoId``
   * **Type**: ``OpenTarget``
   * **Description**: Retrieve known drugs associated with a specific disease by disease efoId.

   **Parameters:**

   * ``efoId`` (string) (required)
     The EFO ID of the disease.

   * ``size`` (integer) (required)
     Number of entries to fetch, recomanding a large number to avoid missing drugs.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "OpenTargets_get_associated_drugs_by_disease_efoId",
          "arguments": {
              "efoId": "example_value",
              "size": 10
          }
      }
      result = tu.run(query)


**OpenTargets_get_associated_drugs_by_target_ensemblID** (Type: OpenTarget)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get known drugs and information (e.g. id, name, MoA) associated with a specific target ensemblID,...

.. dropdown:: OpenTargets_get_associated_drugs_by_target_ensemblID tool specification

   **Tool Information:**

   * **Name**: ``OpenTargets_get_associated_drugs_by_target_ensemblID``
   * **Type**: ``OpenTarget``
   * **Description**: Get known drugs and information (e.g. id, name, MoA) associated with a specific target ensemblID, including clinical trial phase and mechanism of action of the drugs.

   **Parameters:**

   * ``ensemblId`` (string) (required)
     The Ensembl ID of the target.

   * ``size`` (integer) (required)
     Number of entries to fetch.

   * ``cursor`` (string) (optional)
     Cursor for pagination.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "OpenTargets_get_associated_drugs_by_target_ensemblID",
          "arguments": {
              "ensemblId": "example_value",
              "size": 10
          }
      }
      result = tu.run(query)


**OpenTargets_get_associated_phenotypes_by_disease_efoId** (Type: OpenTarget)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Find HPO phenotypes asosciated with the specified disease efoId.

.. dropdown:: OpenTargets_get_associated_phenotypes_by_disease_efoId tool specification

   **Tool Information:**

   * **Name**: ``OpenTargets_get_associated_phenotypes_by_disease_efoId``
   * **Type**: ``OpenTarget``
   * **Description**: Find HPO phenotypes asosciated with the specified disease efoId.

   **Parameters:**

   * ``efoId`` (string) (required)
     The efoId of a disease or phenotype.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "OpenTargets_get_associated_phenotypes_by_disease_efoId",
          "arguments": {
              "efoId": "example_value"
          }
      }
      result = tu.run(query)


**OpenTargets_get_associated_targets_by_disease_efoId** (Type: OpenTarget)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Find targets associated with a specific disease or phenotype based on efoId.

.. dropdown:: OpenTargets_get_associated_targets_by_disease_efoId tool specification

   **Tool Information:**

   * **Name**: ``OpenTargets_get_associated_targets_by_disease_efoId``
   * **Type**: ``OpenTarget``
   * **Description**: Find targets associated with a specific disease or phenotype based on efoId.

   **Parameters:**

   * ``efoId`` (string) (required)
     The efoId of a disease or phenotype.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "OpenTargets_get_associated_targets_by_disease_efoId",
          "arguments": {
              "efoId": "example_value"
          }
      }
      result = tu.run(query)


**OpenTargets_get_associated_targets_by_drug_chemblId** (Type: OpenTarget)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve the list of targets linked to a specific drug chemblId based on its mechanism of action.

.. dropdown:: OpenTargets_get_associated_targets_by_drug_chemblId tool specification

   **Tool Information:**

   * **Name**: ``OpenTargets_get_associated_targets_by_drug_chemblId``
   * **Type**: ``OpenTarget``
   * **Description**: Retrieve the list of targets linked to a specific drug chemblId based on its mechanism of action.

   **Parameters:**

   * ``chemblId`` (string) (required)
     The ChEMBL ID of the drug.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "OpenTargets_get_associated_targets_by_drug_chemblId",
          "arguments": {
              "chemblId": "example_value"
          }
      }
      result = tu.run(query)


**OpenTargets_get_biological_mouse_models_by_ensemblID** (Type: OpenTarget)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve biological mouse models, including allelic compositions and genetic backgrounds, for a s...

.. dropdown:: OpenTargets_get_biological_mouse_models_by_ensemblID tool specification

   **Tool Information:**

   * **Name**: ``OpenTargets_get_biological_mouse_models_by_ensemblID``
   * **Type**: ``OpenTarget``
   * **Description**: Retrieve biological mouse models, including allelic compositions and genetic backgrounds, for a specific target.

   **Parameters:**

   * ``ensemblId`` (string) (required)
     The Ensembl ID of the target.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "OpenTargets_get_biological_mouse_models_by_ensemblID",
          "arguments": {
              "ensemblId": "example_value"
          }
      }
      result = tu.run(query)


**OpenTargets_get_chemical_probes_by_target_ensemblID** (Type: OpenTarget)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve chemical probes associated with a specific target using its ensemblID.

.. dropdown:: OpenTargets_get_chemical_probes_by_target_ensemblID tool specification

   **Tool Information:**

   * **Name**: ``OpenTargets_get_chemical_probes_by_target_ensemblID``
   * **Type**: ``OpenTarget``
   * **Description**: Retrieve chemical probes associated with a specific target using its ensemblID.

   **Parameters:**

   * ``ensemblId`` (string) (required)
     The Ensembl ID of the target for which to retrieve chemical probes.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "OpenTargets_get_chemical_probes_by_target_ensemblID",
          "arguments": {
              "ensemblId": "example_value"
          }
      }
      result = tu.run(query)


**OpenTargets_get_disease_ancestors_parents_by_efoId** (Type: OpenTarget)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve the disease ancestors and parents in the ontology using the disease EFO ID.

.. dropdown:: OpenTargets_get_disease_ancestors_parents_by_efoId tool specification

   **Tool Information:**

   * **Name**: ``OpenTargets_get_disease_ancestors_parents_by_efoId``
   * **Type**: ``OpenTarget``
   * **Description**: Retrieve the disease ancestors and parents in the ontology using the disease EFO ID.

   **Parameters:**

   * ``efoId`` (string) (required)
     The EFO ID of the disease.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "OpenTargets_get_disease_ancestors_parents_by_efoId",
          "arguments": {
              "efoId": "example_value"
          }
      }
      result = tu.run(query)


**OpenTargets_get_disease_descendants_children_by_efoId** (Type: OpenTarget)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve the disease descendants and children in the ontology using the disease EFO ID.

.. dropdown:: OpenTargets_get_disease_descendants_children_by_efoId tool specification

   **Tool Information:**

   * **Name**: ``OpenTargets_get_disease_descendants_children_by_efoId``
   * **Type**: ``OpenTarget``
   * **Description**: Retrieve the disease descendants and children in the ontology using the disease EFO ID.

   **Parameters:**

   * ``efoId`` (string) (required)
     The EFO ID of the disease.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "OpenTargets_get_disease_descendants_children_by_efoId",
          "arguments": {
              "efoId": "example_value"
          }
      }
      result = tu.run(query)


**OpenTargets_get_disease_description_by_efoId** (Type: OpenTarget)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve disease description, name, database cros references, obsolete terms, and whether it's a ...

.. dropdown:: OpenTargets_get_disease_description_by_efoId tool specification

   **Tool Information:**

   * **Name**: ``OpenTargets_get_disease_description_by_efoId``
   * **Type**: ``OpenTarget``
   * **Description**: Retrieve disease description, name, database cros references, obsolete terms, and whether it's a therapeutic area, all using the specified efoId.

   **Parameters:**

   * ``efoId`` (string) (required)
     The EFO ID of the disease.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "OpenTargets_get_disease_description_by_efoId",
          "arguments": {
              "efoId": "example_value"
          }
      }
      result = tu.run(query)


**OpenTargets_get_disease_id_description_by_name** (Type: OpenTarget)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve the efoId and additional details of a disease based on its name.

.. dropdown:: OpenTargets_get_disease_id_description_by_name tool specification

   **Tool Information:**

   * **Name**: ``OpenTargets_get_disease_id_description_by_name``
   * **Type**: ``OpenTarget``
   * **Description**: Retrieve the efoId and additional details of a disease based on its name.

   **Parameters:**

   * ``diseaseName`` (string) (required)
     The name of the disease to search for.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "OpenTargets_get_disease_id_description_by_name",
          "arguments": {
              "diseaseName": "example_value"
          }
      }
      result = tu.run(query)


**OpenTargets_get_disease_locations_by_efoId** (Type: OpenTarget)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve the disease's direct location and indirect location disease terms and IDs using the dise...

.. dropdown:: OpenTargets_get_disease_locations_by_efoId tool specification

   **Tool Information:**

   * **Name**: ``OpenTargets_get_disease_locations_by_efoId``
   * **Type**: ``OpenTarget``
   * **Description**: Retrieve the disease's direct location and indirect location disease terms and IDs using the disease EFO ID.

   **Parameters:**

   * ``efoId`` (string) (required)
     The EFO ID of the disease.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "OpenTargets_get_disease_locations_by_efoId",
          "arguments": {
              "efoId": "example_value"
          }
      }
      result = tu.run(query)


**OpenTargets_get_disease_synonyms_by_efoId** (Type: OpenTarget)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve disease synonyms by its EFO ID.

.. dropdown:: OpenTargets_get_disease_synonyms_by_efoId tool specification

   **Tool Information:**

   * **Name**: ``OpenTargets_get_disease_synonyms_by_efoId``
   * **Type**: ``OpenTarget``
   * **Description**: Retrieve disease synonyms by its EFO ID.

   **Parameters:**

   * ``efoId`` (string) (required)
     The EFO ID of the disease.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "OpenTargets_get_disease_synonyms_by_efoId",
          "arguments": {
              "efoId": "example_value"
          }
      }
      result = tu.run(query)


**OpenTargets_get_disease_therapeutic_areas_by_efoId** (Type: OpenTarget)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve the therapeutic areas associated with a specific disease efoId.

.. dropdown:: OpenTargets_get_disease_therapeutic_areas_by_efoId tool specification

   **Tool Information:**

   * **Name**: ``OpenTargets_get_disease_therapeutic_areas_by_efoId``
   * **Type**: ``OpenTarget``
   * **Description**: Retrieve the therapeutic areas associated with a specific disease efoId.

   **Parameters:**

   * ``efoId`` (string) (required)
     The EFO ID of the disease.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "OpenTargets_get_disease_therapeutic_areas_by_efoId",
          "arguments": {
              "efoId": "example_value"
          }
      }
      result = tu.run(query)


**OpenTargets_get_diseases_phenotypes_by_target_ensembl** (Type: OpenTarget)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Find diseases or phenotypes associated with a specific target using ensemblId.

.. dropdown:: OpenTargets_get_diseases_phenotypes_by_target_ensembl tool specification

   **Tool Information:**

   * **Name**: ``OpenTargets_get_diseases_phenotypes_by_target_ensembl``
   * **Type**: ``OpenTarget``
   * **Description**: Find diseases or phenotypes associated with a specific target using ensemblId.

   **Parameters:**

   * ``ensemblId`` (string) (required)
     The ensemblId of a target.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "OpenTargets_get_diseases_phenotypes_by_target_ensembl",
          "arguments": {
              "ensemblId": "example_value"
          }
      }
      result = tu.run(query)


**OpenTargets_get_drug_adverse_events_by_chemblId** (Type: OpenTarget)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve significant adverse events reported for a specific drug chemblId.

.. dropdown:: OpenTargets_get_drug_adverse_events_by_chemblId tool specification

   **Tool Information:**

   * **Name**: ``OpenTargets_get_drug_adverse_events_by_chemblId``
   * **Type**: ``OpenTarget``
   * **Description**: Retrieve significant adverse events reported for a specific drug chemblId.

   **Parameters:**

   * ``chemblId`` (string) (required)
     The ChEMBL ID of the drug.

   * ``page`` (object) (optional)
     Pagination settings.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "OpenTargets_get_drug_adverse_events_by_chemblId",
          "arguments": {
              "chemblId": "example_value"
          }
      }
      result = tu.run(query)


**OpenTargets_get_drug_approval_status_by_chemblId** (Type: OpenTarget)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve the approval status of a specific drug chemblId.

.. dropdown:: OpenTargets_get_drug_approval_status_by_chemblId tool specification

   **Tool Information:**

   * **Name**: ``OpenTargets_get_drug_approval_status_by_chemblId``
   * **Type**: ``OpenTarget``
   * **Description**: Retrieve the approval status of a specific drug chemblId.

   **Parameters:**

   * ``chemblId`` (string) (required)
     The ChEMBL ID of the drug.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "OpenTargets_get_drug_approval_status_by_chemblId",
          "arguments": {
              "chemblId": "example_value"
          }
      }
      result = tu.run(query)


**OpenTargets_get_drug_chembId_by_generic_name** (Type: OpentargetToolDrugNameMatch)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Fetch the drug chemblId and description based on the drug generic name.

.. dropdown:: OpenTargets_get_drug_chembId_by_generic_name tool specification

   **Tool Information:**

   * **Name**: ``OpenTargets_get_drug_chembId_by_generic_name``
   * **Type**: ``OpentargetToolDrugNameMatch``
   * **Description**: Fetch the drug chemblId and description based on the drug generic name.

   **Parameters:**

   * ``drugName`` (string) (required)
     The generic name of the drug for which the ID is required.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "OpenTargets_get_drug_chembId_by_generic_name",
          "arguments": {
              "drugName": "example_value"
          }
      }
      result = tu.run(query)


**OpenTargets_get_drug_description_by_chemblId** (Type: OpenTarget)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get drug name, year of first approval, type, cross references, and max clinical trial phase based...

.. dropdown:: OpenTargets_get_drug_description_by_chemblId tool specification

   **Tool Information:**

   * **Name**: ``OpenTargets_get_drug_description_by_chemblId``
   * **Type**: ``OpenTarget``
   * **Description**: Get drug name, year of first approval, type, cross references, and max clinical trial phase based on specified chemblId.

   **Parameters:**

   * ``chemblId`` (string) (required)
     The ChEMBL ID of the drug.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "OpenTargets_get_drug_description_by_chemblId",
          "arguments": {
              "chemblId": "example_value"
          }
      }
      result = tu.run(query)


**OpenTargets_get_drug_id_description_by_name** (Type: OpentargetToolDrugNameMatch)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Fetch the drug chemblId and description based on the drug generic name.

.. dropdown:: OpenTargets_get_drug_id_description_by_name tool specification

   **Tool Information:**

   * **Name**: ``OpenTargets_get_drug_id_description_by_name``
   * **Type**: ``OpentargetToolDrugNameMatch``
   * **Description**: Fetch the drug chemblId and description based on the drug generic name.

   **Parameters:**

   * ``drugName`` (string) (required)
     The name of the drug for which the ID is required.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "OpenTargets_get_drug_id_description_by_name",
          "arguments": {
              "drugName": "example_value"
          }
      }
      result = tu.run(query)


**OpenTargets_get_drug_indications_by_chemblId** (Type: OpenTarget)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Fetch indications (treatable phenotypes/diseases) for a given drug chemblId.

.. dropdown:: OpenTargets_get_drug_indications_by_chemblId tool specification

   **Tool Information:**

   * **Name**: ``OpenTargets_get_drug_indications_by_chemblId``
   * **Type**: ``OpenTarget``
   * **Description**: Fetch indications (treatable phenotypes/diseases) for a given drug chemblId.

   **Parameters:**

   * ``chemblId`` (string) (required)
     The chemblId of the drug for which to retrieve treatable phenotypes information.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "OpenTargets_get_drug_indications_by_chemblId",
          "arguments": {
              "chemblId": "example_value"
          }
      }
      result = tu.run(query)


**OpenTargets_get_drug_mechanisms_of_action_by_chemblId** (Type: OpenTarget)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve the mechanisms of action associated with a specific drug using chemblId.

.. dropdown:: OpenTargets_get_drug_mechanisms_of_action_by_chemblId tool specification

   **Tool Information:**

   * **Name**: ``OpenTargets_get_drug_mechanisms_of_action_by_chemblId``
   * **Type**: ``OpenTarget``
   * **Description**: Retrieve the mechanisms of action associated with a specific drug using chemblId.

   **Parameters:**

   * ``chemblId`` (string) (required)
     The ChEMBL ID of the drug.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "OpenTargets_get_drug_mechanisms_of_action_by_chemblId",
          "arguments": {
              "chemblId": "example_value"
          }
      }
      result = tu.run(query)


**OpenTargets_get_drug_names_by_chemblId** (Type: OpenTarget)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get drug generic name and brand names (trade names) based on ChEMBL ID. Returns the drug name (ty...

.. dropdown:: OpenTargets_get_drug_names_by_chemblId tool specification

   **Tool Information:**

   * **Name**: ``OpenTargets_get_drug_names_by_chemblId``
   * **Type**: ``OpenTarget``
   * **Description**: Get drug generic name and brand names (trade names) based on ChEMBL ID. Returns the drug name (typically generic name), trade names (brand names), and synonyms.

   **Parameters:**

   * ``chemblId`` (string) (required)
     The ChEMBL ID of the drug.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "OpenTargets_get_drug_names_by_chemblId",
          "arguments": {
              "chemblId": "example_value"
          }
      }
      result = tu.run(query)


**OpenTargets_get_drug_synonyms_by_chemblId** (Type: OpenTarget)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve the synonyms associated with a specific drug chemblId.

.. dropdown:: OpenTargets_get_drug_synonyms_by_chemblId tool specification

   **Tool Information:**

   * **Name**: ``OpenTargets_get_drug_synonyms_by_chemblId``
   * **Type**: ``OpenTarget``
   * **Description**: Retrieve the synonyms associated with a specific drug chemblId.

   **Parameters:**

   * ``chemblId`` (string) (required)
     The ChEMBL ID of the drug.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "OpenTargets_get_drug_synonyms_by_chemblId",
          "arguments": {
              "chemblId": "example_value"
          }
      }
      result = tu.run(query)


**OpenTargets_get_drug_trade_names_by_chemblId** (Type: OpenTarget)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve the trade names associated with a specific drug chemblId.

.. dropdown:: OpenTargets_get_drug_trade_names_by_chemblId tool specification

   **Tool Information:**

   * **Name**: ``OpenTargets_get_drug_trade_names_by_chemblId``
   * **Type**: ``OpenTarget``
   * **Description**: Retrieve the trade names associated with a specific drug chemblId.

   **Parameters:**

   * ``chemblId`` (string) (required)
     The ChEMBL ID of the drug.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "OpenTargets_get_drug_trade_names_by_chemblId",
          "arguments": {
              "chemblId": "example_value"
          }
      }
      result = tu.run(query)


**OpenTargets_get_drug_warnings_by_chemblId** (Type: OpenTarget)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve warnings for a specific drug using ChEMBL ID.

.. dropdown:: OpenTargets_get_drug_warnings_by_chemblId tool specification

   **Tool Information:**

   * **Name**: ``OpenTargets_get_drug_warnings_by_chemblId``
   * **Type**: ``OpenTarget``
   * **Description**: Retrieve warnings for a specific drug using ChEMBL ID.

   **Parameters:**

   * ``chemblId`` (string) (required)
     The ChEMBL ID of the drug.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "OpenTargets_get_drug_warnings_by_chemblId",
          "arguments": {
              "chemblId": "example_value"
          }
      }
      result = tu.run(query)


**OpenTargets_get_drug_withdrawn_blackbox_status_by_chemblId** (Type: OpenTarget)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Find withdrawn and black-box warning statuses for a specific drug by chemblId.

.. dropdown:: OpenTargets_get_drug_withdrawn_blackbox_status_by_chemblId tool specification

   **Tool Information:**

   * **Name**: ``OpenTargets_get_drug_withdrawn_blackbox_status_by_chemblId``
   * **Type**: ``OpenTarget``
   * **Description**: Find withdrawn and black-box warning statuses for a specific drug by chemblId.

   **Parameters:**

   * ``chemblId`` (array) (required)
     The chemblId of a drug.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "OpenTargets_get_drug_withdrawn_blackbox_status_by_chemblId",
          "arguments": {
              "chemblId": ["item1", "item2"]
          }
      }
      result = tu.run(query)


**OpenTargets_get_gene_ontology_terms_by_goID** (Type: OpenTarget)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve Gene Ontology terms based on a list of GO IDs.

.. dropdown:: OpenTargets_get_gene_ontology_terms_by_goID tool specification

   **Tool Information:**

   * **Name**: ``OpenTargets_get_gene_ontology_terms_by_goID``
   * **Type**: ``OpenTarget``
   * **Description**: Retrieve Gene Ontology terms based on a list of GO IDs.

   **Parameters:**

   * ``goIds`` (array) (required)
     A list of Gene Ontology (GO) IDs to fetch the corresponding terms.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "OpenTargets_get_gene_ontology_terms_by_goID",
          "arguments": {
              "goIds": ["item1", "item2"]
          }
      }
      result = tu.run(query)


**OpenTargets_get_known_drugs_by_drug_chemblId** (Type: OpenTarget)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get a list of known drugs and associated information using the specified chemblId.

.. dropdown:: OpenTargets_get_known_drugs_by_drug_chemblId tool specification

   **Tool Information:**

   * **Name**: ``OpenTargets_get_known_drugs_by_drug_chemblId``
   * **Type**: ``OpenTarget``
   * **Description**: Get a list of known drugs and associated information using the specified chemblId.

   **Parameters:**

   * ``chemblId`` (string) (required)
     The ChEMBL ID of the drug.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "OpenTargets_get_known_drugs_by_drug_chemblId",
          "arguments": {
              "chemblId": "example_value"
          }
      }
      result = tu.run(query)


**OpenTargets_get_parent_child_molecules_by_drug_chembl_ID** (Type: OpenTarget)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get parent and child molecules of specified drug chemblId.

.. dropdown:: OpenTargets_get_parent_child_molecules_by_drug_chembl_ID tool specification

   **Tool Information:**

   * **Name**: ``OpenTargets_get_parent_child_molecules_by_drug_chembl_ID``
   * **Type**: ``OpenTarget``
   * **Description**: Get parent and child molecules of specified drug chemblId.

   **Parameters:**

   * ``chemblId`` (string) (required)
     The ChEMBL ID of the drug.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "OpenTargets_get_parent_child_molecules_by_drug_chembl_ID",
          "arguments": {
              "chemblId": "example_value"
          }
      }
      result = tu.run(query)


**OpenTargets_get_publications_by_disease_efoId** (Type: OpenTarget)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve publications related to a disease efoId, including PubMed IDs and publication dates.

.. dropdown:: OpenTargets_get_publications_by_disease_efoId tool specification

   **Tool Information:**

   * **Name**: ``OpenTargets_get_publications_by_disease_efoId``
   * **Type**: ``OpenTarget``
   * **Description**: Retrieve publications related to a disease efoId, including PubMed IDs and publication dates.

   **Parameters:**

   * ``entityId`` (string) (required)
     The ID of the entity (efoId).

   * ``additionalIds`` (array) (optional)
     List of additional IDs to include in the search.

   * ``startYear`` (integer) (optional)
     Year at the lower end of the filter.

   * ``startMonth`` (integer) (optional)
     Month at the lower end of the filter.

   * ``endYear`` (integer) (optional)
     Year at the higher end of the filter.

   * ``endMonth`` (integer) (optional)
     Month at the higher end of the filter.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "OpenTargets_get_publications_by_disease_efoId",
          "arguments": {
              "entityId": "example_value"
          }
      }
      result = tu.run(query)


**OpenTargets_get_publications_by_drug_chemblId** (Type: OpenTarget)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve publications related to a drug chemblId, including PubMed IDs and publication dates.

.. dropdown:: OpenTargets_get_publications_by_drug_chemblId tool specification

   **Tool Information:**

   * **Name**: ``OpenTargets_get_publications_by_drug_chemblId``
   * **Type**: ``OpenTarget``
   * **Description**: Retrieve publications related to a drug chemblId, including PubMed IDs and publication dates.

   **Parameters:**

   * ``entityId`` (string) (required)
     The ID of the entity (chemblId).

   * ``additionalIds`` (array) (optional)
     List of additional IDs to include in the search.

   * ``startYear`` (integer) (optional)
     Year at the lower end of the filter.

   * ``startMonth`` (integer) (optional)
     Month at the lower end of the filter.

   * ``endYear`` (integer) (optional)
     Year at the higher end of the filter.

   * ``endMonth`` (integer) (optional)
     Month at the higher end of the filter.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "OpenTargets_get_publications_by_drug_chemblId",
          "arguments": {
              "entityId": "example_value"
          }
      }
      result = tu.run(query)


**OpenTargets_get_publications_by_target_ensemblID** (Type: OpenTarget)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve publications related to a target ensemblID, including PubMed IDs and publication dates.

.. dropdown:: OpenTargets_get_publications_by_target_ensemblID tool specification

   **Tool Information:**

   * **Name**: ``OpenTargets_get_publications_by_target_ensemblID``
   * **Type**: ``OpenTarget``
   * **Description**: Retrieve publications related to a target ensemblID, including PubMed IDs and publication dates.

   **Parameters:**

   * ``entityId`` (string) (required)
     The ID of the entity (ensemblID).

   * ``additionalIds`` (array) (optional)
     List of additional IDs to include in the search.

   * ``startYear`` (integer) (optional)
     Year at the lower end of the filter.

   * ``startMonth`` (integer) (optional)
     Month at the lower end of the filter.

   * ``endYear`` (integer) (optional)
     Year at the higher end of the filter.

   * ``endMonth`` (integer) (optional)
     Month at the higher end of the filter.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "OpenTargets_get_publications_by_target_ensemblID",
          "arguments": {
              "entityId": "example_value"
          }
      }
      result = tu.run(query)


**OpenTargets_get_similar_entities_by_disease_efoId** (Type: OpenTarget)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve similar entities for a given disease efoId using a model trained with PubMed.

.. dropdown:: OpenTargets_get_similar_entities_by_disease_efoId tool specification

   **Tool Information:**

   * **Name**: ``OpenTargets_get_similar_entities_by_disease_efoId``
   * **Type**: ``OpenTarget``
   * **Description**: Retrieve similar entities for a given disease efoId using a model trained with PubMed.

   **Parameters:**

   * ``efoId`` (string) (required)
     The EFO ID of the disease.

   * ``threshold`` (number) (required)
     Threshold similarity between 0 and 1. Only results above threshold are returned.

   * ``size`` (integer) (required)
     Number of similar entities to fetch.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "OpenTargets_get_similar_entities_by_disease_efoId",
          "arguments": {
              "efoId": "example_value",
              "threshold": "example_value",
              "size": 10
          }
      }
      result = tu.run(query)


**OpenTargets_get_similar_entities_by_drug_chemblId** (Type: OpenTarget)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve similar entities for a given drug chemblId using a model trained with PubMed.

.. dropdown:: OpenTargets_get_similar_entities_by_drug_chemblId tool specification

   **Tool Information:**

   * **Name**: ``OpenTargets_get_similar_entities_by_drug_chemblId``
   * **Type**: ``OpenTarget``
   * **Description**: Retrieve similar entities for a given drug chemblId using a model trained with PubMed.

   **Parameters:**

   * ``chemblId`` (string) (required)
     The chemblId of the disease.

   * ``threshold`` (number) (required)
     Threshold similarity between 0 and 1. Only results above threshold are returned.

   * ``size`` (integer) (required)
     Number of similar entities to fetch.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "OpenTargets_get_similar_entities_by_drug_chemblId",
          "arguments": {
              "chemblId": "example_value",
              "threshold": "example_value",
              "size": 10
          }
      }
      result = tu.run(query)


**OpenTargets_get_similar_entities_by_target_ensemblID** (Type: OpenTarget)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve similar entities for a given target ensemblID using a model trained with PubMed.

.. dropdown:: OpenTargets_get_similar_entities_by_target_ensemblID tool specification

   **Tool Information:**

   * **Name**: ``OpenTargets_get_similar_entities_by_target_ensemblID``
   * **Type**: ``OpenTarget``
   * **Description**: Retrieve similar entities for a given target ensemblID using a model trained with PubMed.

   **Parameters:**

   * ``ensemblId`` (string) (required)
     The ensemblID of the disease.

   * ``threshold`` (number) (required)
     Threshold similarity between 0 and 1. Only results above threshold are returned.

   * ``size`` (integer) (required)
     Number of similar entities to fetch.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "OpenTargets_get_similar_entities_by_target_ensemblID",
          "arguments": {
              "ensemblId": "example_value",
              "threshold": "example_value",
              "size": 10
          }
      }
      result = tu.run(query)


**OpenTargets_get_target_classes_by_ensemblID** (Type: OpenTarget)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve the target classes associated with a specific target ensemblID.

.. dropdown:: OpenTargets_get_target_classes_by_ensemblID tool specification

   **Tool Information:**

   * **Name**: ``OpenTargets_get_target_classes_by_ensemblID``
   * **Type**: ``OpenTarget``
   * **Description**: Retrieve the target classes associated with a specific target ensemblID.

   **Parameters:**

   * ``ensemblId`` (string) (required)
     The Ensembl ID of the target.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "OpenTargets_get_target_classes_by_ensemblID",
          "arguments": {
              "ensemblId": "example_value"
          }
      }
      result = tu.run(query)


**OpenTargets_get_target_constraint_info_by_ensemblID** (Type: OpenTarget)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve genetic constraint information for a specific target ensemblID, including expected and o...

.. dropdown:: OpenTargets_get_target_constraint_info_by_ensemblID tool specification

   **Tool Information:**

   * **Name**: ``OpenTargets_get_target_constraint_info_by_ensemblID``
   * **Type**: ``OpenTarget``
   * **Description**: Retrieve genetic constraint information for a specific target ensemblID, including expected and observed values, and scores.

   **Parameters:**

   * ``ensemblId`` (string) (required)
     The Ensembl ID of the target.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "OpenTargets_get_target_constraint_info_by_ensemblID",
          "arguments": {
              "ensemblId": "example_value"
          }
      }
      result = tu.run(query)


**OpenTargets_get_target_enabling_packages_by_ensemblID** (Type: OpenTarget)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve the Target Enabling Packages (TEP) associated with a specific target ensemblID.

.. dropdown:: OpenTargets_get_target_enabling_packages_by_ensemblID tool specification

   **Tool Information:**

   * **Name**: ``OpenTargets_get_target_enabling_packages_by_ensemblID``
   * **Type**: ``OpenTarget``
   * **Description**: Retrieve the Target Enabling Packages (TEP) associated with a specific target ensemblID.

   **Parameters:**

   * ``ensemblId`` (string) (required)
     The Ensembl ID of the target.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "OpenTargets_get_target_enabling_packages_by_ensemblID",
          "arguments": {
              "ensemblId": "example_value"
          }
      }
      result = tu.run(query)


**OpenTargets_get_target_gene_ontology_by_ensemblID** (Type: OpenTarget)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve Gene Ontology annotations for a specific target by Ensembl ID.

.. dropdown:: OpenTargets_get_target_gene_ontology_by_ensemblID tool specification

   **Tool Information:**

   * **Name**: ``OpenTargets_get_target_gene_ontology_by_ensemblID``
   * **Type**: ``OpenTarget``
   * **Description**: Retrieve Gene Ontology annotations for a specific target by Ensembl ID.

   **Parameters:**

   * ``ensemblId`` (string) (required)
     The Ensembl ID of the target for which to retrieve Gene Ontology annotations.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "OpenTargets_get_target_gene_ontology_by_ensemblID",
          "arguments": {
              "ensemblId": "example_value"
          }
      }
      result = tu.run(query)


**OpenTargets_get_target_genomic_location_by_ensemblID** (Type: OpenTarget)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve genomic location data for a specific target, including chromosome, start, end, and strand.

.. dropdown:: OpenTargets_get_target_genomic_location_by_ensemblID tool specification

   **Tool Information:**

   * **Name**: ``OpenTargets_get_target_genomic_location_by_ensemblID``
   * **Type**: ``OpenTarget``
   * **Description**: Retrieve genomic location data for a specific target, including chromosome, start, end, and strand.

   **Parameters:**

   * ``ensemblId`` (string) (required)
     The Ensembl ID of the target for which to retrieve genomic location information.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "OpenTargets_get_target_genomic_location_by_ensemblID",
          "arguments": {
              "ensemblId": "example_value"
          }
      }
      result = tu.run(query)


**OpenTargets_get_target_homologues_by_ensemblID** (Type: OpenTarget)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Fetch homologues for a specific target by Ensembl ID.

.. dropdown:: OpenTargets_get_target_homologues_by_ensemblID tool specification

   **Tool Information:**

   * **Name**: ``OpenTargets_get_target_homologues_by_ensemblID``
   * **Type**: ``OpenTarget``
   * **Description**: Fetch homologues for a specific target by Ensembl ID.

   **Parameters:**

   * ``ensemblId`` (string) (required)
     The Ensembl ID of the target for which to retrieve homologues.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "OpenTargets_get_target_homologues_by_ensemblID",
          "arguments": {
              "ensemblId": "example_value"
          }
      }
      result = tu.run(query)


**OpenTargets_get_target_id_description_by_name** (Type: OpenTarget)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get the ensemblId and description based on the target name.

.. dropdown:: OpenTargets_get_target_id_description_by_name tool specification

   **Tool Information:**

   * **Name**: ``OpenTargets_get_target_id_description_by_name``
   * **Type**: ``OpenTarget``
   * **Description**: Get the ensemblId and description based on the target name.

   **Parameters:**

   * ``targetName`` (string) (required)
     The name of the target for which the ID is required.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "OpenTargets_get_target_id_description_by_name",
          "arguments": {
              "targetName": "example_value"
          }
      }
      result = tu.run(query)


**OpenTargets_get_target_interactions_by_ensemblID** (Type: OpenTarget)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve interaction data for a specific target ensemblID, including interaction partners and evi...

.. dropdown:: OpenTargets_get_target_interactions_by_ensemblID tool specification

   **Tool Information:**

   * **Name**: ``OpenTargets_get_target_interactions_by_ensemblID``
   * **Type**: ``OpenTarget``
   * **Description**: Retrieve interaction data for a specific target ensemblID, including interaction partners and evidence.

   **Parameters:**

   * ``ensemblId`` (string) (required)
     The Ensembl ID of the target.

   * ``page`` (object) (optional)
     Pagination parameters.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "OpenTargets_get_target_interactions_by_ensemblID",
          "arguments": {
              "ensemblId": "example_value"
          }
      }
      result = tu.run(query)


**OpenTargets_get_target_safety_profile_by_ensemblID** (Type: OpenTarget)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve known target safety liabilities for a specific target Ensembl ID.

.. dropdown:: OpenTargets_get_target_safety_profile_by_ensemblID tool specification

   **Tool Information:**

   * **Name**: ``OpenTargets_get_target_safety_profile_by_ensemblID``
   * **Type**: ``OpenTarget``
   * **Description**: Retrieve known target safety liabilities for a specific target Ensembl ID.

   **Parameters:**

   * ``ensemblId`` (string) (required)
     The Ensembl ID of the target for which to retrieve safety liabilities.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "OpenTargets_get_target_safety_profile_by_ensemblID",
          "arguments": {
              "ensemblId": "example_value"
          }
      }
      result = tu.run(query)


**OpenTargets_get_target_subcellular_locations_by_ensemblID** (Type: OpenTarget)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve information about subcellular locations for a specific target ensemblID.

.. dropdown:: OpenTargets_get_target_subcellular_locations_by_ensemblID tool specification

   **Tool Information:**

   * **Name**: ``OpenTargets_get_target_subcellular_locations_by_ensemblID``
   * **Type**: ``OpenTarget``
   * **Description**: Retrieve information about subcellular locations for a specific target ensemblID.

   **Parameters:**

   * ``ensemblId`` (string) (required)
     The ensemblId of a target.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "OpenTargets_get_target_subcellular_locations_by_ensemblID",
          "arguments": {
              "ensemblId": "example_value"
          }
      }
      result = tu.run(query)


**OpenTargets_get_target_synonyms_by_ensemblID** (Type: OpenTarget)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve synonyms for specified target, including alternative names and symbols, using given ense...

.. dropdown:: OpenTargets_get_target_synonyms_by_ensemblID tool specification

   **Tool Information:**

   * **Name**: ``OpenTargets_get_target_synonyms_by_ensemblID``
   * **Type**: ``OpenTarget``
   * **Description**: Retrieve synonyms for specified target, including alternative names and symbols, using given ensemblID.

   **Parameters:**

   * ``ensemblId`` (string) (required)
     The Ensembl ID of the target.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "OpenTargets_get_target_synonyms_by_ensemblID",
          "arguments": {
              "ensemblId": "example_value"
          }
      }
      result = tu.run(query)


**OpenTargets_get_target_tractability_by_ensemblID** (Type: OpenTarget)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve tractability assessments, including modality and values, for a specific target ensembl ID.

.. dropdown:: OpenTargets_get_target_tractability_by_ensemblID tool specification

   **Tool Information:**

   * **Name**: ``OpenTargets_get_target_tractability_by_ensemblID``
   * **Type**: ``OpenTarget``
   * **Description**: Retrieve tractability assessments, including modality and values, for a specific target ensembl ID.

   **Parameters:**

   * ``ensemblId`` (string) (required)
     The Ensembl ID of the target.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "OpenTargets_get_target_tractability_by_ensemblID",
          "arguments": {
              "ensemblId": "example_value"
          }
      }
      result = tu.run(query)


**OpenTargets_multi_entity_search_by_query_string** (Type: OpenTarget)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Perform a multi-entity search based on a query string, filtering by entity names and pagination s...

.. dropdown:: OpenTargets_multi_entity_search_by_query_string tool specification

   **Tool Information:**

   * **Name**: ``OpenTargets_multi_entity_search_by_query_string``
   * **Type**: ``OpenTarget``
   * **Description**: Perform a multi-entity search based on a query string, filtering by entity names and pagination settings.

   **Parameters:**

   * ``queryString`` (string) (required)
     The search string for querying information.

   * ``entityNames`` (array) (optional)
     List of entity names to search for (e.g., target, disease, drug).

   * ``page`` (object) (optional)
     Pagination settings with index and size.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "OpenTargets_multi_entity_search_by_query_string",
          "arguments": {
              "queryString": "example_value"
          }
      }
      result = tu.run(query)


**OpenTargets_search_category_counts_by_query_string** (Type: OpenTarget)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get the count of entries in each entity category (disease, target, drug) based on a query string.

.. dropdown:: OpenTargets_search_category_counts_by_query_string tool specification

   **Tool Information:**

   * **Name**: ``OpenTargets_search_category_counts_by_query_string``
   * **Type**: ``OpenTarget``
   * **Description**: Get the count of entries in each entity category (disease, target, drug) based on a query string.

   **Parameters:**

   * ``queryString`` (string) (required)
     The search string for querying information.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "OpenTargets_search_category_counts_by_query_string",
          "arguments": {
              "queryString": "example_value"
          }
      }
      result = tu.run(query)


**OpenTargets_target_disease_evidence** (Type: OpenTarget)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Explore evidence that supports a specific target-disease association. Input is disease efoId and ...

.. dropdown:: OpenTargets_target_disease_evidence tool specification

   **Tool Information:**

   * **Name**: ``OpenTargets_target_disease_evidence``
   * **Type**: ``OpenTarget``
   * **Description**: Explore evidence that supports a specific target-disease association. Input is disease efoId and target ensemblID.

   **Parameters:**

   * ``efoId`` (string) (required)
     The efoId of a disease or phenotype.

   * ``ensemblId`` (string) (required)
     The ensemblId of a target.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "OpenTargets_target_disease_evidence",
          "arguments": {
              "efoId": "example_value",
              "ensemblId": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
