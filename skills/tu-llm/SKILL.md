---
name: tu-llm
description: LLM-powered tool discovery that reasons about which ToolUniverse tools to combine for complex, multi-step scientific queries. Uses Claude CLI (primary) with Ollama fallback.
---

# LLM Tool Finder

Use an LLM to reason about which ToolUniverse tools best answer a complex query. Unlike embedding search (`find_tools`), this finder understands multi-step workflows and selects tool *combinations*.

## When to Use

- Query spans multiple databases ("find drugs targeting BRCA1 and check their clinical trial status")
- Embedding search returned irrelevant tools
- User needs a curated tool pipeline, not a ranked list

## Workflow

1. Call `execute_tool("Tool_Finder_LLM", {"description": "<user's query>", "limit": 10})`
2. Parse the returned tool list
3. For each tool: call `get_tool_info(tool_name)` to get the full schema
4. Present results as a numbered table: tool name, description, why it was selected
5. If the user wants to proceed, execute tools in the suggested order

## Backend

- **Primary**: Claude Code CLI (`claude --print`) — subscription-free, 200K context, best reasoning
- **Fallback**: Ollama (`deepseek-coder:6.7b`) — offline-capable, local GPU, ~11s latency

The backend is selected automatically. Claude CLI is tried first; if unavailable (offline, rate-limited), Ollama is used.

## Output Format

Present results as:

```
Found N tools for: "<query>"

| # | Tool | Why |
|---|------|-----|
| 1 | ToolName | Relevance reasoning |
| ...
```

Then ask: "Run these tools now, or refine the search?"
