Local Tools Tutorial
====================

Learn how to create local Python tools with ToolUniverse. This tutorial teaches you step by step, from the simplest example to advanced features.

Quick Checklist
---------------

**How to add a local tool:**

1. **Create Python file** with your tool class
2. **Add decorator** ``@register_tool('ToolName', config={...})``
3. **Inherit from BaseTool** and implement ``run()`` method
4. **Define parameters** in config (if needed)
5. **Import the file** to register the tool
6. **Use with ToolUniverse** via ``run()``

.. note::
    **Self-Use**: This tutorial covers using tools in your own projects.
   
    **Contributing**: If you want to contribute tools to the ToolUniverse repository, see the contributing guide for additional steps.

Step 1: Your First Tool (Simplest Example)
===========================================

Let's start with the absolute minimum. This tool just says hello:

.. code-block:: python

   # hello_tool.py - Save this file anywhere
   from tooluniverse.tool_registry import register_tool
   from tooluniverse.base_tool import BaseTool

   @register_tool('HelloTool', config={
       "name": "hello_tool",
       "description": "Say hello"
   })
   class HelloTool(BaseTool):
       def run(self, arguments=None, **kwargs):
           return {"message": "Hello!", "success": True}

   # Usage
   from tooluniverse import ToolUniverse
   from hello_tool import HelloTool  # This registers the tool

   tu = ToolUniverse()
   tu.load_tools()

   result = tu.run({
       "name": "hello_tool",
       "arguments": {}
   })
   print(result)  # {"message": "Hello!", "success": True}

**What just happened?**
- ``@register_tool`` tells ToolUniverse about your tool
- ``config`` defines the tool's name and description
- ``run()`` method does the actual work
- ToolUniverse automatically discovers and loads your tool

**Try it:** Save as `hello_tool.py`, run it, and see "Hello!" printed.

Step 2: Adding Parameters
=========================

Now let's add input parameters. This tool greets a specific person:

.. code-block:: python

   @register_tool('GreetTool', config={
       "name": "greet_tool",
       "description": "Greet a person by name",
       "parameter": {  # ← This is new!
           "type": "object",
           "properties": {
               "name": {"type": "string", "description": "Person's name"}
           },
           "required": ["name"]
       }
   })
   class GreetTool(BaseTool):
       def run(self, arguments=None, **kwargs):
           # Handle both direct calls and ToolUniverse calls
           if arguments is None:
               arguments = kwargs
           
           name = arguments.get('name') if isinstance(arguments, dict) else arguments
           return {"message": f"Hello, {name}!", "success": True}

   # Usage
   result = tu.run({
       "name": "greet_tool",
       "arguments": {"name": "Alice"}
   })
   print(result)  # {"message": "Hello, Alice!", "success": True}

**Understanding the config:**
- ``"parameter"``: Defines what inputs your tool accepts
- ``"type": "object"``: Tool accepts multiple parameters (not just one value)
- ``"properties"``: Defines each parameter (name, type, description)
- ``"required"``: Lists which parameters are mandatory

**Parameter types you can use:**
- ``"string"``: Text input
- ``"number"``: Numeric input
- ``"boolean"``: True/false input
- ``"array"``: List of values

Step 3: Adding Input Validation
===============================

Let's add validation to catch bad inputs:

.. code-block:: python

   @register_tool('ValidatedGreetTool', config={
       "name": "validated_greet_tool",
       "description": "Greet a person with validation",
       "parameter": {
           "type": "object",
           "properties": {
               "name": {"type": "string", "description": "Person's name"}
           },
           "required": ["name"]
       }
   })
   class ValidatedGreetTool(BaseTool):
       def run(self, arguments=None, **kwargs):
           if arguments is None:
               arguments = kwargs
           
           name = arguments.get('name') if isinstance(arguments, dict) else arguments
           
           # Validate input
           self.validate_input(name=name)
           
           return {"message": f"Hello, {name}!", "success": True}

       def validate_input(self, **kwargs):
           """Validate input parameters."""
           name = kwargs.get('name')
           
           if not name:
               raise ValueError("Name is required")
           
           if not isinstance(name, str):
               raise ValueError("Name must be a string")
           
           if len(name.strip()) == 0:
               raise ValueError("Name cannot be empty")

**Why validation matters:**
- Prevents crashes from bad input
- Gives clear error messages to users
- Makes your tool more reliable

**Alternative: Using validate_parameters()**

For more complex validation, you can override the `validate_parameters()` method instead:

