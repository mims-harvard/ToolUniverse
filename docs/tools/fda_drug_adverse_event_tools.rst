Fda Drug Adverse Event Tools
============================

**Configuration File**: ``fda_drug_adverse_event_tools.json``
**Tool Type**: Local
**Tools Count**: 15

This page contains all tools defined in the ``fda_drug_adverse_event_tools.json`` configuration file.

Available Tools
---------------

**FAERS_count_additive_administration_routes** (Type: FDACountAdditiveReactionsTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Enumerate and count administration routes for adverse events across specified medicinal products....

.. dropdown:: FAERS_count_additive_administration_routes tool specification

   **Tool Information:**

   * **Name**: ``FAERS_count_additive_administration_routes``
   * **Type**: ``FDACountAdditiveReactionsTool``
   * **Description**: Enumerate and count administration routes for adverse events across specified medicinal products. Only medicinalproducts is required; serious filter is optional. Use filters sparingly to avoid overly restrictive searches. Data source: FDA Adverse Event Reporting System (FAERS).

   **Parameters:**

   * ``medicinalproducts`` (array) (required)
     Array of medicinal product names.

   * ``serious`` (string) (optional)
     Optional: Filter by event seriousness. Omit this parameter if you don't want to filter by seriousness.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FAERS_count_additive_administration_routes",
          "arguments": {
              "medicinalproducts": ["item1", "item2"]
          }
      }
      result = tu.run(query)


**FAERS_count_additive_adverse_reactions** (Type: FDACountAdditiveReactionsTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Aggregate adverse reaction counts across specified medicinal products. Only medicinalproducts is ...

.. dropdown:: FAERS_count_additive_adverse_reactions tool specification

   **Tool Information:**

   * **Name**: ``FAERS_count_additive_adverse_reactions``
   * **Type**: ``FDACountAdditiveReactionsTool``
   * **Description**: Aggregate adverse reaction counts across specified medicinal products. Only medicinalproducts is required; all other filters (patientsex, patientagegroup, occurcountry, serious, seriousnessdeath) are optional. Use filters sparingly to avoid overly restrictive searches that return no results. Data source: FDA Adverse Event Reporting System (FAERS).

   **Parameters:**

   * ``medicinalproducts`` (array) (required)
     Array of medicinal product names.

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
          "name": "FAERS_count_additive_adverse_reactions",
          "arguments": {
              "medicinalproducts": ["item1", "item2"]
          }
      }
      result = tu.run(query)


**FAERS_count_additive_event_reports_by_country** (Type: FDACountAdditiveReactionsTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Aggregate report counts by country of occurrence across specified medicinal products. Only medici...

.. dropdown:: FAERS_count_additive_event_reports_by_country tool specification

   **Tool Information:**

   * **Name**: ``FAERS_count_additive_event_reports_by_country``
   * **Type**: ``FDACountAdditiveReactionsTool``
   * **Description**: Aggregate report counts by country of occurrence across specified medicinal products. Only medicinalproducts is required; all other filters (patientsex, patientagegroup, serious) are optional. Use filters sparingly to avoid overly restrictive searches. Data source: FDA Adverse Event Reporting System (FAERS).

   **Parameters:**

   * ``medicinalproducts`` (array) (required)
     Array of medicinal product names.

   * ``patientsex`` (string) (optional)
     Optional: Filter by patient sex. Omit this parameter if you don't want to filter by sex.

   * ``patientagegroup`` (string) (optional)
     Optional: Filter by patient age group. Omit this parameter if you don't want to filter by age.

   * ``serious`` (string) (optional)
     Optional: Filter by event seriousness. Omit this parameter if you don't want to filter by seriousness.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FAERS_count_additive_event_reports_by_country",
          "arguments": {
              "medicinalproducts": ["item1", "item2"]
          }
      }
      result = tu.run(query)


**FAERS_count_additive_reaction_outcomes** (Type: FDACountAdditiveReactionsTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Determine reaction outcome counts (e.g., recovered, resolving, fatal) across medicinal products. ...

.. dropdown:: FAERS_count_additive_reaction_outcomes tool specification

   **Tool Information:**

   * **Name**: ``FAERS_count_additive_reaction_outcomes``
   * **Type**: ``FDACountAdditiveReactionsTool``
   * **Description**: Determine reaction outcome counts (e.g., recovered, resolving, fatal) across medicinal products. Only medicinalproducts is required; all other filters (patientsex, patientagegroup, occurcountry) are optional. Use filters sparingly to avoid overly restrictive searches. Data source: FDA Adverse Event Reporting System (FAERS).

   **Parameters:**

   * ``medicinalproducts`` (array) (required)
     Array of medicinal product names.

   * ``patientsex`` (string) (optional)
     No description

   * ``patientagegroup`` (string) (optional)
     No description

   * ``occurcountry`` (string) (optional)
     No description

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FAERS_count_additive_reaction_outcomes",
          "arguments": {
              "medicinalproducts": ["item1", "item2"]
          }
      }
      result = tu.run(query)


