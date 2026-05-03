Python Executor Tools
=====================

**Configuration File**: ``python_executor_tools.json``
**Tool Type**: Local
**Tools Count**: 2

This page contains all tools defined in the ``python_executor_tools.json`` configuration file.

Available Tools
---------------

**python_code_executor** (Type: PythonCodeExecutor)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Execute Python code snippets safely in sandboxed environment with timeout and resource limits. Su...

.. dropdown:: python_code_executor tool specification

   **Tool Information:**

   * **Name**: ``python_code_executor``
   * **Type**: ``PythonCodeExecutor``
   * **Description**: Execute Python code snippets safely in sandboxed environment with timeout and resource limits. Supports variable passing and result extraction.

   **Parameters:**

   * ``code`` (string) (required)
     Python code to execute. Can use variables from 'arguments' parameter. Use 'result = ...' to return values.

   * ``arguments`` (object) (optional)
     Variables to pass into execution environment as dictionary. Keys become variable names in the code.

   * ``timeout`` (integer) (optional)
     Execution timeout in seconds

   * ``return_variable`` (string) (optional)
     Variable name to extract as result from the executed code

   * ``allowed_imports`` (array) (optional)
     Additional allowed modules beyond the default safe set (math, json, datetime, etc.)

   * ``dependencies`` (array) (optional)
     List of Python packages that the code depends on. Will be checked and optionally installed before execution.

   * ``auto_install_dependencies`` (boolean) (optional)
     Whether to automatically install missing dependencies without user confirmation

   * ``require_confirmation`` (boolean) (optional)
     Whether to require user confirmation before installing packages

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "python_code_executor",
          "arguments": {
              "code": "example_value"
          }
      }
      result = tu.run(query)


**python_script_runner** (Type: PythonScriptRunner)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run Python script files in isolated subprocess with resource limits and timeout. Supports command...

.. dropdown:: python_script_runner tool specification

   **Tool Information:**

   * **Name**: ``python_script_runner``
   * **Type**: ``PythonScriptRunner``
   * **Description**: Run Python script files in isolated subprocess with resource limits and timeout. Supports command-line arguments and environment variables.

   **Parameters:**

   * ``script_path`` (string) (required)
     Path to Python script file (.py) to execute

   * ``script_args`` (array) (optional)
     Command-line arguments to pass to the script

   * ``timeout`` (integer) (optional)
     Execution timeout in seconds

   * ``working_directory`` (string) (optional)
     Working directory for script execution (defaults to script directory)

   * ``env_vars`` (object) (optional)
     Environment variables to set for script execution

   * ``dependencies`` (array) (optional)
     List of Python packages that the script depends on. Will be checked and optionally installed before execution.

   * ``auto_install_dependencies`` (boolean) (optional)
     Whether to automatically install missing dependencies without user confirmation

   * ``require_confirmation`` (boolean) (optional)
     Whether to require user confirmation before installing packages

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "python_script_runner",
          "arguments": {
              "script_path": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
