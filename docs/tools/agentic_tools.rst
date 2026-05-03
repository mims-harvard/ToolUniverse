Agentic Tools
=============

**Configuration File**: ``agentic_tools.json``
**Tool Type**: Local
**Tools Count**: 25

This page contains all tools defined in the ``agentic_tools.json`` configuration file.

Available Tools
---------------

**AdvancedCodeQualityAnalyzer** (Type: AgenticTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Performs deep analysis of code quality including complexity, security, performance, and maintaina...

.. dropdown:: AdvancedCodeQualityAnalyzer tool specification

   **Tool Information:**

   * **Name**: ``AdvancedCodeQualityAnalyzer``
   * **Type**: ``AgenticTool``
   * **Description**: Performs deep analysis of code quality including complexity, security, performance, and maintainability metrics with domain-specific expertise

   **Parameters:**

   * ``source_code`` (string) (required)
     The source code to analyze for quality assessment

   * ``language`` (string) (optional)
     Programming language (python, javascript, etc.)

   * ``analysis_depth`` (string) (optional)
     Level of analysis depth to perform

   * ``domain_context`` (string) (optional)
     Domain context for specialized analysis (e.g., bioinformatics, web development)

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "AdvancedCodeQualityAnalyzer",
          "arguments": {
              "source_code": "example_value"
          }
      }
      result = tu.run(query)


