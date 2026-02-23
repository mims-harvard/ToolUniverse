Contributing Remote Tools to ToolUniverse
==========================================

This guide covers how to contribute remote tools to the ToolUniverse repository. Remote tools run on separate servers and are accessed via MCP (Model Context Protocol) or REST APIs.

.. note::
   **Key Difference**: Remote tools don't require modifying ``__init__.py``, but you must provide a publicly accessible server or detailed deployment instructions.

Quick Overview
--------------

**10 Steps to Contribute a Remote Tool:**

1. **Environment Setup** - Fork, clone, install dependencies
2. **Choose Implementation** - Independent server vs register_mcp_tool
3. **Create MCP Server** - Implement server with your tool logic
4. **Create Config** - JSON file in ``data/remote_tools/xxx_tools.json``
5. **Deploy Server** - Make it publicly accessible
6. **Write Tests** - Integration tests with mocked server
7. **Code Quality** - Pre-commit hooks (automatic)
8. **Documentation** - Server README and API docs
9. **Create Examples** - Working examples in ``examples/``
10. **Submit PR** - Include server code and deployment docs

Step-by-Step Guide
------------------

Step 1: Environment Setup
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Fork the repository on GitHub first
   git clone https://github.com/yourusername/ToolUniverse.git
   cd ToolUniverse
   
   # Create virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install development dependencies
   pip install -e ".[dev]"
   
   # Install pre-commit hooks
   ./setup_precommit.sh

Step 2: Choose Implementation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Option A: Independent MCP Server (Recommended)**
- Create separate server (any language)
- More flexible and maintainable
- Server code goes in ``src/tooluniverse/remote/``

**Option B: register_mcp_tool Decorator**
- Python class as both local and MCP tool
- Simpler but less flexible
- Good for simple tools

This guide focuses on **Option A** (Independent server).

Step 3: Create MCP Server
~~~~~~~~~~~~~~~~~~~~~~~~~~

Create server directory: ``src/tooluniverse/remote/my_service/``

**Server Structure:**
.. code-block:: text

   src/tooluniverse/remote/my_service/
   ├── __init__.py
   ├── server.py              # Main server file
   ├── tools.py               # Tool implementations
   ├── requirements.txt       # Server dependencies
   ├── README.md              # Deployment instructions
   └── docker-compose.yml     # Optional: Docker setup

**Example server.py:**
.. code-block:: python

   from fastapi import FastAPI
   from tooluniverse.smcp import SMCP
   import uvicorn

   app = FastAPI(title="My Service MCP Server")
   mcp = SMCP()

   @mcp.tool("my_remote_tool")
   def my_remote_tool(input_text: str, operation: str = "uppercase") -> dict:
       """Convert text using specified operation."""
       if operation == "uppercase":
           result = input_text.upper()
       elif operation == "lowercase":
           result = input_text.lower()
       else:
           raise ValueError(f"Unknown operation: {operation}")
       
       return {
           "result": result,
           "operation": operation,
           "success": True
       }

   @mcp.tool("health_check")
   def health_check() -> dict:
       """Health check endpoint."""
       return {"status": "healthy", "service": "my_service"}

   # Mount MCP endpoints
   app.mount("/mcp", mcp.app)

   if __name__ == "__main__":
       uvicorn.run(app, host="0.0.0.0", port=8000)

**requirements.txt:**
.. code-block:: text

   fastapi>=0.100.0
   uvicorn>=0.20.0
   tooluniverse>=1.0.0

Step 4: Create Configuration File
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create ``src/tooluniverse/data/remote_tools/my_service_tools.json``:

.. code-block:: json

   [
     {
       "type": "RemoteTool",
       "name": "my_remote_tool",
       "description": "Convert text using various operations via remote service",
       "parameter": {
         "type": "object",
         "properties": {
           "input_text": {
             "type": "string",
             "description": "Text to process"
           },
           "operation": {
             "type": "string",
             "enum": ["uppercase", "lowercase"],
             "default": "uppercase",
             "description": "Operation to perform on the text"
           }
         },
         "required": ["input_text"]
       },
       "remote_info": {
         "server_type": "MCP",
         "transport": "http",
         "url": "https://my-service.example.com/mcp",
         "code_url": "https://github.com/yourusername/ToolUniverse/tree/main/src/tooluniverse/remote/my_service"
       },
       "examples": [
         {
           "description": "Convert text to uppercase",
           "arguments": {
             "input_text": "hello world",
             "operation": "uppercase"
           }
         }
       ],
       "tags": ["text", "remote", "mcp"],
       "author": "Your Name <your.email@example.com>",
       "version": "1.0.0"
     }
   ]

