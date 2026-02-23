OpenRouter Support
==================

ToolUniverse now includes full support for OpenRouter, allowing you to access a wide variety of LLM models from multiple providers through a single, unified API.

Overview
--------

OpenRouter provides access to models from:

* **OpenAI** (GPT-5)
* **Anthropic** (Claude Sonnet 4.5)
* **Google** (Gemini 2.5 Flash, Gemini 2.5 Pro)
* And many more!

Configuration
-------------

Environment Variables
^^^^^^^^^^^^^^^^^^^^^

To use OpenRouter, set the following environment variables:

.. code-block:: bash

    # Required
    export OPENROUTER_API_KEY="your_openrouter_api_key_here"
    
    # Optional - for usage tracking and attribution
    export OPENROUTER_SITE_URL="https://your-site.com"
    export OPENROUTER_SITE_NAME="Your Application Name"

Getting an API Key
^^^^^^^^^^^^^^^^^^

1. Visit `OpenRouter <https://openrouter.ai/>`_
2. Sign up for an account
3. Navigate to the API Keys section
4. Generate a new API key
5. Copy and set it as the ``OPENROUTER_API_KEY`` environment variable

Using OpenRouter with AgenticTool
----------------------------------

Basic Configuration
^^^^^^^^^^^^^^^^^^^

Configure an AgenticTool to use OpenRouter:

.. code-block:: python

    from tooluniverse import ToolUniverse
    from tooluniverse.agentic_tool import AgenticTool
    
    # Example tool configuration using OpenRouter
    tool_config = {
        "name": "OpenRouter_Summarizer",
        "description": "Summarize text using OpenRouter models",
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
            "api_type": "OPENROUTER",
            "model_id": "openai/gpt-5",
            "temperature": 0.7,
            "return_json": False
        }
    }
    
    # Initialize ToolUniverse and register the tool
    tu = ToolUniverse()
    tu.register_custom_tool(AgenticTool, tool_config=tool_config)
    
    # Use the tool (requires OPENROUTER_API_KEY)
    result = tu.run({"name": "OpenRouter_Summarizer", "arguments": {
        "text": "Your long text here..."
    }})


Using OpenRouter with ToolFinderLLM
------------------------------------

Configure ToolFinderLLM to use OpenRouter models:

.. code-block:: python

    from tooluniverse import ToolUniverse
    from tooluniverse.tool_finder_llm import ToolFinderLLM
    
    # Create ToolUniverse instance
    tu = ToolUniverse()
    
    # Configure ToolFinderLLM with OpenRouter
    tool_finder_config = {
        "type": "ToolFinderLLM",
        "name": "Tool_Finder_OpenRouter",
        "description": "Find tools using OpenRouter LLMs",
        "configs": {
            "api_type": "OPENROUTER",
            "model_id": "anthropic/claude-sonnet-4.5",
            "temperature": 0.1,
            "max_new_tokens": 4096,
            "return_json": True,
            "exclude_tools": ["Tool_RAG", "Tool_Finder", "Finish"]
        }
    }
    
    # Register and use (requires OPENROUTER_API_KEY)
    tu.register_custom_tool(ToolFinderLLM, tool_config=tool_finder_config)
    result = tu.run({"name": "Tool_Finder_OpenRouter", "arguments": {
        "description": "tools for protein analysis",
        "limit": 5
    }})

Fallback Configuration
----------------------

OpenRouter is included in the default fallback chain. If the primary API fails, the system will automatically try OpenRouter:

.. code-block:: python

    # Default fallback chain (in order):
    # 1. CHATGPT (Azure OpenAI)
    # 2. OPENROUTER (with openai/gpt-5)
    # 3. GEMINI (Google Gemini)
    
    # You can customize the fallback chain with environment variable:
    import os
    import json
    
    custom_chain = [
        {"api_type": "OPENROUTER", "model_id": "anthropic/claude-sonnet-4.5"},
        {"api_type": "OPENROUTER", "model_id": "openai/gpt-5"},
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
        "openai/gpt-5": {
            "max_output": 32000,  # Custom limit
            "context_window": 1048576
        },
        "anthropic/claude-sonnet-4.5": {
            "max_output": 4096,
            "context_window": 200000
        }
    }
    
    os.environ["OPENROUTER_DEFAULT_MODEL_LIMITS"] = json.dumps(custom_limits)
