===============================
Tool Finder Tutorial
===============================

**Complete Tutorial to using ToolUniverse's three built-in tool discovery methods**

Introduction
============

ToolUniverse contains a vast repository of over 1000+ scientific tools. To help you quickly find the right tools for your research tasks, ToolUniverse provides three sophisticated tool finder methods, each optimized for different use cases and computational requirements.

Why Use Tool Finders?
---------------------

**The Challenge**: With hundreds of available tools across domains like bioinformatics, chemistry, literature search, and data analysis, manually browsing through tool lists is time-consuming and inefficient.

**The Solution**: ToolUniverse's tool finders allow you to describe your research task in natural language and automatically discover the most relevant tools.

**Three Approaches**:
- **Keyword Search**: Fast, precise, resource-efficient
- **LLM Search**: Intelligent, context-aware, handles complex queries
- **Embedding Search**: Semantic understanding, scalable, similarity-based

Overview of Tool Finder Methods
===============================

Strategic Trade-offs
--------------------

Each method offers different advantages:

.. list-table:: Tool Finder Comparison
   :header-rows: 1
   :widths: 20 25 25 25

   * - Method
     - Speed
     - Semantic Understanding
     - Resource Usage
   * - **Keyword Search**
     - Very Fast
     - Basic
     - Very Low
   * - **LLM Search**
     - Moderate
     - Excellent
     - High
   * - **Embedding Search**
     - Fast
     - Good
     - Moderate

When to Use Each Method
------------------------

**🔍 Keyword Search** - Use when:
- You know specific technical terms
- You need fast results
- Working with limited computational resources
- Looking for tools with specific names or exact terminology

**🧠 LLM Search** - Use when:
- You have complex, multi-step research questions
- Need intelligent interpretation of abstract goals
- Want tool sequence recommendations
- Have access to LLM APIs

**🎯 Embedding Search** - Use when:
- You want semantic similarity matching
- Need scalable search across large tool sets
- Looking for conceptually similar tools
- Want to find tools based on research intent rather than exact keywords

Method 1: Keyword Search
========================

How Keyword Search Works
------------------------

Keyword search uses a sophisticated text processing pipeline:

1. **Query Processing**:
   - Tokenization via regular expressions
   - Removal of 45+ common English stop words
   - Suffix-based stemming using 20 morphological rules
   - Generation of n-grams (bigrams and trigrams)

2. **Relevance Scoring**:

   - Uses TF-IDF (Term Frequency-Inverse Document Frequency)
   - Formula: ``Relevance = TF × IDF × log(1 + QueryFrequency)``
   - Hierarchical bonus structure:

     - Tool name matches: 2.0× multiplier
     - Exact phrase matches: 1.5× multiplier

3. **Fast Matching**: Pre-built index ensures rapid search without ML dependencies

Using Keyword Search
---------------------

Basic Usage
~~~~~~~~~~~

.. code-block:: python

   from tooluniverse import ToolUniverse

   # Initialize ToolUniverse
   tu = ToolUniverse()
   # Load tool finder tools
   tu.load_tools()
   # if you want to load a subset of tools, `tool_finder` must be included in the list of tool types
   # tu.load_tools(tool_type=["tool_finder", ...other tool types...])

   # Use keyword search
   result = tu.run({
       "name": "Tool_Finder_Keyword",
       "arguments": {
           "description": "protein structure prediction",
           "limit": 10
       }
   })
   print(result)

Advanced Usage with Filters
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from tooluniverse import ToolUniverse

   # Initialize ToolUniverse
   tu = ToolUniverse()
   # Load tool finder tools
   tu.load_tools()

   # Search with category filtering
   result = tu.run({
       "name": "Tool_Finder_Keyword",
       "arguments": {
           "description": "drug discovery molecular similarity",
           "limit": 5,
           "categories": ["ChEMBL", "pubchem"]  # Optional: filter by categories
       }
   })

Keyword Search Best Practices
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Effective Queries**:
- Use specific scientific terminology: "CRISPR gene editing", "molecular docking", "phylogenetic analysis"
- Include domain-specific keywords: "protein", "drug", "genomic", "clinical"
- Use technical abbreviations: "PCR", "BLAST", "PDB"

Method 2: LLM Search
====================

How LLM Search Works
--------------------

LLM search leverages Large Language Models for intelligent tool discovery:

1. **Context Construction**: Creates detailed prompts combining user queries with tool specifications
2. **Intelligent Reasoning**: LLM analyzes context to infer optimal tools or tool sequences
3. **Complex Query Handling**: Excels at multi-step, abstract, or complex research questions
4. **Agentic Implementation**: Uses ToolUniverse's agentic tool framework

