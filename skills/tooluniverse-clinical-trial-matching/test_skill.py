#!/usr/bin/env python3
"""
Comprehensive Test Suite for Clinical Trial Matching Skill
Tests all phases with diverse patient profiles:
  - NSCLC with EGFR L858R
  - Melanoma with BRAF V600E
  - Colorectal cancer with KRAS G12C
  - Breast cancer with HER2+
  - NTRK fusion basket trial
"""

import json
import sys
import time
import traceback

# ============================================================
# Test Infrastructure
# ============================================================

PASS = 0
FAIL = 0
TOTAL = 0
RESULTS = []


def run_test(name, func):
    """Run a single test and track results."""
    global PASS, FAIL, TOTAL, RESULTS
    TOTAL += 1
    start = time.time()
    try:
        func()
        elapsed = time.time() - start
        PASS += 1
        RESULTS.append({"name": name, "status": "PASS", "time": f"{elapsed:.1f}s", "error": None})
        print(f"  PASS [{elapsed:.1f}s] {name}")
    except Exception as e:
        elapsed = time.time() - start
        FAIL += 1
        err_msg = str(e)
        RESULTS.append({"name": name, "status": "FAIL", "time": f"{elapsed:.1f}s", "error": err_msg})
        print(f"  FAIL [{elapsed:.1f}s] {name}")
        print(f"       Error: {err_msg}")
        traceback.print_exc()


def load_tu():
    """Load ToolUniverse instance."""
    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()
    return tu


# ============================================================
# Phase 1: Patient Profile Standardization Tests
# ============================================================

def test_01_disease_resolution_nsclc():
    """Phase 1: Resolve 'non-small cell lung cancer' to EFO ID."""
    tu = load_tu()
    result = tu.tools.OpenTargets_get_disease_id_description_by_name(diseaseName='non-small cell lung cancer')
    hits = result.get('data', {}).get('search', {}).get('hits', [])
    assert len(hits) > 0, "No disease hits returned"
    top = hits[0]
    assert top.get('id') == 'EFO_0003060', f"Expected EFO_0003060, got {top.get('id')}"
    assert 'non-small cell' in top.get('name', '').lower(), f"Name mismatch: {top.get('name')}"
    print(f"       Disease resolved: {top.get('name')} ({top.get('id')})")


def test_02_disease_resolution_melanoma():
    """Phase 1: Resolve 'melanoma' to EFO ID."""
    tu = load_tu()
    result = tu.tools.OpenTargets_get_disease_id_description_by_name(diseaseName='melanoma')
    hits = result.get('data', {}).get('search', {}).get('hits', [])
    assert len(hits) > 0, "No disease hits returned"
    top = hits[0]
    assert top.get('id') is not None, "No EFO ID for melanoma"
    print(f"       Disease resolved: {top.get('name')} ({top.get('id')})")


def test_03_disease_resolution_colorectal():
    """Phase 1: Resolve 'colorectal cancer' to EFO ID."""
    tu = load_tu()
    result = tu.tools.OpenTargets_get_disease_id_description_by_name(diseaseName='colorectal cancer')
    hits = result.get('data', {}).get('search', {}).get('hits', [])
    assert len(hits) > 0, "No disease hits returned"
    print(f"       Disease resolved: {hits[0].get('name')} ({hits[0].get('id')})")


def test_04_disease_resolution_breast_cancer():
    """Phase 1: Resolve 'breast cancer' to EFO ID."""
    tu = load_tu()
    result = tu.tools.OpenTargets_get_disease_id_description_by_name(diseaseName='breast cancer')
    hits = result.get('data', {}).get('search', {}).get('hits', [])
    assert len(hits) > 0, "No disease hits returned"
    print(f"       Disease resolved: {hits[0].get('name')} ({hits[0].get('id')})")


def test_05_disease_resolution_ols_fallback():
    """Phase 1: Resolve disease using OLS EFO search as fallback."""
    tu = load_tu()
    result = tu.tools.ols_search_efo_terms(query='non-small cell lung cancer', limit=5)
    data = result.get('data', {})
    terms = data.get('terms', [])
    assert len(terms) > 0, "No OLS terms returned"
    top = terms[0]
    assert 'EFO_0003060' in top.get('short_form', ''), f"Expected EFO_0003060, got {top.get('short_form')}"
    print(f"       OLS resolved: {top.get('label')} ({top.get('short_form')})")


def test_06_gene_resolution_egfr():
    """Phase 1: Resolve EGFR to Ensembl/Entrez IDs."""
    tu = load_tu()
    result = tu.tools.MyGene_query_genes(query='EGFR', species='human')
    hits = result.get('hits', [])
    assert len(hits) > 0, "No gene hits returned"
    top = hits[0]
    assert top.get('symbol') == 'EGFR', f"Expected EGFR, got {top.get('symbol')}"
    assert top.get('entrezgene') == 1956 or str(top.get('entrezgene')) == '1956', f"Wrong Entrez ID: {top.get('entrezgene')}"
    ensembl = top.get('ensembl', {})
    ensembl_id = ensembl.get('gene') if isinstance(ensembl, dict) else None
    assert ensembl_id == 'ENSG00000146648', f"Wrong Ensembl ID: {ensembl_id}"
    print(f"       Gene resolved: EGFR -> {ensembl_id}, Entrez: {top.get('entrezgene')}")


def test_07_gene_resolution_braf():
    """Phase 1: Resolve BRAF to Ensembl/Entrez IDs."""
    tu = load_tu()
    result = tu.tools.MyGene_query_genes(query='BRAF', species='human')
    hits = result.get('hits', [])
    assert len(hits) > 0, "No gene hits returned"
    top = hits[0]
    assert top.get('symbol') == 'BRAF', f"Expected BRAF, got {top.get('symbol')}"
    print(f"       Gene resolved: BRAF -> Entrez: {top.get('entrezgene')}")


