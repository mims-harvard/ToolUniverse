Comprehensive FAQ
=================

This page contains detailed answers to frequently asked questions about ToolUniverse.

.. tip::
   **Need a quick answer?**
   
   For brief answers to the most common questions, see :doc:`../faq`. This page provides comprehensive information with detailed explanations, troubleshooting tips, and advanced topics.

General Questions
-----------------

What is ToolUniverse?
~~~~~~~~~~~~~~~~~~~~~

ToolUniverse is a comprehensive collection of scientific tools for Agentic AI, offering integration with various scientific databases and services. It provides a unified interface to access data from FDA, OpenTargets, ChEMBL, PubTator, and many other sources.

.. tabs::

   .. tab:: Python SDK

      Use ToolUniverse as a Python library:

      .. code-block:: python

         from tooluniverse import ToolUniverse
         tu = ToolUniverse()
         tu.load_tools()

   .. tab:: MCP Server

      Use ToolUniverse with AI assistants via MCP:

      .. code-block:: bash

         tooluniverse-smcp

   .. tab:: Command Line

      Direct tool execution:

      .. code-block:: bash

         tooluniverse-cli run FAERS_count_reactions_by_drug_event

What databases are supported?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

ToolUniverse integrates with 20+ scientific databases:

- **Drug Information**: FDA FAERS, ChEMBL, PubChem, DrugBank
- **Gene/Protein Data**: UniProt, Ensembl, Human Protein Atlas
- **Disease Information**: OpenTargets, DisGeNET, OMIM
- **Literature**: PubMed, PubTator
- **Clinical Data**: ClinicalTrials.gov, UK Biobank
- **Pathway Analysis**: Enrichr, KEGG, Reactome

Installation & Setup
--------------------

How do I install ToolUniverse?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. tabs::

   .. tab:: Basic Installation

      .. code-block:: bash

         pip install tooluniverse

   .. tab:: Development Installation

      .. code-block:: bash

         git clone https://github.com/mims-harvard/ToolUniverse
         cd tooluniverse
         pip install -e .

   .. tab:: With Optional Dependencies

      .. code-block:: bash

         pip install tooluniverse[all]

Do I need API keys?
~~~~~~~~~~~~~~~~~~~

Most tools work without API keys! However, some tools require authentication or provide higher rate limits with API keys.

**Quick answer:**

- **No API keys needed** for most tools (PubMed, UniProt, ChEMBL, OpenTargets, etc.)
- **Recommended for better performance**: NCBI, FDA (3-10x faster rate limits)
- **Required for specific features**: NVIDIA NIM (structure prediction), USPTO (patents), DisGeNET, OMIM

**For complete details**, see :doc:`../guide/api_keys` which covers all API keys, how to obtain them, rate limits, and configuration methods.

Common Issues
-------------

Why am I getting rate limit errors?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Many scientific APIs have rate limits. ToolUniverse implements automatic rate limiting, but you may still encounter limits:

.. tabs::

   .. tab:: Solution 1: API Keys

      Register for API keys to get higher rate limits:

      .. code-block:: python

         # Higher limits with API key
         os.environ['NCBI_API_KEY'] = 'your_key'

   .. tab:: Solution 2: Batch Requests

      Use batch processing for multiple queries:

      .. code-block:: python

         # Process in batches
         for batch in batches(gene_list, batch_size=10):
             results = tu.run(batch, use_cache=True, max_workers=8)
             time.sleep(1)  # Add delay between batches

   .. tab:: Solution 3: Caching

      Enable caching to avoid repeated requests:

      .. code-block:: python

         # Caching is enabled by default
         tu = ToolUniverse()
         result = tu.run(..., use_cache=True)
Tool returns empty results?
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Check these common issues:**

1. **Correct identifiers**: Ensure you're using the right ID format
2. **API connectivity**: Test your internet connection
3. **Service status**: Check if the external service is available
4. **Query parameters**: Verify your search parameters are valid

.. code-block:: python

   # Example: Retrieve UniProt function by accession
   query = {
       "name": "UniProt_get_function_by_accession",
       "arguments": {"accession": "P38398"}  # BRCA1 accession
   }

MCP Integration
---------------

How do I use ToolUniverse with Claude?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. **Start MCP Server:**

   .. code-block:: bash

      tooluniverse-smcp

