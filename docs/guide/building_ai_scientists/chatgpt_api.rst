ChatGPT API Setup
=================

**Build AI scientists with ChatGPT Function Calling**

ChatGPT API integration enables programmatic scientific research through OpenAI's function calling capabilities with ToolUniverse's 1000+ tools.

Prerequisites
-------------

.. important:: ✅ **What you need:**
   
   - **Python 3.10+**
   - **OpenAI API Key** - `Get key <https://platform.openai.com/api-keys>`_
   - **ToolUniverse** - ``pip install tooluniverse``
   - **OpenAI SDK** - ``pip install openai``

Setup Steps
-----------

.. card:: Step 1: Install Packages
   :class-card: step-card completed

   .. code-block:: bash

      pip install tooluniverse openai

.. card:: Step 2: Initialize ToolUniverse
   :class-card: step-card current

   .. code-block:: python

      import os
      import json
      import openai
      from tooluniverse import ToolUniverse

      # Initialize
      client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
      tu = ToolUniverse()
      tu.load_tools()

.. card:: Step 3: Convert Tools to OpenAI Format
   :class-card: step-card pending

   .. code-block:: python

      # Find relevant tools
      tools = tu.run({
          "name": "Tool_Finder_Keyword",
          "arguments": {"description": "protein", "limit": 5}
      })

      # Get tool specifications — format="openai" is required
      tool_specs = [tu.tool_specification(t['name'], format="openai") for t in tools]

      # Convert to OpenAI function format
      functions = [
          {
              "name": spec['name'],
              "description": spec['description'],
              "parameters": spec['parameters']
          }
          for spec in tool_specs
      ]

   .. note::
      Always pass ``format="openai"`` to :meth:`tool_specification`. Without it,
      the returned schema contains boolean ``required`` flags that are not valid
      JSON Schema and will cause OpenAI to reject the request with
      *"True is not of type 'array'"*.

.. card:: Step 4: Create Chat Loop
   :class-card: step-card pending

   .. code-block:: python

      messages = [{"role": "user", "content": "Find protein P05067"}]

      response = client.chat.completions.create(
          model="gpt-4o-mini",
          messages=messages,
          functions=functions,
          function_call="auto"
      )

      # If ChatGPT calls a function
      if response.choices[0].message.function_call:
          function_name = response.choices[0].message.function_call.name
          arguments = json.loads(
              response.choices[0].message.function_call.arguments
          )

          # Execute with ToolUniverse
          result = tu.run({
              "name": function_name,
              "arguments": arguments
          })

.. card:: Step 5: Complete the Loop
   :class-card: step-card pending

   .. code-block:: python

      # Add function result to conversation
      messages.append({
          "role": "assistant",
          "content": None,
          "function_call": {
              "name": function_name,
              "arguments": response.choices[0].message.function_call.arguments
          }
      })
      messages.append({
          "role": "function",
          "name": function_name,
          "content": json.dumps(result)
      })

      # Get final response
      final_response = client.chat.completions.create(
          model="gpt-4o-mini",
          messages=messages
      )

      print(final_response.choices[0].message.content)

Complete Example
----------------

.. code-block:: python

   import os
   import json
   import openai
   from tooluniverse import ToolUniverse

   # Setup
   client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
   tu = ToolUniverse()
   tu.load_tools()

   def chat_with_tools(user_query: str):
       """Chat with ChatGPT using ToolUniverse tools."""

       # Find relevant tools
       tools = tu.run({
           "name": "Tool_Finder_LLM",
           "arguments": {"description": user_query, "limit": 10}
       })

       # Get tool specs — format="openai" required for valid schemas
       functions = []
       for tool in tools:
           spec = tu.tool_specification(tool['name'], format="openai")
           if spec is None:
               continue
           functions.append({
               "name": spec['name'],
               "description": spec['description'],
               "parameters": spec['parameters']
           })

       # Initialize conversation
       messages = [{"role": "user", "content": user_query}]

       while True:
           response = client.chat.completions.create(
               model="gpt-4o-mini",
               messages=messages,
               functions=functions,
               function_call="auto"
           )

           message = response.choices[0].message

           # If no function call, we're done
           if not message.function_call:
               return message.content

           # Execute function
           function_name = message.function_call.name
           arguments = json.loads(message.function_call.arguments)

           result = tu.run({
               "name": function_name,
               "arguments": arguments
           })

           # Add to conversation
           messages.append({
               "role": "assistant",
               "content": None,
               "function_call": {
                   "name": function_name,
                   "arguments": message.function_call.arguments
               }
           })
           messages.append({
               "role": "function",
               "name": function_name,
               "content": json.dumps(result)
           })

   # Use it
   result = chat_with_tools("Find therapeutic targets for Alzheimer's disease")
   print(result)