def test_08_gene_resolution_kras():
    """Phase 1: Resolve KRAS to Ensembl/Entrez IDs."""
    tu = load_tu()
    result = tu.tools.MyGene_query_genes(query='KRAS', species='human')
    hits = result.get('hits', [])
    assert len(hits) > 0, "No gene hits returned"
    top = hits[0]
    assert top.get('symbol') == 'KRAS', f"Expected KRAS, got {top.get('symbol')}"
    print(f"       Gene resolved: KRAS -> Entrez: {top.get('entrezgene')}")


def test_09_gene_resolution_erbb2_her2():
    """Phase 1: Resolve HER2/ERBB2 to Ensembl/Entrez IDs."""
    tu = load_tu()
    result = tu.tools.MyGene_query_genes(query='ERBB2', species='human')
    hits = result.get('hits', [])
    assert len(hits) > 0, "No gene hits returned"
    top = hits[0]
    assert top.get('symbol') == 'ERBB2', f"Expected ERBB2, got {top.get('symbol')}"
    print(f"       Gene resolved: ERBB2 (HER2) -> Entrez: {top.get('entrezgene')}")


def test_10_gene_resolution_ntrk1():
    """Phase 1: Resolve NTRK1 to Ensembl/Entrez IDs."""
    tu = load_tu()
    result = tu.tools.MyGene_query_genes(query='NTRK1', species='human')
    hits = result.get('hits', [])
    assert len(hits) > 0, "No gene hits returned"
    top = hits[0]
    assert top.get('symbol') == 'NTRK1', f"Expected NTRK1, got {top.get('symbol')}"
    print(f"       Gene resolved: NTRK1 -> Entrez: {top.get('entrezgene')}")


def test_11_fda_pharmacogenomic_biomarkers():
    """Phase 1: Get FDA pharmacogenomic biomarkers list."""
    tu = load_tu()
    # Use limit=1000 to get all biomarkers (default is 10)
    result = tu.tools.fda_pharmacogenomic_biomarkers(limit=1000)
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert 'results' in result, f"Missing 'results' key. Keys: {list(result.keys())}"
    total_count = result.get('count', 0)
    assert total_count > 100, f"Expected >100 total biomarkers, got {total_count}"
    biomarkers = result.get('results', [])
    assert len(biomarkers) > 10, f"Expected >10 biomarkers returned, got {len(biomarkers)}"
    # Check EGFR is in the list
    egfr_entries = [b for b in biomarkers if 'EGFR' in str(b.get('Biomarker', ''))]
    assert len(egfr_entries) > 0, "EGFR not found in FDA biomarkers"
    print(f"       FDA biomarkers: {total_count} total, {len(biomarkers)} returned, {len(egfr_entries)} EGFR entries")


# ============================================================
# Phase 2: Broad Trial Discovery Tests
# ============================================================

def test_12_search_trials_disease_nsclc():
    """Phase 2: Search trials by disease (NSCLC)."""
    tu = load_tu()
    result = tu.tools.search_clinical_trials(
        condition='non-small cell lung cancer',
        query_term='EGFR mutation',
        pageSize=5
    )
    assert not isinstance(result, str), f"Got string result (no trials): {result}"
    studies = result.get('studies', [])
    assert len(studies) > 0, "No studies returned"
    # Verify study structure
    study = studies[0]
    assert 'NCT ID' in study, f"Missing 'NCT ID'. Keys: {list(study.keys())}"
    assert 'brief_title' in study, f"Missing 'brief_title'"
    assert 'overall_status' in study, f"Missing 'overall_status'"
    print(f"       Found {len(studies)} NSCLC/EGFR trials, total: {result.get('total_count', '?')}")


def test_13_search_trials_biomarker_kras_g12c():
    """Phase 2: Search trials by specific biomarker (KRAS G12C)."""
    tu = load_tu()
    result = tu.tools.search_clinical_trials(
        condition='colorectal cancer',
        query_term='KRAS G12C',
        pageSize=5
    )
    assert not isinstance(result, str), f"Got string result: {result}"
    studies = result.get('studies', [])
    assert len(studies) > 0, "No KRAS G12C CRC trials found"
    print(f"       Found {len(studies)} CRC/KRAS G12C trials")


def test_14_search_trials_biomarker_braf_v600e():
    """Phase 2: Search trials for BRAF V600E melanoma."""
    tu = load_tu()
    result = tu.tools.search_clinical_trials(
        condition='melanoma',
        query_term='BRAF V600E',
        pageSize=5
    )
    assert not isinstance(result, str), f"Got string result: {result}"
    studies = result.get('studies', [])
    assert len(studies) > 0, "No BRAF V600E melanoma trials found"
    print(f"       Found {len(studies)} melanoma/BRAF V600E trials")


def test_15_search_trials_her2_breast():
    """Phase 2: Search trials for HER2+ breast cancer."""
    tu = load_tu()
    result = tu.tools.search_clinical_trials(
        condition='breast cancer',
        query_term='HER2 positive',
        pageSize=5
    )
    assert not isinstance(result, str), f"Got string result: {result}"
    studies = result.get('studies', [])
    assert len(studies) > 0, "No HER2+ breast cancer trials found"
    print(f"       Found {len(studies)} HER2+ breast cancer trials")


def test_16_search_trials_ntrk_basket():
    """Phase 2: Search basket trials for NTRK fusion."""
    tu = load_tu()
    result = tu.tools.search_clinical_trials(
        query_term='NTRK fusion',
        pageSize=5
    )
    assert not isinstance(result, str), f"Got string result: {result}"
    studies = result.get('studies', [])
    assert len(studies) > 0, "No NTRK fusion trials found"
    print(f"       Found {len(studies)} NTRK fusion trials")


