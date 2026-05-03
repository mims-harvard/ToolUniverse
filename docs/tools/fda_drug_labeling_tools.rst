Fda Drug Labeling Tools
=======================

**Configuration File**: ``fda_drug_labeling_tools.json``
**Tool Type**: Local
**Tools Count**: 158

This page contains all tools defined in the ``fda_drug_labeling_tools.json`` configuration file.

Available Tools
---------------

**FDA_get_abuse_dependence_info_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get information about drug abuse and dependence based on the drug name, specifically information ...

.. dropdown:: FDA_get_abuse_dependence_info_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_abuse_dependence_info_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Get information about drug abuse and dependence based on the drug name, specifically information on whether the drug is a controlled substances, the types of possible abuse, and adverse reactions relevant to those abuse types.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_abuse_dependence_info_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_abuse_info_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve information about types of abuse based on the drug name.

.. dropdown:: FDA_get_abuse_info_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_abuse_info_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve information about types of abuse based on the drug name.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_abuse_info_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_accessories_info_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve information about accessories based on the drug name.

.. dropdown:: FDA_get_accessories_info_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_accessories_info_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve information about accessories based on the drug name.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_accessories_info_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_active_ingredient_info_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Fetch a list of active ingredients in a specific drug product.

.. dropdown:: FDA_get_active_ingredient_info_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_active_ingredient_info_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Fetch a list of active ingredients in a specific drug product.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_active_ingredient_info_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_adverse_reactions_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve adverse reactions information based on the drug name.

.. dropdown:: FDA_get_adverse_reactions_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_adverse_reactions_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve adverse reactions information based on the drug name.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_adverse_reactions_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_alarms_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve alarms based on the specified drug name.

.. dropdown:: FDA_get_alarms_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_alarms_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve alarms based on the specified drug name.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_alarms_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_animal_pharmacology_info_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve animal pharmacology and toxicology information based on drug names.

.. dropdown:: FDA_get_animal_pharmacology_info_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_animal_pharmacology_info_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve animal pharmacology and toxicology information based on drug names.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_animal_pharmacology_info_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_assembly_installation_info_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve assembly or installation instructions based on drug names.

.. dropdown:: FDA_get_assembly_installation_info_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_assembly_installation_info_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve assembly or installation instructions based on drug names.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_assembly_installation_info_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_boxed_warning_info_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve boxed warning and adverse effects information for a specific drug.

.. dropdown:: FDA_get_boxed_warning_info_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_boxed_warning_info_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve boxed warning and adverse effects information for a specific drug.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_boxed_warning_info_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_brand_name_generic_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve the brand name and generic name from generic name or brand name of a drug.

.. dropdown:: FDA_get_brand_name_generic_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_brand_name_generic_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve the brand name and generic name from generic name or brand name of a drug.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The generic name or the brand name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_brand_name_generic_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_calibration_instructions_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve calibration instructions based on the specified drug name.

.. dropdown:: FDA_get_calibration_instructions_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_calibration_instructions_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve calibration instructions based on the specified drug name.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_calibration_instructions_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_carcinogenic_mutagenic_fertility_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve carcinogenic, mutagenic, or fertility impairment information based on the drug name.

.. dropdown:: FDA_get_carcinogenic_mutagenic_fertility_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_carcinogenic_mutagenic_fertility_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve carcinogenic, mutagenic, or fertility impairment information based on the drug name.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_carcinogenic_mutagenic_fertility_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_child_safety_info_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve child safety information for a specific drug based on its name.

.. dropdown:: FDA_get_child_safety_info_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_child_safety_info_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve child safety information for a specific drug based on its name.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_child_safety_info_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_clinical_pharmacology_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve clinical pharmacology information based on drug names.

.. dropdown:: FDA_get_clinical_pharmacology_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_clinical_pharmacology_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve clinical pharmacology information based on drug names.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_clinical_pharmacology_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_clinical_studies_info_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve clinical studies information based on the drug name.

.. dropdown:: FDA_get_clinical_studies_info_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_clinical_studies_info_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve clinical studies information based on the drug name.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_clinical_studies_info_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_contact_for_questions_info_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve information on who to contact with questions about the drug based on the provided drug n...

.. dropdown:: FDA_get_contact_for_questions_info_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_contact_for_questions_info_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve information on who to contact with questions about the drug based on the provided drug name.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_contact_for_questions_info_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_contraindications_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve contraindications information based on the drug name.

.. dropdown:: FDA_get_contraindications_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_contraindications_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve contraindications information based on the drug name.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_contraindications_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_controlled_substance_DEA_schedule_info_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve information about the controlled substance Drug Enforcement Administratino (DEA) schedul...

.. dropdown:: FDA_get_controlled_substance_DEA_schedule_info_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_controlled_substance_DEA_schedule_info_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve information about the controlled substance Drug Enforcement Administratino (DEA) schedule for a specific drug.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_controlled_substance_DEA_schedule_info_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_dear_health_care_provider_letter_info_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Fetch information about dear health care provider letters for a specific drug. The letters are se...

.. dropdown:: FDA_get_dear_health_care_provider_letter_info_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_dear_health_care_provider_letter_info_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Fetch information about dear health care provider letters for a specific drug. The letters are sent by drug manufacturers to provide new or updated information about the drug.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_dear_health_care_provider_letter_info_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_dependence_info_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve information about dependence characteristics based on the drug name.

.. dropdown:: FDA_get_dependence_info_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_dependence_info_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve information about dependence characteristics based on the drug name.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_dependence_info_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_disposal_info_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve disposal and waste handling information based on the drug name.

.. dropdown:: FDA_get_disposal_info_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_disposal_info_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve disposal and waste handling information based on the drug name.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_disposal_info_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_do_not_use_info_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve information about all contraindications for use based on the drug name.

.. dropdown:: FDA_get_do_not_use_info_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_do_not_use_info_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve information about all contraindications for use based on the drug name.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_do_not_use_info_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_document_id_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve the document ID based on the drug name.

.. dropdown:: FDA_get_document_id_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_document_id_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve the document ID based on the drug name.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_document_id_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_dosage_and_storage_information_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve dosage and storage information for a specific drug.

.. dropdown:: FDA_get_dosage_and_storage_information_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_dosage_and_storage_information_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve dosage and storage information for a specific drug.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_dosage_and_storage_information_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_dosage_forms_and_strengths_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve dosage forms and strengths information based on the drug name.