Step 5: Deploy Server
~~~~~~~~~~~~~~~~~~~~~~

**Option A: Cloud Deployment (Recommended)**
- Deploy to cloud platform (AWS, GCP, Azure, Heroku, etc.)
- Provide public URL
- Include deployment documentation

**Option B: Self-hosted with Documentation**
- Provide detailed setup instructions
- Include Docker configuration
- Document requirements and dependencies

**Example deployment documentation (README.md):**
.. code-block:: markdown

   # My Service MCP Server
   
   ## Quick Start
   
   ```bash
   # Install dependencies
   pip install -r requirements.txt
   
   # Run server
   python server.py
   ```
   
   ## Docker Deployment
   
   ```bash
   # Build image
   docker build -t my-service .
   
   # Run container
   docker run -p 8000:8000 my-service
   ```
   
   ## Environment Variables
   
   - `PORT`: Server port (default: 8000)
   - `HOST`: Server host (default: 0.0.0.0)
   
   ## API Endpoints
   
   - `GET /mcp/tools` - List available tools
   - `POST /mcp/tools/my_remote_tool` - Execute tool

Step 6: Write Tests
~~~~~~~~~~~~~~~~~~~

Create ``tests/integration/test_my_remote_tool.py``:

.. code-block:: python

   import pytest
   from unittest.mock import patch, Mock
   from tooluniverse import ToolUniverse

   class TestMyRemoteTool:
       def setup_method(self):
           self.tu = ToolUniverse()
           self.tu.load_tools()

       @patch('requests.post')
       def test_remote_tool_success(self, mock_post):
           """Test successful remote tool execution."""
           # Mock server response
           mock_response = Mock()
           mock_response.json.return_value = {
               "result": "HELLO",
               "operation": "uppercase",
               "success": True
           }
           mock_response.status_code = 200
           mock_post.return_value = mock_response

           # Test tool execution
           result = self.tu.run({
               "name": "my_remote_tool",
               "arguments": {
                   "input_text": "hello",
                   "operation": "uppercase"
               }
           })

           assert result["success"] is True
           assert result["result"] == "HELLO"

       @patch('requests.post')
       def test_remote_tool_error(self, mock_post):
           """Test remote tool error handling."""
           # Mock server error
           mock_response = Mock()
           mock_response.json.return_value = {
               "error": "Unknown operation: invalid",
               "success": False
           }
           mock_response.status_code = 400
           mock_post.return_value = mock_response

           result = self.tu.run({
               "name": "my_remote_tool",
               "arguments": {
                   "input_text": "hello",
                   "operation": "invalid"
               }
           })

           assert result["success"] is False
           assert "error" in result

       def test_tool_discovery(self):
           """Test that tool is discovered correctly."""
           assert "my_remote_tool" in self.tu.all_tool_dict

Run tests:
.. code-block:: bash

   pytest tests/integration/test_my_remote_tool.py -v

Step 7: Code Quality Check (Automatic)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Pre-commit hooks will automatically run when you commit:

.. code-block:: bash

   git add .
   git commit -m "feat: add MyRemoteTool service"
   # Pre-commit will run: Black, Flake8, Ruff, etc.

Step 8: Documentation
~~~~~~~~~~~~~~~~~~~~~

**Server Documentation (README.md):**
.. code-block:: markdown

   # My Service
   
   Remote MCP server providing text processing tools.
   
   ## Features
   
   - Text case conversion (uppercase/lowercase)
   - Health check endpoint
   - MCP protocol support
   
   ## API Reference
   
   ### my_remote_tool
   
   Convert text using specified operation.
   
   **Parameters:**
   - `input_text` (string, required): Text to process
   - `operation` (string, optional): Operation to perform (uppercase/lowercase)
   
   **Returns:**
   - `result` (string): Processed text
   - `operation` (string): Operation performed
   - `success` (boolean): Success status

**Tool Documentation:**
Add comprehensive docstrings to your tool functions in the server code.

Step 9: Create Examples
~~~~~~~~~~~~~~~~~~~~~~~~

Create ``examples/my_remote_tool_example.py``:

.. code-block:: python

   """Example usage of MyRemoteTool."""
   
   from tooluniverse import ToolUniverse

   def main():
       # Initialize ToolUniverse
       tu = ToolUniverse()
       tu.load_tools()
       
       # Test the remote tool
       test_cases = [
           {"input_text": "hello world", "operation": "uppercase"},
           {"input_text": "HELLO WORLD", "operation": "lowercase"},
           {"input_text": "Python", "operation": "uppercase"},
       ]
       
       for i, test_case in enumerate(test_cases, 1):
           print(f"\nTest {i}: {test_case}")
           
           result = tu.run({
               "name": "my_remote_tool",
               "arguments": test_case
           })
           
           if result.get("success"):
               print(f"✅ Result: {result['result']}")
           else:
               print(f"❌ Error: {result.get('error', 'Unknown error')}")

   if __name__ == "__main__":
       main()

