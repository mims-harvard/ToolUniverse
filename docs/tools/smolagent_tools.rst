Smolagent Tools
===============

**Configuration File**: ``smolagent_tools.json``
**Tool Type**: Local
**Tools Count**: 2

This page contains all tools defined in the ``smolagent_tools.json`` configuration file.

Available Tools
---------------

**advanced_literature_search_agent** (Type: SmolAgentTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Advanced multi-agent deep literature search system. This is a SEARCH-FIRST system: agents must ex...

.. dropdown:: advanced_literature_search_agent tool specification

   **Tool Information:**

   * **Name**: ``advanced_literature_search_agent``
   * **Type**: ``SmolAgentTool``
   * **Description**: Advanced multi-agent deep literature search system. This is a SEARCH-FIRST system: agents must extensively use ToolUniverse literature search tools to gather information, NOT rely on their own knowledge. Required pipeline: (1) query_planner analyzes the query to identify key search aspects and generates 3-8 focused search queries; (2) FIRST call web_foundation_searcher (base web tools only) to produce seeds/sources/keywords; (3) For EACH seed query, parallel call ALL THREE specialized searchers: medical_literature_searcher (PubMed, EuropePMC, PMC, MedRxiv, BioRxiv), computer_science_searcher (ArXiv, DBLP, SemanticScholar), and general_literature_searcher (openalex, Crossref, DOAJ, CORE) using concurrent.futures.ThreadPoolExecutor; (4) result_analyzer deduplicates and scores results from all searchers; (5) literature_synthesizer generates the final report strictly from searched results. CRITICAL: All information must come from tool searches, not pre-existing knowledge.

   **Parameters:**

   * ``query`` (string) (required)
     Research query or topic to search in academic literature. The agent will automatically determine search strategy, database selection, filters, and result limits based on the query content and research domain.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "advanced_literature_search_agent",
          "arguments": {
              "query": "example_value"
          }
      }
      result = tu.run(query)


**open_deep_research_agent** (Type: SmolAgentTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Research manager agent that decomposes the user task, delegates focused subtasks to domain sub‑ag...

.. dropdown:: open_deep_research_agent tool specification

   **Tool Information:**

   * **Name**: ``open_deep_research_agent``
   * **Type**: ``SmolAgentTool``
   * **Description**: Research manager agent that decomposes the user task, delegates focused subtasks to domain sub‑agents (web researcher, synthesizer), enforces evidence use, requires numeric outputs with units, and returns a concise final answer with citations. It should: (1) draft a brief plan, (2) ask web_researcher to gather authoritative facts (URLs + extracted numbers), (3) validate consistency across sources, (4) instruct synthesizer to compute/compose the final result, and (5) output only the final, unit‑aware answer plus one short rationale line.

   **Parameters:**

   * ``task`` (string) (required)
     Research query/task to execute

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "open_deep_research_agent",
          "arguments": {
              "task": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
