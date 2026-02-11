# Testing Quick Start Guide - 32 New Tools

**For:** QA Team / Testing Agent
**Date:** 2026-02-08
**Purpose:** Rapid testing protocol for newly implemented tools

---

## Quick Start (5 Minutes)

### Step 1: Verify Tool Loading

```bash
cd /Users/shgao/logs/25.05.28tooluniverse/codes/ToolUniverse-auto
python manual_test_quick.py
```

Expected output: 32/32 tools loaded ✅

### Step 2: Run Basic Tests (No Auth Required)

```bash
# Test best-implemented tools (NCBI SRA)
python scripts/test_new_tools.py NCBI_SRA -v

# Test STRING tools
python scripts/test_new_tools.py STRING -v

# Test ICD-10 tools
python scripts/test_new_tools.py ICD10 -v

# Test LOINC tools
python scripts/test_new_tools.py LOINC -v

# Test SASBDB tools
python scripts/test_new_tools.py SASBDB -v
```

**Expected Pass Rate**: 80-100% (21 tools should work)

### Step 3: Check ProteinsPlus API

```bash
# Manual API test
curl -X POST https://proteins.plus/api/dogsite/predict \
  -H "Content-Type: application/json" \
  -d '{"pdb_id": "1A2B"}' \
  --max-time 10

# If this fails with 404 or timeout, ProteinsPlus API is not accessible
```

---

## Detailed Testing Protocol

### Phase 1: Public API Tools (21 tools - 30 min)

#### 1. NCBI SRA Tools (4 tools) ⭐ HIGHEST PRIORITY
```bash
python scripts/test_new_tools.py NCBI_SRA -v
```

**Why first**: Best implemented, fully tested, production-ready

**Expected Results**:
- ✅ NCBI_SRA_search_runs: Should return SRA UIDs
- ✅ NCBI_SRA_get_run_info: Should return detailed metadata
- ✅ NCBI_SRA_get_download_urls: Should return FTP/S3 URLs
- ✅ NCBI_SRA_link_to_biosample: Should return BioSample UIDs

**If fails**: 🔴 CRITICAL - Check implementation file exists

#### 2. STRING Tools (6 tools)
```bash
python scripts/test_new_tools.py STRING -v
```

**Expected Results**:
- ✅ STRING_map_identifiers: Should map TP53 to STRING ID
- ✅ STRING_get_network: Should return interaction network
- ✅ STRING_functional_enrichment: Should return GO terms/pathways
- Others should also pass

**If fails**: 🟡 Check if STRINGRESTTool implementation exists

#### 3. ICD-10 Tools (2 tools)
```bash
python scripts/test_new_tools.py ICD10 -v
```

**Expected Results**:
- ✅ ICD10_search_codes: Should return diabetes codes
- ✅ ICD10_get_code_info: Should return E11.9 details

**If fails**: 🟡 Check NLM Clinical Tables API availability

#### 4. LOINC Tools (4 tools)
```bash
python scripts/test_new_tools.py LOINC -v
```

**Expected Results**:
- ✅ LOINC_search_tests: Should return cholesterol test codes
- ✅ LOINC_get_code_details: Should return 2093-3 details
- ✅ LOINC_get_answer_list: Should return blood type values
- ✅ LOINC_search_forms: Should return PHQ-9 form

**If fails**: 🟡 Check NLM Clinical Tables API availability

#### 5. SASBDB Tools (5 tools)
```bash
python scripts/test_new_tools.py SASBDB -v
```

**Expected Results**:
- ✅ SASBDB_search_entries: Should return lysozyme entries
- ✅ SASBDB_get_entry_data: Should return SASDBA2 metadata
- ✅ SASBDB_get_scattering_profile: Should return I(q) data
- ✅ SASBDB_get_models: Should return model info
- ✅ SASBDB_download_data: Should return download URLs

**If fails**: 🟡 Check SASBDB REST API availability or type name typo

---

### Phase 2: Authenticated API Tools (7 tools - 1 hour)

#### Setup API Keys First

**BioGRID (4 tools)**:
```bash
# 1. Register at https://webservice.thebiogrid.org/
# 2. Get API key from email
# 3. Set environment variable:
export BIOGRID_ACCESS_KEY="your_api_key_here"
```

