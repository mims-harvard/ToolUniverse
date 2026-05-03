Clinical Trials Tools
=====================

**Configuration File**: ``clinical_trials_tools.json``
**Tool Type**: Local
**Tools Count**: 2

This page contains all tools defined in the ``clinical_trials_tools.json`` configuration file.

Available Tools
---------------

**clinical_trials_get_details** (Type: ClinicalTrialsGovTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieves comprehensive details about a specific clinical trial using its NCT ID.

.. dropdown:: clinical_trials_get_details tool specification

   **Tool Information:**

   * **Name**: ``clinical_trials_get_details``
   * **Type**: ``ClinicalTrialsGovTool``
   * **Description**: Retrieves comprehensive details about a specific clinical trial using its NCT ID.

   **Parameters:**

   * ``action`` (string) (required)
     The specific action to perform. Must be set to 'get_study_details'.

   * ``nct_id`` (string) (required)
     The unique NCT identifier of the study to retrieve (e.g., 'NCT05033756'). This ID is required.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "clinical_trials_get_details",
          "arguments": {
              "action": "example_value",
              "nct_id": "example_value"
          }
      }
      result = tu.run(query)


**clinical_trials_search** (Type: ClinicalTrialsGovTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Searches for clinical trials on ClinicalTrials.gov using conditions and/or interventions as filte...

.. dropdown:: clinical_trials_search tool specification

   **Tool Information:**

   * **Name**: ``clinical_trials_search``
   * **Type**: ``ClinicalTrialsGovTool``
   * **Description**: Searches for clinical trials on ClinicalTrials.gov using conditions and/or interventions as filters. Retrieve a list of trials matching the criteria.

   **Parameters:**

   * ``action`` (string) (required)
     The specific action to perform. Must be set to 'search_studies'.

   * ``condition`` (string) (optional)
     The disease or condition to search for (e.g., 'breast cancer', 'diabetes'). Use this to find trials related to specific health issues.

   * ``intervention`` (string) (optional)
     The drug, treatment, or intervention to search for (e.g., 'pembrolizumab', 'cognitive behavioral therapy'). Use this to find trials testing specific treatments.

   * ``limit`` (integer) (optional)
     The maximum number of study summaries to return. The default is 10. Adjust this limit to control the number of results.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "clinical_trials_search",
          "arguments": {
              "action": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