**FAERS_count_additive_reports_by_reporter_country** (Type: FDACountAdditiveReactionsTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Aggregate adverse event reports by primary reporter country across medicinal products. Only medic...

.. dropdown:: FAERS_count_additive_reports_by_reporter_country tool specification

   **Tool Information:**

   * **Name**: ``FAERS_count_additive_reports_by_reporter_country``
   * **Type**: ``FDACountAdditiveReactionsTool``
   * **Description**: Aggregate adverse event reports by primary reporter country across medicinal products. Only medicinalproducts is required; all other filters (patientsex, patientagegroup, serious) are optional. Use filters sparingly to avoid overly restrictive searches. Data source: FDA Adverse Event Reporting System (FAERS).

   **Parameters:**

   * ``medicinalproducts`` (array) (required)
     Array of medicinal product names.

   * ``patientsex`` (string) (optional)
     Optional: Filter by patient sex. Omit this parameter if you don't want to filter by sex.

   * ``patientagegroup`` (string) (optional)
     Optional: Filter by patient age group. Omit this parameter if you don't want to filter by age.

   * ``serious`` (string) (optional)
     Optional: Filter by event seriousness. Omit this parameter if you don't want to filter by seriousness.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FAERS_count_additive_reports_by_reporter_country",
          "arguments": {
              "medicinalproducts": ["item1", "item2"]
          }
      }
      result = tu.run(query)


**FAERS_count_additive_seriousness_classification** (Type: FDACountAdditiveReactionsTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Quantify serious vs non-serious classifications across medicinal products. Only medicinalproducts...

.. dropdown:: FAERS_count_additive_seriousness_classification tool specification

   **Tool Information:**

   * **Name**: ``FAERS_count_additive_seriousness_classification``
   * **Type**: ``FDACountAdditiveReactionsTool``
   * **Description**: Quantify serious vs non-serious classifications across medicinal products. Only medicinalproducts is required; all other filters (patientsex, patientagegroup, occurcountry) are optional. Use filters sparingly to avoid overly restrictive searches. Data source: FDA Adverse Event Reporting System (FAERS).

   **Parameters:**

   * ``medicinalproducts`` (array) (required)
     Array of medicinal product names.

   * ``patientsex`` (string) (optional)
     Optional: Filter by patient sex. Omit this parameter if you don't want to filter by sex.

   * ``patientagegroup`` (string) (optional)
     Optional: Filter by patient age group. Omit this parameter if you don't want to filter by age.

   * ``occurcountry`` (string) (optional)
     Optional: Filter by country where event occurred (ISO2 code, e.g., 'US', 'GB'). Omit this parameter if you don't want to filter by country.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FAERS_count_additive_seriousness_classification",
          "arguments": {
              "medicinalproducts": ["item1", "item2"]
          }
      }
      result = tu.run(query)


**FAERS_count_country_by_drug_event** (Type: FDADrugAdverseEventTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Count the number of adverse event reports per country of occurrence. Only medicinalproduct is req...

.. dropdown:: FAERS_count_country_by_drug_event tool specification

   **Tool Information:**

   * **Name**: ``FAERS_count_country_by_drug_event``
   * **Type**: ``FDADrugAdverseEventTool``
   * **Description**: Count the number of adverse event reports per country of occurrence. Only medicinalproduct is required; all other filters (patientsex, patientagegroup, serious) are optional. Use filters sparingly to avoid overly restrictive searches. Data source: FDA Adverse Event Reporting System (FAERS).

   **Parameters:**

   * ``medicinalproduct`` (string) (required)
     Drug name.

   * ``patientsex`` (string) (optional)
     Optional: Filter by patient sex. Omit this parameter if you don't want to filter by sex.

   * ``patientagegroup`` (string) (optional)
     Optional: Filter by patient age group. Omit this parameter if you don't want to filter by age.

   * ``serious`` (string) (optional)
     Optional: Filter by event seriousness. Omit this parameter if you don't want to filter by seriousness.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FAERS_count_country_by_drug_event",
          "arguments": {
              "medicinalproduct": "example_value"
          }
      }
      result = tu.run(query)