Advanced Patterns
-----------------

.. dropdown:: 🔄 Dynamic Tool Loading
   :animate: fade-in-slide-down
   :color: primary

   Load tools dynamically based on the query:

   .. code-block:: python

      def get_relevant_tools(query: str):
          """Find and load only relevant tools."""
          tools = tu.run({
              "name": "Tool_Finder_LLM",
              "arguments": {"description": query, "limit": 10}
          })
          specs = []
          for t in tools:
              spec = tu.tool_specification(t['name'], format="openai")
              if spec is not None:
                  specs.append(spec)
          return specs

.. dropdown:: 🛠️ Modern Tools API (Recommended)
   :animate: fade-in-slide-down
   :color: success

   OpenAI now recommends the ``tools`` parameter over the deprecated ``functions``
   parameter. Both work, but new code should prefer ``tools``:

   .. code-block:: python

      # Build tools list in the modern format
      tools_list = [
          {"type": "function", "function": {
              "name": spec['name'],
              "description": spec['description'],
              "parameters": spec['parameters']
          }}
          for spec in tool_specs
      ]

      response = client.chat.completions.create(
          model="gpt-4o-mini",
          messages=messages,
          tools=tools_list,
          tool_choice="auto"
      )

      # Handle tool calls (note: tool_calls is a list, not a single function_call)
      if response.choices[0].message.tool_calls:
          tc = response.choices[0].message.tool_calls[0]
          function_name = tc.function.name
          arguments = json.loads(tc.function.arguments)

          result = tu.run({"name": function_name, "arguments": arguments})

          messages.append(response.choices[0].message)
          messages.append({
              "role": "tool",
              "tool_call_id": tc.id,
              "content": json.dumps(result)
          })

.. dropdown:: 📊 Batch Processing
   :animate: fade-in-slide-down
   :color: info

   Process multiple queries in batch:

   .. code-block:: python

      queries = [
          "Find protein P05067",
          "Search for CRISPR papers",
          "Get disease targets for diabetes"
      ]

      results = [chat_with_tools(q) for q in queries]

Troubleshooting
---------------

.. dropdown:: ❌ Schema error: "True is not of type 'array'"
   :color: danger

   This error means tool schemas are being sent to OpenAI without the
   ``format="openai"`` conversion:

   .. code-block:: text

      openai.BadRequestError: Invalid schema for function 'MyTool':
      True is not of type 'array'.

   **Fix:** always pass ``format="openai"`` to :meth:`tool_specification`:

   .. code-block:: python

      # ✗ Wrong — sends required:True/False flags that OpenAI rejects
      spec = tu.tool_specification(tool_name)

      # ✓ Correct — sanitizes the schema for OpenAI
      spec = tu.tool_specification(tool_name, format="openai")

.. dropdown:: ❌ Rate limit errors
   :color: danger

   Add delays between requests:

   .. code-block:: python

      import time
      time.sleep(1)  # Between API calls

.. dropdown:: ❌ Context length exceeded
   :color: danger

   Some scientific tools return large payloads. If the tool result exceeds
   the model's context window, summarize or truncate it before appending:

   .. code-block:: python

      # Truncate tool result to avoid context overflow
      result_str = json.dumps(result)
      if len(result_str) > 8000:
          result_str = result_str[:8000] + "... [truncated]"

      messages.append({
          "role": "function",
          "name": function_name,
          "content": result_str
      })

.. dropdown:: ⚠️ Function call timeout
   :color: warning

   Use streaming for long-running tools:

   .. code-block:: python

      response = client.chat.completions.create(
          model="gpt-4o-mini",
          messages=messages,
          functions=functions,
          stream=True
      )

Next Steps
----------

.. button-ref:: index
   :color: secondary
   :shadow:
   :expand:

   ← **Back to Platform Selector**

.. seealso::
   - :doc:`../scientific_workflows` - Build complex workflows
   - :doc:`../../api/modules` - Full API reference
   - :doc:`../../help/troubleshooting` - Common issues