**ICD-11 (3 tools)**:
```bash
# 1. Register at https://icd.who.int/icdapi
# 2. Create application
# 3. Get Client ID and Secret
# 4. Set environment variables:
export ICD_CLIENT_ID="your_client_id"
export ICD_CLIENT_SECRET="your_client_secret"
```

#### Run Tests

```bash
# Test BioGRID tools
python scripts/test_new_tools.py BioGRID -v

# Test ICD-11 tools
python scripts/test_new_tools.py ICD11 -v
```

**Expected Results**:
- ✅ All 7 tools should pass if API keys are valid
- ⏭️ Tools will be skipped if keys missing

**If fails**:
- Check API key validity
- Check environment variables are set
- Verify API endpoints are accessible

---

### Phase 3: ProteinsPlus Tools (4 tools - UNCERTAIN)

#### Critical Pre-Test

```bash
# Test API accessibility
curl -v https://proteins.plus/api/dogsite/predict 2>&1 | grep "HTTP"
```

**Possible Outcomes**:

1. **200 OK**: API is accessible → Proceed with testing
2. **404 Not Found**: API endpoint wrong or not public
3. **403 Forbidden**: May require authentication
4. **Timeout**: API not responding

#### If API Accessible

```bash
python scripts/test_new_tools.py ProteinsPlus -v
```

**Note**: These are ASYNCHRONOUS tools with long wait times:
- ProteinsPlus_check_structure: ~2 minutes
- ProteinsPlus_predict_binding_sites: ~15 minutes
- ProteinsPlus_dock_ligand: ~30 minutes
- ProteinsPlus_analyze_interactions: ~5 minutes

#### If API Not Accessible

Document the following in test report:
- ❌ ProteinsPlus API not publicly accessible
- 📝 Tools configured but cannot be tested
- 🔄 Recommend alternatives:
  - AutoDock Vina for docking
  - PLIP (local) for interaction analysis
  - Fpocket for binding site prediction
- 🎯 Consider marking as "local installation only"

---

## Common Issues & Solutions

### Issue 1: Tool Not Found
```
Error: Tool 'STRING_get_network' not found
```

**Solution**:
```bash
# Check if tool is loaded
python -c "from tooluniverse import ToolUniverse; tu = ToolUniverse(); tu.load_tools(); print('STRING_get_network' in tu.tools)"
```

If False:
- Check JSON config file exists
- Check registration in default_config.py
- Check for JSON syntax errors

### Issue 2: Import Error
```
ModuleNotFoundError: No module named 'tooluniverse'
```

**Solution**:
```bash
# Ensure you're in repo root
cd /Users/shgao/logs/25.05.28tooluniverse/codes/ToolUniverse-auto

# Install package
pip install -e .

# Or add to path
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
```

### Issue 3: API Connection Error
```
Error: Connection refused / Timeout
```

**Solution**:
- Check internet connectivity
- Verify API endpoint is correct
- Check if API requires VPN/institutional access
- Try manual curl test to isolate issue

### Issue 4: Rate Limiting
```
Error: 429 Too Many Requests
```

**Solution**:
- Add delays between tests (already in test script)
- For NCBI: Use API key for higher limits
- Wait and retry

### Issue 5: Authentication Error
```
Error: 401 Unauthorized / 403 Forbidden
```

**Solution**:
- Verify API keys are set correctly
- Check key validity (may have expired)
- Ensure keys are for correct environment (dev/prod)
- Re-register if needed

---

## Test Results Checklist

Use this checklist to track testing progress:

### Configuration Validation ✅
- [ ] All 32 tools load successfully
- [ ] All tools registered in default_config.py
- [ ] All tool names < 55 characters
- [ ] All test examples valid JSON

### Public API Tools (21 tools)
**NCBI SRA (4 tools)**
- [ ] NCBI_SRA_search_runs
- [ ] NCBI_SRA_get_run_info
- [ ] NCBI_SRA_get_download_urls
- [ ] NCBI_SRA_link_to_biosample

**STRING (6 tools)**
- [ ] STRING_get_protein_interactions
- [ ] STRING_get_interaction_partners
- [ ] STRING_functional_enrichment
- [ ] STRING_map_identifiers
- [ ] STRING_get_network
- [ ] STRING_ppi_enrichment

**ICD-10 (2 tools)**
- [ ] ICD10_search_codes
- [ ] ICD10_get_code_info

**LOINC (4 tools)**
- [ ] LOINC_search_tests
- [ ] LOINC_get_code_details
- [ ] LOINC_get_answer_list
- [ ] LOINC_search_forms

