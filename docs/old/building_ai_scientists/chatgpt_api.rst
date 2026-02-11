ChatGPT API
=============================

**Building AI Scientists with ChatGPT API and ToolUniverse**

Overview
--------

ChatGPT API integration enables powerful programmatic scientific research through OpenAI's function calling capabilities. This approach provides a scalable, automatable interface for research while leveraging ChatGPT's reasoning and ToolUniverse's comprehensive scientific tools ecosystem.

.. code-block:: text

   ┌─────────────────┐
   │   ChatGPT API   │ ← Function Calling & Reasoning
   │                 │
   └─────────┬───────┘
             │ Functions (OpenAI schema)
             │
   ┌─────────▼───────┐
   │  ToolUniverse   │ ← Tool Registry & Executor
   │   (Python API)  │
   └─────────┬───────┘
             │
   ┌─────────▼───────┐
   │ 1000+ Scientific │ ← Scientific Tools Ecosystem
   │     Tools       │
   └─────────────────┘

**Benefits of ChatGPT API Integration**:

- **Function Calling**: Structured tool selection and execution with JSON arguments
- **Iterative Reasoning**: Feedback loop using tool results to refine subsequent steps
- **Scalability**: Dynamically grow the function list with discovered tools
- **Automation**: Build research workflows and batch processing systems
- **Reusability**: Clear system prompt and minimal boilerplate for new tasks

Prerequisites
-------------

Before setting up ChatGPT API integration, ensure you have:

- **OpenAI API Key**: Valid API key with function calling access
- **ToolUniverse**: Installed
- **Python 3.10+**: For ToolUniverse and OpenAI SDK
- **API Keys**: For specific tools or optional hooks (if required by your research domain)

Installation and Setup
----------------------

Step 1: Install Required Packages
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Install ToolUniverse and OpenAI SDK:

.. code-block:: bash

   pip install tooluniverse openai

Verify installation:

.. code-block:: bash

   python -c "import tooluniverse, openai; print('Packages installed successfully')"

Step 2: Set Up API Key
~~~~~~~~~~~~~~~~~~~~~~

Configure your OpenAI API key:

.. code-block:: bash

   export OPENAI_API_KEY='your-api-key-here'

Or in Python:

.. code-block:: python

   import os
   os.environ['OPENAI_API_KEY'] = 'your-api-key-here'

Step 3: Initialize ToolUniverse
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import os
   import json
   import openai
   from tooluniverse import ToolUniverse

   # Initialize components
   client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
   tu = ToolUniverse()
   tu.load_tools()

Step 4: Configure System Prompt
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Define the system prompt for iterative tool discovery and usage:

.. code-block:: python

   SYSTEM_PROMPT = (
       "You are a scientific assistant using ToolUniverse via function calling.\n"
       "Your job is to solve the user's task by: (1) discovering relevant tools, "
       "(2) selecting and calling the best tool for each step, and (3) iterating on results until the final answer is ready.\n\n"
       "Principles\n"
       "- If you need tools, first call the tool finder Tool_Finder with a short, precise description of the task.\n"
       "- Only call tools listed in the provided function list. Do not invent tools.\n"
       "- One step at a time: choose the single best next tool and provide minimal sufficient arguments.\n"
       "- After each tool result, update your plan. Decide: call another tool (with refined arguments), re-run the tool finder to expand available tools if necessary, or produce the final answer.\n"
       "- Handle tool errors gracefully: adjust parameters, pick an alternative tool, or ask for missing required inputs.\n"
       "- Prefer high-signal outputs: extract key findings, IDs, links, citations if available.\n"
       "- Stop when the answer is sufficient and accurate. Otherwise, continue iterating.\n\n"
       "Output Contract\n"
       "- During the process, respond with function calls only (no extra text), using valid JSON arguments.\n"
       "- When finished, return an assistant message (no function_call) with: \n"
       "  1) a concise answer; and\n"
       "  2) a short bullet summary of the steps/tools used."
   )

Step 5: Set Up Dynamic Tool Discovery
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Start with the tool finder and expand functions dynamically:

.. code-block:: python

   # Start with only the tool finder
   functions = tu.get_tool_specification_by_names(['Tool_Finder'], format='openai')
   tool_finders = {'Tool_Finder'}

Step 6: Implement Chat Loop
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create the iterative chat loop with function calling:

