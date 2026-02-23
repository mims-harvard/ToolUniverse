vLLM Support
=============

ToolUniverse supports vLLM for self-hosted LLM inference. Use vLLM to run models on your own infrastructure for better privacy, cost control, and performance.

Quick Start
-----------

1. **Start a vLLM server**:

.. code-block:: bash

    pip install vllm
    vllm serve meta-llama/Llama-3.1-8B-Instruct

2. **Set environment variables**:

.. code-block:: bash

    export VLLM_SERVER_URL="http://localhost:8000"
    export TOOLUNIVERSE_LLM_DEFAULT_PROVIDER="VLLM"
    export TOOLUNIVERSE_LLM_MODEL_DEFAULT="meta-llama/Llama-3.1-8B-Instruct"

3. **Use with AgenticTool**:

.. code-block:: python

    from tooluniverse import ToolUniverse
    from tooluniverse.agentic_tool import AgenticTool
    
    tool_config = {
        "name": "Summarizer",
        "type": "AgenticTool",
        "prompt": "Summarize: {text}",
        "input_arguments": ["text"],
        "parameter": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"]
        }
    }
    
    # Requires VLLM_SERVER_URL and TOOLUNIVERSE_LLM_DEFAULT_PROVIDER=VLLM
    tu = ToolUniverse()
    tu.register_custom_tool(AgenticTool, tool_config=tool_config)
    result = tu.run({"name": "Summarizer", "arguments": {"text": "Your text here"}})

Configuration
-------------

Environment Variables
^^^^^^^^^^^^^^^^^^^^^

Required:
- ``VLLM_SERVER_URL``: Your vLLM server URL (e.g., ``http://localhost:8000``)

Optional:
- ``TOOLUNIVERSE_LLM_DEFAULT_PROVIDER="VLLM"``: Set vLLM as default
- ``TOOLUNIVERSE_LLM_MODEL_DEFAULT="model-name"``: Default model (must match vLLM server)
- ``TOOLUNIVERSE_LLM_CONFIG_MODE="env_override"``: Make env vars override tool configs

Tool Configuration
^^^^^^^^^^^^^^^^^^^

You can also configure vLLM directly in tool configs:

.. code-block:: python

    tool_config = {
        "name": "MyTool",
        "type": "AgenticTool",
        # ... prompt and parameters ...
        "configs": {
            "api_type": "VLLM",
            "model_id": "meta-llama/Llama-3.1-8B-Instruct",
            "temperature": 0.7
        }
    }

**Note**: Still requires ``VLLM_SERVER_URL`` environment variable.

Using with Space Configurations
--------------------------------

In Space YAML files:

.. code-block:: yaml

    llm_config:
      mode: "env_override"
      default_provider: "VLLM"
      models:
        default: "meta-llama/Llama-3.1-8B-Instruct"

Then set: ``export VLLM_SERVER_URL="http://localhost:8000"``

Configuration Priority
----------------------

With ``env_override`` mode:
1. Environment variables (highest)
2. Tool configuration
3. Space configuration
4. Built-in defaults

Troubleshooting
---------------

**"VLLM_SERVER_URL environment variable not set"**
    Set the environment variable: ``export VLLM_SERVER_URL="http://localhost:8000"``

**"Model not found"**
    Ensure ``model_id`` matches the model name loaded on your vLLM server

**Connection failed**
    Verify vLLM server is running: ``curl http://localhost:8000/health`` (if available)

**URL format**: Use base URL (e.g., ``http://localhost:8000``). ToolUniverse automatically appends ``/v1``.

Test Your Setup
---------------

.. code-block:: python

    from tooluniverse.agentic_tool import AgenticTool
    import os
    
    os.environ["VLLM_SERVER_URL"] = "http://localhost:8000"
    
    tool = AgenticTool({
        "name": "test",
        "prompt": "Say hello",
        "input_arguments": [],
        "parameter": {"type": "object", "properties": {}, "required": []},
        "configs": {
            "api_type": "VLLM",
            "model_id": "meta-llama/Llama-3.1-8B-Instruct"
        }
    })
    
    if tool.is_available():
        print("✅ vLLM connection successful!")
    else:
        print(f"❌ Failed: {tool.get_availability_status()}")

See Also
--------

* :doc:`openrouter_support` - Using OpenRouter as an LLM provider
* :doc:`toolspace` - Space configurations with LLM settings
* :doc:`agentic_tools_tutorial` - Complete guide to creating agentic tools
