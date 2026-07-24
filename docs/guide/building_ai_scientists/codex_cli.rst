Codex CLI
=========

- Install: ``npm install -g @openai/codex``
- `Official MCP setup guide <https://developers.openai.com/codex/mcp/>`_

Codex supports MCP servers through shared CLI and IDE configuration. You can
either ask Codex to perform the setup or add the ToolUniverse server yourself.

To set up ToolUniverse, open Codex CLI and run:

.. code-block:: text

   Read https://aiscientist.tools/setup.md and set up ToolUniverse for me.

Manual MCP setup
----------------

Add ToolUniverse as a stdio MCP server with the Codex CLI:

.. code-block:: bash

   codex mcp add tooluniverse --env PYTHONIOENCODING=utf-8 -- uvx --refresh tooluniverse

Then open Codex and run ``/mcp`` to confirm that the ``tooluniverse`` server is
listed.

You can also edit Codex configuration directly. Codex stores MCP configuration
in ``~/.codex/config.toml`` by default, and trusted projects may use a
project-scoped ``.codex/config.toml``.

.. code-block:: toml

   [mcp_servers.tooluniverse]
   command = "uvx"
   args = ["--refresh", "tooluniverse"]

   [mcp_servers.tooluniverse.env]
   PYTHONIOENCODING = "utf-8"

Validation
----------

Before relying on the MCP server from Codex, verify that ``uvx`` can start
ToolUniverse:

.. code-block:: bash

   uvx --refresh tooluniverse --help

If Codex cannot find ``uvx``, use the absolute path to ``uvx`` as the
``command`` value in ``config.toml``. On Windows, run ``where uvx`` to find the
path; on macOS or Linux, run ``which uvx``.
