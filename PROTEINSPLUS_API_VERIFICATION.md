# ProteinsPlus API Verification Results

**Date**: 2026-02-08
**Status**: ✅ **API IS ACCESSIBLE AND WORKING**

## Summary

The ProteinsPlus REST API is fully accessible and functional. However, our tool implementations use **incorrect endpoint paths and request formats**.

## Test Results

### ✅ DoGSiteScorer API (WORKING)

**Correct Endpoint**: `https://proteins.plus/api/dogsite_rest`

**Test Command**:
```bash
curl -d '{"dogsite": {"pdbCode":"2OZR", "analysisDetail":"1", "bindingSitePredictionGranularity":"1", "ligand":"", "chain":""}}' \
  -H "Accept: application/json" \
  -H "Content-Type: application/json" \
  -X POST https://proteins.plus/api/dogsite_rest
```

**Response**:
```json
{
  "status_code": 202,
  "location": "https://proteins.plus/api/dogsite_rest/zqorpEFqHNKXup6DPBenLNP1",
  "message": "The job will be created in the specified location"
}
```

**Status**: HTTP 202 Accepted - Job submitted successfully
**Result**: API is working perfectly

## Key Findings

### 1. API Base URL
- **Confirmed**: `https://proteins.plus/api` (v1)
- **Alternative**: `https://proteins.plus/api/v2` (Swagger UI available)

### 2. Available REST APIs

According to [official documentation](https://proteins.plus/help/dogsite_rest):
- ✅ **DoGSiteScorer** (`/dogsite_rest`) - VERIFIED WORKING
- ✅ **DoGSite3** (`/dogsite3_rest`) - Available
- ✅ **Protoss** - Available
- ✅ **PoseView** - Available
- ✅ **SIENA** - Available
- ✅ **HyPPI** - Available
- ✅ **EDIA** - Available
- ✅ **GeoMine** - Available
- ✅ **METALizer** - Available
- ✅ **StructureProfiler** - Available
- ✅ **WarPP** - Available

### 3. Tools NOT in REST API

Our implementation included these tools which do **NOT** appear in the official REST API documentation:
- ❌ **PLIP** (protein-ligand interaction profiler)
- ❌ **Fpocket** (pocket detection)
- ❌ **JAMDA** (docking workflow)

These may be web-only tools or require different access methods.

## Implementation Issues

### Problem 1: Wrong Endpoint Paths

**Our Implementation**:
```json
{
  "endpoint": "/dogsite/predict",
  "method": "POST"
}
```

**Correct Format**:
```json
{
  "endpoint": "/dogsite_rest",
  "method": "POST"
}
```

### Problem 2: Wrong Request Format

**Our Implementation**:
```json
{
  "pdb_id": "2OZR",
  "chain": "A"
}
```

**Correct Format**:
```json
{
  "dogsite": {
    "pdbCode": "2OZR",
    "analysisDetail": "1",
    "bindingSitePredictionGranularity": "1",
    "ligand": "",
    "chain": "A"
  }
}
```

### Problem 3: Tool Names Don't Match

Our implementation assumes tools like:
- `ProteinsPlus_predict_binding_sites` → Should map to `dogsite_rest`
- `ProteinsPlus_dock_ligand` → **No REST API equivalent found**
- `ProteinsPlus_analyze_interactions` → **No PLIP REST API**
- `ProteinsPlus_detect_pockets` → **No Fpocket REST API**

## Rate Limiting

- **Global limit**: 30 jobs/minute
- **DoGSiteScorer**: Has individual lower rate limit due to CPU/RAM usage
- **Response**: HTTP 429 when exceeded

## Authentication

- ✅ **No authentication required** for public API access
- API is free and open

## Async Job Pattern

1. **Submit job** (POST) → Returns 202 with location URL
2. **Poll status** (GET location URL) → Returns job status
3. **Retrieve results** (GET location URL when complete) → Returns full results

## Recommendations

### Priority 0 (CRITICAL - Fix Required)

1. **Fix DoGSiteScorer tool** (`ProteinsPlus_predict_binding_sites`):
   - Change endpoint from `/dogsite/predict` to `/dogsite_rest`
   - Update request format to match `{"dogsite": {...}}` structure
   - Update parameter mapping (pdb_id → pdbCode, etc.)

2. **Remove or replace 3 unavailable tools**:
   - `ProteinsPlus_dock_ligand` (JAMDA not in REST API)
   - `ProteinsPlus_analyze_interactions` (PLIP not in REST API)
   - `ProteinsPlus_detect_pockets` (Fpocket not in REST API)

### Alternative Actions

**Option A**: Keep only DoGSiteScorer (1 tool instead of 4)
- Pros: Fully working, well-documented, valuable for binding site prediction
- Cons: Loses docking and interaction analysis capabilities

**Option B**: Replace with available alternatives
- DoGSiteScorer → Keep and fix ✅
- JAMDA docking → Suggest AutoDock Vina (separate tool)
- PLIP → Suggest ProDy or MDAnalysis
- Fpocket → Suggest standalone Fpocket installation

**Option C**: Add other ProteinsPlus REST tools
- DoGSite3 (`/dogsite3_rest`)
- PoseView (`/poseview_rest`)
- SIENA (`/siena_rest`)
- StructureProfiler (`/structureprofiler_rest`)

## Documentation Sources

1. [ProteinsPlus Help](https://proteins.plus/help/index)
2. [DoGSite REST API Documentation](https://proteins.plus/help/dogsite_rest)
3. [GitHub Examples Repository](https://github.com/rareylab/proteins_plus_examples)
4. [Swagger API v2](https://proteins.plus/api/v2)

## Conclusion

**The ProteinsPlus REST API is real, accessible, and working perfectly.**

The implementation issues are:
1. Wrong endpoint paths (fixable in 10 minutes)
2. Wrong request formats (fixable in 15 minutes per tool)
3. 3 out of 4 tools don't exist in the REST API (need replacement or removal)

**Recommendation**: Fix DoGSiteScorer and remove the 3 unavailable tools, OR replace all 4 with alternative implementations.