**FAERS_count_death_related_by_drug** (Type: FDADrugAdverseEventTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Count adverse events associated with patient death for a given drug. Only medicinalproduct is req...

.. dropdown:: FAERS_count_death_related_by_drug tool specification

   **Tool Information:**

   * **Name**: ``FAERS_count_death_related_by_drug``
   * **Type**: ``FDADrugAdverseEventTool``
   * **Description**: Count adverse events associated with patient death for a given drug. Only medicinalproduct is required. Data source: FDA Adverse Event Reporting System (FAERS).

   **Parameters:**

   * ``medicinalproduct`` (string) (required)
     Drug name.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FAERS_count_death_related_by_drug",
          "arguments": {
              "medicinalproduct": "example_value"
          }
      }
      result = tu.run(query)


**FAERS_count_drug_routes_by_event** (Type: FDADrugAdverseEventTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Count the most common routes of administration for drugs involved in adverse event reports. Only ...

.. dropdown:: FAERS_count_drug_routes_by_event tool specification

   **Tool Information:**

   * **Name**: ``FAERS_count_drug_routes_by_event``
   * **Type**: ``FDADrugAdverseEventTool``
   * **Description**: Count the most common routes of administration for drugs involved in adverse event reports. Only medicinalproduct is required; serious filter is optional. Use filters sparingly to avoid overly restrictive searches. Data source: FDA Adverse Event Reporting System (FAERS).

   **Parameters:**

   * ``medicinalproduct`` (string) (required)
     Drug name.

   * ``serious`` (string) (optional)
     Optional: Filter by event seriousness. Omit this parameter if you don't want to filter by seriousness.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FAERS_count_drug_routes_by_event",
          "arguments": {
              "medicinalproduct": "example_value"
          }
      }
      result = tu.run(query)


