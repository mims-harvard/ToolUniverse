Quick Start (Legacy)
====================

.. deprecated:: 0.3.0
   **This page has been reorganized for better user experience.**
   
   Please see our new getting started paths:
   
   - **🐍 Python developers**: :doc:`guide/python_guide`
   - **🤖 AI agent users**: :doc:`guide/building_ai_scientists/index`
   - **📖 Main documentation**: :doc:`index`

**Build your first AI scientist in 5 minutes with ToolUniverse's 1000+ scientific tools**

.. important:: 🎯 **Looking for the new documentation?**
   
   We've redesigned the documentation to make it easier to get started:
   
   .. grid:: 1 1 2 2
      :gutter: 3
   
      .. grid-item-card:: 🐍 Python Developer
         :link: guide/python_guide
         :link-type: doc
         :class-card: choice-card python-card
         :shadow: lg
         
         **Build with Python API**
         
         Install, configure, and use ToolUniverse directly in your code
   
      .. grid-item-card:: 🤖 AI Agent User
         :link: guide/building_ai_scientists/index
         :link-type: doc
         :class-card: choice-card agent-card
         :shadow: lg
         
         **Connect to AI agents**
         
         Integrate with Claude, ChatGPT, Gemini, and more

Legacy Content
--------------

This Tutorial gets you from zero to your first successful query in 5 minutes. For detailed tutorials, see :doc:`getting_started`.

🚀 Quick Start
--------------

**Get your first ToolUniverse running in 2 minutes:**

.. code-block:: python

   # 1. Install ToolUniverse
   pip install tooluniverse

   # 2. Create AI scientist environment
   from tooluniverse import ToolUniverse

   tu = ToolUniverse()
   tu.load_tools()  # Load all 1000+ tools

   # 3. Query scientific databases
   result = tu.run({
       "name": "OpenTargets_get_associated_targets_by_disease_efoId",
       "arguments": {"efoId": "EFO_0000537"}  # hypertension
   })

**Success!** You now have access to 1000+ scientific tools.

.. note::
   Most tools work without API keys! For tools that require authentication or to get higher rate limits, see :doc:`api_keys`.

.. button-ref:: guide/python_guide
   :color: primary
   :shadow:
   :expand:

   ➡️ **Continue to Modern Python Guide**

.. button-ref:: guide/building_ai_scientists/index
   :color: secondary
   :shadow:
   :expand:

   ➡️ **Connect to AI Agent Instead**
