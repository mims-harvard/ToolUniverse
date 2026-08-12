USPTO Downloader Tools
======================

**Configuration File**: ``uspto_downloader_tools.json``
**Tool Type**: MCP Auto Loader
**Tools Count**: 1 loader

This configuration connects ToolUniverse to the separately deployed USPTO
downloader MCP service. The loader discovers the service's abstract, claims,
and full-text tools at startup; it does not run the GPU OCR service locally.

Available Tools
---------------

**mcp_auto_loader_uspto_downloader** (Type: MCPAutoLoaderTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Connects to ``USPTO_MCP_SERVER_HOST`` and discovers the following remote tools:

* ``get_abstract_from_patent_app_number``
* ``get_claims_from_patent_app_number``
* ``get_full_text_from_patent_app_number``

Set ``USPTO_MCP_SERVER_HOST`` to the service host (for example,
``uspto-mcp.internal``). If the service enables Bearer authentication, set
the same ``TOOLUNIVERSE_API_TOKEN`` value in the client environment.

See :doc:`remote/uspto_downloader` for deployment and usage instructions.

Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`remote_tools` - Remote Tools Setup
