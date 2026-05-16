OpenCode
========

- `Download OpenCode <https://opencode.ai/>`_
- `Official MCP setup guide <https://opencode.ai/docs/mcp-servers/>`_

To set up ToolUniverse, open OpenCode and run:

.. code-block:: text

   Read https://aiscientist.tools/setup.md and set up ToolUniverse for me.

Manual MCP configuration
------------------------

If you prefer to configure the MCP server manually, add ToolUniverse as a stdio
server that runs the ``tooluniverse`` command through ``uvx``:

.. code-block:: json

   {
     "mcp": {
       "tooluniverse": {
         "type": "local",
         "command": ["uvx", "--refresh", "tooluniverse"]
       }
     }
   }

After saving the configuration, restart OpenCode and ask it to list available
ToolUniverse tools.