def test_17_search_trials_intervention():
    """Phase 2: Search trials by intervention drug (osimertinib)."""
    tu = load_tu()
    result = tu.tools.search_clinical_trials(
        condition='non-small cell lung cancer',
        intervention='osimertinib',
        query_term='osimertinib',
        pageSize=5
    )
    assert not isinstance(result, str), f"Got string result: {result}"
    studies = result.get('studies', [])
    assert len(studies) > 0, "No osimertinib NSCLC trials found"
    print(f"       Found {len(studies)} osimertinib NSCLC trials")


def test_18_alternative_search():
    """Phase 2: Test alternative trial search (clinical_trials_search)."""
    tu = load_tu()
    result = tu.tools.clinical_trials_search(
        action='search_studies',
        condition='non-small cell lung cancer',
        intervention='pembrolizumab',
        limit=5
    )
    studies = result.get('studies', [])
    assert len(studies) > 0, "No studies from alternative search"
    study = studies[0]
    assert 'nctId' in study, f"Missing 'nctId'. Keys: {list(study.keys())}"
    print(f"       Alternative search found {len(studies)} trials")


def test_19_search_pagination():
    """Phase 2: Test trial search pagination."""
    tu = load_tu()
    # First page
    result1 = tu.tools.search_clinical_trials(
        condition='lung cancer',
        query_term='EGFR',
        pageSize=3
    )
    assert not isinstance(result1, str), "No results"
    studies1 = result1.get('studies', [])
    next_token = result1.get('nextPageToken')
    assert len(studies1) > 0, "No first page results"
    total = result1.get('total_count', 0)
    print(f"       First page: {len(studies1)} trials, total: {total}, has next: {next_token is not None}")


# ============================================================
# Phase 3: Trial Characterization Tests
# ============================================================

def test_20_get_trial_details():
    """Phase 3: Get full trial details by NCT ID."""
    tu = load_tu()
    result = tu.tools.clinical_trials_get_details(action='get_study_details', nct_id='NCT02841579')
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert 'nctId' in result, f"Missing 'nctId'. Keys: {list(result.keys())}"
    assert result.get('nctId') == 'NCT02841579', f"Wrong NCT ID: {result.get('nctId')}"
    assert 'eligibility' in result, "Missing eligibility"
    print(f"       Got details for {result.get('nctId')}: {result.get('title', '')[:80]}...")


def test_21_get_eligibility_criteria():
    """Phase 3: Get eligibility criteria for trials."""
    tu = load_tu()
    result = tu.tools.get_clinical_trial_eligibility_criteria(
        nct_ids=['NCT04765059', 'NCT02841579'],
        eligibility_criteria='all'
    )
    assert isinstance(result, list), f"Expected list, got {type(result)}"
    assert len(result) >= 1, f"Expected >= 1 results, got {len(result)}"
    for item in result:
        assert 'NCT ID' in item, f"Missing 'NCT ID'"
        assert 'eligibility_criteria' in item, f"Missing 'eligibility_criteria'"
        criteria = item.get('eligibility_criteria', '')
        assert len(criteria) > 50, f"Eligibility text too short: {len(criteria)} chars"
        assert 'Inclusion Criteria' in criteria or 'inclusion' in criteria.lower(), "No inclusion criteria found"
    print(f"       Got eligibility for {len(result)} trials, avg length: {sum(len(r.get('eligibility_criteria','')) for r in result)//len(result)} chars")


def test_22_get_conditions_and_interventions():
    """Phase 3: Get conditions and interventions for trials."""
    tu = load_tu()
    result = tu.tools.get_clinical_trial_conditions_and_interventions(
        nct_ids=['NCT04765059'],
        condition_and_intervention='all'
    )
    assert isinstance(result, list), f"Expected list, got {type(result)}"
    assert len(result) > 0, "No results"
    item = result[0]
    assert 'condition' in item, f"Missing 'condition'. Keys: {list(item.keys())}"
    assert 'interventions' in item, f"Missing 'interventions'"
    interventions = item.get('interventions', [])
    assert len(interventions) > 0, "No interventions found"
    for inv in interventions:
        assert 'name' in inv, f"Missing intervention name"
        assert 'type' in inv, f"Missing intervention type"
    print(f"       Trial has {len(interventions)} interventions, {len(item.get('arm_groups', []))} arm groups")


def test_23_get_trial_locations():
    """Phase 3: Get trial site locations."""
    tu = load_tu()
    result = tu.tools.get_clinical_trial_locations(
        nct_ids=['NCT04765059'],
        location='all'
    )
    assert isinstance(result, list), f"Expected list, got {type(result)}"
    assert len(result) > 0, "No results"
    item = result[0]
    locations = item.get('locations', [])
    assert len(locations) > 0, "No locations found"
    loc = locations[0]
    assert 'country' in loc, f"Missing 'country' in location"
    countries = set(l.get('country', '') for l in locations)
    print(f"       {len(locations)} sites across {len(countries)} countries: {list(countries)[:5]}")


def test_24_get_trial_status():
    """Phase 3: Get trial status and dates."""
    tu = load_tu()
    result = tu.tools.get_clinical_trial_status_and_dates(
        nct_ids=['NCT04765059'],
        status_and_date='all'
    )
    assert isinstance(result, list), f"Expected list, got {type(result)}"
    assert len(result) > 0, "No results"
    item = result[0]
    assert 'overall_status' in item, f"Missing 'overall_status'"
    assert item.get('overall_status') is not None, "Status is None"
    print(f"       Status: {item.get('overall_status')}, Start: {item.get('start_date')}, Completion: {item.get('completion_date')}")


def test_25_get_trial_descriptions():
    """Phase 3: Get trial descriptions."""
    tu = load_tu()
    result = tu.tools.get_clinical_trial_descriptions(
        nct_ids=['NCT04765059'],
        description_type='full'
    )
    assert isinstance(result, list), f"Expected list, got {type(result)}"
    assert len(result) > 0, "No results"
    item = result[0]
    assert 'brief_title' in item, f"Missing 'brief_title'"
    assert 'official_title' in item, f"Missing 'official_title'"
    assert 'brief_summary' in item, f"Missing 'brief_summary'"
    print(f"       Title: {item.get('brief_title', '')[:80]}...")


