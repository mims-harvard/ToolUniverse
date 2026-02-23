Contributing Local Tools to ToolUniverse
=========================================

This guide covers how to contribute local Python tools to the ToolUniverse repository. Local tools run within the ToolUniverse process and are available to all users.

.. note::
   **Key Difference**: Contributing to the repository requires additional steps compared to using tools locally. The most critical step is modifying ``__init__.py`` in 4 specific locations.

.. note::
   **For Local Development Only**: If you just want to use a tool locally without contributing to the repository, see the single-file example in ``examples/my_new_tool/single_file_example.py``. This approach doesn't require modifying any core ToolUniverse files (``__init__.py``, ``default_config.py``, or ``data/`` directory). The complete working examples are available in ``examples/my_new_tool/`` directory with a README explaining both approaches.

Quick Overview
--------------

**10 Steps to Contribute a Local Tool:**

1. **Environment Setup** - Fork, clone, install dependencies
2. **Create Tool File** - Python class in ``src/tooluniverse/``
3. **Register Tool** - Use ``@register_tool('Type')`` decorator
4. **Create Config** - JSON file in ``data/xxx_tools.json``
5. **(Optional)** Add unit tests
6. **Done!** Tool is auto-discovered.
7. **Code Quality** - Pre-commit hooks (automatic)
8. **Documentation** - Docstrings and examples
9. **Create Examples** - Working examples in ``examples/``
10. **Submit PR** - Follow contribution guidelines

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

Step 2: Create Tool File
~~~~~~~~~~~~~~~~~~~~~~~~~

Create your tool file in ``src/tooluniverse/xxx_tool.py``:

.. code-block:: python

   from tooluniverse.tool_registry import register_tool
   from tooluniverse.base_tool import BaseTool
   from typing import Dict, Any

   @register_tool('MyNewTool')  # Note: No config here for contributions
   class MyNewTool(BaseTool):
       """My new tool for ToolUniverse."""
       
       def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
           """Execute the tool."""
           # Your tool logic here
           input_value = arguments.get('input', '')
           return {
               "result": input_value.upper(),
               "success": True
           }
       
       def validate_input(self, **kwargs) -> None:
           """Validate input parameters."""
           input_val = kwargs.get('input')
           if not input_val:
               raise ValueError("Input is required")

Step 3: Register Tool
~~~~~~~~~~~~~~~~~~~~~~

The ``@register_tool('MyNewTool')`` decorator registers your tool class. Note that for contributions, we don't include the config in the decorator - that goes in a separate JSON file.

Step 4: Create Configuration File
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create or edit ``src/tooluniverse/data/xxx_tools.json``:

.. code-block:: json

   [
     {
       "name": "my_new_tool",
       "type": "MyNewTool",
       "description": "Convert text to uppercase",
       "parameter": {
         "type": "object",
         "properties": {
           "input": {
             "type": "string",
             "description": "Text to convert to uppercase"
           }
         },
         "required": ["input"]
       },
       "examples": [
         {
           "description": "Convert text to uppercase",
           "arguments": {"input": "hello world"}
         }
       ],
       "tags": ["text", "utility"],
       "author": "Your Name <your.email@example.com>",
       "version": "1.0.0"
     }
   ]

Step 5: No Modifications Needed in __init__.py!
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

With the new automated discovery system, **you do NOT need to modify `src/tooluniverse/__init__.py`**. 

The system will automatically find your tool class if it is decorated with `@register_tool` and located inside the `src/tooluniverse` package tree.

**Verification:**

.. code-block:: python

   # Test that your tool can be imported immediately
   from tooluniverse import MyNewTool
   print(MyNewTool)  # Should show the class or lazy proxy

Step 6: Write Tests
~~~~~~~~~~~~~~~~~~~

Create tests in ``tests/unit/test_my_new_tool.py``:

.. code-block:: python

   import pytest
   from tooluniverse.my_new_tool import MyNewTool

   class TestMyNewTool:
       def setup_method(self):
           self.tool = MyNewTool()

       def test_success(self):
           """Test successful execution."""
           result = self.tool.run({"input": "hello"})
           assert result["success"] is True
           assert result["result"] == "HELLO"

       def test_validation(self):
           """Test input validation."""
           with pytest.raises(ValueError):
               self.tool.validate_input(input="")

       def test_empty_input(self):
           """Test empty input handling."""
           result = self.tool.run({"input": ""})
           assert result["success"] is True
           assert result["result"] == ""

Run tests with coverage:
.. code-block:: bash

   pytest tests/unit/test_my_new_tool.py --cov=tooluniverse --cov-report=html

Step 7: Code Quality Check (Automatic)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Pre-commit hooks will automatically run when you commit:

.. code-block:: bash

   git add .
   git commit -m "feat: add MyNewTool"
   # Pre-commit will run: Black, Flake8, Ruff, etc.
   # If checks fail, fix the issues and commit again

Step 8: Documentation
~~~~~~~~~~~~~~~~~~~~~

Add comprehensive docstrings to your tool class:

.. code-block:: python

   class MyNewTool(BaseTool):
       """
       Convert text to uppercase.
       
       This tool takes a string input and returns it converted to uppercase.
       Useful for text processing workflows.
       
       Args:
           input (str): The text to convert to uppercase
           
       Returns:
           dict: Result dictionary with 'result' and 'success' keys
           
       Example:
           >>> tool = MyNewTool()
           >>> result = tool.run({"input": "hello"})
           >>> print(result["result"])
           HELLO
       """
