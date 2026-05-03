MCP Bundle
====================================================

What is MCPB?
-------------

The **Model Context Protocol Bundle (MCPB)** is a standardized packaging format designed to simplify the distribution and usage of Model Context Protocol (MCP) servers. For **ToolUniverse**, the MCPB wraps the entire ecosystem—including Python dependencies, the Node.js bridge, and the server logic—into a single, standalone executable or bundle.

Why use MCPB with ToolUniverse?
-------------------------------

Traditionally, running an MCP server like ToolUniverse required setting up a specific Python environment, installing dependencies.

**MCPB solves this by providing:**

*   **Zero Configuration**: No need to manage Python virtual environments or install Node.js manually.
*   **One-Click Installation**: In supported clients like Claude Desktop, you just drop the `.mcpb` file.
*   **Portability**: The bundle contains everything needed to run ToolUniverse on your machine.

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

For advanced users who wish to build the bundle from source or understand the protocol details, please refer to the :doc:`MCP Support <mcp_support>` documentation.
