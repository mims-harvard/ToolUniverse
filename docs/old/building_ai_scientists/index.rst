Building AI Scientists
======================

Overview
--------

A customized AI scientist can be developed by integrating ToolUniverse with LLMs, reasoning models, and AI agents. In this configuration, the LLMs and reasoning models provide the core capabilities for reasoning and tool usage, while ToolUniverse serves as the scientific environment for interaction and experimentation.

The development process typically involves three steps:

1. Installing ToolUniverse with a single command (``pip install tooluniverse``)
2. Connecting ToolUniverse to the chosen model so it can access the tools provided by ToolUniverse
3. Instructing the model to use these tools to address a given scientific problem

How AI Scientists Operate
-------------------------

Once the setup is complete, the AI scientist operates as follows: given a user instruction or task, it formulates a plan or hypothesis, employs the tool finder in ToolUniverse to identify relevant tools, and iteratively applies these tools to gather information, conduct experiments, verify hypotheses, and request human feedback when necessary. For each required tool call, the AI scientist generates arguments that conform to the ToolUniverse protocol, after which ToolUniverse executes the tool and returns the results for further reasoning.

Model Types
-----------

The models used to construct AI scientists can include:

- **LLMs**: API-based (GPT, Claude, Gemini) or open-weight models (LLaMA, DeepSeek, Qwen)
- **Reasoning Models**: Enhance problem-solving capabilities by applying built-in chains of thought to analyze the current step before interacting with ToolUniverse
- **Agentic Systems**: Such as Gemini CLI or Claude Code, integrate reasoning models with agentic feedback loops to autonomously manage multi-step problem solving and tool use
- **Specialized Agents**: Trained for specific scientific domains, enabling stronger performance on targeted tasks

Integration Methods
-------------------

.. toctree::
   :maxdepth: 1
   :caption: Integration Methods

   claude_desktop
   claude_code
   gemini_cli
   qwen_code
   codex_cli
   chatgpt_api
