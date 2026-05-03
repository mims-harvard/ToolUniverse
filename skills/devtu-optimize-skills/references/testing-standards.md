# Test-Driven Skill Development Standards

## The Golden Rule

NEVER write skill documentation without first testing all tool calls with real ToolUniverse instance.

All 4 broken skills discovered in Feb 2026 had excellent docs but 0% functionality because tools were never tested.

## Test-First Workflow

1. Write skill implementation (phases, tool calls)
2. Write comprehensive test suite
3. Run tests, achieve 100% pass rate
4. Fix all failures
5. ONLY THEN mark skill as complete

## Test Suite Structure

```python
#!/usr/bin/env python3
"""Comprehensive Test Suite for [Skill Name]"""

# Naming: test_phase[N]_[description]
def test_phase1_gene_resolution():
    result = resolve_gene("BRCA1")  # NOT "TEST_GENE"
    assert result['ensembl_id'] == "ENSG00000012048"

def test_phase1_edge_cases():
    result = resolve_gene("FAKE_GENE_XYZ")
    assert result is None or 'error' in result

def test_integration_full_workflow():
    result = analyze("EGFR", "L858R", "lung adenocarcinoma")
    assert result['clinical_evidence']
    assert result['completeness_score'] >= 80
```

## What to Test

1. All use cases from SKILL.md (4-6)
2. Every documented parameter
3. All response fields
4. Edge cases:
   - Empty/minimal data
   - Large data (500+ genes)
   - Invalid data (unknown gene, typos)
   - Boundary values (TMB=0, TMB=999)
   - Conflicting data (high TMB + low PD-L1)

## Test Output Format

```
PASS Phase1: Gene resolution - BRCA1 -> ENSG00000012048
PASS Phase2: CIViC evidence - Found 12 entries
WARN Phase4: Clinical trials - API timeout (transient)
FAIL Phase5: Pathway enrichment - Missing 'gene_list'

Total: 80 | PASS: 78 | FAIL: 1 | WARN: 1 | Rate: 97.5%
```

## Transient vs Real Errors

**Transient** (retry): timeouts, rate limiting (429), service overload (503)
**Real** (fix): wrong parameters, missing fields, logic errors

Handle transient errors with exponential backoff. In tests, mark as PASS with note.

## Minimum Requirements

- 30+ tests per skill
- 100% pass rate (transient errors = PASS with warning)
- All tests use real data (no "TEST", "DUMMY", "PLACEHOLDER")
- Phase-level + integration + edge case + cross-example tests
- Performance benchmarks documented

## SOAP Tools Special Handling

IMGT, SAbDab, TheraSAbDab require `operation` parameter as first param:
```python
tu.tools.IMGT_search_genes(operation="search_genes", gene_type="IGHV", species="Homo sapiens")
```

## API Documentation Is Often Wrong

Always verify with actual calls:
1. Check tool parameters via `get_tool_info()`
2. Test with real data
3. Inspect actual response structure
4. Document findings in TOOLS_REFERENCE.md
