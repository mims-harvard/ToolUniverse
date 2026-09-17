OrcaRouter Support
==================

ToolUniverse includes full support for OrcaRouter, allowing you to route chat
completions through OrcaRouter's gateway while keeping a single OpenAI-compatible
API. OrcaRouter also runs gateway-level, zero-trust security for AI agents on
the same endpoint.

Overview
--------

OrcaRouter provides access to models through:

* **Smart routing** — the ``orcarouter/auto`` model routes each request to the
  best-fit upstream model automatically.
* **Fusion family** — ``orcarouter/fusion``, ``orcarouter/fusion-flash``, and
  ``orcarouter/fusion-mini`` for large-context workloads.
* And many more via a single unified API.

Configuration
-------------

Environment Variables
^^^^^^^^^^^^^^^^^^^^^

To use OrcaRouter, set the following environment variables:

.. code-block:: bash

    # Required
    export ORCAROUTER_API_KEY="your_orcarouter_api_key_here"

    # Optional - override the gateway endpoint (defaults to https://api.orcarouter.ai/v1)
    export ORCAROUTER_BASE_URL="https://api.orcarouter.ai/v1"

Getting an API Key
^^^^^^^^^^^^^^^^^^

1. Visit `OrcaRouter <https://www.orcarouter.ai>`_
2. Sign up for an account
3. Navigate to the API Keys section
4. Generate a new API key
5. Copy and set it as the ``ORCAROUTER_API_KEY`` environment variable

Using OrcaRouter with AgenticTool
----------------------------------

Basic Configuration
^^^^^^^^^^^^^^^^^^^

Configure an AgenticTool to use OrcaRouter:

.. code-block:: python

    from tooluniverse import ToolUniverse
    from tooluniverse.agentic_tool import AgenticTool

    # Example tool configuration using OrcaRouter
    tool_config = {
        "name": "OrcaRouter_Summarizer",
        "description": "Summarize text using OrcaRouter models",
        "type": "AgenticTool",
        "prompt": "Summarize the following text:\n{text}",
        "input_arguments": ["text"],
        "parameter": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The text to summarize",
                    "required": True
                }
            },
            "required": ["text"]
        },
        "configs": {
            "api_type": "ORCAROUTER",
            "model_id": "orcarouter/auto",
            "temperature": 0.7,
            "return_json": False
        }
    }

    # Initialize ToolUniverse and register the tool
    tu = ToolUniverse()
    tu.register_custom_tool(AgenticTool, tool_config=tool_config)

    # Use the tool (requires ORCAROUTER_API_KEY)
    result = tu.run({"name": "OrcaRouter_Summarizer", "arguments": {
        "text": "Your long text here..."
    }})


Using OrcaRouter with ToolFinderLLM
------------------------------------

Configure ToolFinderLLM to use OrcaRouter models:

.. code-block:: python

    from tooluniverse import ToolUniverse
    from tooluniverse.tool_finder_llm import ToolFinderLLM

    # Create ToolUniverse instance
    tu = ToolUniverse()

    # Configure ToolFinderLLM with OrcaRouter
    tool_finder_config = {
        "type": "ToolFinderLLM",
        "name": "Tool_Finder_OrcaRouter",
        "description": "Find tools using OrcaRouter LLMs",
        "configs": {
            "api_type": "ORCAROUTER",
            "model_id": "orcarouter/auto",
            "temperature": 0.1,
            "max_new_tokens": 4096,
            "return_json": True,
            "exclude_tools": ["Tool_RAG", "Tool_Finder", "Finish"]
        }
    }

    # Register and use (requires ORCAROUTER_API_KEY)
    tu.register_custom_tool(ToolFinderLLM, tool_config=tool_finder_config)
    result = tu.run({"name": "Tool_Finder_OrcaRouter", "arguments": {
        "description": "tools for protein analysis",
        "limit": 5
    }})

Fallback Configuration
----------------------

You can include OrcaRouter in a custom fallback chain:

.. code-block:: python

    import os
    import json

    custom_chain = [
        {"api_type": "ORCAROUTER", "model_id": "orcarouter/auto"},
        {"api_type": "OPENROUTER", "model_id": "anthropic/claude-sonnet-4.5"},
        {"api_type": "GEMINI", "model_id": "gemini-2.5-flash"}
    ]

    os.environ["AGENTIC_TOOL_FALLBACK_CHAIN"] = json.dumps(custom_chain)

Advanced Configuration
----------------------

Custom Model Limits
^^^^^^^^^^^^^^^^^^^

Override default token limits for specific models:

.. code-block:: python

    import os
    import json

    custom_limits = {
        "orcarouter/auto": {
            "max_output": 32000,
            "context_window": 200000
        }
    }

    os.environ["ORCAROUTER_DEFAULT_MODEL_LIMITS"] = json.dumps(custom_limits)
