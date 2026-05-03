Contributing to ToolUniverse
============================

We welcome contributions to ToolUniverse! 

Getting Started
---------------

Development Setup
~~~~~~~~~~~~~~~~~

1. Fork the repository on GitHub
2. Clone your fork locally:

.. code-block:: bash

   git clone https://github.com/yourusername/TxAgent.git
   cd TxAgent/bio/ToolUniverse

3. Create a virtual environment:

.. code-block:: bash

   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate

4. Install in development mode:

.. code-block:: bash

   pip install -e ".[dev]"

5. Install pre-commit hooks:

**Automatic Setup (Recommended):**

.. code-block:: bash

   # Auto-install pre-commit hooks
   ./setup_precommit.sh

**Manual Setup:**

.. code-block:: bash

   # Install pre-commit if not already installed
   pip install pre-commit
   
   # Install hooks
   pre-commit install
   
   # Update to latest versions
   pre-commit autoupdate

Development Dependencies
~~~~~~~~~~~~~~~~~~~~~~~~

The development setup includes:

- ``pytest`` - Testing framework
- ``black`` - Code formatting
- ``flake8`` - Code linting
- ``mypy`` - Type checking
- ``sphinx`` - Documentation
- ``pre-commit`` - Git hooks

Code Standards
--------------

Code Style
~~~~~~~~~~

We use Black for code formatting and follow PEP 8:

.. code-block:: bash

   # Format code
   black src/tooluniverse/

   # Check formatting
   black --check src/tooluniverse/

Linting
~~~~~~~

Use flake8 for linting:

.. code-block:: bash

   flake8 src/tooluniverse/

Type Hints
~~~~~~~~~~

All new code should include type hints:

.. code-block:: python

   from typing import Dict, List, Optional, Any

   def process_data(
       data: List[Dict[str, Any]],
       filter_key: Optional[str] = None
   ) -> Dict[str, int]:
       """Process data and return summary statistics."""
       pass

Testing
-------

Running Tests
~~~~~~~~~~~~~

Run the test suite:

.. code-block:: bash

   # Run all tests
   pytest

   # Run with coverage
   pytest --cov=tooluniverse

   # Run specific test file
   pytest tests/test_graphql_tool.py

Writing Tests
~~~~~~~~~~~~~

Write tests for all new functionality:

.. code-block:: python

   import pytest
   from unittest.mock import patch, Mock
   from tooluniverse import ToolUniverse

   class TestToolUniverse:
       def test_init(self):
           tooluni = ToolUniverse()
           assert tooluni is not None

       def test_load_tools(self):
           tooluni = ToolUniverse()
           tooluni.load_tools()
           tool_names, _ = tooluni.refresh_tool_name_desc()
           assert len(tool_names) > 0

       @patch('requests.post')
       def test_opentargets_query(self, mock_post):
           mock_response = Mock()
           mock_response.json.return_value = {"data": {"test": "result"}}
           mock_response.raise_for_status.return_value = None
           mock_post.return_value = mock_response

           tooluni = ToolUniverse()
           tooluni.load_tools()
           query = {
               "name": "OpenTargets_get_disease_id_description_by_name",
               "arguments": {"diseaseName": "test disease"}
           }
           result = tooluni.run(query)
           assert result is not None

Test Coverage
~~~~~~~~~~~~~

Aim for >90% test coverage:

.. code-block:: bash

   pytest --cov=tooluniverse --cov-report=html
   open htmlcov/index.html

Documentation
-------------

Building Documentation
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   cd docs
   make html
   make serve  # Serve on http://localhost:8080

Live Documentation
~~~~~~~~~~~~~~~~~~

For live editing:

.. code-block:: bash

   cd docs
   make livehtml

Writing Documentation
~~~~~~~~~~~~~~~~~~~~~

- Document all public APIs
- Include examples in docstrings
- Update user guides for new features
- Add tutorials for complex workflows

Docstring Format
~~~~~~~~~~~~~~~~

Use Google-style docstrings:

.. code-block:: python

   def search_targets(self, disease_id: str, limit: int = 10) -> Dict[str, Any]:
       """Search for targets associated with a disease.

       Args:
           disease_id: The EFO ID of the disease
           limit: Maximum number of results to return

       Returns:
           Dictionary containing target information

       Raises:
           ValueError: If disease_id is invalid
           APIError: If the API request fails

       Example:
           >>> from tooluniverse import ToolUniverse
           >>> tooluni = ToolUniverse()
           >>> tooluni.load_tools()
           >>> query = {"name": "search_targets", "arguments": {"disease_id": "EFO_0000685", "limit": 5}}
           >>> results = tooluni.run(query)
           >>> print(f"Found {len(results['targets'])} targets")
       """

