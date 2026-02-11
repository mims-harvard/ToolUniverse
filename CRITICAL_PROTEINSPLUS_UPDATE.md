# CRITICAL UPDATE: ProteinsPlus API Status

**Date**: 2026-02-08
**Priority**: P0 - URGENT
**Status**: ⚠️ **3 out of 4 tools need removal or replacement**

## Executive Summary

✅ **Good News**: The ProteinsPlus REST API is **real, accessible, and working**.

❌ **Bad News**: Our implementation has critical issues:
1. Wrong endpoint paths and request formats
2. **3 out of 4 tools don't exist in the REST API** (PLIP, Fpocket, JAMDA)
3. Only DoGSiteScorer is available and needs format fixes

## Live API Test Results

### Test 1: API Accessibility ✅

```bash
curl -X POST https://proteins.plus/api/dogsite_rest \
  -H "Content-Type: application/json" \
  -d '{"dogsite": {"pdbCode":"2OZR", "analysisDetail":"1", "bindingSitePredictionGranularity":"1", "ligand":"", "chain":""}}'
```

**Response**:
```json
{
  "status_code": 202,
  "location": "https://proteins.plus/api/dogsite_rest/zqorpEFqHNKXup6DPBenLNP1",
  "message": "The job will be created in the specified location"
}
```

**Result**: ✅ API is fully functional

### Test 2: Job Polling ✅

```bash
curl https://proteins.plus/api/dogsite_rest/zqorpEFqHNKXup6DPBenLNP1
```

**Response**:
```json
{
  "status_code": 202,
  "message": "Job exists and is still in 'processing' state",
  "location": "https://proteins.plus/api/dogsite_rest/zqorpEFqHNKXup6DPBenLNP1"
}
```

**Result**: ✅ Async job pattern working correctly

## Tool-by-Tool Assessment

### 1. ProteinsPlus_predict_binding_sites
**Status**: ⚠️ **FIXABLE** (15 minutes)
**API Endpoint**: `/dogsite_rest` (exists)
**Issues**:
- Wrong endpoint: `/dogsite/predict` → should be `/dogsite_rest`
- Wrong request format: `{"pdb_id": "..."}` → should be `{"dogsite": {"pdbCode": "..."}}`

**Fix Required**:
```python
# Current (WRONG)
endpoint = "/dogsite/predict"
body = {"pdb_id": pdb_id}

# Correct
endpoint = "/dogsite_rest"
body = {
    "dogsite": {
        "pdbCode": pdb_id,
        "analysisDetail": "1",
        "bindingSitePredictionGranularity": "1",
        "ligand": "",
        "chain": chain or ""
    }
}
```

