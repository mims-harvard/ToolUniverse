MCP Bundle
====================================================

What is MCPB?
-------------

The **Model Context Protocol Bundle (MCPB)** packages an MCP server for installation
in a desktop client. ToolUniverse's bundle includes its Python source and dependency
declarations. A client supporting the MCPB 0.4 UV runtime prepares the Python
environment during installation, before starting the server.

Why use MCPB with ToolUniverse?
-------------------------------

Traditionally, running an MCP server like ToolUniverse required setting up a specific Python environment, installing dependencies.

**MCPB solves this by providing:**

*   **Zero Configuration**: No need to manage Python virtual environments or install Node.js manually.
*   **One-Click Installation**: In supported clients like Claude Desktop, you just drop the `.mcpb` file.
*   **Portability**: The client installs dependencies for your platform. Internet access is required during the first installation.

Key Features
------------

*   **Standalone Execution**: The bundle acts as a self-contained server.
*   **Seamless Integration**: Designed specifically for **Claude Desktop** and other MCPB-aware clients.
*   **Access to Scientific Tools**: Immediately unlocks 1000+ scientific tools for your AI assistant without command-line setup.

Getting Started
---------------

To use the ToolUniverse MCPB:

1.  Download the latest release from our `GitHub Releases <https://github.com/mims-harvard/ToolUniverse/releases/tag/mcpb>`_.
2.  Follow the instructions in the `official Claude Desktop Guide <https://www.anthropic.com/engineering/desktop-extensions>`_ to configure it with your client.
3.  Wait for dependency installation to finish. In **Settings → Developer**,
    confirm that the extension-managed **ToolUniverse** server is running.
4.  In a chat, open **+ → Connectors** and enable **ToolUniverse**. A running
    server can still be disabled for an individual chat. Allow the requested
    tool call when Claude asks for permission.

To verify a real tool call, ask Claude to use ``execute_tool`` with
``tool_name="Sequence_gc_content"`` and
``arguments={"sequence": "ATGC", "operation": "gc_content"}``.
The tool should return ``gc_percent: 50.0`` and ``length: 4``.

Client compatibility note
-------------------------

MCPB support depends on the client. Use a current Claude Desktop version with
MCPB 0.4 UV runtime support. The first installation can take several minutes
while dependencies download; later starts reuse the prepared environment.
For Claude Desktop, use the MCPB release
flow above. For Claude Code, add ToolUniverse directly as a stdio MCP server
instead of installing the MCPB bundle:

.. code-block:: bash

   claude mcp add --transport stdio tooluniverse -- tooluniverse

This keeps Claude Code on the regular ToolUniverse command path while MCPB
clients can continue using the bundled release.

For advanced users who wish to build the bundle from source or understand the protocol details, please refer to the :doc:`MCP Support <mcp_support>` documentation.