.. code-block:: python

   def run_with_dynamic_tools(query: str, max_iters: int = 12):
       messages = [
           {"role": "system", "content": SYSTEM_PROMPT},
           {"role": "user", "content": query}
       ]

       for _ in range(max_iters):
           resp = client.chat.completions.create(
               model="gpt-4",
               messages=messages,
               functions=functions,
               function_call="auto"
           )
           msg = resp.choices[0].message
           # NOTE:
           # If the model decides to call a function, msg.content is typically None.
           # The OpenAI API expects message content to be a string (not null), so
           # coerce missing content to "" while preserving the function_call.
           assistant_msg = {"role": "assistant", "content": msg.content or ""}
           if msg.function_call:
               assistant_msg["function_call"] = {
                   "name": msg.function_call.name,
                   "arguments": msg.function_call.arguments or "{}"
               }
           messages.append(assistant_msg)

           if msg.function_call:
               name = msg.function_call.name
               args = json.loads(msg.function_call.arguments or "{}")
               result = tu.run({"name": name, "arguments": args})

               # Expand functions if tool finder was called
               if name in tool_finders:
                   try:
                       tool_names = [t['name'] for t in result][:8]
                       if tool_names:
                           functions += tu.get_tool_specification_by_names(tool_names, format='openai')
                   except Exception:
                       pass

               messages.append({
                   "role": "function",
                   "name": name,
                   "content": json.dumps(result, ensure_ascii=False)
               })
               continue

           return msg.content

       return "Reached max iterations without a final answer"

Step 7: Verify Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~

Test the integration with a simple research query:

.. code-block:: python

   # Test basic functionality
   result = run_with_dynamic_tools("Find recent CRISPR gene-editing papers and summarize key findings")
   print(result)

Scientific Research Capabilities
--------------------------------

Drug Discovery and Development
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

ChatGPT API with ToolUniverse enables comprehensive drug discovery workflows:

**Target Identification**:
- Disease analysis and EFO ID lookup
- Target discovery and validation
- Literature-based target assessment

**Drug Analysis**:
- Drug information retrieval from multiple databases
- Safety profile analysis
- Drug interaction checking
- Clinical trial data access

**Example Workflow**:

.. code-block:: python

   result = run_with_dynamic_tools("Find FDA-approved drugs that target the EGFR protein and analyze their safety profiles")

Genomics and Molecular Biology
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Access comprehensive genomics tools for molecular research:

**Gene Analysis**:
- Gene information from UniProt
- Protein structure analysis
- Expression pattern analysis
- Pathway involvement

**Molecular Interactions**:
- Protein-protein interactions
- Drug-target interactions
- Pathway analysis
- Functional annotation

**Example Workflow**:

.. code-block:: python

   result = run_with_dynamic_tools("Analyze the BRCA1 gene and its role in cancer development")

Literature Research and Analysis
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Comprehensive literature search and analysis capabilities:

**Literature Search**:
- PubMed, Europe PMC, and Semantic Scholar
- Citation analysis and trend detection

**Content Analysis**:
- Abstract summarization
- Key finding extraction
- Gap identification

**Example Workflow**:

.. code-block:: python

   result = run_with_dynamic_tools("Find recent papers about COVID-19 vaccine efficacy published in the last year")

Clinical Research and Trials
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Access clinical trial data and regulatory information:

**Clinical Trials**:
- ClinicalTrials.gov searches
- Trial status and results analysis
- Patient population assessment

**Regulatory Information**:
- FDA drug approvals
- Safety warnings and adverse events
- Labeling information

**Example Workflow**:

.. code-block:: python

   result = run_with_dynamic_tools("Search clinical trials for diabetes treatment and analyze their outcomes")

Multi-Step Research Workflows
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

ChatGPT API excels at complex, multi-step research workflows:

**Hypothesis-Driven Research**:
1. Formulate research hypothesis
2. Design experimental approach
3. Gather supporting evidence
4. Validate findings
5. Generate conclusions

**Comparative Analysis**:
1. Identify comparison targets
2. Gather data for each target
3. Perform comparative analysis
4. Identify differences and similarities
5. Draw conclusions

Settings and Configuration
--------------------------

Tool Discovery Options
~~~~~~~~~~~~~~~~~~~~~~

ToolUniverse offers multiple discovery methods:

.. code-block:: python

   # 1) Keyword search (fast, recommended)
   results = tu.run({
       'name': 'Tool_Finder_Keyword',
       'arguments': {
           'description': 'protein analysis',
           'limit': 5
       }
   })

   # 2) LLM-based search (requires API key, more intelligent)
   results = tu.run({
       'name': 'Tool_Finder_LLM',
       'arguments': {
           'description': 'Find tools for drug safety analysis',
           'limit': 5
       }
   })

   # 3) Pattern search
   results = tu.find_tools_by_pattern("ChEMBL")

Advanced Configuration
~~~~~~~~~~~~~~~~~~~~~~

**Batch Processing**: Handle multiple research tasks efficiently:

.. code-block:: python

   def batch_research(queries: list):
       results = []
       for query in queries:
           result = run_with_dynamic_tools(query)
           results.append(result)
       return results

**Periodic Tool Discovery**: Re-run the finder on intermediate results:

.. code-block:: python

   # Example: expand tools every 3 iterations
   if iteration % 3 == 0:
       new_tools = tu.run({
           'name': 'Tool_Finder',
           'arguments': {'description': str(result), 'limit': 3}
       })
       functions += tu.get_tool_specification_by_names(
           [t['name'] for t in new_tools], format='openai'
       )

**Custom Tool Sets**: Load specific tools for focused research:

.. code-block:: python

   # Literature-focused research
   literature_tools = [
       'EuropePMC_search_articles',
       'openalex_literature_search',
       'PubTator3_LiteratureSearch'
   ]
   functions = tu.get_tool_specification_by_names(literature_tools, format='openai')

