Fda Drug Adverse Event Detail Tools
===================================

**Configuration File**: ``fda_drug_adverse_event_detail_tools.json``
**Tool Type**: Local
**Tools Count**: 6

This page contains all tools defined in the ``fda_drug_adverse_event_detail_tools.json`` configuration file.

Available Tools
---------------

**FAERS_search_adverse_event_reports** (Type: FDADrugAdverseEventDetailTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search and retrieve detailed adverse event reports from FAERS. Returns individual case reports wi...

.. dropdown:: FAERS_search_adverse_event_reports tool specification

   **Tool Information:**

   * **Name**: ``FAERS_search_adverse_event_reports``
   * **Type**: ``FDADrugAdverseEventDetailTool``
   * **Description**: Search and retrieve detailed adverse event reports from FAERS. Returns individual case reports with patient information, adverse event details, drug information, and report metadata. Only medicinalproduct is required; all other parameters (limit, skip, patientsex, patientagegroup, occurcountry, serious, seriousnessdeath) are optional. Use filters sparingly to avoid overly restrictive searches. Data source: FDA Adverse Event Reporting System (FAERS).

   **Parameters:**

   * ``medicinalproduct`` (string) (required)
     Drug name (required).

   * ``limit`` (integer) (optional)
     Maximum number of reports to return. Must be between 1 and 100.

   * ``skip`` (integer) (optional)
     Number of reports to skip for pagination. Must be non-negative.

   * ``patientsex`` (string) (optional)
     Optional: Filter by patient sex. Omit this parameter if you don't want to filter by sex.

   * ``patientagegroup`` (string) (optional)
     Optional: Filter by patient age group. Omit this parameter if you don't want to filter by age.

   * ``occurcountry`` (string) (optional)
     Optional: Filter by country where event occurred (ISO2 code, e.g., 'US', 'GB'). Omit this parameter if you don't want to filter by country.

   * ``serious`` (string) (optional)
     Optional: Filter by event seriousness. Omit this parameter if you don't want to filter by seriousness.

   * ``seriousnessdeath`` (string) (optional)
     Optional: Filter for fatal outcomes. Omit this parameter if you don't want to filter by death.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FAERS_search_adverse_event_reports",
          "arguments": {
              "medicinalproduct": "example_value"
          }
      }
      result = tu.run(query)


**FAERS_search_reports_by_drug_and_indication** (Type: FDADrugAdverseEventDetailTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search and retrieve detailed adverse event reports for a specific drug and indication. Returns in...

.. dropdown:: FAERS_search_reports_by_drug_and_indication tool specification

   **Tool Information:**

   * **Name**: ``FAERS_search_reports_by_drug_and_indication``
   * **Type**: ``FDADrugAdverseEventDetailTool``
   * **Description**: Search and retrieve detailed adverse event reports for a specific drug and indication. Returns individual case reports with patient information, adverse event details, drug information, and report metadata. Only medicinalproduct is required; all other parameters (drugindication, limit, skip, patientsex, patientagegroup, serious) are optional. Data source: FDA Adverse Event Reporting System (FAERS).

   **Parameters:**

   * ``medicinalproduct`` (string) (required)
     Drug name (required).

   * ``drugindication`` (string) (optional)
     Optional: Filter by drug indication (e.g., 'Dementia Alzheimer\'s type', 'Alzheimer disease'). Omit this parameter if you don't want to filter by indication.

   * ``limit`` (integer) (optional)
     Maximum number of reports to return. Must be between 1 and 100.

   * ``skip`` (integer) (optional)
     Number of reports to skip for pagination. Must be non-negative.

   * ``patientsex`` (string) (optional)
     Optional: Filter by patient sex. Omit this parameter if you don't want to filter by sex.

   * ``patientagegroup`` (string) (optional)
     Optional: Filter by patient age group. Omit this parameter if you don't want to filter by age.

   * ``serious`` (string) (optional)
     Optional: Filter by event seriousness. Omit this parameter if you don't want to filter by seriousness.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FAERS_search_reports_by_drug_and_indication",
          "arguments": {
              "medicinalproduct": "example_value"
          }
      }
      result = tu.run(query)


