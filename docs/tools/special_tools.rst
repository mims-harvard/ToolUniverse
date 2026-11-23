Special Tools
=============

**Configuration File**: ``special_tools.json``
**Tool Type**: Local
**Tools Count**: 3

This page contains all tools defined in the ``special_tools.json`` configuration file.

Available Tools
---------------

**CallAgent** (Type: SpecialTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Control signal, not an executable tool: raise it to hand a solution plan back to your own agent l...

.. dropdown:: CallAgent tool specification

   **Tool Information:**

   * **Name**: ``CallAgent``
   * **Type**: ``SpecialTool``
   * **Description**: Control signal, not an executable tool: raise it to hand a solution plan back to your own agent loop, which is responsible for executing it. ToolUniverse does not run a sub-agent and does not act on the plan -- it echoes it back. Each plan should reflect a distinct method, approach, or viewpoint; raise the signal several times with plans that start from different aspects of the question, for example genes, phenotypes, diseases, or drugs. Give only the plan, not unverified information.

   **Parameters:**

   * ``solution`` (string) (required)
     A feasible and concise solution plan that address the question.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "CallAgent",
          "arguments": {
              "solution": "example_value"
          }
      }
      result = tu.run(query)


**Finish** (Type: SpecialTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Control signal, not an executable tool: raise it to tell your own multi-step reasoning loop that ...

.. dropdown:: Finish tool specification

   **Tool Information:**

   * **Name**: ``Finish``
   * **Type**: ``SpecialTool``
   * **Description**: Control signal, not an executable tool: raise it to tell your own multi-step reasoning loop that the chain is complete. ToolUniverse queries nothing and returns no data -- it echoes the signal back for your loop to act on.

   **Parameters:**

   No parameters required.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "Finish",
          "arguments": {
          }
      }
      result = tu.run(query)


**ToolUniverse_get_usage_tips** (Type: UsageTipsTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Return concise usage tips for the ToolUniverse SDK. Use topic='all' (default) to get all tips, or...

.. dropdown:: ToolUniverse_get_usage_tips tool specification

   **Tool Information:**

   * **Name**: ``ToolUniverse_get_usage_tips``
   * **Type**: ``UsageTipsTool``
   * **Description**: Return concise usage tips for the ToolUniverse SDK. Use topic='all' (default) to get all tips, or specify a topic: 'loading', 'running', 'searching', 'workspace'. No API keys or network access required — always available offline.

   **Parameters:**

   * ``topic`` (string) (optional)
     Topic to filter tips. One of: 'loading', 'running', 'searching', 'workspace', or 'all' (default) to return every topic.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "ToolUniverse_get_usage_tips",
          "arguments": {
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
