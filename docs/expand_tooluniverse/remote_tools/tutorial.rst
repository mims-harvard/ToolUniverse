Remote Tools Tutorial
=====================

Learn how to create and integrate remote tools with ToolUniverse using the `@register_mcp_tool` decorator. Remote tools run on separate servers and are automatically discovered and loaded via configuration files.

What are Remote Tools?
----------------------

Remote tools are Python classes decorated with `@register_mcp_tool` that run on separate servers and are accessed via MCP (Model Context Protocol). They provide:

- **Scalability**: Offload heavy computation to dedicated servers
- **Integration**: Connect with existing systems and services  
- **Flexibility**: Use tools in different programming languages
- **Isolation**: Keep sensitive operations separate
- **Auto-Discovery**: Automatic loading via configuration files

**Best for:**
- External API integrations
- Machine learning models with heavy dependencies
- Cloud-based AI services
- Proprietary system connections
- Tools requiring specialized hardware

Quick Checklist
---------------

**How to create a remote tool:**

1. **Create Python class** with `@register_mcp_tool` decorator
2. **Implement `run()` method** with your tool logic
3. **Start MCP server** using `start_mcp_server()`
4. **Configure ToolUniverse** to load the remote tool
5. **Use remote tools** via ToolUniverse's standard interface

Step 1: Create Your Remote Tool
-------------------------------

Create a Python class with the `@register_mcp_tool` decorator:

.. code-block:: python

   from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server
   from typing import Dict, Any

   @register_mcp_tool(
       tool_type_name="remote_text_processor",
       config={
           "description": "Processes text using remote computation",
           "parameter_schema": {
               "type": "object",
               "properties": {
                   "text": {"type": "string", "description": "Text to process"},
                   "operation": {
                       "type": "string", 
                       "enum": ["uppercase", "lowercase", "reverse"],
                       "description": "Operation to perform"
                   }
               },
               "required": ["text"]
           }
       },
       mcp_config={
           "server_name": "Text Processing Server",
           "host": "0.0.0.0",
           "port": 8001
       }
   )
   class RemoteTextProcessor:
       """Processes text using remote computation resources."""
       
       def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
           """Execute text processing."""
           text = arguments.get("text", "")
           operation = arguments.get("operation", "uppercase")
           
           # Your processing logic here
           if operation == "uppercase":
               result = text.upper()
           elif operation == "lowercase":
               result = text.lower()
           elif operation == "reverse":
               result = text[::-1]
           else:
               result = text
           
           return {
               "result": result,
               "operation": operation,
               "success": True
           }

   # Start the MCP server
   if __name__ == "__main__":
       start_mcp_server()

Step 2: Configure ToolUniverse to Load Remote Tools
---------------------------------------------------

Create a configuration file to automatically load your remote tool:

**Create `remote_tools_config.json`:**

.. code-block:: json

   [
       {
           "name": "mcp_auto_loader_text_processor",
           "description": "Automatically discover and load text processing tools from MCP Server",
           "type": "MCPAutoLoaderTool",
           "tool_prefix": "remote_",
           "server_url": "http://localhost:8001/mcp",
           "required_api_keys": []
       }
   ]

**Alternative: Use `tu.tools` attribute:**

.. code-block:: python

   # Direct tool access (if tool is loaded)
   try:
       result = tu.tools.remote_text_processor(
           text="Hello World",
           operation="uppercase"
       )
       print(result)
   except AttributeError:
       print("remote_text_processor not loaded — configure remote_tools_config.json first")

**Load the configuration in ToolUniverse:**

.. code-block:: python

   from tooluniverse import ToolUniverse

   # Initialize ToolUniverse
   tu = ToolUniverse()

   # Load remote tools from configuration
   tu.load_tools(tool_config_files={"remote_tools": "remote_tools_config.json"})

   # Use remote tools like any other ToolUniverse tool
   result = tu.run({
       "name": "remote_text_processor",
       "arguments": {
           "text": "Hello World",
           "operation": "uppercase"
       }
   })
   print(result)

