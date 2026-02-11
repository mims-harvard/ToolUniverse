# DepMap Tools Issue Analysis & Solutions

**Date**: 2026-02-09
**Status**: 🔴 **CRITICAL** - All DepMap REST APIs are down
**Impact**: CRISPR Screen Analysis skill 30% non-functional (PATH 0 & 1 blocked)

---

## Root Cause Analysis

### Issue: DepMap REST APIs are Non-Operational

Testing revealed that **both major DepMap REST APIs are currently unavailable**:

#### 1. Sanger Cell Model Passports API
- **URL**: `https://api.cellmodelpassports.sanger.ac.uk`
- **Status**: 404 Not Found (all endpoints)
- **Error**: "404 page not found"
- **Test Results**:
  - `/genes` endpoint: 404
  - `/models` endpoint: 404
  - `/swagger` docs: 404
  - Main site `https://depmap.sanger.ac.uk`: 404

#### 2. Broad Institute DepMap API (NCATS)
- **URL**: `https://indigo.ncats.io/depmap`
- **Status**: Connection timeout (75+ seconds)
- **Error**: "Failed to connect to indigo.ncats.io port 443"
- **Test Results**:
  - `/cell_lines` endpoint: Timeout
  - `/gene_dependency/*` endpoints: Timeout

### Impact on ToolUniverse

**Affected Tools (5 total)**:
1. `DepMap_search_genes` - Returns `{"status": "error", "error": "...404..."}`
2. `DepMap_get_gene_dependencies` - Returns `{"status": "error", "error": "...404..."}`
3. `DepMap_get_cell_lines` - Returns `{"status": "error", "error": "...404..."}`
4. `DepMap_get_cell_line` - Returns `{"status": "error", "error": "...404..."}`
5. `DepMap_search_cell_lines` - Returns `{"status": "error", "error": "...404..."}`

**Affected Skills**:
- **CRISPR Screen Analysis** (HIGH PRIORITY):
  - PATH 0 (Gene Validation): ❌ BLOCKED
  - PATH 1 (Essentiality Analysis): ❌ BLOCKED
  - Overall workflow: 30% non-functional

---

## Solutions

### Solution 1: Use DepMap MCP Server (RECOMMENDED) ⭐

**Status**: Already implemented in ToolUniverse

**Location**: `src/tooluniverse/remote/depmap_24q2/depmap_24q2_mcp_tool.py`

**How it works**:
- Uses predownloaded DepMap 24Q2 correlation data
- Analyzes gene-gene correlations from CRISPR knockout screens
- Covers 1,320+ cancer cell lines
- No external API calls needed (local data)

**Setup Requirements**:
1. Download DepMap 24Q2 correlation matrices
2. Set environment variable: `export DEPMAP_DATA_PATH=/path/to/data`
3. Data files needed:
   - `gene_correlations.h5` (sparse format) OR
   - `corr_matrix.npy` + `p_val_matrix.npy` (dense format)
   - `gene_names.txt` or `gene_idx_array.npy`

**Tool Available**:
- `compute_depmap24q2_gene_correlations(gene_a, gene_b)` - Gene-gene correlation analysis

**Limitations**:
- Only provides correlation data, not essentiality scores for individual genes
- Requires local data download (~several GB)
- Does not replace full DepMap API functionality

