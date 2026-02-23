====================================
Agentic Tools Tutorial
====================================

**Learn to build and use AI-powered tools in ToolUniverse**

What You'll Learn
=================

By the end of this tutorial, you'll be able to:

✅ Understand what agentic tools are and when to use them
✅ Create your own agentic tool from scratch
✅ Configure LLM settings for optimal performance
✅ Load and execute agentic tools in your workflows
✅ Handle errors and troubleshoot common issues

What are Agentic Tools?
=======================

**Agentic Tools** are AI-powered tools that use Large Language Models (LLMs) to perform tasks requiring human-like reasoning, analysis, and creativity. Unlike traditional computational tools that follow fixed algorithms, agentic tools use natural language prompts to Tutorial AI models.

**Perfect for**: Text analysis, research synthesis, creative writing, code review, hypothesis generation

**Not suitable for**: Mathematical calculations, API calls, file processing, deterministic algorithms

Step 1: Understand the Components
=================================

Every agentic tool has 5 essential parts:

1️⃣ **Tool Metadata**
   - Name and description
   - Tool type identifier

2️⃣ **Prompt Template**
   - Natural language instructions
   - Placeholders for user inputs

3️⃣ **Input Parameters**
   - What users need to provide
   - Validation rules and descriptions

4️⃣ **LLM Configuration**
   - Which AI model to use
   - Settings like temperature and response length

5️⃣ **Response Handling**
   - Text or structured JSON output
   - Metadata about execution

Step 2: Choose Your LLM Provider
================================

ToolUniverse supports these AI providers:

**OpenAI/Azure OpenAI**
   - Models: GPT-4, GPT-4o, o1-mini, o1-preview
   - Configuration: Set ``AZURE_OPENAI_API_KEY`` and ``AZURE_OPENAI_ENDPOINT``

**Google Gemini**
   - Models: Gemini 2.0 Flash, Gemini 2.5 Pro
   - Configuration: Set ``GEMINI_API_KEY``

**OpenRouter**
   - Access to multiple providers through one API
   - Models: GPT-5, Claude Sonnet 4.5, and more
   - Configuration: Set ``OPENROUTER_API_KEY``
   - See :doc:`../guide/openrouter_support` for details

**vLLM (Self-Hosted)**
   - Run models on your own infrastructure
   - Models: Any model supported by vLLM (Llama, Mistral, Qwen, etc.)
   - Configuration: Set ``VLLM_SERVER_URL``
   - See :doc:`../guide/openrouter_support` for LLM provider configuration


Step 3: Create Your First Tool
==============================

Let's build a scientific text summarizer step by step.

3.1 Start with the Basic Structure
----------------------------------

Create a JSON file with this foundation:

.. code-block:: json

   {
       "type": "AgenticTool",
       "name": "",
       "description": "",
       "prompt": "",
       "input_arguments": [],
       "parameter": {},
       "configs": {}
   }

3.2 Add Tool Identification
---------------------------

Fill in the basic tool information:

.. code-block:: json

   {
       "type": "AgenticTool",
       "name": "ScientificTextSummarizer",
       "description": "Summarizes biomedical research texts with specified length and focus areas"
   }

3.3 Design Your Prompt
----------------------

Create instructions for the AI with placeholders for user inputs:

.. code-block:: json

   {
       "prompt": "You are a biomedical expert. Please summarize the following biomedical text in {summary_length} words, focusing on {focus_area}:\n\n{text}\n\nProvide a clear, concise summary that captures the most important information."
   }

**Key Tips**:
- Use descriptive placeholders: ``{text}``, ``{summary_length}``
- Give specific output instructions

3.4 Define Input Parameters
---------------------------

List what users need to provide:

.. code-block:: json

   {
       "input_arguments": ["text", "summary_length", "focus_area"]
   }

3.5 Create Parameter Schema
---------------------------

Define validation rules and descriptions:

.. code-block:: json

   {
       "parameter": {
           "type": "object",
           "properties": {
               "text": {
                   "type": "string",
                   "description": "The biomedical text, abstract, or paper content to be summarized",
                   "required": true
               },
               "summary_length": {
                   "type": "string",
                   "description": "Desired length (e.g., '50', '100', '200 words')",
                   "required": true
               },
               "focus_area": {
                   "type": "string",
                   "description": "What to focus on (e.g., 'methodology', 'results', 'clinical implications')",
                   "required": true
               }
           },
           "required": ["text", "summary_length", "focus_area"]
       }
   }

