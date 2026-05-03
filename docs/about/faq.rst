Quick FAQ
=========

Quick answers to the most common questions about ToolUniverse.

.. seealso:: Full FAQ: :doc:`../help/faq`

What is ToolUniverse?
---------------------

ToolUniverse is a collection of 1000+ scientific tools for AI agents, providing unified access to drug safety data, genomics, literature, clinical trials, and more.

.. code-block:: python

   from tooluniverse import ToolUniverse
   tu = ToolUniverse()
   tu.load_tools()

   result = tu.run({
      "name": "UniProt_get_function_by_accession",
      "arguments": {"accession": "P05067"}
   })

How do I install it?
--------------------

.. code-block:: bash

   pip install tooluniverse

Do I need API keys?
-------------------

Most tools work without API keys! However, some tools require authentication or provide higher rate limits with API keys.

**Quick answer:**

- **No API keys needed** for most tools (PubMed, UniProt, ChEMBL, etc.)
- **Recommended for better performance**: NCBI, OpenTargets, FDA (3-10x faster)
- **Required for specific features**: NVIDIA NIM (structure prediction), USPTO (patents), DisGeNET, OMIM

**For complete details**, see :doc:`../guide/api_keys` which covers:

- Which APIs are required vs optional
- How to obtain each API key
- Rate limits with and without keys
- Configuration methods

How do I use it with Claude?
-----------------------------

1. Start the MCP server: ``tooluniverse-smcp``
2. Configure Claude Desktop with the MCP server
3. Ask Claude: "What tools are available from ToolUniverse?"

Need more help?
---------------

- **Troubleshooting**: :doc:`../help/troubleshooting`
- **GitHub Issues**: `Report problems <https://github.com/mims-harvard/ToolUniverse/issues>`_