.. code-block:: python

   def validate_parameters(self, arguments):
       """Validate input parameters using BaseTool's validation system."""
       # First, run base validation
       base_error = super().validate_parameters(arguments)
       if base_error:
           return base_error
       
       # Add your custom validation
       name = arguments.get('name', '')
       if len(name) < 2:
           from tooluniverse.exceptions import ToolValidationError
           return ToolValidationError(
               "Name must be at least 2 characters",
               details={"field": "name", "min_length": 2}
           )
       
       return None  # Validation passed

**When to use which:**
- Use `validate_input()` for simple validation in your `run()` method
- Use `validate_parameters()` for complex validation that integrates with ToolUniverse's error system

Step 4: Complete Real Example
=============================

Now let's build something useful - a protein molecular weight calculator:

.. code-block:: python

   @register_tool('ProteinCalculator', config={
       "name": "protein_calculator",
       "description": "Calculate molecular weight of protein sequences",
       "parameter": {
           "type": "object",
           "properties": {
               "sequence": {"type": "string", "description": "Protein sequence (single letter amino acid codes)"}
           },
           "required": ["sequence"]
       }
   })
   class ProteinCalculator(BaseTool):
       def __init__(self, tool_config=None):
           super().__init__(tool_config)
           # Amino acid molecular weights (in Daltons)
           self.aa_weights = {
               'A': 89.09, 'R': 174.20, 'N': 132.12, 'D': 133.10,
               'C': 121.16, 'Q': 146.15, 'E': 147.13, 'G': 75.07,
               'H': 155.16, 'I': 131.17, 'L': 131.17, 'K': 146.19,
               'M': 149.21, 'F': 165.19, 'P': 115.13, 'S': 105.09,
               'T': 119.12, 'W': 204.23, 'Y': 181.19, 'V': 117.15
           }

       def run(self, arguments=None, **kwargs):
           if arguments is None:
               arguments = kwargs
           
           sequence = arguments.get('sequence') if isinstance(arguments, dict) else arguments
           self.validate_input(sequence=sequence)

           # Clean sequence (remove whitespace, convert to uppercase)
           clean_sequence = sequence.strip().upper()

           # Calculate molecular weight
           total_weight = sum(self.aa_weights.get(aa, 0) for aa in clean_sequence)
           # Subtract water molecules for peptide bonds
           water_weight = (len(clean_sequence) - 1) * 18.015
           molecular_weight = total_weight - water_weight

           return {
               "molecular_weight": round(molecular_weight, 2),
               "sequence_length": len(clean_sequence),
               "sequence": clean_sequence,
               "success": True
           }

       def validate_input(self, **kwargs):
           sequence = kwargs.get('sequence')
           
           if not sequence:
               raise ValueError("Sequence is required")
           
           if not isinstance(sequence, str):
               raise ValueError("Sequence must be a string")
           
           if len(sequence.strip()) == 0:
               raise ValueError("Sequence cannot be empty")
           
           # Check for valid amino acid codes
           valid_aa = set(self.aa_weights.keys())
           invalid_chars = set(sequence.upper()) - valid_aa
           if invalid_chars:
               raise ValueError(f"Invalid amino acid codes: {', '.join(invalid_chars)}")

   # Usage
   result = tu.run({
       "name": "protein_calculator",
       "arguments": {"sequence": "GIVEQCCTSICSLYQLENYCN"}
   })
   print(result)  # {"molecular_weight": 2401.45, "sequence_length": 20, "success": True}

**This example shows:**
- Complex business logic
- Data initialization in ``__init__``
- Input validation with custom rules
- Meaningful return values
- Error handling

Common Scenarios
================

I want to call an external API
-------------------------------

.. code-block:: python

   import requests

   @register_tool('APITool', config={
       "name": "api_tool",
       "description": "Make API call to specified URL",
       "parameter": {
           "type": "object",
           "properties": {
               "url": {"type": "string", "description": "API URL"},
               "method": {"type": "string", "description": "HTTP method", "default": "GET"}
           },
           "required": ["url"]
       }
   })
   class APITool(BaseTool):
       def run(self, arguments=None, **kwargs):
           if arguments is None:
               arguments = kwargs
           
           url = arguments.get('url') if isinstance(arguments, dict) else arguments
           method = arguments.get('method', 'GET') if isinstance(arguments, dict) else 'GET'
           
           self.validate_input(url=url, method=method)

           try:
               if method == "GET":
                   response = requests.get(url)
               else:
                   response = requests.post(url)

               response.raise_for_status()
               return {"data": response.json(), "success": True}
           except Exception as e:
               return {"error": str(e), "success": False}

