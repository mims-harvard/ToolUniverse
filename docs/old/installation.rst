Installation (Legacy)
=====================

.. deprecated:: 0.3.0
   **This page has been reorganized for better user experience.**
   
   Installation instructions are now part of our streamlined getting started guides:
   
   - **🐍 Python developers**: See :doc:`guide/python_guide` (Installation section)
   - **🤖 AI agent users**: See :doc:`guide/building_ai_scientists/index` (Platform-specific setup)
   - **📖 Main documentation**: :doc:`index`

.. important:: 🎯 **Looking for installation instructions?**
   
   Choose your path to get the right installation guide:
   
   .. grid:: 1 1 2 2
      :gutter: 3
   
      .. grid-item-card:: 🐍 Python Developer
         :link: guide/python_guide
         :link-type: doc
         :class-card: choice-card python-card
         :shadow: lg
         
         **Python Installation**
         
         Complete installation with pip, uv, or development setup
   
      .. grid-item-card:: 🤖 AI Agent User
         :link: guide/building_ai_scientists/index
         :link-type: doc
         :class-card: choice-card agent-card
         :shadow: lg
         
         **Platform Setup**
         
         Platform-specific installation for Claude, ChatGPT, Gemini, etc.

Legacy Content
--------------

**Complete installation options for ToolUniverse**

This Tutorial covers all installation methods and environment setup options.

System Requirements
-------------------

* Python 3.10 or higher
* uv package manager (recommended) or pip
* Internet connection for API access
* GPU for machine learning models (optional)
* API keys for external services (optional)

Installation Methods
--------------------

Choose the installation method that best fits your needs:

.. tab-set::

   .. tab-item:: 📦 PyPI Installation

      Install ToolUniverse using pip:

      .. code-block:: bash

         pip install tooluniverse

   .. tab-item:: 🔧 Development Installation

      For development or custom modifications:

      .. code-block:: bash

         git clone https://github.com/mims-harvard/ToolUniverse.git
         cd ToolUniverse
         uv sync  # or: pip install -e .[dev]

.. button-ref:: guide/python_guide
   :color: primary
   :shadow:
   :expand:

   ➡️ **Continue to Modern Installation Guide**

.. button-ref:: index
   :color: secondary
   :shadow:
   :expand:

   ⬅️ **Back to Main Documentation**