.. dropdown:: FDA_get_dosage_forms_and_strengths_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_dosage_forms_and_strengths_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve dosage forms and strengths information based on the drug name.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_dosage_forms_and_strengths_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_generic_name** (Type: FDADrugLabelGetDrugGenericNameTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get the drug’s generic name based on the drug's generic or brand name.

.. dropdown:: FDA_get_drug_generic_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_generic_name``
   * **Type**: ``FDADrugLabelGetDrugGenericNameTool``
   * **Description**: Get the drug’s generic name based on the drug's generic or brand name.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The generic or brand name of the drug.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_generic_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_interactions_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve drug interactions based on the specified drug name.

.. dropdown:: FDA_get_drug_interactions_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_interactions_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve drug interactions based on the specified drug name.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_interactions_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_name_by_SPL_ID** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve the drug name based on the FDA application number, NUI unique identifier, document ID of...

.. dropdown:: FDA_get_drug_name_by_SPL_ID tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_name_by_SPL_ID``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve the drug name based on the FDA application number, NUI unique identifier, document ID of a specific version of the drug's Structured Product Label (SPL), or set ID of the drug's Structured Product Label that works across label versions.

   **Parameters:**

   * ``field_info`` (string) (required)
     The specific field information to search for.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_name_by_SPL_ID",
          "arguments": {
              "field_info": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_name_by_adverse_reaction** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve the drug name based on specific adverse reactions reported. Warning: This tool only outp...

.. dropdown:: FDA_get_drug_name_by_adverse_reaction tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_name_by_adverse_reaction``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve the drug name based on specific adverse reactions reported. Warning: This tool only outputs a predefined limited number of drug names and does not cover all possible drugs. Use with caution.

   **Parameters:**

   * ``adverse_reaction`` (string) (required)
     The adverse reaction to search for.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_name_by_adverse_reaction",
          "arguments": {
              "adverse_reaction": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_name_by_calibration_instructions** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve the drug name based on the calibration instructions provided.

.. dropdown:: FDA_get_drug_name_by_calibration_instructions tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_name_by_calibration_instructions``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve the drug name based on the calibration instructions provided.

   **Parameters:**

   * ``calibration_instructions`` (string) (required)
     Instructions used for calibration of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_name_by_calibration_instructions",
          "arguments": {
              "calibration_instructions": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_name_by_dependence_info** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve the drug name based on information about dependence characteristics.

.. dropdown:: FDA_get_drug_name_by_dependence_info tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_name_by_dependence_info``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve the drug name based on information about dependence characteristics.

   **Parameters:**

   * ``dependence_info`` (string) (required)
     Information related to psychological and physical dependence of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_name_by_dependence_info",
          "arguments": {
              "dependence_info": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_name_by_document_id** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve the drug name based on the document ID.

.. dropdown:: FDA_get_drug_name_by_document_id tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_name_by_document_id``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve the drug name based on the document ID.

   **Parameters:**

   * ``document_id`` (string) (required)
     The document ID, a globally unique identifier (GUID) for the particular revision of a labeling document.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_name_by_document_id",
          "arguments": {
              "document_id": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_name_by_dosage_info** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve the drug name based on dosage and administration information.

.. dropdown:: FDA_get_drug_name_by_dosage_info tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_name_by_dosage_info``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve the drug name based on dosage and administration information.

   **Parameters:**

   * ``dosage_info`` (string) (required)
     Information about the drug product’s dosage and administration recommendations.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_name_by_dosage_info",
          "arguments": {
              "dosage_info": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_name_by_environmental_warning** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve the drug name based on the specified environmental warnings.

.. dropdown:: FDA_get_drug_name_by_environmental_warning tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_name_by_environmental_warning``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve the drug name based on the specified environmental warnings.

   **Parameters:**

   * ``environmental_warning`` (string) (required)
     The environmental warning text to search for.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_name_by_environmental_warning",
          "arguments": {
              "environmental_warning": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_name_by_inactive_ingredient** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve the drug name based on the inactive ingredient information.

.. dropdown:: FDA_get_drug_name_by_inactive_ingredient tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_name_by_inactive_ingredient``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve the drug name based on the inactive ingredient information.

   **Parameters:**

   * ``inactive_ingredient`` (string) (required)
     The name of the inactive ingredient.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_name_by_inactive_ingredient",
          "arguments": {
              "inactive_ingredient": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_name_by_info_on_conditions_for_doctor_consultation** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve the drug names that require asking a doctor before use due to a patient's specific condi...

.. dropdown:: FDA_get_drug_name_by_info_on_conditions_for_doctor_consultation tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_name_by_info_on_conditions_for_doctor_consultation``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve the drug names that require asking a doctor before use due to a patient's specific conditions and symptoms.  Warning: This tool only outputs a predefined limited number of drug names and does not cover all possible drugs. Use with caution.

   **Parameters:**

   * ``condition`` (string) (required)
     The condition or symptom that requires consulting a doctor.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_name_by_info_on_conditions_for_doctor_consultation",
          "arguments": {
              "condition": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_name_by_labor_and_delivery_info** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve the drug name based on information about the drug’s use during labor or delivery.

.. dropdown:: FDA_get_drug_name_by_labor_and_delivery_info tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_name_by_labor_and_delivery_info``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve the drug name based on information about the drug’s use during labor or delivery.

   **Parameters:**

   * ``labor_and_delivery_info`` (string) (required)
     Information about the drug’s use during labor or delivery.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_name_by_labor_and_delivery_info",
          "arguments": {
              "labor_and_delivery_info": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_name_by_microbiology** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve the drug name based on microbiology field information.

.. dropdown:: FDA_get_drug_name_by_microbiology tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_name_by_microbiology``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve the drug name based on microbiology field information.

   **Parameters:**

   * ``microbiology_info`` (string) (required)
     Information related to the microbiology field.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_name_by_microbiology",
          "arguments": {
              "microbiology_info": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_name_by_other_safety_info** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve the drug name based on the provided safety information. This tool looks through safety i...

.. dropdown:: FDA_get_drug_name_by_other_safety_info tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_name_by_other_safety_info``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve the drug name based on the provided safety information. This tool looks through safety information that may not be specified in other fields.

   **Parameters:**

   * ``safety_info`` (string) (required)
     Information about safe use and handling of the product.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_name_by_other_safety_info",
          "arguments": {
              "safety_info": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_name_by_pharmacodynamics** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve the drug name based on pharmacodynamics information.

.. dropdown:: FDA_get_drug_name_by_pharmacodynamics tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_name_by_pharmacodynamics``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve the drug name based on pharmacodynamics information.

   **Parameters:**

   * ``pharmacodynamics`` (string) (required)
     Information about the biochemical or physiologic pharmacologic effects of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_name_by_pharmacodynamics",
          "arguments": {
              "pharmacodynamics": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_name_by_pharmacogenomics** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve the drug name based on pharmacogenomics field information.

.. dropdown:: FDA_get_drug_name_by_pharmacogenomics tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_name_by_pharmacogenomics``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve the drug name based on pharmacogenomics field information.

   **Parameters:**

   * ``pharmacogenomics`` (string) (required)
     Pharmacogenomics information to search for.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_name_by_pharmacogenomics",
          "arguments": {
              "pharmacogenomics": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_name_by_precautions** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve the drug name based on the precautions field information.

.. dropdown:: FDA_get_drug_name_by_precautions tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_name_by_precautions``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve the drug name based on the precautions field information.

   **Parameters:**

   * ``precautions`` (string) (required)
     Information about any special care to be exercised for safe and effective use of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_name_by_precautions",
          "arguments": {
              "precautions": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_name_by_pregnancy_or_breastfeeding_info** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve the drug names based on pregnancy or breastfeeding information.

.. dropdown:: FDA_get_drug_name_by_pregnancy_or_breastfeeding_info tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_name_by_pregnancy_or_breastfeeding_info``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve the drug names based on pregnancy or breastfeeding information.

   **Parameters:**

   * ``pregnancy_info`` (string) (required)
     Information related to pregnancy or breastfeeding.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_name_by_pregnancy_or_breastfeeding_info",
          "arguments": {
              "pregnancy_info": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_name_by_principal_display_panel** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve the drug name based on the content of the principal display panel of the product package.

.. dropdown:: FDA_get_drug_name_by_principal_display_panel tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_name_by_principal_display_panel``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve the drug name based on the content of the principal display panel of the product package.

   **Parameters:**

   * ``display_panel_content`` (string) (required)
     The content of the principal display panel of the product package.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_name_by_principal_display_panel",
          "arguments": {
              "display_panel_content": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_name_by_reference** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve the drug name based on the reference information provided in the drug labeling.

.. dropdown:: FDA_get_drug_name_by_reference tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_name_by_reference``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve the drug name based on the reference information provided in the drug labeling.

   **Parameters:**

   * ``reference`` (string) (required)
     The reference information to search for in the drug labeling.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_name_by_reference",
          "arguments": {
              "reference": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_name_by_set_id** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve the drug name based on the Set ID of the labeling.

.. dropdown:: FDA_get_drug_name_by_set_id tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_name_by_set_id``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve the drug name based on the Set ID of the labeling.

   **Parameters:**

   * ``set_id`` (string) (required)
     The Set ID, a globally unique identifier for the labeling.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_name_by_set_id",
          "arguments": {
              "set_id": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_name_by_stop_use_info** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve the drug name based on the stop use information provided.

.. dropdown:: FDA_get_drug_name_by_stop_use_info tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_name_by_stop_use_info``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve the drug name based on the stop use information provided.

   **Parameters:**

   * ``stop_use_info`` (string) (required)
     Information about when use of the drug product should be discontinued immediately and a doctor consulted.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_name_by_stop_use_info",
          "arguments": {
              "stop_use_info": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_name_by_storage_and_handling_info** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve the drug name based on storage and handling information.

.. dropdown:: FDA_get_drug_name_by_storage_and_handling_info tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_name_by_storage_and_handling_info``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve the drug name based on storage and handling information.

   **Parameters:**

   * ``storage_info`` (string) (required)
     Information about the storage and handling of the drug product.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_name_by_storage_and_handling_info",
          "arguments": {
              "storage_info": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_name_by_warnings** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve the drug names based on specific warning information.

.. dropdown:: FDA_get_drug_name_by_warnings tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_name_by_warnings``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve the drug names based on specific warning information.

   **Parameters:**

   * ``warning_text`` (string) (required)
     The warning text to search for in the drug labeling.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_name_by_warnings",
          "arguments": {
              "warning_text": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_name_from_patient_package_insert** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve the drug name based on the information provided in the patient package insert.

.. dropdown:: FDA_get_drug_name_from_patient_package_insert tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_name_from_patient_package_insert``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve the drug name based on the information provided in the patient package insert.

   **Parameters:**

   * ``patient_package_insert`` (string) (required)
     Information necessary for patients to use the drug safely and effectively.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_name_from_patient_package_insert",
          "arguments": {
              "patient_package_insert": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_names_by_abuse_dependence_info** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve the drug name based on information about drug abuse and dependence, including whether th...

.. dropdown:: FDA_get_drug_names_by_abuse_dependence_info tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_names_by_abuse_dependence_info``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve the drug name based on information about drug abuse and dependence, including whether the drug is a controlled substances, the types of possible abuse, and adverse reactions relevant to those abuse types.

   **Parameters:**

   * ``abuse_info`` (string) (required)
     Information about drug abuse and dependence.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_names_by_abuse_dependence_info",
          "arguments": {
              "abuse_info": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_names_by_abuse_info** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve drug names based on information about types of abuse and adverse reactions pertinent to ...

.. dropdown:: FDA_get_drug_names_by_abuse_info tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_names_by_abuse_info``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve drug names based on information about types of abuse and adverse reactions pertinent to those types of abuse. Warning: This tool only outputs a predefined limited number of drug names and does not cover all possible drugs. Use with caution.

   **Parameters:**

   * ``abuse_info`` (string) (required)
     Information about the types of abuse that can occur with the drug.

   * ``indication`` (string) (optional)
     The indication or usage of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_names_by_abuse_info",
          "arguments": {
              "abuse_info": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_names_by_accessories** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve drug names based on the accessories field information.

.. dropdown:: FDA_get_drug_names_by_accessories tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_names_by_accessories``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve drug names based on the accessories field information.

   **Parameters:**

   * ``accessory_name`` (string) (required)
     The name or part of the name of the accessory.

   * ``indication`` (string) (optional)
     The indication or usage of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_names_by_accessories",
          "arguments": {
              "accessory_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_names_by_active_ingredient** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve drug names based on the active ingredient information.

.. dropdown:: FDA_get_drug_names_by_active_ingredient tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_names_by_active_ingredient``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve drug names based on the active ingredient information.

   **Parameters:**

   * ``active_ingredient`` (string) (required)
     The active ingredient in the drug product.

   * ``indication`` (string) (optional)
     The indication or usage of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_names_by_active_ingredient",
          "arguments": {
              "active_ingredient": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_names_by_alarm** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve drug names based on the presence of specific alarms, which are related to adverse reacti...

.. dropdown:: FDA_get_drug_names_by_alarm tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_names_by_alarm``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve drug names based on the presence of specific alarms, which are related to adverse reaction events. Warning: This tool only outputs a predefined limited number of drug names and does not cover all possible drugs. Use with caution.

   **Parameters:**

   * ``alarm_type`` (string) (required)
     The type of alarm to search for.

   * ``indication`` (string) (optional)
     The indication or usage of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_names_by_alarm",
          "arguments": {
              "alarm_type": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_names_by_animal_pharmacology_info** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve drug names based on animal pharmacology and toxicology information.  Warning: This tool ...

.. dropdown:: FDA_get_drug_names_by_animal_pharmacology_info tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_names_by_animal_pharmacology_info``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve drug names based on animal pharmacology and toxicology information.  Warning: This tool only outputs a predefined limited number of drug names and does not cover all possible drugs. Use with caution.

   **Parameters:**

   * ``pharmacology_info`` (string) (required)
     Information from studies of the drug in animals.

   * ``indication`` (string) (optional)
     The indication or usage of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_names_by_animal_pharmacology_info",
          "arguments": {
              "pharmacology_info": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_names_by_application_number_NDC_number** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve drug names based on the specified FDA application number or National Drug Code (NDC) num...

.. dropdown:: FDA_get_drug_names_by_application_number_NDC_number tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_names_by_application_number_NDC_number``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve drug names based on the specified FDA application number or National Drug Code (NDC) number.

   **Parameters:**

   * ``application_manufacturer_or_NDC_info`` (string) (required)
     FDA application, manufacturer, or NDC number info

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_names_by_application_number_NDC_number",
          "arguments": {
              "application_manufacturer_or_NDC_info": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_names_by_assembly_installation_info** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve drug names based on assembly or installation instructions. Warning: This tool only outpu...

.. dropdown:: FDA_get_drug_names_by_assembly_installation_info tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_names_by_assembly_installation_info``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve drug names based on assembly or installation instructions. Warning: This tool only outputs a predefined limited number of drug names and does not cover all possible drugs. Use with caution.

   **Parameters:**

   * ``field_info`` (string) (required)
     Information related to assembly or installation instructions.

   * ``indication`` (string) (optional)
     The indication or usage of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_names_by_assembly_installation_info",
          "arguments": {
              "field_info": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_names_by_boxed_warning** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve drug names that have specific boxed warnings and adverse effects.

.. dropdown:: FDA_get_drug_names_by_boxed_warning tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_names_by_boxed_warning``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve drug names that have specific boxed warnings and adverse effects.

   **Parameters:**

   * ``warning_text`` (string) (required)
     The text of the boxed warning to search for.

   * ``indication`` (string) (optional)
     The indication or usage of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_names_by_boxed_warning",
          "arguments": {
              "warning_text": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_names_by_child_safety_info** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve drug names based on whether the product should be kept out of the reach of children and ...

.. dropdown:: FDA_get_drug_names_by_child_safety_info tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_names_by_child_safety_info``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve drug names based on whether the product should be kept out of the reach of children and instructions about what to do in the case of accidental contact or ingestion.

   **Parameters:**

   * ``child_safety_info`` (string) (required)
     Information pertaining to whether the product should be kept out of the reach of children.

   * ``indication`` (string) (optional)
     The indication or usage of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_names_by_child_safety_info",
          "arguments": {
              "child_safety_info": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_names_by_clinical_pharmacology** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve drug names based on clinical pharmacology information. Warning: This tool only outputs a...

.. dropdown:: FDA_get_drug_names_by_clinical_pharmacology tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_names_by_clinical_pharmacology``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve drug names based on clinical pharmacology information. Warning: This tool only outputs a predefined limited number of drug names and does not cover all possible drugs. Use with caution.

   **Parameters:**

   * ``clinical_pharmacology`` (string) (required)
     Information about the clinical pharmacology and actions of the drug in humans. Use key words

   * ``indication`` (string) (optional)
     The indication or usage of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_names_by_clinical_pharmacology",
          "arguments": {
              "clinical_pharmacology": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_names_by_clinical_studies** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve drug names based on the presence of clinical studies information.

.. dropdown:: FDA_get_drug_names_by_clinical_studies tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_names_by_clinical_studies``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve drug names based on the presence of clinical studies information.

   **Parameters:**

   * ``clinical_studies`` (string) (required)
     Information related to clinical studies. Use keywords split by blank space.

   * ``indication`` (string) (required)
     The indication or usage of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_names_by_clinical_studies",
          "arguments": {
              "clinical_studies": "example_value",
              "indication": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_names_by_consulting_doctor_pharmacist_info** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve drug names based on information about when a doctor or pharmacist should be consulted re...

.. dropdown:: FDA_get_drug_names_by_consulting_doctor_pharmacist_info tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_names_by_consulting_doctor_pharmacist_info``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve drug names based on information about when a doctor or pharmacist should be consulted regarding drug interactions. Warning: This tool only outputs a predefined limited number of drug names and does not cover all possible drugs. Use with caution.

   **Parameters:**

   * ``interaction_info`` (string) (required)
     Information about when a doctor or pharmacist should be consulted regarding drug interactions.

   * ``indication`` (string) (optional)
     The indication or usage of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_names_by_consulting_doctor_pharmacist_info",
          "arguments": {
              "interaction_info": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_names_by_contraindications** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve drug names based on specific contraindications information.

.. dropdown:: FDA_get_drug_names_by_contraindications tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_names_by_contraindications``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve drug names based on specific contraindications information.

   **Parameters:**

   * ``contraindication_info`` (string) (required)
     Information about situations in which the drug product is contraindicated.

   * ``indication`` (string) (optional)
     The indication or usage of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_names_by_contraindications",
          "arguments": {
              "contraindication_info": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_names_by_controlled_substance_DEA_schedule** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve drug names based on the Drug Enforcement Administration (DEA) schedule information.

.. dropdown:: FDA_get_drug_names_by_controlled_substance_DEA_schedule tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_names_by_controlled_substance_DEA_schedule``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve drug names based on the Drug Enforcement Administration (DEA) schedule information.

   **Parameters:**

   * ``controlled_substance_schedule`` (string) (required)
     The schedule in which the drug is controlled by the Drug Enforcement Administration.

   * ``indication`` (string) (optional)
     The indication or usage of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_names_by_controlled_substance_DEA_schedule",
          "arguments": {
              "controlled_substance_schedule": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_names_by_dear_health_care_provider_letter_info** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Fetch drug names based on information about dear health care provider letters. The letters are se...

.. dropdown:: FDA_get_drug_names_by_dear_health_care_provider_letter_info tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_names_by_dear_health_care_provider_letter_info``
   * **Type**: ``FDADrugLabel``
   * **Description**: Fetch drug names based on information about dear health care provider letters. The letters are sent by drug manufacturers to provide new or updated information about the drug.

   **Parameters:**

   * ``letter_info`` (string) (required)
     Information about the specific dear health care provider letters.

   * ``indication`` (string) (optional)
     The indication or usage of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_names_by_dear_health_care_provider_letter_info",
          "arguments": {
              "letter_info": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_names_by_disposal_info** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve drug names based on disposal and waste handling information.

.. dropdown:: FDA_get_drug_names_by_disposal_info tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_names_by_disposal_info``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve drug names based on disposal and waste handling information.

   **Parameters:**

   * ``disposal_info`` (string) (required)
     Information related to the disposal and waste handling of the drug.

   * ``indication`` (string) (optional)
     The indication or usage of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_names_by_disposal_info",
          "arguments": {
              "disposal_info": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_names_by_dosage_forms_and_strengths_info** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve drug names based on specific dosage forms and strengths information.

.. dropdown:: FDA_get_drug_names_by_dosage_forms_and_strengths_info tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_names_by_dosage_forms_and_strengths_info``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve drug names based on specific dosage forms and strengths information.

   **Parameters:**

   * ``dosage_forms_and_strengths`` (string) (required)
     Information about the dosage forms and strengths of the drug.

   * ``indication`` (string) (optional)
     The indication or usage of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_names_by_dosage_forms_and_strengths_info",
          "arguments": {
              "dosage_forms_and_strengths": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_names_by_drug_interactions** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve a list of drug names that have the specified drug interactions.

.. dropdown:: FDA_get_drug_names_by_drug_interactions tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_names_by_drug_interactions``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve a list of drug names that have the specified drug interactions.

   **Parameters:**

   * ``interaction_term`` (string) (required)
     The term to search for in drug interactions.

   * ``indication`` (string) (optional)
     The indication or usage of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_names_by_drug_interactions",
          "arguments": {
              "interaction_term": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_names_by_effective_time** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve drug names based on the effective time of the labeling document.

.. dropdown:: FDA_get_drug_names_by_effective_time tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_names_by_effective_time``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve drug names based on the effective time of the labeling document.

   **Parameters:**

   * ``effective_time`` (string) (required)
     Date reference to the particular version of the labeling document in YYYYmmdd format.

   * ``indication`` (string) (optional)
     The indication or usage of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_names_by_effective_time",
          "arguments": {
              "effective_time": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_names_by_food_safety_warnings** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve drug names based on specific food safety warnings.

.. dropdown:: FDA_get_drug_names_by_food_safety_warnings tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_names_by_food_safety_warnings``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve drug names based on specific food safety warnings.

   **Parameters:**

   * ``field_info`` (string) (required)
     Information related to food safety warnings.

   * ``indication`` (string) (optional)
     The indication or usage of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_names_by_food_safety_warnings",
          "arguments": {
              "field_info": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_names_by_general_precautions** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve drug names based on specific general precautions information.

.. dropdown:: FDA_get_drug_names_by_general_precautions tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_names_by_general_precautions``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve drug names based on specific general precautions information.

   **Parameters:**

   * ``precaution_info`` (string) (required)
     Information about any special care to be exercised for safe and effective use of the drug.

   * ``indication`` (string) (optional)
     The indication or usage of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_names_by_general_precautions",
          "arguments": {
              "precaution_info": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_names_by_geriatric_use** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve drug names that have specific information about geriatric use.

.. dropdown:: FDA_get_drug_names_by_geriatric_use tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_names_by_geriatric_use``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve drug names that have specific information about geriatric use.

   **Parameters:**

   * ``geriatric_use`` (string) (required)
     Information about any limitations on any geriatric indications, needs for specific monitoring, hazards associated with use of the drug in the geriatric population.

   * ``indication`` (string) (optional)
     The indication or usage of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_names_by_geriatric_use",
          "arguments": {
              "geriatric_use": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_names_by_health_claim** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve drug names based on specific health claims.

.. dropdown:: FDA_get_drug_names_by_health_claim tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_names_by_health_claim``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve drug names based on specific health claims.

   **Parameters:**

   * ``health_claim`` (string) (required)
     The health claim associated with the drug.

   * ``indication`` (string) (optional)
     The indication or usage of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_names_by_health_claim",
          "arguments": {
              "health_claim": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_names_by_indication** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve a list of drug names based on a specific indication or usage.

.. dropdown:: FDA_get_drug_names_by_indication tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_names_by_indication``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve a list of drug names based on a specific indication or usage.

   **Parameters:**

   * ``indication`` (string) (required)
     The indication or usage of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_names_by_indication",
          "arguments": {
              "indication": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_names_by_indication_aggregated** (Type: FDADrugLabelAggregated)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve and aggregate drug names by indication, grouping by generic name with all brand names. T...

.. dropdown:: FDA_get_drug_names_by_indication_aggregated tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_names_by_indication_aggregated``
   * **Type**: ``FDADrugLabelAggregated``
   * **Description**: Retrieve and aggregate drug names by indication, grouping by generic name with all brand names. This tool iterates through all available results without limit restrictions.

   **Parameters:**

   * ``indication`` (string) (required)
     The indication or usage of the drug.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_names_by_indication_aggregated",
          "arguments": {
              "indication": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_names_by_indication_stats** (Type: FDADrugLabelStats)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve and aggregate drug names by indication using FDA count API. This tool uses count mechani...

.. dropdown:: FDA_get_drug_names_by_indication_stats tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_names_by_indication_stats``
   * **Type**: ``FDADrugLabelStats``
   * **Description**: Retrieve and aggregate drug names by indication using FDA count API. This tool uses count mechanism to efficiently get brand_name and generic_name distributions without fetching full records.

   **Parameters:**

   * ``indication`` (string) (required)
     The indication or usage of the drug.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_names_by_indication_stats",
          "arguments": {
              "indication": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_names_by_info_for_nursing_mothers** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve drug names based on information related to nursing mothers.

.. dropdown:: FDA_get_drug_names_by_info_for_nursing_mothers tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_names_by_info_for_nursing_mothers``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve drug names based on information related to nursing mothers.

   **Parameters:**

   * ``nursing_mothers_info`` (string) (required)
     Information about excretion of the drug in human milk and effects on the nursing infant.

   * ``indication`` (string) (optional)
     The indication or usage of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_names_by_info_for_nursing_mothers",
          "arguments": {
              "nursing_mothers_info": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_names_by_information_for_owners_or_caregivers** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve drug names based on information for owners or caregivers.

.. dropdown:: FDA_get_drug_names_by_information_for_owners_or_caregivers tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_names_by_information_for_owners_or_caregivers``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve drug names based on information for owners or caregivers.

   **Parameters:**

   * ``field_info`` (string) (required)
     The specific information related to owners or caregivers to search for.

   * ``indication`` (string) (optional)
     The indication or usage of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_names_by_information_for_owners_or_caregivers",
          "arguments": {
              "field_info": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_names_by_ingredient** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve drug names based on a specific ingredient present in the drug product.

.. dropdown:: FDA_get_drug_names_by_ingredient tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_names_by_ingredient``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve drug names based on a specific ingredient present in the drug product.

   **Parameters:**

   * ``ingredient_name`` (string) (required)
     The name of the ingredient to search for in drug products.

   * ``indication`` (string) (optional)
     The indication or usage of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_names_by_ingredient",
          "arguments": {
              "ingredient_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_names_by_instructions_for_use** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve drug names based on specific instructions for use.

.. dropdown:: FDA_get_drug_names_by_instructions_for_use tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_names_by_instructions_for_use``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve drug names based on specific instructions for use.

   **Parameters:**

   * ``instructions_for_use`` (string) (required)
     Information about safe handling and use of the drug product.

   * ``indication`` (string) (optional)
     The indication or usage of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_names_by_instructions_for_use",
          "arguments": {
              "instructions_for_use": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_names_by_lab_test_interference** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve drug names that have known interference with laboratory tests.

.. dropdown:: FDA_get_drug_names_by_lab_test_interference tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_names_by_lab_test_interference``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve drug names that have known interference with laboratory tests.

   **Parameters:**

   * ``lab_test_interference`` (string) (required)
     Information about any known interference by the drug with laboratory tests.

   * ``indication`` (string) (optional)
     The indication or usage of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_names_by_lab_test_interference",
          "arguments": {
              "lab_test_interference": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_names_by_lab_tests** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve drug names based on laboratory tests information.

.. dropdown:: FDA_get_drug_names_by_lab_tests tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_names_by_lab_tests``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve drug names based on laboratory tests information.

   **Parameters:**

   * ``lab_test_info`` (string) (required)
     Information related to laboratory tests.

   * ``indication`` (string) (optional)
     The indication or usage of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_names_by_lab_tests",
          "arguments": {
              "lab_test_info": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_names_by_mechanism_of_action** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve drug names based on the specified mechanism of action information.

.. dropdown:: FDA_get_drug_names_by_mechanism_of_action tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_names_by_mechanism_of_action``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve drug names based on the specified mechanism of action information.

   **Parameters:**

   * ``mechanism_info`` (string) (required)
     Information related to the desired mechanism of action.

   * ``indication`` (string) (optional)
     The indication or usage of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_names_by_mechanism_of_action",
          "arguments": {
              "mechanism_info": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_names_by_medication_guide** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve drug names based on the presence of specific information in the medication guide.

.. dropdown:: FDA_get_drug_names_by_medication_guide tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_names_by_medication_guide``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve drug names based on the presence of specific information in the medication guide.

   **Parameters:**

   * ``medguide_info`` (string) (required)
     Information contained in the medication guide.

   * ``indication`` (string) (optional)
     The indication or usage of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_names_by_medication_guide",
          "arguments": {
              "medguide_info": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_names_by_nonclinical_toxicology_info** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve drug names based on nonclinical toxicology information.

.. dropdown:: FDA_get_drug_names_by_nonclinical_toxicology_info tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_names_by_nonclinical_toxicology_info``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve drug names based on nonclinical toxicology information.

   **Parameters:**

   * ``toxicology_info`` (string) (required)
     Information about toxicology in non-human subjects.

   * ``indication`` (string) (optional)
     The indication or usage of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_names_by_nonclinical_toxicology_info",
          "arguments": {
              "toxicology_info": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_names_by_nonteratogenic_effects** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve drug names based on the presence of nonteratogenic effects information.

.. dropdown:: FDA_get_drug_names_by_nonteratogenic_effects tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_names_by_nonteratogenic_effects``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve drug names based on the presence of nonteratogenic effects information.

   **Parameters:**

   * ``nonteratogenic_effects`` (string) (required)
     Information about the drug’s nonteratogenic effects.

   * ``indication`` (string) (optional)
     The indication or usage of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_names_by_nonteratogenic_effects",
          "arguments": {
              "nonteratogenic_effects": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_names_by_overdosage_info** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve drug names based on information about signs, symptoms, and laboratory findings of acute ...

.. dropdown:: FDA_get_drug_names_by_overdosage_info tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_names_by_overdosage_info``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve drug names based on information about signs, symptoms, and laboratory findings of acute overdosage.

   **Parameters:**

   * ``overdosage_info`` (string) (required)
     Information about signs, symptoms, and laboratory findings of acute overdosage.

   * ``indication`` (string) (optional)
     The indication or usage of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_names_by_overdosage_info",
          "arguments": {
              "overdosage_info": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_names_by_pediatric_use** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve drug names based on pediatric use information.

.. dropdown:: FDA_get_drug_names_by_pediatric_use tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_names_by_pediatric_use``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve drug names based on pediatric use information.

   **Parameters:**

   * ``pediatric_use_info`` (string) (required)
     Information related to the safe and effective pediatric use of the drug.

   * ``indication`` (string) (optional)
     The indication or usage of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_names_by_pediatric_use",
          "arguments": {
              "pediatric_use_info": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_names_by_pharmacokinetics** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve drug names based on specific pharmacokinetics information, such as absorption, distribut...

.. dropdown:: FDA_get_drug_names_by_pharmacokinetics tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_names_by_pharmacokinetics``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve drug names based on specific pharmacokinetics information, such as absorption, distribution, elimination, metabolism, drug interactions, and specific patient populations.

   **Parameters:**

   * ``pharmacokinetics_info`` (string) (required)
     Information about the clinically significant pharmacokinetics of a drug or active metabolites.

   * ``indication`` (string) (optional)
     The indication or usage of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_names_by_pharmacokinetics",
          "arguments": {
              "pharmacokinetics_info": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_names_by_population_use** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve drug names based on their use in specific populations, such as pregnant women, nursing m...

.. dropdown:: FDA_get_drug_names_by_population_use tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_names_by_population_use``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve drug names based on their use in specific populations, such as pregnant women, nursing mothers, pediatric patients, and geriatric patients.

   **Parameters:**

   * ``population_use`` (string) (required)
     The specific population use to search for (e.g., pregnant women, nursing mothers).

   * ``indication`` (string) (optional)
     The indication or usage of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_names_by_population_use",
          "arguments": {
              "population_use": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_names_by_pregnancy_effects_info** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve drug names based on information about effects the drug may have on pregnant women or on ...

.. dropdown:: FDA_get_drug_names_by_pregnancy_effects_info tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_names_by_pregnancy_effects_info``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve drug names based on information about effects the drug may have on pregnant women or on a fetus.

   **Parameters:**

   * ``pregnancy_info`` (string) (required)
     Information about the effects on pregnancy to search for.

   * ``indication`` (string) (optional)
     The indication or usage of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_names_by_pregnancy_effects_info",
          "arguments": {
              "pregnancy_info": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_names_by_residue_warning** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve drug names based on the presence of residue warnings.

.. dropdown:: FDA_get_drug_names_by_residue_warning tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_names_by_residue_warning``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve drug names based on the presence of residue warnings.

   **Parameters:**

   * ``residue_warning`` (string) (required)
     The residue warning information to search for.

   * ``indication`` (string) (optional)
     The indication or usage of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_names_by_residue_warning",
          "arguments": {
              "residue_warning": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_names_by_risk** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve drug names based on specific risk information, especially regarding pregnancy or breastf...

.. dropdown:: FDA_get_drug_names_by_risk tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_names_by_risk``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve drug names based on specific risk information, especially regarding pregnancy or breastfeeding.

   **Parameters:**

   * ``risk_info`` (string) (required)
     Specific risk information to search for.

   * ``indication`` (string) (optional)
     The indication or usage of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_names_by_risk",
          "arguments": {
              "risk_info": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_names_by_route** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve the drug names based on the route of administration.

.. dropdown:: FDA_get_drug_names_by_route tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_names_by_route``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve the drug names based on the route of administration.

   **Parameters:**

   * ``route`` (string) (required)
     The route of administration of the drug.

   * ``indication`` (string) (optional)
     The indication or usage of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_names_by_route",
          "arguments": {
              "route": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_names_by_safe_handling_warning** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve drug names that have specific safe handling warnings.

.. dropdown:: FDA_get_drug_names_by_safe_handling_warning tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_names_by_safe_handling_warning``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve drug names that have specific safe handling warnings.

   **Parameters:**

   * ``safe_handling_warning`` (string) (required)
     The specific safe handling warning to search for.

   * ``indication`` (string) (optional)
     The indication or usage of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_names_by_safe_handling_warning",
          "arguments": {
              "safe_handling_warning": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_names_by_safety_summary** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve drug names based on the summary of safety and effectiveness information.

.. dropdown:: FDA_get_drug_names_by_safety_summary tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_names_by_safety_summary``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve drug names based on the summary of safety and effectiveness information.

   **Parameters:**

   * ``summary_text`` (string) (required)
     Text to search within the summary of safety and effectiveness field.

   * ``indication`` (string) (optional)
     The indication or usage of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_names_by_safety_summary",
          "arguments": {
              "summary_text": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_names_by_spl_indexing_data_elements** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve drug names based on Structured Product Labeling (SPL) indexing data elements.

.. dropdown:: FDA_get_drug_names_by_spl_indexing_data_elements tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_names_by_spl_indexing_data_elements``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve drug names based on Structured Product Labeling (SPL) indexing data elements.

   **Parameters:**

   * ``spl_indexing_data_elements`` (string) (required)
     The SPL indexing data elements to search for.

   * ``indication`` (string) (optional)
     The indication or usage of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_names_by_spl_indexing_data_elements",
          "arguments": {
              "spl_indexing_data_elements": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_names_by_teratogenic_effects** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve drug names based on specific teratogenic effects categories.

.. dropdown:: FDA_get_drug_names_by_teratogenic_effects tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_names_by_teratogenic_effects``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve drug names based on specific teratogenic effects categories.

   **Parameters:**

   * ``teratogenic_effects`` (string) (required)
     The teratogenic effects category to search for (e.g., Pregnancy category A, B, C, D, or X).

   * ``indication`` (string) (optional)
     The indication or usage of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_names_by_teratogenic_effects",
          "arguments": {
              "teratogenic_effects": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_names_by_user_safety_warning** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve drug names that have specific user safety warnings.

.. dropdown:: FDA_get_drug_names_by_user_safety_warning tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_names_by_user_safety_warning``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve drug names that have specific user safety warnings.

   **Parameters:**

   * ``safety_warning`` (string) (required)
     The specific safety warning to search for.

   * ``indication`` (string) (optional)
     The indication or usage of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_names_by_user_safety_warning",
          "arguments": {
              "safety_warning": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drug_names_by_warnings_and_cautions** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve drug names based on specific warnings and cautions information.

.. dropdown:: FDA_get_drug_names_by_warnings_and_cautions tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drug_names_by_warnings_and_cautions``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve drug names based on specific warnings and cautions information.

   **Parameters:**

   * ``warnings_and_cautions_info`` (string) (required)
     The warnings and cautions text to search for.

   * ``indication`` (string) (optional)
     The indication or usage of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drug_names_by_warnings_and_cautions",
          "arguments": {
              "warnings_and_cautions_info": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_drugs_by_carcinogenic_mutagenic_fertility** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve drug names based on the presence of carcinogenic, mutagenic, or fertility impairment inf...

.. dropdown:: FDA_get_drugs_by_carcinogenic_mutagenic_fertility tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_drugs_by_carcinogenic_mutagenic_fertility``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve drug names based on the presence of carcinogenic, mutagenic, or fertility impairment information.

   **Parameters:**

   * ``carcinogenic_info`` (string) (required)
     Information about carcinogenic, mutagenic, or fertility impairment potential.

   * ``indication`` (string) (optional)
     The indication or usage of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_drugs_by_carcinogenic_mutagenic_fertility",
          "arguments": {
              "carcinogenic_info": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_effective_time_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve effective time of the labeling document based on the drug name.

.. dropdown:: FDA_get_effective_time_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_effective_time_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve effective time of the labeling document based on the drug name.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_effective_time_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_environmental_warning_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Fetch environmental warnings for a specific drug based on its name.

.. dropdown:: FDA_get_environmental_warning_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_environmental_warning_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Fetch environmental warnings for a specific drug based on its name.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_environmental_warning_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_general_precautions_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve general precautions information based on the drug name.

.. dropdown:: FDA_get_general_precautions_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_general_precautions_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve general precautions information based on the drug name.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_general_precautions_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_geriatric_use_info_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve information about geriatric use based on the drug name.

.. dropdown:: FDA_get_geriatric_use_info_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_geriatric_use_info_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve information about geriatric use based on the drug name.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_geriatric_use_info_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_health_claims_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve health claims associated with a specific drug name.

.. dropdown:: FDA_get_health_claims_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_health_claims_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve health claims associated with a specific drug name.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_health_claims_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_inactive_ingredient_info_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Fetch a list of inactive ingredients in a specific drug product based on the drug name.

.. dropdown:: FDA_get_inactive_ingredient_info_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_inactive_ingredient_info_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Fetch a list of inactive ingredients in a specific drug product based on the drug name.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_inactive_ingredient_info_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_indications_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve indications and usage information based on a specific drug name.

.. dropdown:: FDA_get_indications_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_indications_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve indications and usage information based on a specific drug name.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_indications_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_info_for_nursing_mothers_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve information about nursing mothers for a specific drug.

.. dropdown:: FDA_get_info_for_nursing_mothers_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_info_for_nursing_mothers_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve information about nursing mothers for a specific drug.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_info_for_nursing_mothers_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_info_for_patients_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Fetch information for patients based on the drug name.

.. dropdown:: FDA_get_info_for_patients_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_info_for_patients_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Fetch information for patients based on the drug name.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_info_for_patients_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_info_on_conditions_for_doctor_consultation_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get information about when a doctor should be consulted before using a specific drug.

.. dropdown:: FDA_get_info_on_conditions_for_doctor_consultation_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_info_on_conditions_for_doctor_consultation_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Get information about when a doctor should be consulted before using a specific drug.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_info_on_conditions_for_doctor_consultation_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_info_on_consulting_doctor_pharmacist_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get information about when a doctor or pharmacist should be consulted regarding drug interactions...

.. dropdown:: FDA_get_info_on_consulting_doctor_pharmacist_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_info_on_consulting_doctor_pharmacist_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Get information about when a doctor or pharmacist should be consulted regarding drug interactions for a specific drug.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_info_on_consulting_doctor_pharmacist_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_information_for_owners_or_caregivers_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve specific information for owners or caregivers based on the drug name.

.. dropdown:: FDA_get_information_for_owners_or_caregivers_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_information_for_owners_or_caregivers_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve specific information for owners or caregivers based on the drug name.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_information_for_owners_or_caregivers_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_ingredients_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve a list of drug ingredients based on the drug name.

.. dropdown:: FDA_get_ingredients_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_ingredients_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve a list of drug ingredients based on the drug name.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_ingredients_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_instructions_for_use_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve instructions for use information based on the drug name.

.. dropdown:: FDA_get_instructions_for_use_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_instructions_for_use_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve instructions for use information based on the drug name.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_instructions_for_use_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_lab_test_interference_info_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve information about laboratory test interferences for a specific drug.

.. dropdown:: FDA_get_lab_test_interference_info_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_lab_test_interference_info_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve information about laboratory test interferences for a specific drug.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_lab_test_interference_info_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_lab_tests_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve laboratory tests information based on drug names.

.. dropdown:: FDA_get_lab_tests_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_lab_tests_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve laboratory tests information based on drug names.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_lab_tests_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_labor_and_delivery_info_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve information about the drug’s use during labor or delivery based on the drug name.

.. dropdown:: FDA_get_labor_and_delivery_info_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_labor_and_delivery_info_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve information about the drug’s use during labor or delivery based on the drug name.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_labor_and_delivery_info_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_manufacturer_name_NDC_number_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve detailed information about a drug's active ingredient, FDA application number, manufactu...

.. dropdown:: FDA_get_manufacturer_name_NDC_number_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_manufacturer_name_NDC_number_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve detailed information about a drug's active ingredient, FDA application number, manufacturer name, National Drug Code (NDC) number, and route of administration; all based on the drug name.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_manufacturer_name_NDC_number_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_mechanism_of_action_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve the mechanism of action information for a specific drug.

.. dropdown:: FDA_get_mechanism_of_action_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_mechanism_of_action_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve the mechanism of action information for a specific drug.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_mechanism_of_action_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_medication_guide_info_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve medication guide information based on the drug name.

.. dropdown:: FDA_get_medication_guide_info_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_medication_guide_info_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve medication guide information based on the drug name.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_medication_guide_info_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_microbiology_info_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve microbiology information based on the drug name.

.. dropdown:: FDA_get_microbiology_info_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_microbiology_info_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve microbiology information based on the drug name.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_microbiology_info_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_nonclinical_toxicology_info_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve nonclinical toxicology information based on drug names.

.. dropdown:: FDA_get_nonclinical_toxicology_info_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_nonclinical_toxicology_info_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve nonclinical toxicology information based on drug names.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_nonclinical_toxicology_info_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_nonteratogenic_effects_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve information about nonteratogenic effects based on the drug name.

.. dropdown:: FDA_get_nonteratogenic_effects_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_nonteratogenic_effects_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve information about nonteratogenic effects based on the drug name.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_nonteratogenic_effects_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_other_safety_info_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve safety information that may not be specified in other fields based on the provided drug ...

.. dropdown:: FDA_get_other_safety_info_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_other_safety_info_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve safety information that may not be specified in other fields based on the provided drug name.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_other_safety_info_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_overdosage_info_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve information about signs, symptoms, and laboratory findings of acute overdosage based on ...

.. dropdown:: FDA_get_overdosage_info_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_overdosage_info_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve information about signs, symptoms, and laboratory findings of acute overdosage based on the drug name.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_overdosage_info_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_patient_package_insert_from_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve the patient package insert information based on the drug name.

.. dropdown:: FDA_get_patient_package_insert_from_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_patient_package_insert_from_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve the patient package insert information based on the drug name.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_patient_package_insert_from_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_pediatric_use_info_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve pediatric use information based on drug names.

.. dropdown:: FDA_get_pediatric_use_info_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_pediatric_use_info_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve pediatric use information based on drug names.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_pediatric_use_info_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_pharmacodynamics_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve pharmacodynamics information based on the drug name.

.. dropdown:: FDA_get_pharmacodynamics_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_pharmacodynamics_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve pharmacodynamics information based on the drug name.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_pharmacodynamics_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_pharmacogenomics_info_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve pharmacogenomics information based on the drug name.

.. dropdown:: FDA_get_pharmacogenomics_info_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_pharmacogenomics_info_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve pharmacogenomics information based on the drug name.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_pharmacogenomics_info_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_pharmacokinetics_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve pharmacokinetics information (e.g. absorption, distribution, elimination, metabolism, dr...

.. dropdown:: FDA_get_pharmacokinetics_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_pharmacokinetics_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve pharmacokinetics information (e.g. absorption, distribution, elimination, metabolism, drug interactions, and specific patient populations) for a specific drug based on its name.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_pharmacokinetics_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_population_use_info_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve information about the use of a drug in specific populations based on the drug name.

.. dropdown:: FDA_get_population_use_info_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_population_use_info_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve information about the use of a drug in specific populations based on the drug name.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_population_use_info_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_precautions_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve precautions information based on the drug name.

.. dropdown:: FDA_get_precautions_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_precautions_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve precautions information based on the drug name.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_precautions_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_pregnancy_effects_info_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve information about the effects on pregnancy for a specific drug.

.. dropdown:: FDA_get_pregnancy_effects_info_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_pregnancy_effects_info_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve information about the effects on pregnancy for a specific drug.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_pregnancy_effects_info_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_pregnancy_or_breastfeeding_info_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve the pregnancy or breastfeeding information based on the specified drug name.

.. dropdown:: FDA_get_pregnancy_or_breastfeeding_info_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_pregnancy_or_breastfeeding_info_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve the pregnancy or breastfeeding information based on the specified drug name.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_pregnancy_or_breastfeeding_info_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_principal_display_panel_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve the content of the principal display panel of the product package based on the drug name.

.. dropdown:: FDA_get_principal_display_panel_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_principal_display_panel_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve the content of the principal display panel of the product package based on the drug name.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_principal_display_panel_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_purpose_info_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve about the drug product’s indications for use based on the drug name.

.. dropdown:: FDA_get_purpose_info_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_purpose_info_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve about the drug product’s indications for use based on the drug name.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_purpose_info_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_recent_changes_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve recent major changes in labeling for a specific drug.

.. dropdown:: FDA_get_recent_changes_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_recent_changes_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve recent major changes in labeling for a specific drug.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_recent_changes_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_reference_info_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve reference information based on the drug name provided.

.. dropdown:: FDA_get_reference_info_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_reference_info_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve reference information based on the drug name provided.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_reference_info_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_residue_warning_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve the residue warning based on drug name.

.. dropdown:: FDA_get_residue_warning_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_residue_warning_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve the residue warning based on drug name.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_residue_warning_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_risk_info_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve risk information (especially regarding pregnancy or breastfeeding) based on the drug name.

.. dropdown:: FDA_get_risk_info_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_risk_info_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve risk information (especially regarding pregnancy or breastfeeding) based on the drug name.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_risk_info_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_route_info_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve the route of administration information based on the drug name.

.. dropdown:: FDA_get_route_info_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_route_info_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve the route of administration information based on the drug name.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_route_info_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_safe_handling_warnings_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve safe handling warnings for a specific drug based on its name.

.. dropdown:: FDA_get_safe_handling_warnings_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_safe_handling_warnings_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve safe handling warnings for a specific drug based on its name.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_safe_handling_warnings_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_safety_summary_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve a summary of safety and effectiveness information based on the drug name.

.. dropdown:: FDA_get_safety_summary_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_safety_summary_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve a summary of safety and effectiveness information based on the drug name.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug (either brand name or generic name).

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_safety_summary_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_spl_indexing_data_elements_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve Structured Product Labeling (SPL) indexing data elements based on drug names.

.. dropdown:: FDA_get_spl_indexing_data_elements_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_spl_indexing_data_elements_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve Structured Product Labeling (SPL) indexing data elements based on drug names.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_spl_indexing_data_elements_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_spl_unclassified_section_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve the SPL unclassified section information based on the drug name.

.. dropdown:: FDA_get_spl_unclassified_section_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_spl_unclassified_section_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve the SPL unclassified section information based on the drug name.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_spl_unclassified_section_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_stop_use_info_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve stop use information based on the drug name provided.

.. dropdown:: FDA_get_stop_use_info_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_stop_use_info_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve stop use information based on the drug name provided.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_stop_use_info_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_storage_and_handling_info_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve storage and handling information based on the drug name.

.. dropdown:: FDA_get_storage_and_handling_info_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_storage_and_handling_info_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve storage and handling information based on the drug name.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_storage_and_handling_info_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_teratogenic_effects_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve teratogenic effects information based on the drug name.

.. dropdown:: FDA_get_teratogenic_effects_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_teratogenic_effects_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve teratogenic effects information based on the drug name.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug (either brand name or generic name).

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_teratogenic_effects_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_user_safety_warning_by_drug_names** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve specific user safety warnings based on drug names.

.. dropdown:: FDA_get_user_safety_warning_by_drug_names tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_user_safety_warning_by_drug_names``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve specific user safety warnings based on drug names.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The specific drug name.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_user_safety_warning_by_drug_names",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_warnings_and_cautions_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve warnings and cautions information for a specific drug based on its name.

.. dropdown:: FDA_get_warnings_and_cautions_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_warnings_and_cautions_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve warnings and cautions information for a specific drug based on its name.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_warnings_and_cautions_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_warnings_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve warning information based on the drug name.

.. dropdown:: FDA_get_warnings_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_warnings_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve warning information based on the drug name.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_warnings_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_get_when_using_info** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve information about side effects and substances or activities to avoid while using a speci...

.. dropdown:: FDA_get_when_using_info tool specification

   **Tool Information:**

   * **Name**: ``FDA_get_when_using_info``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve information about side effects and substances or activities to avoid while using a specific drug.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_get_when_using_info",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_retrieve_device_use_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve the intended use of the device based on the drug name.

.. dropdown:: FDA_retrieve_device_use_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_retrieve_device_use_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve the intended use of the device based on the drug name.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_retrieve_device_use_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


**FDA_retrieve_drug_name_by_device_use** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve the drug name based on the intended use of the device.

.. dropdown:: FDA_retrieve_drug_name_by_device_use tool specification

   **Tool Information:**

   * **Name**: ``FDA_retrieve_drug_name_by_device_use``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve the drug name based on the intended use of the device.

   **Parameters:**

   * ``intended_use_of_the_device`` (string) (required)
     The intended use of the device.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_retrieve_drug_name_by_device_use",
          "arguments": {
              "intended_use_of_the_device": "example_value"
          }
      }
      result = tu.run(query)


**FDA_retrieve_drug_names_by_patient_medication_info** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve drug names based on patient medication information, which is about safe use of the drug.

.. dropdown:: FDA_retrieve_drug_names_by_patient_medication_info tool specification

   **Tool Information:**

   * **Name**: ``FDA_retrieve_drug_names_by_patient_medication_info``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve drug names based on patient medication information, which is about safe use of the drug.

   **Parameters:**

   * ``patient_info`` (string) (required)
     Information or instructions to patients about safe use of the drug product.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_retrieve_drug_names_by_patient_medication_info",
          "arguments": {
              "patient_info": "example_value"
          }
      }
      result = tu.run(query)


**FDA_retrieve_patient_medication_info_by_drug_name** (Type: FDADrugLabel)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve patient medication information (which is about safe use of the drug) based on drug names.

.. dropdown:: FDA_retrieve_patient_medication_info_by_drug_name tool specification

   **Tool Information:**

   * **Name**: ``FDA_retrieve_patient_medication_info_by_drug_name``
   * **Type**: ``FDADrugLabel``
   * **Description**: Retrieve patient medication information (which is about safe use of the drug) based on drug names.

   **Parameters:**

   * ``drug_name`` (string) (required)
     The name of the drug.

   * ``limit`` (integer) (optional)
     The number of records to return.

   * ``skip`` (integer) (optional)
     The number of records to skip.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FDA_retrieve_patient_medication_info_by_drug_name",
          "arguments": {
              "drug_name": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