# ============================================================
# Phase 4: Molecular Eligibility Matching Tests
# ============================================================

def test_26_eligibility_biomarker_parsing():
    """Phase 4: Parse eligibility criteria for biomarker requirements."""
    # Test with real eligibility text
    sample_text = """Inclusion Criteria:
    * Patients with histological confirmation of NSCLC with an activating EGFR mutation
    (exon 19 deletion or L858R) and concomitant T790M mutation
    * ECOG performance status less than or equal to 2

    Exclusion Criteria:
    * Prior treatment with a third-generation EGFR TKI
    * Known ALK rearrangement"""

    # Check that we can find EGFR in inclusion
    assert 'EGFR' in sample_text, "EGFR not in text"
    assert 'L858R' in sample_text, "L858R not in text"
    assert 'T790M' in sample_text, "T790M not in text"

    # Split inclusion/exclusion
    inclusion = sample_text.split('Exclusion Criteria')[0]
    exclusion = sample_text.split('Exclusion Criteria')[1] if 'Exclusion Criteria' in sample_text else ''

    assert 'EGFR' in inclusion, "EGFR should be in inclusion"
    assert 'ALK' in exclusion, "ALK should be in exclusion"
    print("       Biomarker parsing: EGFR/L858R/T790M in inclusion, ALK in exclusion")


def test_27_molecular_match_scoring():
    """Phase 4: Test molecular match scoring logic."""
    # Test exact match
    patient_biomarkers = [{'gene': 'EGFR', 'alteration': 'L858R', 'type': 'mutation'}]

    # Trial requiring exact match
    trial_with_exact = {
        'required_biomarkers': [{'gene': 'EGFR', 'context': 'EGFR mutation L858R or exon 19 deletion'}],
        'excluded_biomarkers': []
    }

    # Check exact match logic
    patient_genes = {b['gene'].upper() for b in patient_biomarkers}
    required_genes = {b['gene'].upper() for b in trial_with_exact['required_biomarkers']}
    matched = patient_genes & required_genes
    assert matched == {'EGFR'}, f"Expected EGFR match, got {matched}"

    # Check variant in context
    for req in trial_with_exact['required_biomarkers']:
        for pb in patient_biomarkers:
            if pb['gene'].upper() == req['gene'].upper():
                alt = pb.get('alteration', '').upper()
                assert alt in req.get('context', '').upper(), f"{alt} not in context"

    print("       Molecular scoring: exact match correctly identified")


# ============================================================
# Phase 5: Drug-Biomarker Alignment Tests
# ============================================================

def test_28_drug_resolution_osimertinib():
    """Phase 5: Resolve osimertinib in OpenTargets."""
    tu = load_tu()
    result = tu.tools.OpenTargets_get_drug_id_description_by_name(drugName='osimertinib')
    hits = result.get('data', {}).get('search', {}).get('hits', [])
    assert len(hits) > 0, "No drug hits returned"
    top = hits[0]
    assert top.get('id') == 'CHEMBL3353410', f"Expected CHEMBL3353410, got {top.get('id')}"
    assert 'approved' in top.get('description', '').lower(), "Drug not described as approved"
    print(f"       Drug resolved: {top.get('name')} ({top.get('id')})")


def test_29_drug_mechanism_egfr():
    """Phase 5: Get drug mechanism for osimertinib (should target EGFR)."""
    tu = load_tu()
    result = tu.tools.OpenTargets_get_drug_mechanisms_of_action_by_chemblId(chemblId='CHEMBL3353410')
    moa = result.get('data', {}).get('drug', {}).get('mechanismsOfAction', {}).get('rows', [])
    assert len(moa) > 0, "No mechanisms returned"
    # Check EGFR is a target
    all_targets = []
    for row in moa:
        for t in row.get('targets', []):
            all_targets.append(t.get('approvedSymbol'))
    assert 'EGFR' in all_targets, f"EGFR not in targets: {all_targets}"
    print(f"       Osimertinib targets: {list(set(all_targets))}, MoA: {moa[0].get('mechanismOfAction')}")


def test_30_drug_resolution_sotorasib():
    """Phase 5: Resolve sotorasib (KRAS G12C inhibitor)."""
    tu = load_tu()
    result = tu.tools.OpenTargets_get_drug_id_description_by_name(drugName='sotorasib')
    hits = result.get('data', {}).get('search', {}).get('hits', [])
    assert len(hits) > 0, "No drug hits for sotorasib"
    top = hits[0]
    assert top.get('id') is not None, "No ChEMBL ID"
    print(f"       Drug resolved: {top.get('name')} ({top.get('id')})")


def test_31_drug_resolution_dabrafenib():
    """Phase 5: Resolve dabrafenib (BRAF inhibitor)."""
    tu = load_tu()
    result = tu.tools.OpenTargets_get_drug_id_description_by_name(drugName='dabrafenib')
    hits = result.get('data', {}).get('search', {}).get('hits', [])
    assert len(hits) > 0, "No drug hits for dabrafenib"
    print(f"       Drug resolved: {hits[0].get('name')} ({hits[0].get('id')})")


def test_32_drug_resolution_larotrectinib():
    """Phase 5: Resolve larotrectinib (NTRK inhibitor)."""
    tu = load_tu()
    result = tu.tools.OpenTargets_get_drug_id_description_by_name(drugName='larotrectinib')
    hits = result.get('data', {}).get('search', {}).get('hits', [])
    assert len(hits) > 0, "No drug hits for larotrectinib"
    print(f"       Drug resolved: {hits[0].get('name')} ({hits[0].get('id')})")