Using LLM Search
-----------------

Basic Usage
~~~~~~~~~~~

.. code-block:: python

   from tooluniverse import ToolUniverse

   # Initialize ToolUniverse
   tu = ToolUniverse()
   # Load tool finder tools
   tu.load_tools()

   # Set up environment variables first
   import os
   os.environ["AZURE_OPENAI_API_KEY"] = "your-api-key"
   os.environ["AZURE_OPENAI_ENDPOINT"] = "https://your-endpoint.openai.azure.com"

   # Use LLM search
   result = tu.run({
       "name": "Tool_Finder_LLM",
       "arguments": {
           "description": "I want to analyze the safety profile of a drug by looking at adverse events and clinical trial data",
           "limit": 8
       }
   })
   print(result)

Complex Multi-Step Queries
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from tooluniverse import ToolUniverse

   # Initialize ToolUniverse
   tu = ToolUniverse()
   # Load tool finder tools
   tu.load_tools()

   # Complex research workflow query
   complex_query = """
   I'm researching potential drug targets for Alzheimer's disease.
   I need to:
   1. Find proteins associated with Alzheimer's
   2. Identify existing drugs that target these proteins
   3. Search for recent literature on these drug-target interactions
   4. Check for any adverse events reported for these drugs
   """

   result = tu.run({
       "name": "Tool_Finder_LLM",
       "arguments": {
           "description": complex_query,
           "limit": 12
       }
   })

   print(result)

Abstract Goal Interpretation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from tooluniverse import ToolUniverse

   # Initialize ToolUniverse
   tu = ToolUniverse()
   # Load tool finder tools
   tu.load_tools()

   # Abstract research goals
   abstract_queries = [
       "I want to understand the molecular basis of cancer drug resistance",
       "Help me find computational tools for personalized medicine research",
       "I'm looking for ways to predict drug-drug interactions",
       "Find tools for analyzing genetic variants in rare diseases"
   ]

   for query in abstract_queries:
       result = tu.run({
           "name": "Tool_Finder_LLM",
           "arguments": {
               "description": query,
               "limit": 6
           }
       })

       print(f"\n🎯 Query: {query}")
       print(f"Result: {result}")

LLM Search Best Practices
~~~~~~~~~~~~~~~~~~~~~~~~~

**Effective Strategies**:
- Describe your research context and goals clearly
- Mention specific diseases, molecules, or research areas
- Include workflow steps if you have a multi-step process
- Ask for reasoning to understand why tools were recommended

Method 3: Embedding Search
==========================

How Embedding Search Works
--------------------------

Embedding search uses semantic similarity for tool discovery:

1. **Model Training**: Fine-tuned embedding model on synthetic query-tool pairs
2. **Offline Indexing**: Tool specifications converted to semantic vectors and stored in vector database
3. **Online Querying**: User queries converted to vectors and matched via cosine similarity
4. **Semantic Understanding**: Captures conceptual relationships beyond keyword matching

Using Embedding Search
-----------------------

Basic Usage
~~~~~~~~~~~

.. code-block:: python

   from tooluniverse import ToolUniverse

   # Initialize ToolUniverse
   tu = ToolUniverse()
   # Load tool finder tools
   tu.load_tools()

   # Use embedding search
   result = tu.run({
       "name": "Tool_Finder",
       "arguments": {
           "description": "analyze protein interactions",
           "limit": 10
       }
   })

   print(result)

Semantic Similarity Examples
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from tooluniverse import ToolUniverse

   # Initialize ToolUniverse
   tu = ToolUniverse()
   # Load tool finder tools
   tu.load_tools()

   # Embedding search excels at conceptual matching
   semantic_queries = [
       # These queries will find conceptually related tools
       # even if exact keywords don't match
       "molecular interactions",           # Finds protein, drug, gene interaction tools
       "therapeutic compounds",            # Finds drug, chemical, pharmaceutical tools
       "genetic variations",               # Finds mutation, SNP, variant analysis tools
       "disease mechanisms",               # Finds pathway, target, biomarker tools
       "clinical outcomes"                 # Finds trial, efficacy, safety tools
   ]

   for query in semantic_queries:
       result = tu.run({
           "name": "Tool_Finder",
           "arguments": {
               "description": query,
               "limit": 5
           }
       })

       print(f"\n🔍 Semantic search for: '{query}'")
       print(f"Result: {result}")