**DataAnalysisValidityReviewer** (Type: AgenticTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Checks statistical choices, assumption testing, and reporting transparency.

.. dropdown:: DataAnalysisValidityReviewer tool specification

   **Tool Information:**

   * **Name**: ``DataAnalysisValidityReviewer``
   * **Type**: ``AgenticTool``
   * **Description**: Checks statistical choices, assumption testing, and reporting transparency.

   **Parameters:**

   * ``analysis_section`` (string) (required)
     No description

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "DataAnalysisValidityReviewer",
          "arguments": {
              "analysis_section": "example_value"
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


**DomainExpertValidator** (Type: AgenticTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Provides domain-specific validation and expert recommendations for tools with deep expertise acro...

.. dropdown:: DomainExpertValidator tool specification

   **Tool Information:**

   * **Name**: ``DomainExpertValidator``
   * **Type**: ``AgenticTool``
   * **Description**: Provides domain-specific validation and expert recommendations for tools with deep expertise across scientific and technical domains

   **Parameters:**

   * ``tool_config`` (string) (required)
     JSON string of tool configuration to validate

   * ``domain`` (string) (required)
     Domain expertise area for validation

   * ``validation_aspects`` (string) (optional)
     JSON array string of specific aspects to validate

   * ``implementation_code`` (string) (optional)
     Implementation code to validate (optional)

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "DomainExpertValidator",
          "arguments": {
              "tool_config": "example_value",
              "domain": "example_value"
          }
      }
      result = tu.run(query)


**EthicalComplianceReviewer** (Type: AgenticTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Checks adherence to ethical standards and disclosure practices.

.. dropdown:: EthicalComplianceReviewer tool specification

   **Tool Information:**

   * **Name**: ``EthicalComplianceReviewer``
   * **Type**: ``AgenticTool``
   * **Description**: Checks adherence to ethical standards and disclosure practices.

   **Parameters:**

   * ``ethics_section`` (string) (required)
     No description

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "EthicalComplianceReviewer",
          "arguments": {
              "ethics_section": "example_value"
          }
      }
      result = tu.run(query)


**ExperimentalDesignScorer** (Type: AgenticTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Assesses a proposed experimental design by assigning scores and structured feedback on hypothesis...

.. dropdown:: ExperimentalDesignScorer tool specification

   **Tool Information:**

   * **Name**: ``ExperimentalDesignScorer``
   * **Type**: ``AgenticTool``
   * **Description**: Assesses a proposed experimental design by assigning scores and structured feedback on hypothesis clarity, variable definitions, sample size, controls, randomization, measurement methods, statistical analysis, bias mitigation, ethical considerations, and overall feasibility.

   **Parameters:**

   * ``hypothesis`` (string) (required)
     A clear statement of the research hypothesis to be tested.

   * ``design_description`` (string) (required)
     A detailed description of the proposed experimental design, including variables, methods, sample details, and planned analyses.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "ExperimentalDesignScorer",
          "arguments": {
              "hypothesis": "example_value",
              "design_description": "example_value"
          }
      }
      result = tu.run(query)


**HypothesisGenerator** (Type: AgenticTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Generates research hypotheses based on provided background context, domain, and desired format. U...

.. dropdown:: HypothesisGenerator tool specification

   **Tool Information:**

   * **Name**: ``HypothesisGenerator``
   * **Type**: ``AgenticTool``
   * **Description**: Generates research hypotheses based on provided background context, domain, and desired format. Uses AI to propose novel, testable hypotheses for scientific exploration.

   **Parameters:**

   * ``context`` (string) (required)
     Background information, observations, or data description from which to derive hypotheses.

   * ``domain`` (string) (required)
     Field of study or research area (e.g., 'neuroscience', 'ecology', 'materials science').

   * ``number_of_hypotheses`` (string) (required)
     Number of hypotheses to generate (e.g., '3', '5').

   * ``hypothesis_format`` (string) (optional)
     Optional directive on how to structure each hypothesis. Choose from one of the following formats:

1. If–Then Statements: "If [independent variable condition], then [expected outcome]."
2. Null and Alternative (Statistical):
   • H₀ (Null): "There is no difference/effect/association between X and Y."
   • H₁ (Alt): "There is a difference/effect/association between X and Y."
3. Associative (Correlation-Focused): "There is a relationship/association between [Variable A] and [Variable B]."
4. Directional (Non-If–Then): "Increasing/decreasing [Variable A] will lead to [directional change] in [Variable B]."
5. Comparative (Group Comparison): "Group A will show higher/lower [dependent measure] compared to Group B under [condition]."
6. Mechanistic: "Because [mechanism or process], [Variable A] will cause [Variable B]."
7. Descriptive (Exploratory/Pattern-Oriented): "Population X exhibits pattern Y in context Z."

If omitted, defaults to concise declarative sentences.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "HypothesisGenerator",
          "arguments": {
              "context": "example_value",
              "domain": "example_value",
              "number_of_hypotheses": "example_value"
          }
      }
      result = tu.run(query)


**LabelGenerator** (Type: AgenticTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Generates relevant keyword labels for tools based on their name, description, parameters, and cat...

.. dropdown:: LabelGenerator tool specification

   **Tool Information:**

   * **Name**: ``LabelGenerator``
   * **Type**: ``AgenticTool``
   * **Description**: Generates relevant keyword labels for tools based on their name, description, parameters, and category. Creates a comprehensive list of tags for tool discovery and categorization.

   **Parameters:**

   * ``tool_name`` (string) (required)
     The name of the tool

   * ``tool_description`` (string) (required)
     Detailed description of what the tool does

   * ``tool_parameters`` (string) (required)
     JSON string describing the tool's input parameters and their types

   * ``category`` (string) (required)
     The general category or domain the tool belongs to

   * ``existing_labels`` (string) (optional)
     JSON array string of existing labels to consider reusing (optional)

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "LabelGenerator",
          "arguments": {
              "tool_name": "example_value",
              "tool_description": "example_value",
              "tool_parameters": "example_value",
              "category": "example_value"
          }
      }
      result = tu.run(query)


**LiteratureContextReviewer** (Type: AgenticTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Reviews coverage, relevance, and critical synthesis of prior scholarship.

.. dropdown:: LiteratureContextReviewer tool specification

   **Tool Information:**

   * **Name**: ``LiteratureContextReviewer``
   * **Type**: ``AgenticTool``
   * **Description**: Reviews coverage, relevance, and critical synthesis of prior scholarship.

   **Parameters:**

   * ``paper_title`` (string) (required)
     No description

   * ``literature_review`` (string) (required)
     Full literature-review text

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "LiteratureContextReviewer",
          "arguments": {
              "paper_title": "example_value",
              "literature_review": "example_value"
          }
      }
      result = tu.run(query)


**MedicalLiteratureReviewer** (Type: AgenticTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Conducts systematic reviews of medical literature on specific topics. Synthesizes findings from m...

.. dropdown:: MedicalLiteratureReviewer tool specification

   **Tool Information:**

   * **Name**: ``MedicalLiteratureReviewer``
   * **Type**: ``AgenticTool``
   * **Description**: Conducts systematic reviews of medical literature on specific topics. Synthesizes findings from multiple studies and provides evidence-based conclusions with structured analysis and quality assessment.

   **Parameters:**

   * ``research_topic`` (string) (required)
     The specific medical/research topic for literature review (e.g., 'efficacy of drug X in treating condition Y').

   * ``literature_content`` (string) (required)
     The literature content, abstracts, full studies, or research papers to review and synthesize.

   * ``focus_area`` (string) (required)
     Primary focus area for the review (e.g., 'therapeutic efficacy', 'safety profile', 'diagnostic accuracy', 'biomarker validation').

   * ``study_types`` (string) (required)
     Types of studies to prioritize in the analysis (e.g., 'randomized controlled trials', 'meta-analyses', 'cohort studies', 'case-control studies').

   * ``quality_level`` (string) (required)
     Minimum evidence quality level to include (e.g., 'high quality only', 'moderate and above', 'all available evidence').

   * ``review_scope`` (string) (required)
     Scope of the review (e.g., 'comprehensive systematic review', 'rapid review', 'scoping review', 'narrative review').

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "MedicalLiteratureReviewer",
          "arguments": {
              "research_topic": "example_value",
              "literature_content": "example_value",
              "focus_area": "example_value",
              "study_types": "example_value",
              "quality_level": "example_value",
              "review_scope": "example_value"
          }
      }
      result = tu.run(query)


**MedicalTermNormalizer** (Type: AgenticTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Identifies and corrects misspelled drug or disease names, returning a list of plausible standardi...

.. dropdown:: MedicalTermNormalizer tool specification

   **Tool Information:**

   * **Name**: ``MedicalTermNormalizer``
   * **Type**: ``AgenticTool``
   * **Description**: Identifies and corrects misspelled drug or disease names, returning a list of plausible standardized terms.

   **Parameters:**

   * ``raw_terms`` (string) (required)
     A comma- or whitespace-separated string containing one misspelled drug or disease name.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "MedicalTermNormalizer",
          "arguments": {
              "raw_terms": "example_value"
          }
      }
      result = tu.run(query)


**MethodologyRigorReviewer** (Type: AgenticTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Evaluates design appropriateness, sampling, and procedural transparency.

.. dropdown:: MethodologyRigorReviewer tool specification

   **Tool Information:**

   * **Name**: ``MethodologyRigorReviewer``
   * **Type**: ``AgenticTool``
   * **Description**: Evaluates design appropriateness, sampling, and procedural transparency.

   **Parameters:**

   * ``methods_section`` (string) (required)
     Full Methods text

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "MethodologyRigorReviewer",
          "arguments": {
              "methods_section": "example_value"
          }
      }
      result = tu.run(query)


**NoveltySignificanceReviewer** (Type: AgenticTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Provides a structured peer-review of the work's originality and potential impact.

.. dropdown:: NoveltySignificanceReviewer tool specification

   **Tool Information:**

   * **Name**: ``NoveltySignificanceReviewer``
   * **Type**: ``AgenticTool``
   * **Description**: Provides a structured peer-review of the work's originality and potential impact.

   **Parameters:**

   * ``paper_title`` (string) (required)
     Manuscript title

   * ``abstract`` (string) (required)
     Manuscript abstract

   * ``manuscript_text`` (string) (required)
     Full manuscript text

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "NoveltySignificanceReviewer",
          "arguments": {
              "paper_title": "example_value",
              "abstract": "example_value",
              "manuscript_text": "example_value"
          }
      }
      result = tu.run(query)


**ProtocolOptimizer** (Type: AgenticTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Reviews an initial protocol and delivers targeted revisions that improve clarity, feasibility, ri...

.. dropdown:: ProtocolOptimizer tool specification

   **Tool Information:**

   * **Name**: ``ProtocolOptimizer``
   * **Type**: ``AgenticTool``
   * **Description**: Reviews an initial protocol and delivers targeted revisions that improve clarity, feasibility, risk-management, and evaluation rigor.

   **Parameters:**

   * ``initial_protocol`` (string) (required)
     No description

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "ProtocolOptimizer",
          "arguments": {
              "initial_protocol": "example_value"
          }
      }
      result = tu.run(query)


**QuestionRephraser** (Type: AgenticTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Generates three distinct paraphrases of a given question while ensuring answer options remain val...

.. dropdown:: QuestionRephraser tool specification

   **Tool Information:**

   * **Name**: ``QuestionRephraser``
   * **Type**: ``AgenticTool``
   * **Description**: Generates three distinct paraphrases of a given question while ensuring answer options remain valid and applicable.

   **Parameters:**

   * ``question`` (string) (required)
     The original question text to be rephrased

   * ``options`` (string) (optional)
     Answer options (e.g., multiple choice options) that should remain valid for the rephrased questions. Leave empty if no options are provided.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "QuestionRephraser",
          "arguments": {
              "question": "example_value"
          }
      }
      result = tu.run(query)


**ReproducibilityTransparencyReviewer** (Type: AgenticTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Evaluates data, code, and protocol availability for replication.

.. dropdown:: ReproducibilityTransparencyReviewer tool specification

   **Tool Information:**

   * **Name**: ``ReproducibilityTransparencyReviewer``
   * **Type**: ``AgenticTool``
   * **Description**: Evaluates data, code, and protocol availability for replication.

   **Parameters:**

   * ``availability_statement`` (string) (required)
     No description

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "ReproducibilityTransparencyReviewer",
          "arguments": {
              "availability_statement": "example_value"
          }
      }
      result = tu.run(query)


**ResultsInterpretationReviewer** (Type: AgenticTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Judges whether conclusions are data-justified and limitations addressed.

.. dropdown:: ResultsInterpretationReviewer tool specification

   **Tool Information:**

   * **Name**: ``ResultsInterpretationReviewer``
   * **Type**: ``AgenticTool``
   * **Description**: Judges whether conclusions are data-justified and limitations addressed.

   **Parameters:**

   * ``results_section`` (string) (required)
     No description

   * ``discussion_section`` (string) (required)
     No description

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "ResultsInterpretationReviewer",
          "arguments": {
              "results_section": "example_value",
              "discussion_section": "example_value"
          }
      }
      result = tu.run(query)


**ScientificTextSummarizer** (Type: AgenticTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Summarizes biomedical research texts, abstracts, or papers with specified length and focus areas....

.. dropdown:: ScientificTextSummarizer tool specification

   **Tool Information:**

   * **Name**: ``ScientificTextSummarizer``
   * **Type**: ``AgenticTool``
   * **Description**: Summarizes biomedical research texts, abstracts, or papers with specified length and focus areas. Uses AI to extract key findings, methodology, and conclusions from complex biomedical literature.

   **Parameters:**

   * ``text`` (string) (required)
     The biomedical text, abstract, or paper content to be summarized.

   * ``summary_length`` (string) (required)
     Desired length of summary (e.g., '50', '100', '200 words').

   * ``focus_area`` (string) (required)
     What to focus on in the summary (e.g., 'methodology', 'results', 'clinical implications', 'drug interactions').

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "ScientificTextSummarizer",
          "arguments": {
              "text": "example_value",
              "summary_length": "example_value",
              "focus_area": "example_value"
          }
      }
      result = tu.run(query)


**ToolMetadataGenerator** (Type: AgenticTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Generates a JSON structure with the metadata of a tool in ToolUniverse, given the JSON configurat...

.. dropdown:: ToolMetadataGenerator tool specification

   **Tool Information:**

   * **Name**: ``ToolMetadataGenerator``
   * **Type**: ``AgenticTool``
   * **Description**: Generates a JSON structure with the metadata of a tool in ToolUniverse, given the JSON configuration of the tool.

   **Parameters:**

   * ``tool_config`` (string) (required)
     JSON string of the tool configuration to extract metadata from

   * ``tool_type_mappings`` (object) (optional)
     A mapping from a simplified toolType to a list of tool_config.type that fall under the toolType (e.g., {'Databases': ['XMLTool']})

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "ToolMetadataGenerator",
          "arguments": {
              "tool_config": "example_value"
          }
      }
      result = tu.run(query)


**ToolMetadataStandardizer** (Type: AgenticTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Standardizes and groups semantically equivalent metadata strings (e.g., sources, tags) into canon...

.. dropdown:: ToolMetadataStandardizer tool specification

   **Tool Information:**

   * **Name**: ``ToolMetadataStandardizer``
   * **Type**: ``AgenticTool``
   * **Description**: Standardizes and groups semantically equivalent metadata strings (e.g., sources, tags) into canonical forms for consistent downstream usage.

   **Parameters:**

   * ``metadata_list`` (array) (required)
     List of raw metadata strings (e.g., sources, tags) to standardize and group.

   * ``limit`` (integer) (optional)
     If provided, the maximum number of canonical strings to return. The LLM will group terms more aggressively to meet this limit, ensuring all raw strings are mapped.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "ToolMetadataStandardizer",
          "arguments": {
              "metadata_list": ["item1", "item2"]
          }
      }
      result = tu.run(query)


**ToolQualityEvaluator** (Type: AgenticTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Evaluates the quality of tool configurations and implementations. Provides detailed scoring and f...

.. dropdown:: ToolQualityEvaluator tool specification

   **Tool Information:**

   * **Name**: ``ToolQualityEvaluator``
   * **Type**: ``AgenticTool``
   * **Description**: Evaluates the quality of tool configurations and implementations. Provides detailed scoring and feedback for improvement.

   **Parameters:**

   * ``tool_config`` (string) (required)
     JSON string of the tool configuration

   * ``test_cases`` (string) (required)
     JSON string of test cases

   * ``evaluation_aspects`` (array) (required)
     Aspects to evaluate (functionality, usability, completeness, best_practices)

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "ToolQualityEvaluator",
          "arguments": {
              "tool_config": "example_value",
              "test_cases": "example_value",
              "evaluation_aspects": ["item1", "item2"]
          }
      }
      result = tu.run(query)


**ToolRelationshipDetector** (Type: AgenticTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Analyzes a primary tool against a list of other tools to identify meaningful, directional data fl...

.. dropdown:: ToolRelationshipDetector tool specification

   **Tool Information:**

   * **Name**: ``ToolRelationshipDetector``
   * **Type**: ``AgenticTool``
   * **Description**: Analyzes a primary tool against a list of other tools to identify meaningful, directional data flow compatibilities for scientific workflows. Returns a list of compatible pairs with direction and rationale.

   **Parameters:**

   * ``tool_a`` (string) (required)
     JSON string for the primary tool configuration (Tool A).

   * ``other_tools`` (string) (required)
     JSON string of a list of other tool configurations to compare against Tool A.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "ToolRelationshipDetector",
          "arguments": {
              "tool_a": "example_value",
              "other_tools": "example_value"
          }
      }
      result = tu.run(query)


**WritingPresentationReviewer** (Type: AgenticTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Assesses clarity, organization, grammar, and visual presentation quality.

.. dropdown:: WritingPresentationReviewer tool specification

   **Tool Information:**

   * **Name**: ``WritingPresentationReviewer``
   * **Type**: ``AgenticTool``
   * **Description**: Assesses clarity, organization, grammar, and visual presentation quality.

   **Parameters:**

   * ``manuscript_text`` (string) (required)
     No description

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "WritingPresentationReviewer",
          "arguments": {
              "manuscript_text": "example_value"
          }
      }
      result = tu.run(query)


**call_agentic_human** (Type: AgenticTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Produces a concise, practical answer that emulates how a well-informed human would respond to the...

.. dropdown:: call_agentic_human tool specification

   **Tool Information:**

   * **Name**: ``call_agentic_human``
   * **Type**: ``AgenticTool``
   * **Description**: Produces a concise, practical answer that emulates how a well-informed human would respond to the question.

   **Parameters:**

   * ``question`` (string) (required)
     The user's question to be answered in a human-like manner.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "call_agentic_human",
          "arguments": {
              "question": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