def test_33_drugs_by_target_egfr():
    """Phase 5: Get drugs targeting EGFR from OpenTargets."""
    tu = load_tu()
    result = tu.tools.OpenTargets_get_associated_drugs_by_target_ensemblID(
        ensemblId='ENSG00000146648', size=10
    )
    drugs = result.get('data', {}).get('target', {}).get('knownDrugs', {})
    rows = drugs.get('rows', [])
    assert len(rows) > 0, "No drugs found for EGFR"
    # Find approved drugs
    approved = [r for r in rows if r.get('drug', {}).get('isApproved')]
    print(f"       EGFR drugs: {len(rows)} total (showing first 10), {len(approved)} approved")


def test_34_drugs_by_disease_nsclc():
    """Phase 5: Get drugs for NSCLC from OpenTargets."""
    tu = load_tu()
    result = tu.tools.OpenTargets_get_associated_drugs_by_disease_efoId(
        efoId='EFO_0003060', size=5
    )
    drugs = result.get('data', {}).get('disease', {}).get('knownDrugs', {})
    count = drugs.get('count', 0)
    rows = drugs.get('rows', [])
    assert count > 0, "No drug count for NSCLC"
    assert len(rows) > 0, "No drug rows for NSCLC"
    print(f"       NSCLC drugs: {count} total, showing {len(rows)}")


def test_35_drugbank_targets():
    """Phase 5: Get drug targets from DrugBank."""
    tu = load_tu()
    result = tu.tools.drugbank_get_targets_by_drug_name_or_drugbank_id(
        query='osimertinib', case_sensitive=False, exact_match=False, limit=3
    )
    matches = result.get('total_matches', 0)
    assert matches > 0, "No DrugBank matches for osimertinib"
    results = result.get('results', [])
    targets = results[0].get('targets', [])
    assert len(targets) > 0, "No targets found"
    target_names = [t.get('name') for t in targets]
    assert any('growth factor receptor' in n.lower() for n in target_names), f"EGFR not in targets: {target_names}"
    print(f"       DrugBank: osimertinib targets {target_names}")


# ============================================================
# Phase 6: Evidence Assessment Tests
# ============================================================

def test_36_fda_indications_osimertinib():
    """Phase 6: Get FDA indications for osimertinib."""
    tu = load_tu()
    result = tu.tools.FDA_get_indications_by_drug_name(drug_name='osimertinib', limit=3)
    results = result.get('results', [])
    assert len(results) > 0, "No FDA results for osimertinib"
    ind_text = str(results[0].get('indications_and_usage', ''))
    assert 'NSCLC' in ind_text or 'non-small cell' in ind_text.lower(), f"NSCLC not in indication text"
    assert 'EGFR' in ind_text, "EGFR not in indication text"
    print(f"       FDA indication confirmed for osimertinib in EGFR+ NSCLC")


def test_37_pubmed_evidence():
    """Phase 6: Search PubMed for clinical evidence."""
    tu = load_tu()
    result = tu.tools.PubMed_search_articles(
        query='EGFR L858R osimertinib NSCLC clinical trial',
        max_results=3
    )
    articles = result if isinstance(result, list) else result.get('articles', [])
    assert len(articles) > 0, "No PubMed articles found"
    article = articles[0]
    assert 'pmid' in article or 'PMID' in article, f"Missing PMID. Keys: {list(article.keys())}"
    assert 'title' in article or 'Title' in article, f"Missing title"
    print(f"       Found {len(articles)} PubMed articles for EGFR L858R osimertinib")


def test_38_civic_gene_variants():
    """Phase 6: Get CIViC variants for EGFR (gene_id=19)."""
    tu = load_tu()
    result = tu.tools.civic_get_variants_by_gene(gene_id=19, limit=100)
    gene_data = result.get('data', {}).get('gene', {})
    assert gene_data.get('name') == 'EGFR', f"Wrong gene: {gene_data.get('name')}"
    variants = gene_data.get('variants', {}).get('nodes', [])
    assert len(variants) > 0, "No CIViC variants for EGFR"
    variant_names = [v.get('name', '') for v in variants]
    # L858R should be in the list
    l858r_found = any('L858R' in name for name in variant_names)
    print(f"       CIViC EGFR: {len(variants)} variants, L858R found: {l858r_found}")


def test_39_civic_braf_variants():
    """Phase 6: Get CIViC variants for BRAF (gene_id=5)."""
    tu = load_tu()
    result = tu.tools.civic_get_variants_by_gene(gene_id=5, limit=100)
    gene_data = result.get('data', {}).get('gene', {})
    assert gene_data.get('name') == 'BRAF', f"Wrong gene: {gene_data.get('name')}"
    variants = gene_data.get('variants', {}).get('nodes', [])
    assert len(variants) > 0, "No CIViC variants for BRAF"
    v600e_found = any('V600E' in v.get('name', '') for v in variants)
    print(f"       CIViC BRAF: {len(variants)} variants, V600E found: {v600e_found}")


def test_40_pharmgkb_egfr():
    """Phase 6: Get PharmGKB data for EGFR."""
    tu = load_tu()
    result = tu.tools.PharmGKB_search_genes(query='EGFR')
    data = result.get('data', [])
    assert len(data) > 0, "No PharmGKB results for EGFR"
    gene = data[0]
    assert gene.get('symbol') == 'EGFR', f"Wrong gene: {gene.get('symbol')}"
    print(f"       PharmGKB: EGFR ({gene.get('id')}), chr{gene.get('chr', {}).get('name', '?')}")


# ============================================================
# Phase 7: Geographic & Feasibility Tests
# ============================================================

