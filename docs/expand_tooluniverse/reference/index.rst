Reference Documentation
========================

This section provides detailed reference information for tool development in ToolUniverse.

Architecture
------------

Understanding the internal architecture of ToolUniverse helps you build better tools and integrate more effectively with the system.

.. toctree::
   :maxdepth: 1
   :hidden:

   architecture

**I want to compare tool types:**
→ Review the tool type comparison table in :doc:`../contributing/index`

Tool Comparison
---------------

Understanding the differences between local and remote tools helps you choose the right approach for your needs.

**Key Differences:**

| Aspect | Local Tools | Remote Tools |
|--------|-------------|--------------|
| **Performance** | High (no network overhead) | Lower (network latency) |
| **Development** | Simple Python classes | MCP servers or API wrappers |
| **Deployment** | Part of ToolUniverse | Independent servers |
| **Scalability** | Limited by process | Highly scalable |
| **Integration** | Full ToolUniverse access | Limited to MCP/API |
| **Contribution** | Requires ``__init__.py`` changes | No code changes needed |

**When to Use Local Tools:**
- Data processing and analysis
- File manipulation utilities
- Simple API wrappers
- Tools that need full ToolUniverse integration

**When to Use Remote Tools:**
- External service integration
- Heavy computational tasks
- Microservice architecture
- Tools in different programming languages

Architecture Details
-------------------

**ToolUniverse Core Components:**
- **Tool Registry**: Manages tool discovery and registration
- **Execution Engine**: Handles tool execution and error management
- **Configuration System**: Manages tool parameters and settings
- **MCP Integration**: Connects with remote tools via MCP protocol

**Tool Lifecycle:**
1. **Registration**: Tools register with the registry
2. **Discovery**: ToolUniverse discovers available tools
3. **Configuration**: Tools load their configuration
4. **Execution**: Tools are called with parameters
5. **Response**: Results are returned to the caller

**Error Handling:**
- Input validation at multiple levels
- Graceful error recovery
- Comprehensive error reporting
- Timeout management for remote tools

Best Practices
--------------

**Local Tools:**
- Keep tools focused and single-purpose
- Use proper error handling
- Implement input validation
- Add comprehensive tests
- Document all parameters clearly

**Remote Tools:**
- Implement proper authentication
- Use circuit breakers for resilience
- Add retry logic for transient failures
- Monitor performance and errors
- Provide clear deployment documentation

**General:**
- Follow naming conventions
- Use descriptive parameter names
- Provide clear error messages
- Include usage examples
- Test with real-world data

Troubleshooting
---------------

**Common Issues:**

**Local Tools:**
- Tool not found: Check registration and imports
- Parameter errors: Verify JSON schema
- Execution failures: Check BaseTool inheritance
- Import errors: Verify module structure

**Remote Tools:**
- Connection errors: Check server URL and network
- Authentication failures: Verify credentials
- Timeout issues: Check server performance
- Discovery problems: Verify MCP server status

**General:**
- Configuration errors: Check JSON syntax
- Permission issues: Verify file access
- Version conflicts: Check dependencies
- Performance issues: Profile and optimize

Resources
---------

- **Local Tools Guide**: :doc:`../local_tools/index`
- **Remote Tools Guide**: :doc:`../remote_tools/index`
- **Contributing Guide**: :doc:`../contributing/index`
- **Quick Start**: :doc:`../quick_start`
- **Architecture**: :doc:`architecture`
- **Comparison**: Review the comparison table in :doc:`../contributing/index`

Next Steps
----------

Ready to dive deeper? Choose your focus:

* 🏗️ **Architecture**: :doc:`architecture` - Understand system design
* ⚖️ **Comparison**: Review the tool type comparison table in :doc:`../contributing/index`
* 🏠 **Local Tools**: :doc:`../local_tools/index` - Learn local tool development
* 🔗 **Remote Tools**: :doc:`../remote_tools/index` - Learn remote tool integration
* 🎁 **Contributing**: :doc:`../contributing/index` - Submit tools to ToolUniverse

.. tip::
   **Reference First**: Understanding the architecture and differences between tool types will help you make better decisions about which approach to use for your specific needs.
