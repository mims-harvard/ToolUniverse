Glossary
========

Technical terms and concepts used throughout ToolUniverse documentation.

.. glossary::

   AI Scientist
      An AI system (LLM, agent, or reasoning model) enhanced with ToolUniverse capabilities to autonomously perform scientific research tasks including literature search, data analysis, and experimental design.

   AI-Tool Interaction Protocol
      Standardized interface governing how AI scientists issue tool requests and receive structured results. Ensures compatibility across different LLM providers and tool implementations.

   Agentic Tool
      A tool that uses LLM capabilities internally to perform complex tasks like summarization, extraction, or intelligent search. Examples: Tool_Finder_LLM, summarization hooks.

   ChEMBL
      European Molecular Biology Laboratory's database of bioactive drug-like small molecules. ChEMBL IDs are identifiers like "CHEMBL25" for aspirin.

   ChEMBL ID
      Unique identifier for chemical compounds in the ChEMBL database (e.g., CHEMBL25 for aspirin).

   Compact Mode
      Context window optimization mode that exposes only 4-5 core discovery tools instead of 1000+ tools. Reduces context usage by 99% while maintaining full functionality through the ``execute_tool`` tool.

   EFO
   EFO ID
      Experimental Factor Ontology - A standardized disease classification system used in biomedical research. EFO IDs are identifiers like "EFO_0000537" for hypertension.

   Embedding
   Embedding Search
      Vector-based semantic search where text is converted to numerical vectors. Similar concepts have similar vectors, enabling "meaning-based" search beyond keyword matching. Used in Tool_Finder for intelligent tool discovery.

   Hook
      Output processing function that transforms or enhances tool results. Examples: SummarizationHook (AI-powered summaries), FileSaveHook (automatic file saving).

   MCP
   Model Context Protocol
      Open standard protocol enabling AI assistants to securely connect to external tools and data sources. Think of it as "USB for AI tools" - a standardized connection interface.

   SMCP
   Scientific Model Context Protocol
      ToolUniverse's implementation of MCP, optimized for scientific workflows. Extends standard MCP with scientific domain features, intelligent tool discovery, and hooks system.

   Space
   Toolspace
      Pre-configured collection of tools for specific research domains (e.g., "proteomics-toolkit", "drug-discovery"). Spaces can be loaded from GitHub, local files, or URLs using ``--load`` parameter.

   STDIO Transport
      Communication method where data flows through standard input/output streams. Used by desktop applications like Claude Desktop to communicate with MCP servers.

   Tool Composition
      Chaining multiple tools together in sequential or parallel workflows. Example: Search PubMed → Extract abstracts → Summarize findings.

   Tool Finder
      Family of specialized search tools for discovering relevant ToolUniverse tools:
      
      - **Tool_Finder_Keyword**: Fast keyword search
      - **Tool_Finder_LLM**: Natural language search using LLM
      - **Tool_Finder**: Semantic embedding search (most powerful)

   Tool Specification
      JSON definition describing a tool's purpose, input parameters, output format, and execution details. Think of it as the "instruction manual" for each tool.

   ToolSpace
      See :term:`Space`.

   PubChem CID
      PubChem Compound Identifier - unique numerical ID for chemical compounds in PubChem database (e.g., CID 2244 for aspirin).

   UniProt Accession
      Unique identifier for protein sequences in UniProt database. Format: 1-6 characters (e.g., "P05067" for amyloid precursor protein).

   FAERS
      FDA Adverse Event Reporting System - Database of adverse drug reactions reported to FDA. Used for pharmacovigilance and drug safety monitoring.

   SSE
      Server-Sent Events - HTTP-based protocol for servers to push updates to clients. One of the transport methods supported by ToolUniverse MCP servers.

   TTL
      Time To Live - Duration (in seconds) that cached results remain valid before expiration. Set via ``TOOLUNIVERSE_CACHE_DEFAULT_TTL``.

   LRU Cache
      Least Recently Used cache - Memory cache that evicts oldest unused entries when full. ToolUniverse uses LRU for in-memory caching.

   Rate Limit
      Maximum number of API requests allowed per time period. Example: NCBI allows 3 requests/second without API key, 10 requests/second with key.

   Tool Category
   Tool Type
      Classification of tools by data source or functionality. Examples: ``uniprot``, ``chembl``, ``pubmed``, ``fda``, ``nvidia_nim``. Used for selective tool loading.

   Fingerprint
   Cache Fingerprint
      Unique hash computed from tool's source code and parameter schema. When tool implementation changes, fingerprint changes, invalidating old cache entries.

   Workspace Configuration
      YAML or JSON file defining tool selection, hooks, and settings for a specific research workflow or domain. See :term:`Space`.

   JSON-RPC
      Remote Procedure Call protocol using JSON for data encoding. Some MCP servers use JSON-RPC for communication.

   OpenTargets
      Open Targets Platform - Database connecting genes to diseases with evidence scores. Provides target-disease associations for drug discovery.

   AlphaFold
   AlphaFold2
      AI system for predicting 3D protein structures from amino acid sequences. Accessible through ToolUniverse via NVIDIA NIM tools.

   NCBI
      National Center for Biotechnology Information - US government agency providing biomedical databases including PubMed, GenBank, and protein databases.

   Ontology
      Structured vocabulary defining terms and relationships in a domain. Examples: EFO (diseases), Gene Ontology (biological processes), ChEBI (chemicals).

   API Endpoint
      URL path for making API requests to web services. Example: ``/api/search`` or ``https://rest.uniprot.org/uniprotkb/search``.

See Also
--------

- :doc:`reference/cli_tools` - Command-line tools
- :doc:`reference/environment_variables` - Configuration variables
- :doc:`../guide/api_keys` - API key configuration
- :doc:`guide/interaction_protocol` - AI-Tool Interaction Protocol details