**FAERS_search_reports_by_drug_and_outcome** (Type: FDADrugAdverseEventDetailTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search and retrieve detailed adverse event reports for a specific drug filtered by reaction outco...

.. dropdown:: FAERS_search_reports_by_drug_and_outcome tool specification

   **Tool Information:**

   * **Name**: ``FAERS_search_reports_by_drug_and_outcome``
   * **Type**: ``FDADrugAdverseEventDetailTool``
   * **Description**: Search and retrieve detailed adverse event reports for a specific drug filtered by reaction outcome. Returns individual case reports with patient information, adverse event details, drug information, and report metadata. Only medicinalproduct is required; all other parameters (reactionoutcome, limit, skip, patientsex, patientagegroup, serious) are optional. Data source: FDA Adverse Event Reporting System (FAERS).

   **Parameters:**

   * ``medicinalproduct`` (string) (required)
     Drug name (required).

   * ``reactionoutcome`` (string) (optional)
     Optional: Filter by reaction outcome. Omit this parameter if you don't want to filter by outcome.

   * ``limit`` (integer) (optional)
     Maximum number of reports to return. Must be between 1 and 100.

   * ``skip`` (integer) (optional)
     Number of reports to skip for pagination. Must be non-negative.

   * ``patientsex`` (string) (optional)
     Optional: Filter by patient sex. Omit this parameter if you don't want to filter by sex.

   * ``patientagegroup`` (string) (optional)
     Optional: Filter by patient age group. Omit this parameter if you don't want to filter by age.

   * ``serious`` (string) (optional)
     Optional: Filter by event seriousness. Omit this parameter if you don't want to filter by seriousness.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FAERS_search_reports_by_drug_and_outcome",
          "arguments": {
              "medicinalproduct": "example_value"
          }
      }
      result = tu.run(query)


**FAERS_search_reports_by_drug_and_reaction** (Type: FDADrugAdverseEventDetailTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search and retrieve detailed adverse event reports for a specific drug and reaction type. Returns...

.. dropdown:: FAERS_search_reports_by_drug_and_reaction tool specification

   **Tool Information:**

   * **Name**: ``FAERS_search_reports_by_drug_and_reaction``
   * **Type**: ``FDADrugAdverseEventDetailTool``
   * **Description**: Search and retrieve detailed adverse event reports for a specific drug and reaction type. Returns individual case reports with patient information, adverse event details, drug information, and report metadata. Only medicinalproduct and reactionmeddrapt are required; all other parameters (limit, skip, patientsex, patientagegroup, serious) are optional. Data source: FDA Adverse Event Reporting System (FAERS).

   **Parameters:**

   * ``medicinalproduct`` (string) (required)
     Drug name (required).

   * ``reactionmeddrapt`` (string) (required)
     MedDRA preferred term for the adverse reaction (required). Example: 'INFUSION RELATED REACTION', 'DYSPNOEA'.

   * ``limit`` (integer) (optional)
     Maximum number of reports to return. Must be between 1 and 100.

   * ``skip`` (integer) (optional)
     Number of reports to skip for pagination. Must be non-negative.

   * ``patientsex`` (string) (optional)
     Optional: Filter by patient sex. Omit this parameter if you don't want to filter by sex.

   * ``patientagegroup`` (string) (optional)
     Optional: Filter by patient age group. Omit this parameter if you don't want to filter by age.

   * ``serious`` (string) (optional)
     Optional: Filter by event seriousness. Omit this parameter if you don't want to filter by seriousness.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FAERS_search_reports_by_drug_and_reaction",
          "arguments": {
              "medicinalproduct": "example_value",
              "reactionmeddrapt": "example_value"
          }
      }
      result = tu.run(query)


