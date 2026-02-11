Claude Desktop
=================================

**Building AI Scientists with Claude Desktop App and ToolUniverse**

Overview
--------

Claude Desktop Integration enables seamless connection between Claude Desktop App and ToolUniverse's scientific tools ecosystem through the Model Context Protocol (MCP). This approach provides a user-friendly interface for scientific research while leveraging Claude's advanced reasoning capabilities and ToolUniverse's comprehensive scientific tools.

Prerequisites
-------------

Before setting up Claude Desktop integration, ensure you have:

- **Claude Desktop App**: `Download and install <https://claude.com/download>`_ Claude Desktop on your system

Installation and Setup
----------------------

Step 1: Locate Claude Desktop Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Open Claude Desktop App and navigate to the configuration:

1. **Open Claude Desktop App**
2. **Go to Settings** → **Developer** → **Edit Config**
3. **Note the configuration file location** (typically in your user directory)

The configuration file will be opened in your default text editor.

Step 2: Configure ToolUniverse MCP Server
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Add the ToolUniverse MCP server configuration to your Claude Desktop config:

.. code-block:: json

   {
     "mcpServers": {
       "tooluniverse": {
         "command": "uvx",
         "args": ["tooluniverse"],
         "env": {"PYTHONIOENCODING": "utf-8"}
       }
     }
   }

Step 3: Install Agent Skills
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Install ToolUniverse agent skills for enhanced research capabilities:

.. code-block:: bash

   npx skills add mims-harvard/ToolUniverse

These skills provide specialized research workflows for drug discovery, target research, disease analysis, and more.

Step 4: Restart Claude Desktop
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

After saving the configuration:

1. **Completely quit Claude Desktop App**
2. **Restart Claude Desktop App**
3. **Verify the MCP server is loaded** (check the developer console if needed)

Step 5: Verify Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~

Test the integration by asking Claude to:

1. **List available tools**:
   - "What scientific tools are available?"
   - "Show me the tools for drug discovery"

2. **Execute a tool**:
   - "Search for information about Alzheimer's disease"
   - "Find protein information for BRCA1"

Example Integration
-------------------

For a practical example of using ToolUniverse-MCP with Claude Desktop, see the following demonstration:

.. image:: /_static/claude_desktop.jpg
   :alt: Claude Desktop Integration Example
   :align: center
   :width: 800px

.. note::
   **Image Source**: This example shows Claude Desktop using ToolUniverse tools for scientific research. To view the full interactive example, visit the `Claude MCP Integration Example <https://claude.ai/share/ab797b7f-6e6b-46f6-b1d5-5a790b90f42d>`_.

Settings and Configuration
--------------------------