```

Step 9: Create Examples
~~~~~~~~~~~~~~~~~~~~~~~~

Create ``examples/my_new_tool/my_new_tool_example.py``:

.. code-block:: python

   """Example usage of MyNewTool.
   
   This example follows the documentation pattern for contributing tools to the
   repository. It demonstrates the multi-file structure:
   - my_new_tool.py: Tool class definition
   - my_new_tool_tools.json: Tool configuration
   - my_new_tool_example.py: Example usage
   
   Note: In a real contribution, these files would be placed in:
   - src/tooluniverse/my_new_tool.py
   - src/tooluniverse/data/my_new_tool_tools.json
   - examples/my_new_tool_example.py
   
   And you would need to modify __init__.py in 4 locations.
   """
   
   import os
   import sys
   
   # Import the tool class to register it
   from my_new_tool import MyNewTool  # noqa: E402, F401
   
   from tooluniverse import ToolUniverse  # noqa: E402
   
   
   def main():
       # Initialize ToolUniverse
       tu = ToolUniverse()
       
       # Load tools with the config file
       # In a real contribution, this would be in default_tool_files
       current_dir = os.path.dirname(os.path.abspath(__file__))
       config_path = os.path.join(current_dir, 'my_new_tool_tools.json')
       tu.load_tools(tool_config_files={"my_new_tool": config_path})
       
       # Use the tool
       result = tu.run({
           "name": "my_new_tool",
           "arguments": {"input": "hello world"}
       })
       
       print(f"Result: {result}")
       
       # Test with different inputs
       test_inputs = ["hello", "world", "python"]
       for text in test_inputs:
           result = tu.run({
               "name": "my_new_tool",
               "arguments": {"input": text}
           })
           print(f"'{text}' -> '{result.get('result', 'ERROR')}'")
   
   if __name__ == "__main__":
       main()

**Note**: A complete working example can be found in ``examples/my_new_tool/`` directory,
which includes both the multi-file structure (for contributions) and a single-file
example (for local development). See ``examples/my_new_tool/README.md`` for details.

Step 10: Submit Pull Request
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Create feature branch
   git checkout -b feature/add-my-new-tool
   
   # Add all files
   git add src/tooluniverse/my_new_tool.py
   git add src/tooluniverse/data/xxx_tools.json
   git add src/tooluniverse/__init__.py
   git add tests/unit/test_my_new_tool.py
   git add examples/my_new_tool_example.py
   
   # Commit with descriptive message
   git commit -m "feat: add MyNewTool for text processing
   
   - Implement MyNewTool class with uppercase conversion
   - Add comprehensive unit tests with >95% coverage
   - Include usage examples and documentation
   - Support input validation and error handling
   
   Closes #[issue-number]"
   
   # Push and create PR
   git push origin feature/add-my-new-tool

**PR Template:**
.. code-block:: markdown

   ## Description
   
   This PR adds MyNewTool, a new local tool for text processing.
   
   ## Changes Made
   
   - ✅ **Tool Implementation**: Complete MyNewTool class
   - ✅ **Testing**: Unit tests with >95% coverage
   - ✅ **Documentation**: Comprehensive docstrings and examples
   - ✅ **Configuration**: JSON config in data/xxx_tools.json
   - ✅ **Integration**: Modified __init__.py in 4 locations
   
   ## Testing
   
   ```bash
   pytest tests/unit/test_my_new_tool.py --cov=tooluniverse
   python examples/my_new_tool/my_new_tool_example.py
   ```
   
   ## Checklist
   
   - [x] Tests pass locally
   - [x] Code follows project style guidelines
   - [x] Documentation is complete
   - [x] __init__.py modified in all 4 locations
   - [x] Examples work as expected

Common Mistakes
----------------

**❌ Most Common: Missing @register_tool decorator**
- Tool won't be discovered if not decorated
- Solution: Add ``@register_tool("MyTool")``

**❌ Config in wrong place**
- Don't put config in ``@register_tool()`` decorator (for contributions)
- Put it in ``data/my_new_tool_tools.json`` instead
- Note: For local development only, you CAN put config in the decorator (see ``examples/my_new_tool/single_file_example.py``)

**❌ Wrong file location**
- Tool file must be in ``src/tooluniverse/``
- Not in your project directory

**❌ Missing tests**
- Coverage must be >90%
- Test both success and error cases

**❌ Import errors**
- Check module name matches file name
- Check class name matches exactly (case-sensitive)

Troubleshooting
---------------

**ImportError: cannot import name 'MyNewTool'**
.. code-block:: python

   # Check if tool is in __all__ list
   from tooluniverse import __all__
   print("MyNewTool" in __all__)  # Should be True
   
   # Check if import statement exists
   # Look for: from .my_new_tool import MyNewTool

**AttributeError: module 'tooluniverse' has no attribute 'MyNewTool'**
- Verify the tool name is in ``__all__`` list
- Check that the tool name matches the class name exactly

**Tool not found when using ToolUniverse**
.. code-block:: python

   # Verify tool loads correctly
   from tooluniverse import ToolUniverse
   tu = ToolUniverse()
   tu.load_tools()
   
   # Check if tool is in the loaded tools
   print("my_new_tool" in tu.all_tool_dict)  # Should be True

Next Steps
----------

After successfully contributing your local tool:

* 🚀 **Remote Tools**: :doc:`remote_tools` - Learn about contributing remote tools
* 🔍 **Architecture**: :doc:`../reference/architecture` - Understand ToolUniverse internals
* 📊 **Comparison**: Review the tool type comparison table in :doc:`../contributing/index`

.. tip::
   **Success Tips**: Start with simple tools, test thoroughly, and ask for help in GitHub discussions if you get stuck!