3.6 Configure the LLM
---------------------

Set up AI model settings:

.. code-block:: json

   {
       "configs": {
           "api_type": "CHATGPT",
           "model_id": "o4-mini-0416",
           "temperature": 1.0,
           "return_json": false
       }
   }

**Configuration Options**:

- ``api_type``: "CHATGPT", "GEMINI", "OPENROUTER", or "VLLM"
- ``model_id``: Choose your model (see Step 2)
  - For vLLM: Must match the model name loaded on your vLLM server
  - Set ``VLLM_SERVER_URL`` environment variable when using vLLM
- ``temperature``: 0.0-2.0 (higher = more creative)
- ``return_json``: true for structured data, false for text

**Using vLLM**: Set ``api_type: "VLLM"`` and ensure ``VLLM_SERVER_URL`` is set. See :doc:`../guide/vllm_support` for complete setup guide.

3.7 Complete Tool Example
-------------------------

Here's your finished tool:

.. code-block:: json

   {
       "type": "AgenticTool",
       "name": "ScientificTextSummarizer",
       "description": "Summarizes biomedical research texts with specified length and focus areas",
       "prompt": "You are a biomedical expert. Please summarize the following biomedical text in {summary_length} words, focusing on {focus_area}:\n\n{text}\n\nProvide a clear, concise summary that captures the most important information.",
       "input_arguments": ["text", "summary_length", "focus_area"],
       "parameter": {
           "type": "object",
           "properties": {
               "text": {
                   "type": "string",
                   "description": "The biomedical text, abstract, or paper content to be summarized",
                   "required": true
               },
               "summary_length": {
                   "type": "string",
                   "description": "Desired length (e.g., '50', '100', '200 words')",
                   "required": true
               },
               "focus_area": {
                   "type": "string",
                   "description": "What to focus on (e.g., 'methodology', 'results', 'clinical implications')",
                   "required": true
               }
           },
           "required": ["text", "summary_length", "focus_area"]
       },
       "configs": {
           "api_type": "CHATGPT",
           "model_id": "o4-mini-0416",
           "temperature": 1.0,
           "return_json": false
       }
   }

Step 4: Save Your Tool
======================

4.1 Save as JSON File
---------------------

Save your tool configuration as a `.json` file:

.. code-block:: bash

   # Create directory for your tools
   mkdir my_tools
   cd my_tools

Then create `scientific_summarizer.json` and paste your complete tool configuration from Step 3.7:

.. code-block:: bash

   # The file should contain the complete JSON from Step 3.7
   # scientific_summarizer.json
   {
       "type": "AgenticTool",
       "name": "ScientificTextSummarizer",
       ...
   }

4.2 Important Notes
--------------------

**Key Point**: When loading from custom config files, you need to specify which tools to actually load using `include_tools` parameter.

The config file only makes tools *available* - you still need to tell ToolUniverse which specific tools to load from that file.

**Alternative**: Add to Built-in Collection
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can also add your tool to ToolUniverse's built-in agentic tools collection:

.. code-block:: bash

   # Add your tool to the main agentic tools file
   src/tooluniverse/data/agentic_tools.json

Step 5: Use Your Tool
=====================

5.1 Set Up Environment
----------------------

First, ensure you have API keys configured:

.. code-block:: bash

   # For OpenAI/Azure OpenAI
   export AZURE_OPENAI_API_KEY_GPT4O="your-key"
   export AZURE_OPENAI_ENDPOINT="https://your-endpoint.openai.azure.com"

   # For Gemini
   export GEMINI_API_KEY="your-gemini-key"

5.2 Load Your Tool
------------------

Import ToolUniverse and load your specific tool from the config file:

.. code-block:: python

   from tooluniverse import ToolUniverse

   # Initialize ToolUniverse
   tu = ToolUniverse()

   # Option 1: Load specific tool from custom config file
   tu.load_tools(
       tool_config_files={"custom_tools": "my_tools/scientific_summarizer.json"},
       include_tools=["ScientificTextSummarizer"]
   )

   # Option 2: Load all tools from custom category (if file has multiple tools)
   # tu.load_tools(
   #     tool_config_files={"custom_tools": "my_tools/scientific_summarizer.json"},
   #     tool_type=["custom_tools"]
   # )

   # Option 3: Load from built-in agentic tools collection
   # tu.load_tools(tool_type=["agentic"], include_tools=["ScientificTextSummarizer"])

   # Verify your tool is loaded
   print(f"Loaded {len(tu.all_tools)} tools")
   print("Available tools:", [tool["name"] for tool in tu.all_tools])