**Full Example (All Steps Combined)**:

.. code-block:: python

   import os
   import json
   import openai
   from tooluniverse import ToolUniverse

   os.environ['OPENAI_API_KEY'] = 'your-api-key-here'

   def run_with_dynamic_tools(query: str, max_iters: int = 12):
       client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
       tu = ToolUniverse(); tu.load_tools()

       SYSTEM_PROMPT = (
           "You are a scientific assistant using ToolUniverse via function calling.\n"
           "Your job is to solve the user's task by: (1) discovering relevant tools, "
           "(2) selecting and calling the best tool for each step, and (3) iterating on results until the final answer is ready.\n\n"
           "Principles\n"
           "- If you need tools, first call the tool finder Tool_Finder with a short, precise description of the task.\n"
           "- Only call tools listed in the provided function list. Do not invent tools.\n"
           "- One step at a time: choose the single best next tool and provide minimal sufficient arguments.\n"
           "- After each tool result, update your plan. Decide: call another tool (with refined arguments), re-run the tool finder to expand available tools if necessary, or produce the final answer.\n"
           "- Handle tool errors gracefully: adjust parameters, pick an alternative tool, or ask for missing required inputs.\n"
           "- Prefer high-signal outputs: extract key findings, IDs, links, citations if available.\n"
           "- Stop when the answer is sufficient and accurate. Otherwise, continue iterating.\n\n"
           "Output Contract\n"
           "- During the process, respond with function calls only (no extra text), using valid JSON arguments.\n"
           "- When finished, return an assistant message (no function_call) with: \n"
           "  1) a concise answer; and\n"
           "  2) a short bullet summary of the steps/tools used."
       )

       functions = tu.get_tool_specification_by_names(['Tool_Finder'], format='openai')
       tool_finders = {'Tool_Finder'}
       messages = [
           {"role": "system", "content": SYSTEM_PROMPT},
           {"role": "user", "content": query}
       ]

       for _ in range(max_iters):
           resp = client.chat.completions.create(
               model="gpt-4",
               messages=messages,
               functions=functions,
               function_call="auto"
           )
           msg = resp.choices[0].message
           # NOTE:
           # If the model decides to call a function, msg.content is typically None.
           # The OpenAI API expects message content to be a string (not null), so
           # coerce missing content to "" while preserving the function_call.
           assistant_msg = {"role": "assistant", "content": msg.content or ""}
           if msg.function_call:
               assistant_msg["function_call"] = {
                   "name": msg.function_call.name,
                   "arguments": msg.function_call.arguments or "{}"
               }
           messages.append(assistant_msg)

           if msg.function_call:
               name = msg.function_call.name
               args = json.loads(msg.function_call.arguments or "{}")
               result = tu.run({"name": name, "arguments": args})

               if name in tool_finders:
                   try:
                       tool_names = [t['name'] for t in result][:8]
                       if tool_names:
                           functions += tu.get_tool_specification_by_names(tool_names, format='openai')
                   except Exception:
                       pass

               messages.append({
                   "role": "function",
                   "name": name,
                   "content": json.dumps(result, ensure_ascii=False)
               })
               continue

           return msg.content

       return "Reached max iterations without a final answer"

   # Example usage
   print(run_with_dynamic_tools("Find recent CRISPR gene-editing papers and summarize key findings"))

Troubleshooting
---------------

Common Issues and Solutions
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**API Key Errors**:
- Ensure `OPENAI_API_KEY` is set correctly
- Verify your API key has function calling access
- Check your OpenAI account billing status

**Tool Not Found**:
- Use the tool finder to discover available tools
- Verify tool names match exactly
- Check if tools require specific API keys

**Function Call Errors**:
- Inspect tool parameter schemas using `tu.tool_specification("tool_name")`
- Ensure JSON arguments are properly formatted
- Handle missing required parameters gracefully

**Performance Issues**:
- Limit the number of tools added to the function list
- Use `Tool_Finder_Keyword` instead of `Tool_Finder_LLM` for faster discovery
- Implement timeout handling for long-running tools

**Debug Mode**:

.. code-block:: python

   # Inspect a tool's OpenAI function schema
   spec = tu.tool_specification("EuropePMC_search_articles")
   import json; print(json.dumps(spec, indent=2))

Tips
----

**Tool Selection**: Start with the tool finder, then add discovered tools incrementally.

**Error Handling**: Always wrap tool execution in try-catch blocks for production use.

**Prompt Engineering**: Customize the system prompt for domain-specific research tasks.

**Batch Processing**: Use the pattern for processing multiple queries efficiently.

**Rate Limiting**: Implement delays between API calls if you hit OpenAI rate limits.

.. tip::
   **Start Simple**: Begin with basic research queries to understand the integration, then progress to complex multi-step workflows as you become familiar with the capabilities.

.. note::
   **Function Calling**: ChatGPT API provides a powerful programmatic interface for scientific research, enabling both interactive exploration and automated batch processing of research tasks.
