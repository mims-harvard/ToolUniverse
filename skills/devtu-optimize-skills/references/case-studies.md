# Case Studies: Fixing Non-Functional Skills

Real-world examples from fixing 4 broken skills in February 2026.

## Case 1: Drug-Drug Interaction Skill

**Original**: 0% functional. Docs showed `drugbank_get_drug_basic_info(drug_name_or_drugbank_id="...")` but tool requires `query`.

**Fixes**:
| Tool | WRONG (in docs) | CORRECT (tested) |
|------|-----------------|------------------|
| RxNorm_get_drug_names | query | drug_name |
| drugbank_* | drug_name_or_id | query |
| FAERS_count_reactions | drug_name | medicinalproduct |

**Lesson**: Function names are misleading. `get_drug_basic_info_by_drug_name_or_id` takes `query`, not `drug_name_or_id`.

## Case 2: Antibody Engineering Skill

**Original**: 0% functional. All SOAP tool calls missing `operation` parameter.

**Fix**: Added `operation` parameter to all SOAP calls (IMGT, SAbDab, TheraSAbDab).

**Lesson**: SOAP tools have special requirements not obvious from function signatures.

## Case 3: CRISPR Screen Analysis Skill

**Original**: 20% functional. Primary API (DepMap) completely down (404).

**Fix**: Implemented Pharos TDL fallback. TDL classification (Tclin/Tchem/Tbio/Tdark) as essentiality proxy.

**Lesson**: External APIs fail. Always implement fallback chains.

## Case 4: Clinical Trial Design Skill

**Original**: 0% functional. All DrugBank tool parameters wrong throughout.

**Fix**: ALL DrugBank tools use `query`, not the parameter names in their function names.

**Lesson**: Even when multiple tools have similar naming patterns, always verify each one.

## Common Thread

All 4 skills had excellent documentation (300+ lines) but were never tested. The fix was always the same: test with real ToolUniverse instance first, then write docs from working code.