Advanced Embedding Search
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from tooluniverse import ToolUniverse

   # Initialize ToolUniverse
   tu = ToolUniverse()
   # Load tool finder tools
   tu.load_tools()

   # Fine-tune search parameters
   result = tu.run({
       "name": "Tool_Finder",
       "arguments": {
           "description": "computational drug design",
           "limit": 15,
           "categories": ["ChEMBL", "pubchem", "opentarget"]  # Filter categories
       }
   })
   print(result)

Comparing Search Methods
========================

Practical Comparison
---------------------

Let's compare all three methods on the same query:

.. code-block:: python

   from tooluniverse import ToolUniverse

   # Initialize ToolUniverse
   tu = ToolUniverse()
   # Load tool finder tools
   tu.load_tools()

   query = "find drugs for treating diabetes"

   # Method 1: Keyword Search
   keyword_result = tu.run({
       "name": "Tool_Finder_Keyword",
       "arguments": {"description": query, "limit": 5}
   })

   # Method 2: LLM Search
   llm_result = tu.run({
       "name": "Tool_Finder_LLM",
       "arguments": {"description": query, "limit": 5}
   })

   # Method 3: Embedding Search
   embedding_result = tu.run({
       "name": "Tool_Finder",
       "arguments": {"description": query, "limit": 5}
   })

   # Compare results
   print("🔍 KEYWORD SEARCH RESULTS:")
   print(keyword_result)

   print("\n🧠 LLM SEARCH RESULTS:")
   print(llm_result)

   print("\n🎯 EMBEDDING SEARCH RESULTS:")
   print(embedding_result)

Performance Analysis
---------------------

Measure and compare performance:

.. code-block:: python

   from tooluniverse import ToolUniverse

   # Initialize ToolUniverse
   tu = ToolUniverse()
   # Load tool finder tools
   tu.load_tools()
   import time

   test_queries = [
       "protein structure analysis",
       "drug adverse events",
       "gene expression profiling",
       "molecular similarity search"
   ]

   def benchmark_search_method(method_name, queries):
       times = []
       total_results = 0

       for query in queries:
           start_time = time.time()
           result = tu.run({
               "name": method_name,
               "arguments": {"description": query, "limit": 5}
           })
           end_time = time.time()

           times.append(end_time - start_time)
           total_results += len(result)

       avg_time = sum(times) / len(times)
       return avg_time, total_results

   # Benchmark all methods
   methods = [
       "Tool_Finder_Keyword",
       "Tool_Finder_LLM",
       "Tool_Finder"
   ]

   for method in methods:
       avg_time, total_results = benchmark_search_method(method, test_queries)
       print(f"{method}:")
       print(f"  Average time: {avg_time:.3f}s")
       print(f"  Total results: {total_results}")

Troubleshooting
===============

Common Issues and Solutions
----------------------------

**Issue**: LLM search fails

.. code-block:: python

   # Check API configuration
   import os

   required_env_vars = [
       "AZURE_OPENAI_API_KEY",
       "AZURE_OPENAI_ENDPOINT"
   ]

   for var in required_env_vars:
       if not os.getenv(var):
           print(f"❌ Missing environment variable: {var}")
       else:
           print(f"✅ {var} is set")


Conclusion
==========

ToolUniverse's three tool finder methods provide powerful and flexible approaches to discovering the right tools for your research:

**🔍 Keyword Search**: Perfect for precise, fast searches with technical terminology

**🧠 LLM Search**: Ideal for complex, multi-step research workflows requiring intelligence

**🎯 Embedding Search**: Excellent for semantic similarity and conceptual tool discovery

**Key Takeaways**:

1. **Choose the right method** for your specific use case and computational constraints
2. **Combine methods** for comprehensive tool discovery
3. **Optimize queries** based on the search method's strengths
4. **Use fallback strategies** when initial searches don't yield results

Happy tool hunting! 🔬

Further Resources
=================

**Related Documentation**:
- :doc:`../guide/tools` - Overview of all ToolUniverse tools
- :doc:`../guide/examples` - **Custom Tools**: Create your own tools using :doc:`../expand_tooluniverse/local_tools/local_tools_tutorial` - Creating your own tools

- **API Reference**: Check :doc:`../api/modules` for programmatic access
- **Tool Categories**: Browse tools by category in :doc:`../tools/tools_config_index` - Tool categories and descriptions

**Need Help?**:
- :doc:`../help/troubleshooting` - Common issues and solutions
- :doc:`../help/faq` - Frequently asked questions