2. **Configure Claude Desktop:**

   Add to your Claude configuration:

   .. code-block:: json

      {
        "mcpServers": {
          "tooluniverse": {
            "command": "tooluniverse-smcp-stdio",
            "args": ["--compact-mode"]
          }
        }
      }

3. **Test the connection:**

   Ask Claude: "What tools are available from ToolUniverse?"

Can I use multiple MCP servers?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Yes! You can run multiple ToolUniverse instances or combine with other MCP servers:

.. code-block:: json

   {
     "mcpServers": {
       "tooluniverse-main": {
         "command": "tooluniverse-smcp",
         "args": ["--port", "3000", "--compact-mode"]
       },
       "tooluniverse-dev": {
         "command": "tooluniverse-smcp",
         "args": ["--port", "3001", "--compact-mode", "--load", "community/dev-tools"]
       }
     }
   }

Development
-----------

How do I add a new tool?
~~~~~~~~~~~~~~~~~~~~~~~~

1. **Create tool class:**

   .. code-block:: python

      from tooluniverse.base_tool import BaseTool

      class MyNewTool(BaseTool):
          def __init__(self):
              super().__init__(
                  name="my_new_tool",
                  description="Description of what it does"
              )

          def run(self, **kwargs):
              # Implementation here
              return results

2. **Register the tool:**

   .. code-block:: python

      from tooluniverse import ToolRegistry

      registry = ToolRegistry()
      registry.register_tool(MyNewTool)

3. **Add tests:**

   .. code-block:: python

      def test_my_new_tool():
          tool = MyNewTool()
          result = tool.run(test_parameter="test_value")
          assert result is not None

How do I contribute?
~~~~~~~~~~~~~~~~~~~~

1. Fork the repository
2. Create a feature branch
3. Add your changes with tests
4. Submit a pull request

See our :doc:`about/contributing` Tutorial for detailed instructions.

Performance
-----------

How can I speed up queries?
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. tabs::

   .. tab:: Enable Caching

      .. code-block:: python

         import os
         os.environ["TOOLUNIVERSE_CACHE_DEFAULT_TTL"] = "3600"  # 1 hour
         tu = ToolUniverse()
         result = tu.run(..., use_cache=True)

   .. tab:: Batch Processing

      .. code-block:: python

         # Process multiple queries at once
         queries = [
             {"name": "tool1", "arguments": {"id": "1"}},
             {"name": "tool1", "arguments": {"id": "2"}},
         ]
         results = tu.run(queries, max_workers=4)

   .. tab:: Async Operations

      .. code-block:: python

         import asyncio

         async def main():
             results = await tu.run(query)  # run() is context-aware

         asyncio.run(main())

Why is the first query slow?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The first query often takes longer because:

1. **Tool loading**: Tools are loaded on first use
2. **API connection**: Initial connection setup
3. **Authentication**: API key validation

Subsequent queries will be much faster.

Troubleshooting
---------------

Getting import errors?
~~~~~~~~~~~~~~~~~~~~~~

**Common solutions:**

.. tabs::

   .. tab:: Missing Dependencies

      .. code-block:: bash

         pip install tooluniverse[all]

   .. tab:: Python Version

      Ensure Python 3.8+ is installed:

      .. code-block:: bash

         python --version

   .. tab:: Virtual Environment

      Use a clean virtual environment:

      .. code-block:: bash

         python -m venv venv
         source venv/bin/activate  # Linux/Mac
         # or
         venv\Scripts\activate  # Windows
         pip install tooluniverse

Network connectivity issues?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. **Check internet connection**
2. **Verify proxy settings** if behind corporate firewall
3. **Test specific endpoints:**

   .. code-block:: python

      import requests
      response = requests.get('https://platform-api.opentargets.org/api/v4/graphql')
      print(response.status_code)

4. **Configure timeouts:**

   .. code-block:: python

      tu = ToolUniverse()  # timeout is set per HTTP request, not at the ToolUniverse level

Still Having Issues?
--------------------

If you can't find the answer here:

1. **Check the documentation**: :doc:`../guide/index`
2. **Search existing issues**: `GitHub Issues <https://github.com/mims-harvard/ToolUniverse/issues>`_
3. **Ask the community**: Join our Discord server
4. **Report a bug**: Create a new GitHub issue with details

.. note::
   When reporting issues, please include:

   - ToolUniverse version
   - Python version
   - Operating system
   - Full error message
   - Minimal code example
