Tool Discovery Agents
=====================

**Configuration File**: ``tool_discovery_agents.json``
**Tool Type**: Local
**Tools Count**: 7

This page contains all tools defined in the ``tool_discovery_agents.json`` configuration file.

Available Tools
---------------

**CodeQualityAnalyzer** (Type: AgenticTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Analyzes code quality from multiple dimensions including algorithmic correctness, functional impl...

.. dropdown:: CodeQualityAnalyzer tool specification

   **Tool Information:**

   * **Name**: ``CodeQualityAnalyzer``
   * **Type**: ``AgenticTool``
   * **Description**: Analyzes code quality from multiple dimensions including algorithmic correctness, functional implementation capability, performance characteristics, and best practices. Provides detailed feedback and improvement suggestions.

   **Parameters:**

   * ``tool_name`` (string) (required)
     Name of the tool being analyzed

   * ``tool_description`` (string) (required)
     Description of what the tool is supposed to do

   * ``tool_parameters`` (string) (required)
     JSON string of tool parameters and their types

   * ``implementation_code`` (string) (required)
     The actual implementation code to analyze

   * ``test_cases`` (string) (required)
     JSON string of test cases for the tool

   * ``test_execution_results`` (string) (required)
     JSON string of test execution results including pass/fail status and actual outputs

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "CodeQualityAnalyzer",
          "arguments": {
              "tool_name": "example_value",
              "tool_description": "example_value",
              "tool_parameters": "example_value",
              "implementation_code": "example_value",
              "test_cases": "example_value",
              "test_execution_results": "example_value"
          }
      }
      result = tu.run(query)


**PackageAnalyzer** (Type: AgenticTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Analyzes package candidates and recommends the best options based on quality metrics and suitability

.. dropdown:: PackageAnalyzer tool specification

   **Tool Information:**

   * **Name**: ``PackageAnalyzer``
   * **Type**: ``AgenticTool``
   * **Description**: Analyzes package candidates and recommends the best options based on quality metrics and suitability

   **Parameters:**

   * ``tool_description`` (string) (required)
     Description of the tool being generated

   * ``package_candidates`` (string) (required)
     JSON string containing package candidates with their metadata (from PyPI, search results, etc.)

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "PackageAnalyzer",
          "arguments": {
              "tool_description": "example_value",
              "package_candidates": "example_value"
          }
      }
      result = tu.run(query)


**ReferenceInfoAnalyzer** (Type: AgenticTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Analyzes and curates reference information to provide high-quality context for tool generation

.. dropdown:: ReferenceInfoAnalyzer tool specification

   **Tool Information:**

   * **Name**: ``ReferenceInfoAnalyzer``
   * **Type**: ``AgenticTool``
   * **Description**: Analyzes and curates reference information to provide high-quality context for tool generation

   **Parameters:**

   * ``tool_description`` (string) (required)
     Description of the tool being generated

   * ``raw_reference_info`` (string) (required)
     JSON string containing raw reference information from web search and package discovery

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "ReferenceInfoAnalyzer",
          "arguments": {
              "tool_description": "example_value",
              "raw_reference_info": "example_value"
          }
      }
      result = tu.run(query)


**TestResultsAnalyzer** (Type: AgenticTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Analyzes test execution results and extracts key issues for targeted optimization

.. dropdown:: TestResultsAnalyzer tool specification

   **Tool Information:**

   * **Name**: ``TestResultsAnalyzer``
   * **Type**: ``AgenticTool``
   * **Description**: Analyzes test execution results and extracts key issues for targeted optimization

   **Parameters:**

   * ``test_results`` (string) (required)
     JSON string containing test execution results with pass/fail status, error messages, and tracebacks

   * ``tool_implementation`` (string) (required)
     Current tool implementation code for context

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "TestResultsAnalyzer",
          "arguments": {
              "test_results": "example_value",
              "tool_implementation": "example_value"
          }
      }
      result = tu.run(query)


**ToolDiscover** (Type: ComposeTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Generates new ToolUniverse-compliant tools based on short descriptions using XML format for simul...

.. dropdown:: ToolDiscover tool specification

   **Tool Information:**

   * **Name**: ``ToolDiscover``
   * **Type**: ``ComposeTool``
   * **Description**: Generates new ToolUniverse-compliant tools based on short descriptions using XML format for simultaneous code and specification generation. Automatically discovers similar tools, curates high-quality reference information, and iteratively optimizes the tool using agentic optimization.

   **Parameters:**

   * ``tool_description`` (string) (required)
     Short description of the desired tool functionality

   * ``max_iterations`` (integer) (optional)
     Maximum number of optimization iterations

   * ``save_to_file`` (boolean) (optional)
     Whether to save the generated tool files

   * ``output_file`` (string) (optional)
     Optional file path to save the generated tool

   * ``save_dir`` (string) (optional)
     Directory path to save the generated tool files (defaults to current working directory)

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "ToolDiscover",
          "arguments": {
              "tool_description": "example_value"
          }
      }
      result = tu.run(query)


**UnifiedToolGenerator** (Type: AgenticTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Generates complete ToolUniverse tools using simplified XML format that simultaneously creates bot...

.. dropdown:: UnifiedToolGenerator tool specification

   **Tool Information:**

   * **Name**: ``UnifiedToolGenerator``
   * **Type**: ``AgenticTool``
   * **Description**: Generates complete ToolUniverse tools using simplified XML format that simultaneously creates both implementation code and specification

   **Parameters:**

   * ``tool_description`` (string) (required)
     Description of the desired tool functionality

   * ``reference_info`` (string) (required)
     JSON string containing curated reference information including API documentation and package recommendations

   * ``xml_template`` (string) (required)
     XML template example showing the expected format with code and spec sections

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "UnifiedToolGenerator",
          "arguments": {
              "tool_description": "example_value",
              "reference_info": "example_value",
              "xml_template": "example_value"
          }
      }
      result = tu.run(query)


**XMLToolOptimizer** (Type: AgenticTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Optimizes tools defined in XML format based on test results and quality feedback

.. dropdown:: XMLToolOptimizer tool specification

   **Tool Information:**

   * **Name**: ``XMLToolOptimizer``
   * **Type**: ``AgenticTool``
   * **Description**: Optimizes tools defined in XML format based on test results and quality feedback

   **Parameters:**

   * ``xml_tool`` (string) (required)
     Current XML-formatted tool definition with code and spec sections

   * ``optimization_context`` (string) (required)
     JSON string containing test results, quality feedback, iteration info, improvement history, and any special instructions

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "XMLToolOptimizer",
          "arguments": {
              "xml_tool": "example_value",
              "optimization_context": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