5.3 Prepare Your Input
-----------------------

Create the arguments dictionary:

.. code-block:: python

   # Prepare input arguments
   arguments = {
       "text": """
       Recent studies have shown that CRISPR-Cas9 gene editing technology
       can be used to modify T-cells for cancer immunotherapy. Researchers
       successfully edited CAR-T cells to enhance their ability to target
       and destroy cancer cells while reducing off-target effects.
       """,
       "summary_length": "50",
       "focus_area": "clinical implications"
   }

5.4 Execute the Tool
--------------------

Run your tool and handle the response:

.. code-block:: python

   # Execute the tool
   result = tu.run_one_function({
       "name": "ScientificTextSummarizer",
       "arguments": arguments
   })

   # Check if successful
   if result["success"]:
       print("✅ Summary:", result["result"])
       print(f"⏱️ Execution time: {result['metadata']['execution_time_seconds']:.2f}s")
   else:
       print("❌ Error:", result["error"])

Step 6: Handle Common Issues
============================

6.1 Check for Missing API Keys
------------------------------

If you get authentication errors:

.. code-block:: python

   import os

   # Check if API keys are set
   if not os.getenv("AZURE_OPENAI_API_KEY_GPT4O"):
       print("❌ Missing Azure OpenAI API key")
       print("Set with: export AZURE_OPENAI_API_KEY_GPT4O='your-key'")


6.2 Debug Response Issues
-------------------------

If the tool returns unexpected results:

.. code-block:: python

   # Enable detailed logging
   import logging
   logging.getLogger('tooluniverse.agentic_tool').setLevel(logging.DEBUG)

   # Inspect the tool configuration
   tool = tu.get_tool_by_name("ScientificTextSummarizer")
   if tool:
       spec = tu.tool_specification(tool_name="ScientificTextSummarizer", format="openai")
       print("🔍 Tool specification:", spec.get("description", "N/A")[:200])
   else:
       print("⚠️  Tool not found — check the tool name is loaded")


Step 7: Create More Complex Tools
=================================

7.1 JSON Response Tool
----------------------

Create a tool that returns structured data:

.. code-block:: json

   {
       "type": "AgenticTool",
       "name": "CodeQualityAnalyzer",
       "description": "Analyzes code quality and provides structured feedback",
       "prompt": "You are an expert code reviewer. Analyze this code and return ONLY a JSON object with your assessment:\n\nCode: {code}\n\nReturn format: {\"score\": 8.5, \"strengths\": [\"list\"], \"improvements\": [\"list\"]}",
       "input_arguments": ["code"],
       "parameter": {
           "type": "object",
           "properties": {
               "code": {
                   "type": "string",
                   "description": "The code to analyze",
                   "required": true
               }
           },
           "required": ["code"]
       },
       "configs": {
           "api_type": "CHATGPT",
           "model_id": "o4-mini-0416",
           "temperature": 0.3,
           "return_json": true
       }
   }

**Key difference**: Set ``"return_json": true`` for structured responses.

7.2 Tool with Optional Parameters
---------------------------------

Create a tool with both required and optional inputs:

.. code-block:: json

   {
       "type": "AgenticTool",
       "name": "HypothesisGenerator",
       "description": "Generates research hypotheses from context",
       "prompt": "Generate {number_of_hypotheses} research hypotheses in {domain} based on: {context}\n\nFormat: {hypothesis_format}",
       "input_arguments": ["context", "domain", "number_of_hypotheses", "hypothesis_format"],
       "parameter": {
           "type": "object",
           "properties": {
               "context": {
                   "type": "string",
                   "description": "Background information",
                   "required": true
               },
               "domain": {
                   "type": "string",
                   "description": "Research field (e.g., 'neuroscience')",
                   "required": true
               },
               "number_of_hypotheses": {
                   "type": "string",
                   "description": "How many hypotheses to generate",
                   "required": true
               },
               "hypothesis_format": {
                   "type": "string",
                   "description": "Format style for hypotheses",
                   "default": "If-Then statements",
                   "required": false
               }
           },
           "required": ["context", "domain", "number_of_hypotheses"]
       },
       "configs": {
           "api_type": "CHATGPT",
           "model_id": "o4-mini-0416",
           "temperature": 1.0,
           "return_json": false
       }
   }