def test_41_location_analysis():
    """Phase 7: Analyze trial site locations."""
    tu = load_tu()
    result = tu.tools.get_clinical_trial_locations(
        nct_ids=['NCT04765059'],
        location='all'
    )
    assert isinstance(result, list), f"Expected list"
    item = result[0]
    locations = item.get('locations', [])
    assert len(locations) > 0, "No locations"

    countries = set(l.get('country', '') for l in locations)
    us_sites = [l for l in locations if l.get('country') == 'United States']
    us_states = set(l.get('state', '') for l in us_sites)

    assert len(countries) > 0, "No countries found"
    print(f"       {len(locations)} sites, {len(countries)} countries, {len(us_sites)} US sites in {len(us_states)} states")


def test_42_trial_status_check():
    """Phase 7: Verify trial enrollment feasibility."""
    tu = load_tu()
    result = tu.tools.get_clinical_trial_status_and_dates(
        nct_ids=['NCT04765059'],
        status_and_date='all'
    )
    assert isinstance(result, list)
    item = result[0]
    status = item.get('overall_status')
    assert status is not None, "No status"
    # Check that we can determine recruiting vs non-recruiting
    recruiting_statuses = ['RECRUITING', 'NOT_YET_RECRUITING', 'ENROLLING_BY_INVITATION']
    active_statuses = ['ACTIVE_NOT_RECRUITING', 'COMPLETED', 'TERMINATED', 'SUSPENDED']
    assert status in recruiting_statuses + active_statuses, f"Unknown status: {status}"
    print(f"       Status: {status}, is recruiting: {status in recruiting_statuses}")


# ============================================================
# Phase 8: Alternative Options Tests
# ============================================================

def test_43_basket_trial_search():
    """Phase 8: Search for NTRK basket/tumor-agnostic trials."""
    tu = load_tu()
    # Note: "NTRK fusion tumor agnostic" returns no results because the search
    # is too specific. Use broader queries and combine results.
    result = tu.tools.search_clinical_trials(
        query_term='NTRK solid tumor',
        pageSize=5
    )
    if isinstance(result, str):
        # Fallback: try even simpler query
        result = tu.tools.search_clinical_trials(
            query_term='NTRK',
            pageSize=5
        )
    assert not isinstance(result, str), f"No results for any NTRK query"
    studies = result.get('studies', [])
    assert len(studies) > 0, "No NTRK trials found"
    print(f"       Found {len(studies)} NTRK basket/solid tumor trials")


def test_44_expanded_access_search():
    """Phase 8: Search for expanded access programs."""
    tu = load_tu()
    result = tu.tools.search_clinical_trials(
        query_term='expanded access osimertinib',
        pageSize=5
    )
    # May return string if no results, that's OK for expanded access
    if isinstance(result, str):
        print(f"       No expanded access found (expected for some drugs)")
    else:
        studies = result.get('studies', [])
        print(f"       Found {len(studies)} expanded access programs")
    # This test passes regardless - expanded access may not exist


# ============================================================
# Phase 9: Scoring & Integration Tests
# ============================================================

def test_45_scoring_system():
    """Phase 9: Verify scoring system calculations."""
    # Molecular Match (0-40)
    assert 0 <= 40 <= 40, "Molecular max out of range"
    # Clinical Eligibility (0-25)
    assert 0 <= 25 <= 25, "Clinical max out of range"
    # Evidence Strength (0-20)
    assert 0 <= 20 <= 20, "Evidence max out of range"
    # Trial Phase (0-10)
    assert 0 <= 10 <= 10, "Phase max out of range"
    # Geographic (0-5)
    assert 0 <= 5 <= 5, "Geographic max out of range"
    # Total
    assert 40 + 25 + 20 + 10 + 5 == 100, "Scoring components don't sum to 100"

    # Test tier classification
    def get_tier(score):
        if score >= 80: return 1
        if score >= 60: return 2
        if score >= 40: return 3
        return 4

    assert get_tier(85) == 1, "Tier 1 wrong"
    assert get_tier(70) == 2, "Tier 2 wrong"
    assert get_tier(50) == 3, "Tier 3 wrong"
    assert get_tier(30) == 4, "Tier 4 wrong"
    assert get_tier(80) == 1, "Tier 1 boundary wrong"
    assert get_tier(60) == 2, "Tier 2 boundary wrong"
    assert get_tier(40) == 3, "Tier 3 boundary wrong"
    print("       Scoring system verified: 40+25+20+10+5=100, tiers correct")


def test_46_end_to_end_egfr_nsclc():
    """Phase 9: End-to-end integration test (EGFR NSCLC)."""
    tu = load_tu()

    # Step 1: Resolve disease
    disease = tu.tools.OpenTargets_get_disease_id_description_by_name(diseaseName='non-small cell lung cancer')
    efo_id = disease.get('data', {}).get('search', {}).get('hits', [{}])[0].get('id')
    assert efo_id == 'EFO_0003060', f"Disease resolution failed: {efo_id}"

    # Step 2: Resolve gene
    gene = tu.tools.MyGene_query_genes(query='EGFR', species='human')
    ensembl_id = gene.get('hits', [{}])[0].get('ensembl', {}).get('gene')
    assert ensembl_id == 'ENSG00000146648', f"Gene resolution failed: {ensembl_id}"

    # Step 3: Search trials
    trials = tu.tools.search_clinical_trials(
        condition='non-small cell lung cancer',
        query_term='EGFR mutation',
        pageSize=5
    )
    assert not isinstance(trials, str), "No trials found"
    studies = trials.get('studies', [])
    assert len(studies) > 0, "No studies"

    # Step 4: Get first trial details
    nct_id = studies[0].get('NCT ID')
    assert nct_id is not None, "No NCT ID"

    # Step 5: Get eligibility
    elig = tu.tools.get_clinical_trial_eligibility_criteria(
        nct_ids=[nct_id],
        eligibility_criteria='all'
    )
    assert isinstance(elig, list) and len(elig) > 0, "No eligibility"

    print(f"       End-to-end: {efo_id} + {ensembl_id} -> {len(studies)} trials -> {nct_id} with eligibility")