Step 3: Advanced Configuration
------------------------------

**Multiple Tools on Same Server:**

You can register multiple tools on the same MCP server:

.. code-block:: python

   @register_mcp_tool(
       tool_type_name="remote_data_analyzer",
       config={"description": "Analyzes data using remote resources"},
       mcp_config={"port": 8001}  # Same port as text processor
   )
   class RemoteDataAnalyzer:
       def run(self, arguments):
           # Analysis logic
           return {"analysis": "complete"}

   @register_mcp_tool(
       tool_type_name="remote_model_predictor", 
       config={"description": "Makes predictions using remote ML models"},
       mcp_config={"port": 8001}  # Same port
   )
   class RemoteModelPredictor:
       def run(self, arguments):
           # Prediction logic
           return {"prediction": "result"}

**Environment Variables:**

Use environment variables for configuration:

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

**Tool Composition:**

Remote tools can be composed with local tools:

.. code-block:: python

   # Sequential execution
   result1 = tu.run({"name": "remote_data_fetcher", "arguments": {...}})
   result2 = tu.run({"name": "local_data_processor", "arguments": {...}})

   # Parallel execution (using list format)
   results = tu.run([
       {"name": "remote_ml_model", "arguments": {...}},
       {"name": "remote_api_call", "arguments": {...}}
   ])

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

**Timeout errors**
- Check network connectivity
- Verify server performance
- Increase timeout in configuration if needed

Real-World Example: Human Expert Feedback
------------------------------------------

The Human Expert Feedback system demonstrates a complete remote tool implementation:

**Server Side (`examples/remote_tools/create_remote_tool.py`):**

.. code-block:: python

   @register_mcp_tool(
       tool_type_name="consult_human_expert",
       config={
           "description": "Consult human experts for complex decisions",
           "parameter_schema": {
               "type": "object",
               "properties": {
                   "question": {"type": "string", "description": "Question for expert"},
                   "specialty": {"type": "string", "default": "general"},
                   "priority": {"type": "string", "enum": ["low", "normal", "high", "urgent"]}
               },
               "required": ["question"]
           }
       },
       mcp_config={
           "server_name": "Human Expert Consultation Server",
           "host": "0.0.0.0",
           "port": 9876
       }
   )
   class ConsultHumanExpertTool:
       def run(self, arguments):
           # Expert consultation logic
           return {"expert_response": "..."}

   if __name__ == "__main__":
       start_mcp_server()

**Client Configuration (`examples/remote_tools/expert_feedback_config.json`):**

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

**Usage:**

.. code-block:: python

   from tooluniverse import ToolUniverse
   
   tu = ToolUniverse()
   tu.load_tools(tool_config_files={"expert_feedback": "expert_feedback_tools.json"})
   
   result = tu.run({
       "name": "expert_consult_human_expert",
       "arguments": {
           "question": "Is this drug interaction safe?",
           "specialty": "pharmacology",
           "priority": "high"
       }
   })

Examples
--------

Complete working examples are available in the `examples/remote_tools/` directory:

* **`create_remote_tool.py`** - Create and start a remote tool server
* **`use_remote_tool.py`** - Use remote tools in ToolUniverse

**Quick Start:**
```bash
cd examples/remote_tools
python create_remote_tool.py  # In one terminal
python use_remote_tool.py     # In another terminal
```

Next Steps
----------

* 🔧 **MCP Integration**: :doc:`mcp_integration` - Detailed MCP integration guide
* 🏠 **Local Tools**: :doc:`../local_tools/local_tools_tutorial` - Learn about local tool development
* 🚀 **Contributing**: :doc:`../contributing/remote_tools` - Submit remote tools to ToolUniverse
* 🔍 **Architecture**: :doc:`../reference/architecture` - Understand ToolUniverse internals

.. tip::
   **Integration tip**: Start with simple MCP servers and gradually add complexity. The ToolUniverse ecosystem supports over 1000 tools including machine learning models, datasets, and APIs!