I want to process files
-----------------------

.. code-block:: python

   @register_tool('FileProcessor', config={
       "name": "file_processor",
       "description": "Process file based on specified operation",
       "parameter": {
           "type": "object",
           "properties": {
               "file_path": {"type": "string", "description": "Path to file"},
               "operation": {"type": "string", "description": "Operation to perform", "default": "read"}
           },
           "required": ["file_path"]
       }
   })
   class FileProcessor(BaseTool):
       def run(self, arguments=None, **kwargs):
           if arguments is None:
               arguments = kwargs
           
           file_path = arguments.get('file_path') if isinstance(arguments, dict) else arguments
           operation = arguments.get('operation', 'read') if isinstance(arguments, dict) else 'read'
           
           self.validate_input(file_path=file_path, operation=operation)

           try:
               with open(file_path, 'r') as f:
                   content = f.read()

               if operation == "analyze":
                   result = {"lines": len(content.split('\n')), "chars": len(content)}
               else:
                   result = {"content": content}

               return {"result": result, "success": True}
           except Exception as e:
               return {"error": str(e), "success": False}

I want to use API keys (environment variables)
-----------------------------------------------

Add to your config:

.. code-block:: python

   @register_tool('MyAPITool', config={
       "name": "my_api_tool",
       "description": "Tool that uses API keys",
       "parameter": {
           "type": "object",
           "properties": {
               "query": {"type": "string", "description": "Search query"}
           },
           "required": ["query"]
       },
       "settings": {  # ← Add this section
           "api_key": "env:MY_API_KEY",  # ← Reference environment variable
           "base_url": "https://api.example.com"
       }
   })

Then in your run method:

.. code-block:: python

   def __init__(self, tool_config: Dict[str, Any] = None):
       super().__init__(tool_config)
       self.api_key = self.config.get("settings", {}).get("api_key")
       self.base_url = self.config.get("settings", {}).get("base_url")

I want better error handling
-----------------------------

For more sophisticated error handling, override the `handle_error()` method:

.. code-block:: python

   from tooluniverse.exceptions import ToolValidationError, ToolAuthError

   class APITool(BaseTool):
       def handle_error(self, exception):
           """Provide tool-specific error classification."""
           error_str = str(exception).lower()
           
           # API-specific error patterns
           if "api_key" in error_str or "unauthorized" in error_str:
               return ToolAuthError(
                   "API authentication failed",
                   next_steps=[
                       "Check API key configuration",
                       "Verify API key permissions",
                       "Contact API provider if issues persist"
                   ]
               )
           
           if "rate limit" in error_str:
               return ToolValidationError(
                   "API rate limit exceeded",
                   next_steps=[
                       "Wait before retrying",
                       "Check your API usage limits",
                       "Consider upgrading your plan"
                   ]
               )
           
           # Fall back to base error handling
           return super().handle_error(exception)

**Benefits of custom error handling:**
- Users get specific, actionable error messages
- Different error types can be handled differently
- Better debugging and troubleshooting experience

Troubleshooting
===============

Naming Conflicts (Failed to initialize tool for validation)
------------------------------------------------------------

**Problem**: Getting "Failed to initialize tool for validation" error

**Cause**: Wrapper function name matches the class name

**Solution**: Use different names
.. code-block:: python

   # Wrapper function must use snake_case
   def my_tool(...):  # ✅ Good
   def MyTool(...):  # ❌ Bad if class is also called MyTool

**Convention**: Class names use PascalCase, wrapper functions use snake_case.

Tool not found
---------------

- Is the tool file imported? (need to ``import`` or run directly)
- Is the ``@register_tool`` decorator used correctly?
- Is ToolUniverse instantiated after tool import?

Parameter errors
-----------------

- Do ``"parameter"`` definitions in config match ``run()`` method parameters?
- Are required parameters listed in ``"required"`` array?
- Are parameter types (``string``/``number``/``object``) correct?

Execution failures
-------------------

- Does the class inherit from ``BaseTool``?
- Does ``__init__`` call ``super().__init__(tool_config)``?
- Does ``run()`` return a dict with ``"success"`` field?
- Is ``validate_input()`` implemented for parameter validation?

Next Steps
==========

Now that you can create local tools:

* **Remote Tools**: Learn about remote tool integration
* **Contributing**: Submit your tools to ToolUniverse
* **AI Integration**: Connect your tools with AI assistants
* **Scientific Workflows**: Build research pipelines

.. tip::
   **Development tip**: Start simple, test thoroughly, and gradually add complexity. The ToolUniverse community is here to help if you get stuck!