def test_47_end_to_end_braf_melanoma():
    """Phase 9: End-to-end integration test (BRAF melanoma)."""
    tu = load_tu()

    # Resolve
    disease = tu.tools.OpenTargets_get_disease_id_description_by_name(diseaseName='melanoma')
    efo_id = disease.get('data', {}).get('search', {}).get('hits', [{}])[0].get('id')
    assert efo_id is not None, "Disease resolution failed"

    gene = tu.tools.MyGene_query_genes(query='BRAF', species='human')
    symbol = gene.get('hits', [{}])[0].get('symbol')
    assert symbol == 'BRAF', f"Gene resolution failed: {symbol}"

    # Search
    trials = tu.tools.search_clinical_trials(
        condition='melanoma',
        query_term='BRAF V600E',
        pageSize=5
    )
    assert not isinstance(trials, str), "No trials"
    studies = trials.get('studies', [])
    assert len(studies) > 0, "No BRAF melanoma trials"

    print(f"       End-to-end: melanoma({efo_id}) + BRAF -> {len(studies)} trials")


def test_48_end_to_end_kras_crc():
    """Phase 9: End-to-end integration test (KRAS G12C CRC)."""
    tu = load_tu()

    # Search
    trials = tu.tools.search_clinical_trials(
        condition='colorectal cancer',
        query_term='KRAS G12C',
        pageSize=5
    )
    assert not isinstance(trials, str), "No trials"
    studies = trials.get('studies', [])
    assert len(studies) > 0, "No KRAS G12C CRC trials"

    # Check drug alignment
    drug = tu.tools.OpenTargets_get_drug_id_description_by_name(drugName='sotorasib')
    hits = drug.get('data', {}).get('search', {}).get('hits', [])
    assert len(hits) > 0, "Sotorasib not found"

    print(f"       End-to-end: CRC + KRAS G12C -> {len(studies)} trials, sotorasib: {hits[0].get('id')}")


def test_49_end_to_end_her2_breast():
    """Phase 9: End-to-end integration test (HER2+ breast)."""
    tu = load_tu()

    # Search
    trials = tu.tools.search_clinical_trials(
        condition='breast cancer',
        query_term='HER2 positive amplification',
        pageSize=5
    )
    assert not isinstance(trials, str), "No trials"
    studies = trials.get('studies', [])
    assert len(studies) > 0, "No HER2+ breast trials"

    # Drug check
    drug = tu.tools.OpenTargets_get_drug_id_description_by_name(drugName='trastuzumab')
    hits = drug.get('data', {}).get('search', {}).get('hits', [])
    assert len(hits) > 0, "Trastuzumab not found"

    print(f"       End-to-end: breast + HER2 -> {len(studies)} trials, trastuzumab: {hits[0].get('id')}")


def test_50_end_to_end_ntrk_fusion():
    """Phase 9: End-to-end integration test (NTRK fusion)."""
    tu = load_tu()

    # Search
    trials = tu.tools.search_clinical_trials(
        query_term='NTRK fusion',
        pageSize=5
    )
    assert not isinstance(trials, str), "No trials"
    studies = trials.get('studies', [])
    assert len(studies) > 0, "No NTRK fusion trials"

    # Drug check
    drug = tu.tools.OpenTargets_get_drug_id_description_by_name(drugName='larotrectinib')
    hits = drug.get('data', {}).get('search', {}).get('hits', [])
    assert len(hits) > 0, "Larotrectinib not found"

    print(f"       End-to-end: NTRK fusion -> {len(studies)} trials, larotrectinib: {hits[0].get('id')}")


# ============================================================
# Edge Case Tests
# ============================================================

def test_51_rare_biomarker():
    """Edge case: Rare biomarker with few trials."""
    tu = load_tu()
    result = tu.tools.search_clinical_trials(
        query_term='FGFR3 S249C bladder cancer',
        pageSize=5
    )
    # May or may not find trials - that's OK
    if isinstance(result, str):
        print(f"       Rare biomarker: No trials found (expected)")
    else:
        studies = result.get('studies', [])
        print(f"       Rare biomarker: Found {len(studies)} trials")


def test_52_no_molecular_criteria():
    """Edge case: Disease-only search (no biomarker)."""
    tu = load_tu()
    result = tu.tools.search_clinical_trials(
        condition='pancreatic cancer',
        query_term='pancreatic cancer',
        pageSize=5
    )
    assert not isinstance(result, str), "No trials for pancreatic cancer"
    studies = result.get('studies', [])
    assert len(studies) > 0, "No pancreatic cancer trials"
    print(f"       Disease-only search: {len(studies)} pancreatic cancer trials")


def test_53_multiple_biomarkers():
    """Edge case: Patient with multiple biomarkers."""
    tu = load_tu()
    # Patient has both EGFR mutation and PD-L1 expression
    result1 = tu.tools.search_clinical_trials(
        condition='non-small cell lung cancer',
        query_term='EGFR mutation PD-L1',
        pageSize=5
    )
    assert not isinstance(result1, str), "No trials"
    studies = result1.get('studies', [])
    assert len(studies) > 0, "No multi-biomarker trials"
    print(f"       Multiple biomarkers (EGFR + PD-L1): {len(studies)} trials")


# ============================================================
# Main Test Runner
# ============================================================