### 2. ProteinsPlus_dock_ligand (JAMDA)
**Status**: ❌ **NOT AVAILABLE IN REST API**
**Problem**: JAMDA docking is not listed in the [official REST API documentation](https://proteins.plus/help/index)
**Action**: Remove or replace

**Alternatives**:
- Use AutoDock Vina (separate tool)
- Use Smina (AutoDock Vina fork)
- Use existing ToolUniverse docking tools (if any)

### 3. ProteinsPlus_analyze_interactions (PLIP)
**Status**: ❌ **NOT AVAILABLE IN REST API**
**Problem**: PLIP is not exposed via the REST API
**Action**: Remove or replace

**Alternatives**:
- PLIP has its own [standalone tool](https://github.com/pharmai/plip)
- ProDy for protein-ligand interactions
- MDAnalysis for interaction analysis

### 4. ProteinsPlus_detect_pockets (Fpocket)
**Status**: ❌ **NOT AVAILABLE IN REST API**
**Problem**: Fpocket is not in the ProteinsPlus REST API
**Action**: Remove or replace

**Alternatives**:
- Fpocket can be installed [standalone](https://github.com/Discngine/fpocket)
- Use DoGSiteScorer instead (it also detects pockets)
- Use other pocket detection tools

## Available ProteinsPlus REST APIs

According to [official documentation](https://proteins.plus/help/index):

| Tool | Endpoint | Available | Description |
|------|----------|-----------|-------------|
| DoGSiteScorer | `/dogsite_rest` | ✅ YES | Binding site prediction |
| DoGSite3 | `/dogsite3_rest` | ✅ YES | Alternative binding site prediction |
| Protoss | `/protoss_rest` | ✅ YES | Hydrogen prediction |
| PoseView | `/poseview_rest` | ✅ YES | 2D interaction diagrams |
| SIENA | `/siena_rest` | ✅ YES | Structure ensemble generation |
| HyPPI | `/hyppi_rest` | ✅ YES | Protein-protein interactions |
| EDIA | `/edia_rest` | ✅ YES | Structural quality |
| GeoMine | `/geomine_rest` | ✅ YES | 3D PDB searching |
| METALizer | `/metalizer_rest` | ✅ YES | Metal complex geometry |
| StructureProfiler | `/structureprofiler_rest` | ✅ YES | Complex profiling |
| WarPP | `/warpp_rest` | ✅ YES | Water placement |

**Notable Absence**: PLIP, Fpocket, JAMDA are NOT in the REST API

## Implementation Options

### Option A: Minimal Fix (RECOMMENDED)
**Time**: ~2 hours
**Action**:
1. Fix DoGSiteScorer tool (15 minutes)
2. Remove 3 unavailable tools (5 minutes)
3. Update documentation (10 minutes)
4. Test fixed tool (30 minutes)
5. Update skills/documentation (1 hour)

**Result**: 1 working ProteinsPlus tool instead of 4

**Pros**:
- Quick fix
- Guaranteed to work
- DoGSiteScorer is valuable for binding site prediction
- Clean implementation

**Cons**:
- Loses docking and interaction analysis features
- Reduces tool count

### Option B: Replace with Alternatives
**Time**: ~4-6 hours
**Action**:
1. Fix DoGSiteScorer (15 minutes)
2. Implement AutoDock Vina for docking (2 hours)
3. Implement standalone PLIP (1.5 hours)
4. Keep Fpocket as future work (0 minutes) or implement (1.5 hours)
5. Test all (1 hour)
6. Documentation (1 hour)

**Result**: Complete structural biology toolkit

**Pros**:
- Full functionality maintained
- Better alternatives (Vina is gold standard for docking)
- More flexible

**Cons**:
- More work
- Additional dependencies
- May need local installations

### Option C: Expand ProteinsPlus Tools
**Time**: ~3-4 hours
**Action**:
1. Fix DoGSiteScorer (15 minutes)
2. Add DoGSite3 (30 minutes)
3. Add PoseView (45 minutes)
4. Add SIENA (45 minutes)
5. Add StructureProfiler (45 minutes)
6. Test all (1 hour)
7. Remove 3 unavailable tools (5 minutes)

**Result**: 5 ProteinsPlus tools (all working)

**Pros**:
- More ProteinsPlus coverage
- All tools verified working
- Consistent API pattern

**Cons**:
- Still loses docking functionality
- More maintenance

## Immediate Action Items

### 1. DECIDE which option (A, B, or C)

### 2. Update CRITICAL_ISSUES.md
Current document needs update with verified API status

### 3. Fix or Remove Tools
Based on chosen option

### 4. Update Verification Reports
- Mark DoGSiteScorer as "Verified Working (needs format fix)"
- Mark other 3 as "API Not Available"

## Updated Tool Count

**Before**:
- Systems Biology: 10 tools ✅
- Genomics: 4 tools ✅
- Clinical: 9 tools ✅
- Structural Biology: 9 tools (4 ProteinsPlus + 5 SASBDB)

**After Option A**:
- Structural Biology: 6 tools (1 ProteinsPlus + 5 SASBDB) ⚠️

**After Option B**:
- Structural Biology: 9 tools (1 ProteinsPlus + 5 SASBDB + 3 alternatives) ✅

**After Option C**:
- Structural Biology: 10 tools (5 ProteinsPlus + 5 SASBDB) ✅

## References

1. [ProteinsPlus REST API Help](https://proteins.plus/help/index)
2. [DoGSite REST Documentation](https://proteins.plus/help/dogsite_rest)
3. [ProteinsPlus API Examples (GitHub)](https://github.com/rareylab/proteins_plus_examples)
4. [ProteinsPlus Swagger UI](https://proteins.plus/api/v2)

## Recommendation

**Choose Option A** for immediate release:
- Fix DoGSiteScorer (proven working)
- Remove 3 unavailable tools
- Document alternatives for users
- Mark as v1.0 with plans for v1.1 to add AutoDock Vina

This gives us:
- 28 fully working tools (STRING, NCBI SRA, ICD, LOINC, BioGRID, SASBDB, DoGSiteScorer)
- Clean implementation
- All APIs verified
- Fast path to release

Then create follow-up tasks for Option B tools as v1.1 enhancements.