**FAERS_count_drugs_by_drug_event** (Type: FDADrugAdverseEventTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Count the number of different drugs involved in FDA adverse event reports. All filters (patientse...

.. dropdown:: FAERS_count_drugs_by_drug_event tool specification

   **Tool Information:**

   * **Name**: ``FAERS_count_drugs_by_drug_event``
   * **Type**: ``FDADrugAdverseEventTool``
   * **Description**: Count the number of different drugs involved in FDA adverse event reports. All filters (patientsex, patientagegroup, occurcountry, serious) are optional. Use filters sparingly to avoid overly restrictive searches. Data source: FDA Adverse Event Reporting System (FAERS).

   **Parameters:**

   * ``patientsex`` (string) (optional)
     Optional: Filter by patient sex. Omit this parameter if you don't want to filter by sex.

   * ``patientagegroup`` (string) (optional)
     Optional: Filter by patient age group. Omit this parameter if you don't want to filter by age.

   * ``occurcountry`` (string) (optional)
     Optional: Filter by country where event occurred (ISO2 code, e.g., 'US', 'GB'). Omit this parameter if you don't want to filter by country.

   * ``serious`` (string) (optional)
     Optional: Filter by event seriousness. Omit this parameter if you don't want to filter by seriousness.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FAERS_count_drugs_by_drug_event",
          "arguments": {
          }
      }
      result = tu.run(query)


**FAERS_count_outcomes_by_drug_event** (Type: FDADrugAdverseEventTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Count the outcome of adverse reactions (recovered, recovering, fatal, unresolved). Only medicinal...

.. dropdown:: FAERS_count_outcomes_by_drug_event tool specification

   **Tool Information:**

   * **Name**: ``FAERS_count_outcomes_by_drug_event``
   * **Type**: ``FDADrugAdverseEventTool``
   * **Description**: Count the outcome of adverse reactions (recovered, recovering, fatal, unresolved). Only medicinalproduct is required; all other filters (patientsex, patientagegroup, occurcountry) are optional. Use filters sparingly to avoid overly restrictive searches. Data source: FDA Adverse Event Reporting System (FAERS).

   **Parameters:**

   * ``medicinalproduct`` (string) (required)
     Drug name.

   * ``patientsex`` (string) (optional)
     No description

   * ``patientagegroup`` (string) (optional)
     No description

   * ``occurcountry`` (string) (optional)
     No description

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FAERS_count_outcomes_by_drug_event",
          "arguments": {
              "medicinalproduct": "example_value"
          }
      }
      result = tu.run(query)


**FAERS_count_patient_age_distribution** (Type: FDADrugAdverseEventTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Analyze the age distribution of patients experiencing adverse events for a specific drug. Only me...

.. dropdown:: FAERS_count_patient_age_distribution tool specification

   **Tool Information:**

   * **Name**: ``FAERS_count_patient_age_distribution``
   * **Type**: ``FDADrugAdverseEventTool``
   * **Description**: Analyze the age distribution of patients experiencing adverse events for a specific drug. Only medicinalproduct is required. The age groups are: Neonate (0-28 days), Infant (29 days - 23 months), Child (2-11 years), Adolescent (12-17 years), Adult (18-64 years), Elderly (65+ years). Data source: FDA Adverse Event Reporting System (FAERS).

   **Parameters:**

   * ``medicinalproduct`` (string) (required)
     Drug name.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FAERS_count_patient_age_distribution",
          "arguments": {
              "medicinalproduct": "example_value"
          }
      }
      result = tu.run(query)


**FAERS_count_reactions_by_drug_event** (Type: FDADrugAdverseEventTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Count the number of adverse reactions reported for a given drug. Only medicinalproduct is require...

.. dropdown:: FAERS_count_reactions_by_drug_event tool specification

   **Tool Information:**

   * **Name**: ``FAERS_count_reactions_by_drug_event``
   * **Type**: ``FDADrugAdverseEventTool``
   * **Description**: Count the number of adverse reactions reported for a given drug. Only medicinalproduct is required; all other filters (patientsex, patientagegroup, occurcountry, serious, seriousnessdeath, reactionmeddraverse) are optional. When reactionmeddraverse is not specified, returns all adverse reactions (AE) with their counts grouped by MedDRA Preferred Term. When reactionmeddraverse is specified, filters results to only include that specific MedDRA Lowest Level Term. Use filters sparingly to avoid overly restrictive searches that return no results. Data source: FDA Adverse Event Reporting System (FAERS).

   **Parameters:**

   * ``medicinalproduct`` (string) (required)
     Drug name.

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

   * ``reactionmeddraverse`` (string) (optional)
     Optional: Filter by MedDRA reaction term (Lowest Level Term). When omitted, returns all adverse reactions with their counts. When specified, filters results to only include that specific reaction term.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FAERS_count_reactions_by_drug_event",
          "arguments": {
              "medicinalproduct": "example_value"
          }
      }
      result = tu.run(query)


**FAERS_count_reportercountry_by_drug_event** (Type: FDADrugAdverseEventTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Count the number of FDA adverse event reports grouped by the country of the primary reporter. Onl...

.. dropdown:: FAERS_count_reportercountry_by_drug_event tool specification

   **Tool Information:**

   * **Name**: ``FAERS_count_reportercountry_by_drug_event``
   * **Type**: ``FDADrugAdverseEventTool``
   * **Description**: Count the number of FDA adverse event reports grouped by the country of the primary reporter. Only medicinalproduct is required; all other filters (patientsex, patientagegroup, serious) are optional. Use filters sparingly to avoid overly restrictive searches. Data source: FDA Adverse Event Reporting System (FAERS).

   **Parameters:**

   * ``medicinalproduct`` (string) (required)
     Drug name.

   * ``patientsex`` (string) (optional)
     Optional: Filter by patient sex. Omit this parameter if you don't want to filter by sex.

   * ``patientagegroup`` (string) (optional)
     Optional: Filter by patient age group. Omit this parameter if you don't want to filter by age.

   * ``serious`` (string) (optional)
     Optional: Filter by event seriousness. Omit this parameter if you don't want to filter by seriousness.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FAERS_count_reportercountry_by_drug_event",
          "arguments": {
              "medicinalproduct": "example_value"
          }
      }
      result = tu.run(query)


**FAERS_count_seriousness_by_drug_event** (Type: FDADrugAdverseEventTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Count the number of adverse event reports classified as serious or non-serious. Only medicinalpro...

.. dropdown:: FAERS_count_seriousness_by_drug_event tool specification

   **Tool Information:**

   * **Name**: ``FAERS_count_seriousness_by_drug_event``
   * **Type**: ``FDADrugAdverseEventTool``
   * **Description**: Count the number of adverse event reports classified as serious or non-serious. Only medicinalproduct is required; all other filters (patientsex, patientagegroup, occurcountry) are optional. Use filters sparingly to avoid overly restrictive searches. In results, term Serious means: "The adverse event resulted in death, a life threatening condition, hospitalization, disability, congenital anomaly, or other serious condition", term Non-serious means "The adverse event did not result in any of the above". Data source: FDA Adverse Event Reporting System (FAERS).

   **Parameters:**

   * ``medicinalproduct`` (string) (required)
     Drug name.

   * ``patientsex`` (string) (optional)
     Optional: Filter by patient sex. Omit this parameter if you don't want to filter by sex.

   * ``patientagegroup`` (string) (optional)
     Optional: Filter by patient age group. Omit this parameter if you don't want to filter by age.

   * ``occurcountry`` (string) (optional)
     Optional: Filter by country where event occurred (ISO2 code, e.g., 'US', 'GB'). Omit this parameter if you don't want to filter by country.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "FAERS_count_seriousness_by_drug_event",
          "arguments": {
              "medicinalproduct": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
