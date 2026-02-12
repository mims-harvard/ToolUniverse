# ToolUniverse Tool Creator Skill

A comprehensive skill for creating new scientific tools in the ToolUniverse framework following established best practices.

## Overview

This skill guides you through creating tools for ToolUniverse, covering:

- Tool class implementation with proper structure
- JSON configuration with comprehensive schemas
- Error handling and validation patterns
- Testing strategies
- MCP compatibility
- Common tool patterns (API integration, pagination, caching, etc.)

## Skill Structure

```
devtu-create-tool/
├── SKILL.md                              # Main skill file with core guidance
├── references/                           # Detailed reference documentation
│   ├── implementation-guide.md          # Full implementation plan & maintenance checklist
│   ├── tool-improvement-checklist.md    # 7-phase improvement process (detailed)
│   ├── advanced-patterns.md             # Advanced implementation patterns
│   └── quick-reference.md               # Quick lookup guide
└── templates/                            # Ready-to-use templates
    ├── simple_tool_template.py          # Basic tool template
    ├── api_tool_template.py             # API tool with retry logic
    ├── simple_tools_config.json         # Basic JSON config
    ├── api_tools_config.json            # API tools JSON config
    └── test_template.py                 # Comprehensive test suite
```

## When This Skill Triggers

Use this skill when users need to:

- Add new tools to ToolUniverse
- Implement API integrations for scientific databases
- Create tool wrappers for external services
- Expand ToolUniverse capabilities with new data sources
- Follow ToolUniverse contribution guidelines
- Improve or maintain existing tools

## Quick Start

### Creating a New Tool

1. **Read SKILL.md** for core guidance on tool creation
2. **Use templates** from `templates/` directory as starting points
3. **Follow checklist** in SKILL.md for complete implementation
4. **Test thoroughly** using test templates and validation commands

### Improving Existing Tools

1. **Read references/tool-improvement-checklist.md** for systematic 7-phase process
2. **Apply patterns** from references/advanced-patterns.md as needed
3. **Use quick-reference.md** for fast lookup during implementation

### Getting Unstuck

- **Quick lookup**: Check `references/quick-reference.md`
- **Advanced features**: See `references/advanced-patterns.md`
- **Systematic improvement**: Follow `references/tool-improvement-checklist.md`
- **Templates**: Copy from `templates/` and customize

## Key Features

### SKILL.md Covers

- Quick start guide with minimal examples
- File structure and location requirements
- Basic and API integration patterns
- JSON configuration best practices
- Tool naming guidelines (MCP compatibility)
- Error handling strategies
- Testing approaches
- Development checklist
- Common issues and solutions

### References Cover

**implementation-guide.md** (authoritative source):
- Guidelines for adding tools (file structure, conventions, auto-discovery)
- JSON config conventions (`type`, `return_schema`, schema hygiene)
- Development checklist with all validation steps
- Full maintenance checklist (7-phase)
- Large API expansion guidance

**tool-improvement-checklist.md** (7-phase systematic process, detailed):
- Phase 1: Initial Assessment
- Phase 2: Functionality Testing
- Phase 3: Description Improvement
- Phase 4: Error Handling
- Phase 5: Finding Missing Tools
- Phase 6: Fixing Common Issues
- Phase 7: Final Verification

**advanced-patterns.md** (advanced techniques):
- Caching strategies (LRU, time-based)
- Batch processing and parallel requests
- Streaming and pagination
- Authentication patterns (API key, OAuth)
- Data transformation (filtering, projection)
- GraphQL integration
- Rate limiting
- Async operations
- Multi-source aggregation

**quick-reference.md** (fast lookup):
- File locations
- Basic patterns
- Common return structures
- HTTP request patterns
- Error handling templates
- Validation patterns
- Testing commands
- JSON schema types
- Debugging tips

### Templates Include

**Python Templates**:
- `simple_tool_template.py`: Basic tool with clean structure
- `api_tool_template.py`: API tool with retry logic and comprehensive error handling
- `test_template.py`: Complete test suite with unit, integration, and performance tests

**JSON Templates**:
- `simple_tools_config.json`: Minimal configuration example
- `api_tools_config.json`: API tools with search/detail pattern

## Best Practices Highlighted

1. **Tool Naming**: Keep ≤ 55 characters for MCP compatibility
2. **Auto-Generated Files**: Never edit `src/tooluniverse/tools/` files
3. **Return Schemas**: Make them meaningful, not just `additionalProperties: true`
4. **Error Messages**: Specific, actionable, with context
5. **Testing**: Comprehensive with valid, invalid, and edge cases
6. **Documentation**: Clear descriptions with examples
7. **Retry Logic**: For transient failures only (not 4xx errors)
8. **Validation**: Both JSON schema and custom Python validation

## Common Workflows

### Create Simple Tool
1. Copy `templates/simple_tool_template.py`
2. Copy `templates/simple_tools_config.json`
3. Customize for your use case
4. Add tests using `templates/test_template.py`
5. Validate and test

### Create API Integration Tool
1. Copy `templates/api_tool_template.py`
2. Copy `templates/api_tools_config.json`
3. Implement API-specific logic
4. Add comprehensive error handling
5. Test with real API endpoints

### Improve Existing Tool
1. Read `references/tool-improvement-checklist.md`
2. Follow 7-phase process systematically
3. Apply advanced patterns as needed
4. Test thoroughly
5. Document changes

## Validation Commands

```bash
# JSON validation
python3 -m json.tool src/tooluniverse/data/{category}_tools.json

# Python syntax check
python3 -m py_compile src/tooluniverse/{category}_tool.py

# Tool name length check
python scripts/check_tool_name_lengths.py --test-shortening

# Run tests
pytest tests/unit/test_{category}_tool.py -v
```

## Progressive Disclosure Design

The skill uses a three-level loading system:

1. **SKILL.md** (~500 lines): Core guidance, always loaded when skill triggers
2. **References** (~1000+ lines each): Loaded only when needed for specific topics
3. **Templates**: Copied and customized, not loaded into context

This design minimizes context window usage while providing comprehensive guidance.

## Integration with ToolUniverse

This skill is designed to work with:

- ToolUniverse SDK (1000++ scientific tools)
- Scientific databases (PubMed, DrugBank, UniProt, etc.)
- MCP (Model Context Protocol) server
- Python 3.8+
- Standard scientific libraries (requests, pandas, etc.)

## Notes

- The implementation guide (`references/implementation-guide.md`) is the authoritative source, previously maintained as a standalone `tool_implementation_guide.md` at the repo root
- Follows ToolUniverse best practices and conventions
- Includes real-world patterns from existing tools
- Templates are production-ready starting points
- Checklist ensures nothing is missed

## Version

Created: 2026-01-31
Updated: 2026-02-12 — Integrated `tool_implementation_guide.md` into skill as `references/implementation-guide.md`
Skill Creator Guidelines: Cursor Codex skill-creator
