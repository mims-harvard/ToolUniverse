Streaming Tools Tutorial
========================

.. contents:: Table of Contents
   :local:
   :depth: 2

What Is Streaming Mode?
-----------------------

*Streaming* lets a tool send partial results back to the caller while the task
is still running. Instead of waiting for the entire response, the caller receives
chunks (text fragments, structured updates, etc.) in real time. This is useful
when:

* Responses are long or detailed and you want early insight
* The user interface (CLI, notebook, MCP client) benefits from progressive
  updates
* You plan to pipe each chunk into another system (logging, partial rendering,
  incremental processing)

All tools built on :class:`AgenticTool` already support streaming. Other tool
types can opt in by following the instructions in
:ref:`building-custom-streaming-tools`.

Streaming Built-in Agentic Tools
--------------------------------

The ToolUniverse distribution ships with many Agentic tools, such as
``ScientificTextSummarizer`` (defined in ``agentic_tools.json``). The snippet
below shows how to run it with a streaming callback using
``ToolUniverse.run``:

.. code-block:: python

   from tooluniverse.execute_function import ToolUniverse
   import json

   tu = ToolUniverse()
   tu.load_tools(include_tools=["ScientificTextSummarizer"])

   chunks = []

   def on_chunk(text: str) -> None:
       chunks.append(text)
       print(text, end="", flush=True)

   fcall = json.dumps(
       {
           "name": "ScientificTextSummarizer",
           "arguments": {
               "text": "Long paper...",
               "summary_length": "100",
               "focus_area": "results",
           },
       }
   )

   result = tu.run(
       fcall,
       return_message=False,
       verbose=False,
       stream_callback=on_chunk,
   )

   print("\nFinal result:\n", result)

Key points:

* Passing ``stream_callback`` tells ToolUniverse that the caller can accept
  streamed chunks.
* ``ToolUniverse.run`` accepts the same JSON structure used by MCP calls. When a
  callback is present the framework automatically sets
  ``AgenticTool.STREAM_FLAG_KEY`` in the argument dict so AgenticTool knows
  streaming was requested.
* If the callback is omitted the tool still works—it simply returns one final
  string.

The streaming demonstration script ``examples/agentic_streaming_example.py``
wraps the same logic with a longer prompt so chunks are visually obvious.

.. _building-custom-streaming-tools:

Building Your Own Streaming Tool
--------------------------------

Any custom tool can opt into streaming with three small changes:

1. **Declare a flag key** on the class so ToolUniverse knows which argument to
   populate when a callback is provided.

   .. code-block:: python

      class MyStreamingTool(BaseTool):
          STREAM_FLAG_KEY = "_tooluniverse_stream"

2. **Accept ``stream_callback`` in ``run`` and forward chunks.** Remove the flag
   from the argument dict before downstream validation.

   .. code-block:: python

      from typing import Callable, Optional

      class MyStreamingTool(BaseTool):
          STREAM_FLAG_KEY = "_tooluniverse_stream"

          def run(
              self,
              arguments: dict,
              stream_callback: Optional[Callable[[str], None]] = None,
          ):
              arguments = dict(arguments)
              stream_enabled = bool(arguments.pop(self.STREAM_FLAG_KEY, False))

              if stream_enabled and stream_callback:
                  for chunk in self.generate_chunks(arguments):
                      stream_callback(chunk)
                  return "".join(self.generate_chunks(arguments))

              return self.run_without_streaming(arguments)

   If the tool cannot deliver chunks for some reason, fall back to your
   non-streaming path (as AgenticTool does).

3. **Optional** – document the flag in the tool's schema if external callers
   should be able to toggle streaming without relying on ``stream_callback``.

Testing
-------

Use the existing test suites as references when adding streaming support:

* ``tests/test_streaming_support.py`` – Unit tests covering callback injection
  and automatic flag handling.
* ``tests/test_agentic_streaming_integration.py`` – Integration tests covering
  AgenticTool streaming and SMCP log propagation.

Run them with:

.. code-block:: bash

   pytest tests/test_streaming_support.py tests/test_agentic_streaming_integration.py
