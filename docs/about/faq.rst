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

ToolUniverse is a **system**, not just a pip package — a tool registry plus an MCP
server, a ``tu`` CLI, a Python SDK, agent skills, and optional API keys. The simplest
way to set up the whole thing is to let your AI agent do it:

   ``Read https://aiscientist.tools/setup.md and set up ToolUniverse for me.``

That covers ``uv``, the MCP server, API keys, skills, and validation. To install just the
Python SDK access mode, use the **full** package so every tool registers:

.. code-block:: bash

   uv pip install "tooluniverse[all]"   # or:  pip install "tooluniverse[all]"

.. note::

   ``pip install tooluniverse`` (without ``[all]``) installs only the core Python package —
   not the MCP server, skills, or keys that make up the full system — and tools that depend
   on optional scientific packages (ML, cheminformatics, visualization, bioinformatics,
   single-cell) silently fail to register. Use ``[all]`` unless you want a slim install.

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