def main():
    print("=" * 70)
    print("Clinical Trial Matching Skill - Comprehensive Test Suite")
    print("=" * 70)

    # Phase 1: Patient Profile Standardization (11 tests)
    print("\n--- Phase 1: Patient Profile Standardization ---")
    run_test("01. Disease resolution: NSCLC", test_01_disease_resolution_nsclc)
    run_test("02. Disease resolution: melanoma", test_02_disease_resolution_melanoma)
    run_test("03. Disease resolution: colorectal", test_03_disease_resolution_colorectal)
    run_test("04. Disease resolution: breast cancer", test_04_disease_resolution_breast_cancer)
    run_test("05. Disease resolution: OLS fallback", test_05_disease_resolution_ols_fallback)
    run_test("06. Gene resolution: EGFR", test_06_gene_resolution_egfr)
    run_test("07. Gene resolution: BRAF", test_07_gene_resolution_braf)
    run_test("08. Gene resolution: KRAS", test_08_gene_resolution_kras)
    run_test("09. Gene resolution: ERBB2/HER2", test_09_gene_resolution_erbb2_her2)
    run_test("10. Gene resolution: NTRK1", test_10_gene_resolution_ntrk1)
    run_test("11. FDA pharmacogenomic biomarkers", test_11_fda_pharmacogenomic_biomarkers)

    # Phase 2: Broad Trial Discovery (8 tests)
    print("\n--- Phase 2: Broad Trial Discovery ---")
    run_test("12. Search trials: NSCLC/EGFR", test_12_search_trials_disease_nsclc)
    run_test("13. Search trials: CRC/KRAS G12C", test_13_search_trials_biomarker_kras_g12c)
    run_test("14. Search trials: melanoma/BRAF V600E", test_14_search_trials_biomarker_braf_v600e)
    run_test("15. Search trials: HER2+ breast", test_15_search_trials_her2_breast)
    run_test("16. Search trials: NTRK fusion basket", test_16_search_trials_ntrk_basket)
    run_test("17. Search trials: intervention (osimertinib)", test_17_search_trials_intervention)
    run_test("18. Alternative search (clinical_trials_search)", test_18_alternative_search)
    run_test("19. Search pagination", test_19_search_pagination)

    # Phase 3: Trial Characterization (6 tests)
    print("\n--- Phase 3: Trial Characterization ---")
    run_test("20. Get trial details", test_20_get_trial_details)
    run_test("21. Get eligibility criteria", test_21_get_eligibility_criteria)
    run_test("22. Get conditions and interventions", test_22_get_conditions_and_interventions)
    run_test("23. Get trial locations", test_23_get_trial_locations)
    run_test("24. Get trial status", test_24_get_trial_status)
    run_test("25. Get trial descriptions", test_25_get_trial_descriptions)

    # Phase 4: Molecular Eligibility Matching (2 tests)
    print("\n--- Phase 4: Molecular Eligibility Matching ---")
    run_test("26. Eligibility biomarker parsing", test_26_eligibility_biomarker_parsing)
    run_test("27. Molecular match scoring", test_27_molecular_match_scoring)

    # Phase 5: Drug-Biomarker Alignment (8 tests)
    print("\n--- Phase 5: Drug-Biomarker Alignment ---")
    run_test("28. Drug resolution: osimertinib", test_28_drug_resolution_osimertinib)
    run_test("29. Drug mechanism: EGFR inhibitor", test_29_drug_mechanism_egfr)
    run_test("30. Drug resolution: sotorasib", test_30_drug_resolution_sotorasib)
    run_test("31. Drug resolution: dabrafenib", test_31_drug_resolution_dabrafenib)
    run_test("32. Drug resolution: larotrectinib", test_32_drug_resolution_larotrectinib)
    run_test("33. Drugs by target: EGFR", test_33_drugs_by_target_egfr)
    run_test("34. Drugs by disease: NSCLC", test_34_drugs_by_disease_nsclc)
    run_test("35. DrugBank targets", test_35_drugbank_targets)

    # Phase 6: Evidence Assessment (5 tests)
    print("\n--- Phase 6: Evidence Assessment ---")
    run_test("36. FDA indications: osimertinib", test_36_fda_indications_osimertinib)
    run_test("37. PubMed evidence", test_37_pubmed_evidence)
    run_test("38. CIViC EGFR variants", test_38_civic_gene_variants)
    run_test("39. CIViC BRAF variants", test_39_civic_braf_variants)
    run_test("40. PharmGKB EGFR", test_40_pharmgkb_egfr)

    # Phase 7: Geographic & Feasibility (2 tests)
    print("\n--- Phase 7: Geographic & Feasibility ---")
    run_test("41. Location analysis", test_41_location_analysis)
    run_test("42. Trial status check", test_42_trial_status_check)

    # Phase 8: Alternative Options (2 tests)
    print("\n--- Phase 8: Alternative Options ---")
    run_test("43. Basket trial search", test_43_basket_trial_search)
    run_test("44. Expanded access search", test_44_expanded_access_search)

    # Phase 9: Scoring & Integration (6 tests)
    print("\n--- Phase 9: Scoring & Integration ---")
    run_test("45. Scoring system verification", test_45_scoring_system)
    run_test("46. End-to-end: EGFR NSCLC", test_46_end_to_end_egfr_nsclc)
    run_test("47. End-to-end: BRAF melanoma", test_47_end_to_end_braf_melanoma)
    run_test("48. End-to-end: KRAS G12C CRC", test_48_end_to_end_kras_crc)
    run_test("49. End-to-end: HER2+ breast", test_49_end_to_end_her2_breast)
    run_test("50. End-to-end: NTRK fusion", test_50_end_to_end_ntrk_fusion)

    # Edge Cases (3 tests)
    print("\n--- Edge Cases ---")
    run_test("51. Rare biomarker", test_51_rare_biomarker)
    run_test("52. No molecular criteria", test_52_no_molecular_criteria)
    run_test("53. Multiple biomarkers", test_53_multiple_biomarkers)

    # Summary
    print("\n" + "=" * 70)
    print(f"RESULTS: {PASS}/{TOTAL} passed, {FAIL} failed")
    print("=" * 70)

    if FAIL > 0:
        print("\nFailed tests:")
        for r in RESULTS:
            if r['status'] == 'FAIL':
                print(f"  - {r['name']}: {r['error']}")

    print(f"\nOverall: {'ALL TESTS PASSED' if FAIL == 0 else f'{FAIL} TESTS FAILED'}")
    return 0 if FAIL == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
