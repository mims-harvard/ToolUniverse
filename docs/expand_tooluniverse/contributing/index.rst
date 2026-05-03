Contributing to ToolUniverse
============================

Welcome! Choose the type of tool you want to contribute and follow the detailed guide.

Choose Your Tool Type
---------------------

| Feature | Local Tools | Remote Tools |
|---------|-------------|--------------|
| **Runs** | In ToolUniverse process | Independent server |
| **Language** | Python only | Any language |
| **Setup** | Modify __init__.py in 4 locations | Deploy server publicly |
| **Testing** | Unit tests (>90% coverage) | Integration tests |
| **Best For** | API wrappers, data processing | Heavy computation, external services |

**Quick Decision Guide:**

I want to...
- Build a Python tool that processes data → :doc:`local_tools`
- Integrate an external API or service → :doc:`local_tools` or :doc:`remote_tools`
- Run heavy computations separately → :doc:`remote_tools`
- Use a language other than Python → :doc:`remote_tools`
- Not sure which to choose? → Review the comparison table above, or read the introductions in both detailed guides

Detailed Guides
---------------

.. toctree::
   :maxdepth: 2
   :hidden:
   :caption: Tool Contribution Guides

   local_tools
   remote_tools

Next Steps
----------

* **Local Tools**: :doc:`local_tools` - Complete 10-step guide with environment setup
* **Remote Tools**: :doc:`remote_tools` - Complete 10-step guide with deployment instructions
* **Compare Types**: Review the comparison table above to understand tool type differences

.. tip::
   Each guide includes complete setup instructions, code examples, and troubleshooting. Start with the guide that matches your tool type.