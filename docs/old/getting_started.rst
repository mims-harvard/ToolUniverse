Getting Started (Legacy)
========================

.. deprecated:: 0.3.0
   **This page has been reorganized for better user experience.**
   
   Getting started content is now split into focused paths:
   
   - **🐍 Python developers**: :doc:`guide/python_guide`
   - **🤖 AI agent users**: :doc:`guide/building_ai_scientists/index`
   - **📖 Main documentation**: :doc:`index`

.. important:: 🎯 **Looking for the getting started guide?**
   
   We've redesigned the documentation to make onboarding easier:
   
   .. grid:: 1 1 2 2
      :gutter: 3
   
      .. grid-item-card:: 🐍 Python Developer
         :link: guide/python_guide
         :link-type: doc
         :class-card: choice-card python-card
         :shadow: lg
         
         **Python Getting Started**
         
         Complete tutorial: install → configure → execute → build workflows
   
      .. grid-item-card:: 🤖 AI Agent User
         :link: guide/building_ai_scientists/index
         :link-type: doc
         :class-card: choice-card agent-card
         :shadow: lg
         
         **Platform Setup Guides**
         
         Step-by-step guides for each AI agent platform

Legacy Content
--------------

This tutorial provides detailed, step-by-step instructions for using ToolUniverse effectively.

.. tip::
   **Coming from the quickstart?** Great! This tutorial goes deeper into ToolUniverse features.
   
   **New here?** This tutorial works standalone, but you might enjoy the :doc:`quickstart` for a quick overview first.

**Prerequisites**: 

- Python 3.10+ installed
- ToolUniverse installed (see :doc:`installation`)
- Basic Python knowledge
- Internet access for API calls

.. note::
   Many tools work without API keys, but some require authentication. For information about which API keys you need and how to obtain them, see :doc:`api_keys`.

🧪 Step-by-Step Tutorial
-------------------------

Understanding Basic Workflow
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

ToolUniverse follows a simple but powerful pattern:

1. **Initialize once**: Create a ToolUniverse instance
2. **Load tools**: Load available tools from various databases
3. **Query tools**: Use standardized query format
4. **Get results**: Receive structured data

.. seealso::
   For full AI-Tool Interaction Protocol, see :doc:`guide/interaction_protocol`

.. button-ref:: guide/python_guide
   :color: primary
   :shadow:
   :expand:

   ➡️ **Continue to Modern Tutorial**

.. button-ref:: index
   :color: secondary
   :shadow:
   :expand:

   ⬅️ **Back to Main Documentation**
