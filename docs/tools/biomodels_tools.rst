Biomodels Tools
===============

**Configuration File**: ``biomodels_tools.json``
**Tool Type**: Local
**Tools Count**: 2

This page contains all tools defined in the ``biomodels_tools.json`` configuration file.

Available Tools
---------------

**biomodels_get_files** (Type: BioModelsTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieves the download link for a specific biological model from the BioModels database using its...

.. dropdown:: biomodels_get_files tool specification

   **Tool Information:**

   * **Name**: ``biomodels_get_files``
   * **Type**: ``BioModelsTool``
   * **Description**: Retrieves the download link for a specific biological model from the BioModels database using its Model ID.

   **Parameters:**

   * ``action`` (string) (required)
     The specific action to perform. Must be set to 'get_model_files'.

   * ``model_id`` (string) (required)
     The unique Model ID (e.g., 'BIOMD0000000469') for which to retrieve the download link.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "biomodels_get_files",
          "arguments": {
              "action": "example_value",
              "model_id": "example_value"
          }
      }
      result = tu.run(query)


**biomodels_search** (Type: BioModelsTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Searches for computational biological models in the EBI BioModels database. Use this tool to find...

.. dropdown:: biomodels_search tool specification

   **Tool Information:**

   * **Name**: ``biomodels_search``
   * **Type**: ``BioModelsTool``
   * **Description**: Searches for computational biological models in the EBI BioModels database. Use this tool to find models related to specific biological processes, such as 'glycolysis' or 'apoptosis'.

   **Parameters:**

   * ``action`` (string) (required)
     The specific action to perform. Must be set to 'search_models'.

   * ``query`` (string) (required)
     The search term to query the BioModels database. Example queries include pathway names ('glycolysis'), disease names, or other biological keywords.

   * ``limit`` (integer) (optional)
     The maximum number of model results to return. The default is 10.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "biomodels_search",
          "arguments": {
              "action": "example_value",
              "query": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
