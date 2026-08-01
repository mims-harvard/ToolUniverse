OpenAI-Compatible Provider Support
==================================

ToolUniverse agentic tools support a generic ``OPENAI`` provider backed by the
OpenAI Python SDK. Use it for OpenAI directly or for OpenAI-compatible hosted
endpoints.

Configuration
-------------

Set an API key:

.. code-block:: bash

   export OPENAI_API_KEY=your_key_here

For OpenAI-compatible endpoints, also set a base URL:

.. code-block:: bash

   export OPENAI_BASE_URL=https://your-provider.example/v1

Then configure an agentic tool with ``api_type: "OPENAI"``:

.. code-block:: json

   {
     "name": "openai_compatible_reasoning_tool",
     "type": "AgenticTool",
     "prompt": "Answer this question: {question}",
     "input_arguments": ["question"],
     "api_type": "OPENAI",
     "model_id": "gpt-4o-mini",
     "parameter": {
       "type": "object",
       "properties": {
         "question": {"type": "string"}
       },
       "required": ["question"]
     }
   }

Environment Variables
---------------------

``OPENAI_API_KEY``
   Required API key for the selected endpoint.

``OPENAI_BASE_URL``
   Optional OpenAI-compatible API base URL. If unset, the OpenAI SDK default is
   used.

``OPENAI_MAX_TOKENS_BY_MODEL``
   Optional JSON mapping of model ID or model prefix to default max output
   tokens. Example: ``{"gpt-4o": 4096}``.

``OPENAI_DEFAULT_MODEL_LIMITS``
   Optional JSON mapping that extends or overrides ToolUniverse's built-in
   model-family defaults.

Provider Notes
--------------

Use ``OPENAI`` for OpenAI-compatible chat completions endpoints. Use
``OPENROUTER`` when you want OpenRouter-specific headers and model naming, and
use ``VLLM`` for self-hosted vLLM servers.
