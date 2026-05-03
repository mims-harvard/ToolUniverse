---
name: tooluniverse-[domain-name]
description: [Complete description of what the skill does, which databases it uses, and when to use it. Include specific trigger phrases like "analyze [domain]", "find [data type]", etc. This description is the primary way Claude determines when to use your skill.]
---

# [Domain Name] Analysis

[One paragraph overview describing what this skill does, what problems it solves, and what outputs it provides.]

## When to Use This Skill

**Triggers**:
- "[Trigger phrase 1]"
- "[Trigger phrase 2]"
- "[Trigger phrase 3]"

**Use Cases**:
1. **[Use Case 1]**: [Description]
2. **[Use Case 2]**: [Description]
3. **[Use Case 3]**: [Description]

## Core Databases Integrated

| Database | Coverage | Strengths |
|----------|----------|-----------|
| **Database 1** | [What it covers] | [What it's best for] |
| **Database 2** | [What it covers] | [What it's best for] |
| **Database 3** | [What it covers] | [What it's best for] |

## Workflow Overview

```
Input → Phase 1: [Name] → Phase 2: [Name] → Phase 3: [Name] → Report
```

---

## Phase 1: [Phase Name]

**When**: [When this phase runs - e.g., "When input_param_1 provided"]

**Objective**: [What this phase achieves]

### Tools Used

**TOOL_NAME_1**:
- **Input**:
  - `parameter1` (type, required/optional): Description
  - `parameter2` (type, required/optional): Description
- **Output**: Description of what the tool returns
- **Use**: What this tool provides for the analysis

**TOOL_NAME_2** (Fallback):
- **Input**: [Parameters]
- **Output**: [Description]
- **Use**: [Purpose]

### Workflow

1. Query TOOL_NAME_1 with [input description]
2. Extract [specific data fields] from response
3. If no results → try TOOL_NAME_2 (fallback)
4. Process data and add to report
5. Continue with available data

### Decision Logic

- **Successful query**: Process and display top 10-15 results
- **Empty results**: Note "[Database] returned no results"
- **API error**: Fall back to TOOL_NAME_2
- **Both fail**: Document unavailability and continue

---

## Phase 2: [Phase Name]

**When**: [Conditions]

**Objective**: [Goal]

### Tools Used

[Similar structure to Phase 1]

### Workflow

[Step-by-step process]

### Decision Logic

[How to handle different scenarios]

---

## Phase 3: [Phase Name]

[Similar structure]

---

## Phase 4: [Summary/Context Phase]

**When**: Always included

**Objective**: Provide context even when specific phases empty

[Structure similar to above phases]

---

## Output Structure

### Report Format

**Progressive Markdown Report**:
- Create report file first
- Add sections progressively
- Each section self-contained
- Handles empty data gracefully

**Required Sections**:
1. **Header**: Analysis parameters and metadata
2. **Phase 1 Results**: [Description]
3. **Phase 2 Results**: [Description]
4. **Phase 3 Results**: [Description]
5. **Phase 4 Results**: [Description]

**Per-Database Subsections**:
- Database name and result count
- Table of results with key metadata
- Note if database returns no results
- Links or IDs for follow-up

### Data Tables

**Phase 1 Results**:
| Column 1 | Column 2 | Column 3 |
| ... | ... | ... |

**Phase 2 Results**:
| Column 1 | Column 2 | Column 3 |
| ... | ... | ... |

---

## Tool Parameter Reference

**Critical Parameter Notes** (from testing):

| Tool | Parameter | CORRECT Name | Common Mistake |
|------|-----------|--------------|----------------|
| TOOL_NAME_1 | `param` | ✅ `actual_param_name` | ❌ `assumed_param_name` |
| TOOL_NAME_2 | `param` | ✅ `correct_name` | ❌ `function_name_param` |

**Response Format Notes**:
- **TOOL_NAME_1**: Returns standard `{status: "success", data: [...]}` format
- **TOOL_NAME_2**: Returns list directly (not wrapped in status/data)
- **TOOL_NAME_3**: Returns dict with custom structure `{field1: ..., field2: ...}`

**SOAP Tools** (if applicable):
- **TOOL_NAME_4**: Requires `operation` parameter (e.g., `operation="method_name"`)
- See QUICK_START.md for side-by-side Python/MCP examples

---

## Fallback Strategies

### Phase 1: [Phase Name]
- **Primary**: TOOL_NAME_1 ([reason it's primary])
- **Fallback**: TOOL_NAME_2 ([what it provides instead])
- **Default**: Continue with noting data unavailable

### Phase 2: [Phase Name]
- **Primary**: TOOL_NAME_3
- **Fallback**: [Alternative approach]
- **Default**: [How to proceed]

---

## Common Use Patterns

### Pattern 1: [Use Case Name]
```
Input: [Description of typical input]
Workflow: Phase 1 → Phase 3 → Report
Output: [What user gets]
```

### Pattern 2: [Use Case Name]
```
Input: [Description]
Workflow: [Which phases run]
Output: [Result type]
```

### Pattern 3: [Comprehensive Analysis]
```
Input: [Multiple inputs]
Workflow: All phases
Output: [Complete analysis]
```

---

## Quality Checks

### Data Completeness
- [ ] At least one phase completed successfully
- [ ] Each database result includes source attribution
- [ ] Empty results explicitly noted (not silently omitted)
- [ ] All required fields documented in tables
- [ ] IDs provided for follow-up analysis

### Biological/Scientific Validity
- [ ] Results consistent with known [domain] knowledge
- [ ] Cross-database results show expected overlaps
- [ ] Anomalies flagged for review
- [ ] Data quality indicators included

### Report Quality
- [ ] All sections present even if "no data"
- [ ] Tables formatted consistently
- [ ] Source databases clearly attributed
- [ ] Follow-up recommendations if data sparse

---

## Limitations & Known Issues

### Database-Specific
- **Database 1**: [Known limitations, coverage gaps, update frequency]
- **Database 2**: [Limitations]
- **Database 3**: [Limitations]

### Technical
- **Response formats**: Different tools use different structures (handled in implementation)
- **Rate limits**: [Any rate limiting concerns]
- **Version differences**: [Database version considerations]

### Analysis
- **[Domain]-specific limitation 1**: [Description]
- **[Domain]-specific limitation 2**: [Description]

---

## Summary

**[Domain] Analysis Skill** provides:
1. ✅ [Capability 1 with database]
2. ✅ [Capability 2 with databases]
3. ✅ [Capability 3 with databases]
4. ✅ [Capability 4]

**Outputs**: Markdown report with [description of content]

**Best for**: [Primary use cases and target users]
