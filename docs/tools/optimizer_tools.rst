Optimizer Tools
===============

**Configuration File**: ``optimizer_tools.json``
**Tool Type**: Local
**Tools Count**: 5

This page contains all tools defined in the ``optimizer_tools.json`` configuration file.

Available Tools
---------------

**ArgumentDescriptionOptimizer** (Type: AgenticTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Optimizes the descriptions of tool arguments/parameters based on test case results and actual usa...

.. dropdown:: ArgumentDescriptionOptimizer tool specification

   **Tool Information:**

   * **Name**: ``ArgumentDescriptionOptimizer``
   * **Type**: ``AgenticTool``
   * **Description**: Optimizes the descriptions of tool arguments/parameters based on test case results and actual usage patterns. Provides improved descriptions that are more accurate and user-friendly.

   **Parameters:**

   * ``parameter_schema`` (string) (required)
     JSON string of the original parameter schema with properties and descriptions.

   * ``test_results`` (string) (required)
     A JSON string containing test case input/output pairs showing parameter usage.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "ArgumentDescriptionOptimizer",
          "arguments": {
              "parameter_schema": "example_value",
              "test_results": "example_value"
          }
      }
      result = tu.run(query)


**DescriptionAnalyzer** (Type: AgenticTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Analyzes a tool's original description and the results of multiple test cases, then suggests an i...

.. dropdown:: DescriptionAnalyzer tool specification

   **Tool Information:**

   * **Name**: ``DescriptionAnalyzer``
   * **Type**: ``AgenticTool``
   * **Description**: Analyzes a tool's original description and the results of multiple test cases, then suggests an improved description that is more accurate, comprehensive, and user-friendly. Optionally provides a rationale for the changes.

   **Parameters:**

   * ``original_description`` (string) (required)
     The original description of the tool.

   * ``test_results`` (string) (required)
     A JSON string containing a list of test case input/output pairs.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "DescriptionAnalyzer",
          "arguments": {
              "original_description": "example_value",
              "test_results": "example_value"
          }
      }
      result = tu.run(query)


**DescriptionQualityEvaluator** (Type: AgenticTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Evaluates the quality of tool descriptions and parameter descriptions, providing a score and spec...

.. dropdown:: DescriptionQualityEvaluator tool specification

   **Tool Information:**

   * **Name**: ``DescriptionQualityEvaluator``
   * **Type**: ``AgenticTool``
   * **Description**: Evaluates the quality of tool descriptions and parameter descriptions, providing a score and specific feedback for improvements.

   **Parameters:**

   * ``tool_description`` (string) (required)
     The tool description to evaluate.

   * ``parameter_descriptions`` (string) (required)
     JSON string of parameter names and their descriptions.

   * ``test_results`` (string) (required)
     JSON string containing test case results.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "DescriptionQualityEvaluator",
          "arguments": {
              "tool_description": "example_value",
              "parameter_descriptions": "example_value",
              "test_results": "example_value"
          }
      }
      result = tu.run(query)


**TestCaseGenerator** (Type: AgenticTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Generates diverse and representative ToolUniverse tool call dictionaries for a given tool based o...

.. dropdown:: TestCaseGenerator tool specification

   **Tool Information:**

   * **Name**: ``TestCaseGenerator``
   * **Type**: ``AgenticTool``
   * **Description**: Generates diverse and representative ToolUniverse tool call dictionaries for a given tool based on its parameter schema. Each tool call should be a JSON object with 'name' (the tool's name) and 'arguments' (a dict of input arguments), covering different parameter combinations, edge cases, and typical usage. Can generate targeted test cases based on previous optimization feedback.

   **Parameters:**

   * ``tool_config`` (object) (required)
     The full configuration of the tool to generate test cases for. May include '_optimization_feedback' and '_iteration' fields for feedback-driven test generation.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "TestCaseGenerator",
          "arguments": {
              "tool_config": "example_value"
          }
      }
      result = tu.run(query)


**ToolDescriptionOptimizer** (Type: ComposeTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Optimizes a tool's description and parameter descriptions by generating test cases, executing the...

.. dropdown:: ToolDescriptionOptimizer tool specification

   **Tool Information:**

   * **Name**: ``ToolDescriptionOptimizer``
   * **Type**: ``ComposeTool``
   * **Description**: Optimizes a tool's description and parameter descriptions by generating test cases, executing them, analyzing the results, and suggesting improved descriptions for both the tool and its arguments. Optionally saves a comprehensive optimization report to a file without overwriting the original.

   **Parameters:**

   * ``tool_config`` (object) (required)
     The full configuration of the tool to optimize.

   * ``save_to_file`` (boolean) (required)
     If true, save the optimized description to a file (do not overwrite the original).

   * ``output_file`` (string) (required)
     Optional file path to save the optimized description. If not provided, use '<tool_name>_optimized_description.txt'.

   * ``max_iterations`` (integer) (required)
     Maximum number of optimization rounds to perform.

   * ``satisfaction_threshold`` (number) (required)
     Quality score threshold (1-10) to consider optimization satisfactory.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "ToolDescriptionOptimizer",
          "arguments": {
              "tool_config": "example_value",
              "save_to_file": true,
              "output_file": "example_value",
              "max_iterations": 10,
              "satisfaction_threshold": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
