MCP Integration
===============

Learn how to integrate MCP (Model Context Protocol) servers with ToolUniverse using configuration-based loading. This approach automatically discovers and loads remote tools without manual setup.

What is MCP?
------------

MCP is a standardized protocol for tool communication that allows:
- **Standardized Interface**: Consistent tool discovery and execution
- **Language Agnostic**: Servers can be written in any language
- **Scalable**: Support for multiple tools on one server
- **Secure**: Built-in authentication and error handling

Configuration-Based Loading
----------------------------

Instead of programmatic loading, use configuration files for automatic tool discovery:

**Create `mcp_tools_config.json`:**

.. code-block:: json

   [
       {
           "name": "mcp_auto_loader_my_tools",
           "description": "Automatically load tools from My Remote Server",
           "type": "MCPAutoLoaderTool",
           "tool_prefix": "remote_",
           "server_url": "http://localhost:8001/mcp",
           "required_api_keys": []
       }
   ]

**Load in ToolUniverse:**

.. code-block:: python

   from tooluniverse import ToolUniverse

   tu = ToolUniverse()
   tu.load_tools(tool_config_files={"mcp_tools": "mcp_tools_config.json"})

   # Use remote tools
   result = tu.run({
       "name": "remote_my_remote_tool",
       "arguments": {"input": "test data"}
   })
   print(result)

Configuration Options
---------------------

**MCPAutoLoaderTool Parameters:**

- ``name``: Unique name for the loader tool (required)
- ``description``: Description of what tools this loader provides
- ``type``: Must be "MCPAutoLoaderTool" (required)
- ``tool_prefix``: Prefix for loaded tool names (optional)
- ``server_url``: URL of your MCP server (required)
- ``required_api_keys``: Environment variables needed (optional)

**Environment Variables:**

Use environment variables for dynamic configuration:

.. code-block:: json

   [
       {
           "name": "mcp_auto_loader_expert_feedback",
           "description": "Load expert feedback tools",
           "type": "MCPAutoLoaderTool",
           "tool_prefix": "expert_",
           "server_url": "http://${EXPERT_FEEDBACK_MCP_SERVER_URL}/mcp",
           "required_api_keys": ["EXPERT_FEEDBACK_MCP_SERVER_URL"]
       }
   ]

**Multiple Servers:**

Load tools from multiple MCP servers:

.. code-block:: json

   [
       {
           "name": "mcp_auto_loader_server1",
           "description": "Load tools from Server 1",
           "type": "MCPAutoLoaderTool",
           "tool_prefix": "s1_",
           "server_url": "http://server1:8000/mcp",
           "required_api_keys": []
       },
       {
           "name": "mcp_auto_loader_server2",
           "description": "Load tools from Server 2", 
           "type": "MCPAutoLoaderTool",
           "tool_prefix": "s2_",
           "server_url": "http://server2:8000/mcp",
           "required_api_keys": []
       }
   ]

Troubleshooting
---------------

**Common Issues:**

**Connection refused**
- Check if MCP server is running: `python your_tool_file.py`
- Verify the server URL in configuration
- Check firewall settings

**Tool not found**
- Verify tool names (check if prefix is correct)
- Check MCP server logs
- Ensure tool is properly registered with `@register_mcp_tool`

**Configuration errors**
- Validate JSON configuration syntax
- Check required API keys are set
- Verify server URLs are accessible

**Environment variable issues**
- Ensure all required API keys are set
- Check variable names match exactly
- Verify environment is loaded before ToolUniverse initialization

Next Steps
----------

* **Contributing**: :doc:`../contributing/remote_tools` - Submit your MCP server to ToolUniverse
* **Tutorial**: :doc:`tutorial` - Learn about remote tool integration
* **Architecture**: :doc:`../reference/architecture` - Understand ToolUniverse internals

.. tip::
   **Integration tip**: Start with simple MCP servers and gradually add complexity. Always test your integration thoroughly!