**FAERS_search_reports_by_drug_combination** (Type: FDADrugInteractionDetailTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search and retrieve detailed adverse event reports involving multiple drugs (drug interactions). ...

.. dropdown:: FAERS_search_reports_by_drug_combination tool specification

   **Tool Information:**

   * **Name**: ``FAERS_search_reports_by_drug_combination``
   * **Type**: ``FDADrugInteractionDetailTool``
   * **Description**: Search and retrieve detailed adverse event reports involving multiple drugs (drug interactions). Returns individual case reports where all specified drugs are present. Only medicinalproducts (list of at least 2 drug names) is required; all other parameters (limit, skip, patientsex, patientagegroup, serious) are optional. Data source: FDA Adverse Event Reporting System (FAERS).

   **Parameters:**

   * ``medicinalproducts`` (array) (required)
     List of at least 2 drug names (required). Reports will include cases where all specified drugs are present.

   * ``limit`` (integer) (optional)
     Maximum number of reports to return. Must be between 1 and 100.

   * ``skip`` (integer) (optional)
     Number of reports to skip for pagination. Must be non-negative.

   * ``patientsex`` (string) (optional)
     Optional: Filter by patient sex. Omit this parameter if you don't want to filter by sex.

   * ``patientagegroup`` (string) (optional)
     Optional: Filter by patient age group. Omit this parameter if you don't want to filter by age.

   * ``serious`` (string) (optional)
     Optional: Filter by event seriousness. Omit this parameter if you don't want to filter by seriousness.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FAERS_search_reports_by_drug_combination",
          "arguments": {
              "medicinalproducts": ["item1", "item2"]
          }
      }
      result = tu.run(query)


**FAERS_search_serious_reports_by_drug** (Type: FDADrugAdverseEventDetailTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search and retrieve detailed reports of serious adverse events for a specific drug. Returns indiv...

.. dropdown:: FAERS_search_serious_reports_by_drug tool specification

   **Tool Information:**

   * **Name**: ``FAERS_search_serious_reports_by_drug``
   * **Type**: ``FDADrugAdverseEventDetailTool``
   * **Description**: Search and retrieve detailed reports of serious adverse events for a specific drug. Returns individual case reports with patient information, adverse event details, drug information, and report metadata. Only medicinalproduct is required; all other parameters (limit, skip, seriousnessdeath, seriousnesshospitalization, seriousnesslifethreatening, seriousnessdisabling, patientsex, patientagegroup) are optional. Data source: FDA Adverse Event Reporting System (FAERS).

   **Parameters:**

   * ``medicinalproduct`` (string) (required)
     Drug name (required).

   * ``seriousnessdeath`` (string) (optional)
     Optional: Filter for reports where death was reported. Set to 'Yes' to include only fatal cases.

   * ``seriousnesshospitalization`` (string) (optional)
     Optional: Filter for reports where hospitalization was required. Set to 'Yes' to include only cases requiring hospitalization.

   * ``seriousnesslifethreatening`` (string) (optional)
     Optional: Filter for reports where the event was life-threatening. Set to 'Yes' to include only life-threatening cases.

   * ``seriousnessdisabling`` (string) (optional)
     Optional: Filter for reports where the event was disabling. Set to 'Yes' to include only disabling cases.

   * ``limit`` (integer) (optional)
     Maximum number of reports to return. Must be between 1 and 100.

   * ``skip`` (integer) (optional)
     Number of reports to skip for pagination. Must be non-negative.

   * ``patientsex`` (string) (optional)
     Optional: Filter by patient sex. Omit this parameter if you don't want to filter by sex.

   * ``patientagegroup`` (string) (optional)
     Optional: Filter by patient age group. Omit this parameter if you don't want to filter by age.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FAERS_search_serious_reports_by_drug",
          "arguments": {
              "medicinalproduct": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
