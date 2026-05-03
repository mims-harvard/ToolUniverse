Create Your First Tool
====================================

Get up and running with ToolUniverse in 5 minutes! This guide shows you how to create a simple local tool for your own use.

What You'll Build
-----------------

A text processing tool that converts text to uppercase - simple but demonstrates all the core concepts.

Complete Working Example
-------------------------

**Step 1: Create the tool file**

Create ``my_text_tool.py`` in your project directory:

.. code-block:: python

   from tooluniverse.tool_registry import register_tool
   from tooluniverse.base_tool import BaseTool
   from typing import Dict, Any

   @register_tool('TextProcessor', config={
       "name": "text_processor",
       "type": "TextProcessor", 
       "description": "Process text with various operations",
       "parameter": {
           "type": "object",
           "properties": {
               "text": {
                   "type": "string",
                   "description": "Text to process"
               },
               "operation": {
                   "type": "string",
                   "enum": ["uppercase", "lowercase", "reverse"],
                   "default": "uppercase",
                   "description": "Operation to perform"
               }
           },
           "required": ["text"]
       }
   })
   class TextProcessor(BaseTool):
       """Process text with various operations."""
       
       def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
           """Execute the text processing."""
           text = arguments.get("text", "")
           operation = arguments.get("operation", "uppercase")
           
           if operation == "uppercase":
               result = text.upper()
           elif operation == "lowercase":
               result = text.lower()
           elif operation == "reverse":
               result = text[::-1]
           else:
               return {"error": f"Unknown operation: {operation}", "success": False}
           
           return {
               "result": result,
               "operation": operation,
               "original": text,
               "success": True
           }

**Step 2: Use the tool**

Create ``main.py`` in the same directory:

.. code-block:: python

   from tooluniverse import ToolUniverse
   from my_text_tool import TextProcessor  # Import to register the tool

   def main():
       # Initialize ToolUniverse
       tu = ToolUniverse()
       tu.load_tools()
       
       # Test different operations
       test_cases = [
           {"text": "Hello World", "operation": "uppercase"},
           {"text": "PYTHON", "operation": "lowercase"},
           {"text": "ToolUniverse", "operation": "reverse"},
       ]
       
       print("Text Processing Results:")
       print("-" * 40)
       
       for i, test_case in enumerate(test_cases, 1):
           print(f"\nTest {i}: {test_case['operation']}")
           print(f"Input:  '{test_case['text']}'")
           
           result = tu.run({
               "name": "text_processor",
               "arguments": test_case
           })
           
           if result.get("success"):
               print(f"Output: '{result['result']}'")
           else:
               print(f"Error:  {result.get('error', 'Unknown error')}")

   if __name__ == "__main__":
       main()

**Step 3: Run it**

.. code-block:: bash

   python main.py

**Expected Output:**
.. code-block:: text

   Text Processing Results:
   ----------------------------------------

   Test 1: uppercase
   Input:  'Hello World'
   Output: 'HELLO WORLD'

   Test 2: lowercase
   Input:  'PYTHON'
   Output: 'python'

   Test 3: reverse
   Input:  'ToolUniverse'
   Output: 'esrevinUlooT'

That's It! 
--------------

You've successfully created and used your first ToolUniverse tool! Here's what happened:

1. **Tool Definition**: The ``@register_tool`` decorator registered your tool with ToolUniverse
2. **Configuration**: The config dictionary defined the tool's interface and parameters
3. **Implementation**: The ``run()`` method contained your tool's logic
4. **Usage**: ToolUniverse automatically discovered and loaded your tool

Key Concepts Explained
----------------------

**Tool Registration**
- ``@register_tool('ToolType', config={...})`` registers your tool
- The config defines the tool's name, parameters, and metadata
- ToolUniverse automatically discovers registered tools

**BaseTool Class**
- All tools must inherit from ``BaseTool``
- Implement the ``run(arguments)`` method with your logic
- Return a dictionary with ``success`` and result data

**Tool Execution**
- Use ``tu.run()`` to execute tools
- Pass tool name and arguments as a dictionary
- ToolUniverse handles parameter validation and execution

**Parameter Validation**
- ToolUniverse automatically validates parameters based on your config
- Required parameters are enforced
- Type checking happens automatically

Next Steps
----------

Now that you have a working tool, you can:

** Learn More:**
- :doc:`local_tools/local_tools_tutorial` - Comprehensive local tool development
- :doc:`remote_tools/tutorial` - Create remote tools and MCP servers
- Review the tool type comparison table in :doc:`contributing/index`

** Contribute to Community:**
- :doc:`contributing/local_tools` - Submit your tool to ToolUniverse (requires additional steps)
- :doc:`contributing/remote_tools` - Submit remote tools to the community

** Advanced Features:**
- Add input validation with ``validate_input()`` method
- Implement error handling and retry logic
- Add caching and performance optimizations
- Create more complex tools with multiple operations

** Pro Tips:**
- Start simple and add complexity gradually
- Test your tools thoroughly before contributing
- Use meaningful parameter names and descriptions
- Follow the existing tool patterns in the codebase

Common Questions
----------------

**Q: Can I put the tool in a different file?**
A: Yes! Just make sure to import it where you use ToolUniverse.

**Q: What if I want to add more operations?**
A: Just add them to the ``enum`` list in the config and implement them in the ``run()`` method.

**Q: Can I use this tool in other projects?**
A: Yes! Copy the tool file and import it in any project that has ToolUniverse installed.

**Q: How do I handle errors better?**
A: Add a ``validate_input()`` method to your tool class for custom validation.

**Q: Can I make this a remote tool?**
A: Yes! See :doc:`remote_tools/tutorial` for creating MCP servers.

Ready to build something amazing? Let's go! 
