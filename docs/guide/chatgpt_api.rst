ChatGPT API
===========

Use ToolUniverse with the `OpenAI Python SDK <https://platform.openai.com/docs/guides/function-calling>`_ to call scientific tools as functions.

- `OpenAI platform <https://platform.openai.com>`_ (requires API key)
- `OpenAI function calling guide <https://platform.openai.com/docs/guides/function-calling>`_

Quick setup
-----------

Install ToolUniverse and the OpenAI SDK:

.. code-block:: bash

   pip install tooluniverse openai

Example
-------

Uses the OpenAI Chat Completions API with dynamic tool discovery via ``Tool_Finder``.

.. code-block:: python

   import json
   import openai
   from tooluniverse import ToolUniverse

   tu = ToolUniverse()
   tu.load_tools()

   client = openai.OpenAI(api_key="your-api-key")

   # Get tool schemas in OpenAI format.
   # format="openai" returns {"name": ..., "description": ..., "parameters": {...}}
   # Chat Completions expects these nested under "function"
   specs = tu.get_tool_specification_by_names(["Tool_Finder"], format="openai")
   tools = [{"type": "function", "function": spec} for spec in specs]

   messages = [{"role": "user", "content": "What are the side effects of metformin?"}]

   for _ in range(10):
       resp = client.chat.completions.create(
           model="gpt-4o",
           messages=messages,
           tools=tools,
           tool_choice="auto",
       )
       msg = resp.choices[0].message
       messages.append(msg)

       if not msg.tool_calls:
           print(msg.content)
           break

       for tc in msg.tool_calls:
           name = tc.function.name
           args = json.loads(tc.function.arguments)

           result = tu.run({"name": name, "arguments": args})

           # If Tool_Finder returned tool names, add those tools for subsequent turns
           if name == "Tool_Finder":
               new_names = [t["name"] for t in result][:8]
               new_specs = tu.get_tool_specification_by_names(new_names, format="openai")
               tools += [{"type": "function", "function": s} for s in new_specs]

           messages.append({
               "role": "tool",
               "tool_call_id": tc.id,
               "content": json.dumps(result, ensure_ascii=False),
           })

For AI agent setup with ChatGPT, use the :doc:`building_ai_scientists/index` guide instead.