**Data Source**: [DepMap Portal Downloads](https://depmap.org/portal/data_page/?tab=currentRelease)

---

### Solution 2: Download & Cache DepMap CSV Files

**Approach**: Modify DepMap tool to download and cache CSV files locally

**Data Available from DepMap 25Q3 Release**:
- `Achilles_gene_effect.csv` - CRISPR gene effect scores (essentiality)
- `sample_info.csv` - Cell line metadata
- `CCLE_expression.csv` - Gene expression data
- `CRISPR_gene_dependency.csv` - Gene dependency scores

**Implementation Steps**:
1. Download CSV files from depmap.org on first use
2. Cache locally (e.g., `~/.tooluniverse/depmap_cache/`)
3. Update automatically on new releases
4. Parse CSV files for gene/cell line queries

**Advantages**:
- ✅ Full functionality (gene search, essentiality, cell lines)
- ✅ No external API dependency
- ✅ Data is official and complete

**Disadvantages**:
- ❌ Large download size (~2-5 GB total)
- ❌ Slower first-time use (download + parsing)
- ❌ Requires implementation work (2-3 days)

**Priority**: HIGH (recommended for full feature parity)

---

### Solution 3: Fallback to Alternative Tools

**Approach**: Use other gene essentiality databases when DepMap fails

**Alternative Tools**:

#### A. Open Targets Platform
- **Tool**: `OpenTargets_get_target`
- **Data**: Includes tractability, safety, essentiality info
- **Coverage**: Gene-level essentiality from multiple sources
- **Status**: ✅ Working in ToolUniverse

#### B. CCLE (Cancer Cell Line Encyclopedia)
- **Tool**: Currently not wrapped in ToolUniverse
- **Data**: Gene expression, mutations, drug sensitivity
- **Coverage**: 1,000+ cell lines (overlaps with DepMap)
- **Status**: ❌ Needs implementation

#### C. GeneSCF / GeneWalk
- **Tool**: Currently not wrapped
- **Data**: Functional annotation, pathway essentiality
- **Status**: ❌ Needs implementation

**Implementation**:
- Add fallback logic in CRISPR skill: `if DepMap fails → try Open Targets`
- Document alternative data sources in skill
- Provide evidence grading (DepMap = ★★★, Open Targets = ★★☆)

**Priority**: MEDIUM (quick win, but less comprehensive than DepMap)

---

### Solution 4: R/Bioconductor DepMap Package

**Approach**: Use R package to access DepMap data programmatically

**Package**: `depmap` (Bioconductor)
- **Function**: `depmap_crispr()` - Loads CRISPR knockout data
- **Coverage**: Latest DepMap releases
- **Status**: Requires R integration

**Implementation**:
- Add R subprocess call from Python
- Parse R data frames → JSON
- Cache results

**Advantages**:
- ✅ Well-maintained package
- ✅ Automatic updates

**Disadvantages**:
- ❌ Requires R installation
- ❌ Slower (subprocess overhead)
- ❌ Complex dependency

**Priority**: LOW (adds complexity, Solution 2 is better)

---

## Recommended Action Plan

### Phase 1: Immediate Fix (TODAY)

**Goal**: Make CRISPR skill functional with minimal work

1. **Update CRISPR skill documentation** (15 minutes)
   - Add warning that DepMap tools are temporarily unavailable
   - Document workaround using Open Targets
   - Update PATH 0 & 1 to use fallback tools

2. **Implement fallback in skill** (1 hour)
   - PATH 0: Use `OpenTargets_get_target()` for gene validation
   - PATH 1: Skip essentiality analysis OR use Open Targets tractability
   - Add note: "DepMap unavailable, using Open Targets (reduced data)"

**Expected Outcome**: CRISPR skill 20% → 60% functional

---

### Phase 2: Sustainable Fix (THIS WEEK)

**Goal**: Implement CSV download solution for full functionality

1. **Create DepMap data downloader** (4 hours)
   ```python
   # depmap_data_manager.py
   class DepMapDataManager:
       def __init__(self, cache_dir="~/.tooluniverse/depmap_cache"):
           self.cache_dir = cache_dir

       def download_latest_release(self):
           # Download CSV files from depmap.org/portal/download/
           # Cache locally
           pass

       def get_gene_essentiality(self, gene_symbol):
           # Parse Achilles_gene_effect.csv
           pass

       def search_cell_lines(self, query):
           # Parse sample_info.csv
           pass
   ```

2. **Update DepMap tool implementation** (4 hours)
   - Replace REST API calls with CSV parsing
   - Add automatic download on first use
   - Add cache invalidation (30 days)

3. **Test all 5 DepMap tools** (2 hours)
   - Verify return schemas match original
   - Test with CRISPR skill
   - Update test examples

**Total Time**: 10 hours (1.5 days)

**Expected Outcome**: CRISPR skill 100% functional, all DepMap tools working

---

### Phase 3: MCP Server Integration (OPTIONAL)

**Goal**: Leverage existing MCP server for correlation analysis

1. **Check if DepMap MCP is registered** (30 minutes)
   - Verify tool loads into ToolUniverse
   - Test `compute_depmap24q2_gene_correlations()`

2. **Update CRISPR skill to use MCP tool** (1 hour)
   - Add PATH 3B: Use DepMap MCP for PPI correlation analysis
   - Document as premium feature (requires data download)

**Total Time**: 1.5 hours

**Expected Outcome**: Enhanced PPI analysis in CRISPR skill

---

## Cost-Benefit Analysis

| Solution | Time to Implement | Functionality | Maintenance | Priority |
|----------|-------------------|---------------|-------------|----------|
| **Fallback to Open Targets** | 1 hour | 60% | LOW | 🟢 HIGH |
| **CSV Download** | 10 hours | 100% | LOW | 🟢 HIGH |
| **MCP Server** | 1.5 hours | 50% (correlation only) | MEDIUM | 🟡 MEDIUM |
| **R Package** | 8 hours | 100% | HIGH | 🔴 LOW |

**Recommended Path**: Implement both **Fallback** (today) + **CSV Download** (this week)

---

## Documentation Updates Needed

### 1. CRISPR Screen Analysis Skill
- [ ] Add "Known Issues" section to README.md
- [ ] Update EXAMPLES.md with fallback tool usage
- [ ] Modify SKILL.md PATH 0 & 1 to document alternatives
- [ ] Add troubleshooting section

### 2. DepMap Tools
- [ ] Update depmap_tools.json descriptions to note CSV backend
- [ ] Add setup instructions (auto-download on first use)
- [ ] Document cache location and manual download option
- [ ] Update test examples to reflect new behavior

### 3. TEST_REPORT_CRISPR.md
- [ ] Add resolution notes
- [ ] Update "What's Fixed" section
- [ ] Document final success rate after fixes

---

## References

**Data Sources**:
- [DepMap Portal Downloads](https://depmap.org/portal/data_page/?tab=currentRelease) - Official CSV downloads
- [DepMap 25Q3 Release Notes](https://depmap.org/portal/) - Latest release info
- [GitHub: broadinstitute/depmap-api](https://github.com/broadinstitute/depmap-api) - API repository (outdated)
- [Bioconductor depmap package](https://www.bioconductor.org/packages/release/data/experiment/html/depmap.html) - R package

**Technical Documentation**:
- [Harmonizome: DepMap CRISPR Gene Dependency](https://maayanlab.cloud/Harmonizome/dataset/DepMap+CRISPR+Gene+Dependency)
- [ToolUniverse DepMap MCP Server Docs](https://zitniklab.hms.harvard.edu/ToolUniverse/tools/remote/depmap_24q2.html)

**Related Test Reports**:
- `TEST_REPORT_CRISPR.md` - Detailed DepMap failure analysis
- `test_depmap_debug.py` - Debug script showing API failures

---

## Next Steps

**Immediate (TODAY)**:
1. ✅ Document root cause (this file)
2. ⏭️ Implement Open Targets fallback (1 hour)
3. ⏭️ Update CRISPR skill documentation

**This Week**:
4. ⏭️ Implement CSV download solution (10 hours)
5. ⏭️ Test all DepMap tools with new backend
6. ⏭️ Update TEST_REPORT_CRISPR.md with resolution

**Future**:
7. ⏭️ Integrate DepMap MCP server for correlation analysis
8. ⏭️ Create automated data update mechanism

---

*Analysis completed: 2026-02-09*
*Priority: CRITICAL - Blocks CRISPR Screen Analysis skill*
*Estimated fix time: 1 hour (fallback) + 10 hours (full solution) = 11 hours total*
