# SKILL.md Template

Use this template when writing the implementation-agnostic SKILL.md for a new ToolUniverse skill.

**Key Rule**: SKILL.md must have ZERO Python/MCP specific code. Describe WHAT to do, not HOW in a specific language.

---

```markdown
---
name: tooluniverse-[domain-name]
description: [What it does]. [Capabilities]. [Databases used]. Use when [triggers].
---

# [Domain Name] Analysis

[One paragraph overview]

## When to Use This Skill

**Triggers**:
- "Analyze [domain] for [input]"
- "Find [data type] related to [query]"
- "[Domain-specific action]"

**Use Cases**:
1. [Use case 1 with description]
2. [Use case 2 with description]

## Core Databases Integrated

| Database | Coverage | Strengths |
|----------|----------|-----------|
| **Database 1** | [Scope] | [What it's good for] |
| **Database 2** | [Scope] | [What it's good for] |

## Workflow Overview

```
Input -> Phase 1 -> Phase 2 -> Phase 3 -> Report
```

---

## Phase 1: [Phase Name]

**When**: [Conditions]

**Objective**: [What this phase achieves]

### Tools Used

**TOOL_NAME**:
- **Input**:
  - `parameter1`: Description
  - `parameter2`: Description
- **Output**: Description
- **Use**: What it's used for

### Workflow

1. [Step 1]
2. [Step 2]
3. [Step 3]

### Decision Logic

- **Condition 1**: Action to take
- **Empty results**: How to handle
- **Errors**: Fallback strategy

---

## Phase 2, 3, 4... (similar structure)

---

## Output Structure

[Description of report format]

### Report Format

**Required Sections**:
1. Header with parameters
2. Phase 1 results
3. Phase 2 results
...

---

## Tool Parameter Reference

**Critical Parameter Notes** (from testing):

| Tool | Parameter | CORRECT Name | Common Mistake |
|------|-----------|--------------|----------------|
| TOOL_NAME | `param` | actual_param | assumed_param |

**Response Format Notes**:
- **TOOL_1**: Returns [format]
- **TOOL_2**: Returns [format]

---

## Fallback Strategies

[Document Primary -> Fallback -> Default for critical tools]

---

## Limitations & Known Issues

### Database-Specific
- **Database 1**: [Limitations]
- **Database 2**: [Limitations]

### Technical
- **Response formats**: [Notes]
- **Rate limits**: [If any]

---

## Summary

[Domain] skill provides:
1. [Capability 1]
2. [Capability 2]

**Outputs**: [Description]
**Best for**: [Use cases]
```