Step 10: Submit Pull Request
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Create feature branch
   git checkout -b feature/add-my-remote-tool
   
   # Add all files
   git add src/tooluniverse/remote/my_service/
   git add src/tooluniverse/data/remote_tools/my_service_tools.json
   git add tests/integration/test_my_remote_tool.py
   git add examples/my_remote_tool_example.py
   
   # Commit with descriptive message
   git commit -m "feat: add MyRemoteTool MCP service
   
   - Implement MCP server with text processing tools
   - Add comprehensive integration tests
   - Include deployment documentation and examples
   - Support uppercase/lowercase text conversion
   
   Closes #[issue-number]"
   
   # Push and create PR
   git push origin feature/add-my-remote-tool

**PR Template:**
.. code-block:: markdown

   ## Description
   
   This PR adds MyRemoteTool, a new MCP server for text processing.
   
   ## Changes Made
   
   - ✅ **MCP Server**: Complete server implementation in remote/my_service/
   - ✅ **Configuration**: JSON config in data/remote_tools/
   - ✅ **Testing**: Integration tests with mocked server
   - ✅ **Documentation**: Server README and API docs
   - ✅ **Examples**: Working usage examples
   - ✅ **Deployment**: Docker and cloud deployment instructions
   
   ## Server Information
   
   - **Protocol**: MCP (Model Context Protocol)
   - **Transport**: HTTP
   - **Deployment**: [Cloud platform / Self-hosted]
   - **URL**: https://my-service.example.com/mcp
   
   ## Testing
   
   ```bash
   pytest tests/integration/test_my_remote_tool.py
   python examples/my_remote_tool_example.py
   ```
   
   ## Deployment
   
   See `src/tooluniverse/remote/my_service/README.md` for deployment instructions.
   
   ## Checklist
   
   - [x] Tests pass locally
   - [x] Server is publicly accessible or deployment docs provided
   - [x] Code follows project style guidelines
   - [x] Documentation is complete
   - [x] Examples work as expected

Key Differences from Local Tools
---------------------------------

| Aspect | Local Tools | Remote Tools |
|--------|-------------|--------------|
| **__init__.py** | ✅ Must modify 4 locations | ❌ No modification needed |
| **File Location** | ``src/tooluniverse/xxx_tool.py`` | ``src/tooluniverse/remote/xxx/`` |
| **Config Location** | ``data/xxx_tools.json`` | ``data/remote_tools/xxx_tools.json`` |
| **Server Deployment** | Not needed | ✅ Must provide public access |
| **Testing** | Unit tests | Integration tests (mock server) |
| **Dependencies** | Python only | Server + dependencies |

Common Mistakes
----------------

**❌ Server not accessible**
- Tool will fail with connection errors
- Solution: Ensure server is publicly accessible or provide clear deployment docs

**❌ Wrong config location**
- Config must be in ``data/remote_tools/``
- Not in ``data/``

**❌ Missing server code**
- Include complete server implementation
- Don't just provide config

**❌ No deployment documentation**
- Users need to know how to run the server
- Include setup and deployment instructions

**❌ Poor error handling**
- Server should return proper error responses
- Tool should handle network failures gracefully

Troubleshooting
---------------

**Connection Error: Server not accessible**
.. code-block:: python

   # Test server connectivity
   import requests
   response = requests.get("https://your-server.com/mcp/tools")
   print(f"Status: {response.status_code}")
   print(f"Response: {response.json()}")

**Tool not found in ToolUniverse**
.. code-block:: python

   # Check if config is loaded
   from tooluniverse import ToolUniverse
   tu = ToolUniverse()
   tu.load_tools()
   
   print("my_remote_tool" in tu.all_tool_dict)  # Should be True

**Server returns unexpected format**
- Ensure server follows MCP protocol
- Check that responses match expected schema
- Verify tool parameter validation

Next Steps
----------

After successfully contributing your remote tool:

* 🏠 **Local Tools**: :doc:`local_tools` - Learn about contributing local tools
* 📚 **MCP Integration**: :doc:`../remote_tools/mcp_integration` - MCP integration patterns
* 🔍 **Architecture**: :doc:`../reference/architecture` - Understand ToolUniverse internals
* 📊 **Comparison**: Review the tool type comparison table in :doc:`index`

.. tip::
   **Success Tips**: Start with simple servers, test thoroughly with real deployments, and provide clear documentation for users to run your service!