Contributing Workflow
---------------------

1. Create a Feature Branch
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   git checkout -b feature/your-feature-name

2. Make Changes
~~~~~~~~~~~~~~~

- Write code following our standards
- Add comprehensive tests
- Update documentation
- Run the test suite

3. Commit Changes
~~~~~~~~~~~~~~~~~

Use conventional commit messages:

.. code-block:: bash

   git add .
   git commit -m "feat: add new drug interaction tool

   - Implement DrugInteractionTool class
   - Add support for drug-drug interaction queries
   - Include comprehensive test coverage
   - Update documentation with examples"

Commit Types:
- ``feat``: New features
- ``fix``: Bug fixes
- ``docs``: Documentation updates
- ``test``: Test additions or modifications
- ``refactor``: Code refactoring
- ``style``: Code style changes
- ``chore``: Build/maintenance tasks

4. Push and Create PR
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   git push origin feature/your-feature-name

Then create a Pull Request on GitHub with:
- Clear description of changes
- Link to related issues
- Screenshots for UI changes
- Performance impact notes

Types of Contributions
----------------------

Bug Reports
~~~~~~~~~~~

When reporting bugs, include:

- Python version and OS
- ToolUniverse version
- Minimal code to reproduce
- Full error traceback
- Expected vs actual behavior

Feature Requests
~~~~~~~~~~~~~~~~

For new features, provide:

- Clear use case description
- Proposed API design
- Implementation suggestions
- Impact on existing code

New Tools
~~~~~~~~~

When adding new scientific tools:

1. Research the data source thoroughly
2. Design a clean, consistent API
3. Implement comprehensive error handling
4. Add extensive tests and documentation
5. Include usage examples

Example new tool structure:

.. code-block:: python

   from tooluniverse.base_tool import BaseTool
   from typing import Dict, Any, List

   class NewScientificTool(BaseTool):
       """Tool for accessing [Data Source Name] API."""

       def __init__(self, config: Dict[str, Any] = None):
           super().__init__(config)
           self.base_url = self.config.get('base_url', 'https://api.example.com')

       def search_data(self, query: str, **kwargs) -> Dict[str, Any]:
           """Search for scientific data.

           Args:
               query: Search query
               **kwargs: Additional search parameters

           Returns:
               Search results with metadata
           """
           self.validate_input(query=query, **kwargs)
           return self._execute_search(query, **kwargs)

Documentation Improvements
~~~~~~~~~~~~~~~~~~~~~~~~~~

Help improve documentation by:

- Fixing typos and grammar
- Adding missing examples
- Clarifying confusing sections
- Translating to other languages
- Adding video tutorials

Review Process
--------------

All contributions go through code review:

1. **Automated Checks**: CI runs tests, linting, and type checking
2. **Manual Review**: Maintainers review code quality and design
3. **Documentation Review**: Ensure docs are clear and complete
4. **Testing**: Verify functionality works as expected

Review Criteria
~~~~~~~~~~~~~~~

- Code follows project standards
- Tests provide adequate coverage
- Documentation is complete and clear
- Performance impact is acceptable
- Breaking changes are justified

Getting Help
------------

Community Resources
~~~~~~~~~~~~~~~~~~~

- **GitHub Discussions**: General questions and ideas
- **GitHub Issues**: Bug reports and feature requests
- **Email**: Direct contact with maintainers

Maintainer Contact
~~~~~~~~~~~~~~~~~~

- **Shanghua Gao**: shanghuagao@gmail.com
- **GitHub**: @shanghuagao

Development Tips
----------------

Debugging
~~~~~~~~~

Use the built-in debugging features:

.. code-block:: python

   import logging
   logging.basicConfig(level=logging.DEBUG)

   # Enable tool debugging
   from tooluniverse import ToolUniverse
   tooluni = ToolUniverse()
   tooluni.load_tools()
   # Access specific tools through the registry for debugging

Testing API Changes
~~~~~~~~~~~~~~~~~~~

Test against multiple data sources:

.. code-block:: bash

   # Test against staging API
   export OPENTARGETS_BASE_URL=https://staging-api.opentargets.org
   pytest tests/test_graphql_tool.py

Performance Testing
~~~~~~~~~~~~~~~~~~~

Profile your changes:

.. code-block:: python

   import cProfile
   import pstats

   profiler = cProfile.Profile()
   profiler.enable()

   # Your code here

   profiler.disable()
   stats = pstats.Stats(profiler)
   stats.sort_stats('cumulative').print_stats(10)

Recognition
-----------

Contributors are recognized in:

- Release notes
- Contributors file
- Documentation acknowledgments
- Annual contributor highlights

Thank you for contributing to ToolUniverse! 