**SASBDB (5 tools)**
- [ ] SASBDB_search_entries
- [ ] SASBDB_get_entry_data
- [ ] SASBDB_get_scattering_profile
- [ ] SASBDB_get_models
- [ ] SASBDB_download_data

### Authenticated API Tools (7 tools)
**BioGRID (4 tools)**
- [ ] BioGRID_get_interactions
- [ ] BioGRID_get_chemical_interactions
- [ ] BioGRID_search_by_pubmed
- [ ] BioGRID_get_ptms

**ICD-11 (3 tools)**
- [ ] ICD11_search_diseases
- [ ] ICD11_get_entity
- [ ] ICD11_browse_hierarchy

### ProteinsPlus (4 tools - Uncertain)
- [ ] ProteinsPlus_predict_binding_sites
- [ ] ProteinsPlus_dock_ligand
- [ ] ProteinsPlus_analyze_interactions
- [ ] ProteinsPlus_check_structure

### Integration Tests
- [ ] STRING workflow (map → network → enrichment)
- [ ] NCBI SRA workflow (search → info → URLs → biosample)
- [ ] Clinical workflow (ICD search → LOINC tests)
- [ ] SASBDB workflow (search → entry → scattering → models)

---

## Success Criteria

### Minimum Acceptable
- ✅ 21/32 tools pass (all public API tools)
- ✅ NCBI SRA tools work (highest priority)
- ✅ No critical implementation errors
- 📝 ProteinsPlus status documented

### Target
- ✅ 28/32 tools pass (21 public + 7 authenticated)
- ✅ All authenticated tools work with valid keys
- ✅ Integration workflows validated
- 📝 Complete test documentation

### Excellent
- ✅ 32/32 tools pass
- ✅ ProteinsPlus API accessible and working
- ✅ All workflows tested
- ✅ Performance benchmarks documented
- 📚 User documentation complete

---

## Reporting Template

Use this template for final test report:

```markdown
# Test Execution Report - 32 New Tools

**Date**: [Date]
**Tester**: [Name]
**Duration**: [Time]

## Results Summary
- **Total Tools**: 32
- **Passed**: X
- **Failed**: Y
- **Skipped** (no auth): Z
- **Pass Rate**: X%

## Detailed Results

### Public API Tools (21 expected)
- NCBI SRA: X/4
- STRING: X/6
- ICD-10: X/2
- LOINC: X/4
- SASBDB: X/5

### Authenticated Tools (7 expected)
- BioGRID: X/4 (API key: [✅/❌])
- ICD-11: X/3 (API key: [✅/❌])

### ProteinsPlus Tools (4 uncertain)
- API Status: [Accessible/Not Accessible/Unknown]
- Tools Tested: X/4

## Critical Issues
[List any critical failures]

## Recommendations
[List recommendations for fixes]

## Next Steps
[List next steps]
```

---

## Quick Reference

### API Endpoints
- STRING: `https://string-db.org/api/`
- BioGRID: `https://webservice.thebiogrid.org/`
- NCBI: `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/`
- ICD-11: `https://id.who.int/icd/release/11/2024-01/`
- NLM Tables: `https://clinicaltables.nlm.nih.gov/api/`
- SASBDB: `https://www.sasbdb.org/rest-api/`
- ProteinsPlus: `https://proteins.plus/` (web interface)

### Key Files
- Test script: `scripts/test_new_tools.py`
- Quick test: `manual_test_quick.py`
- Config: `src/tooluniverse/default_config.py`
- Tool JSONs: `src/tooluniverse/data/*.json`

### Environment Variables
```bash
# BioGRID
export BIOGRID_ACCESS_KEY="your_key"

# ICD-11
export ICD_CLIENT_ID="your_id"
export ICD_CLIENT_SECRET="your_secret"

# NCBI (optional, for higher rate limits)
export NCBI_API_KEY="your_key"
```

---

## Support

**Questions?** Check detailed reports:
- TEST_REPORT_SYSTEMS_BIOLOGY.md
- TEST_REPORT_GENOMICS.md
- TEST_REPORT_CLINICAL.md
- TEST_REPORT_STRUCTURAL.md
- TEST_SUMMARY.md

**Issues?** Contact development team or use `/devtu-fix-tool` skill

---

**Good luck with testing!** 🚀
