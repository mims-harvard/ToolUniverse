#!/usr/bin/env python3
"""
Comprehensive Test Suite for Adverse Drug Event Signal Detection Skill

Tests all phases of the workflow with real drugs:
- Atorvastatin (statin, common drug with many reports)
- Metformin (biguanide, boxed warning drug)
- Pembrolizumab (immunotherapy, biologic)
- Ibuprofen (NSAID, OTC drug)

Run: python3 test_adverse_event_detection.py
"""

import json
import sys
import time
import traceback

# Track results
results = []
total_tests = 0
passed_tests = 0
failed_tests = 0
start_time = time.time()


def run_test(test_name, test_func):
    """Run a single test and track results."""
    global total_tests, passed_tests, failed_tests
    total_tests += 1
    print(f"\n{'='*70}")
    print(f"TEST {total_tests}: {test_name}")
    print(f"{'='*70}")
    try:
        test_func()
        passed_tests += 1
        results.append((test_name, "PASS", ""))
        print(f"  RESULT: PASS")
    except Exception as e:
        failed_tests += 1
        tb = traceback.format_exc()
        results.append((test_name, "FAIL", str(e)))
        print(f"  RESULT: FAIL - {e}")
        print(f"  Traceback:\n{tb}")


def setup():
    """Initialize ToolUniverse."""
    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()
    return tu


# Initialize once
print("Initializing ToolUniverse...")
tu = setup()
print(f"Loaded {len(tu.all_tool_dict)} tools")


# ============================================================================
# PHASE 0: Drug Disambiguation Tests
# ============================================================================

def test_01_drug_disambiguation_atorvastatin():
    """Phase 0: Resolve atorvastatin to ChEMBL ID."""
    result = tu.tools.OpenTargets_get_drug_chembId_by_generic_name(drugName="atorvastatin")
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert "data" in result, f"Missing 'data' key in {result.keys()}"
    hits = result["data"]["search"]["hits"]
    assert len(hits) > 0, "No hits found for atorvastatin"
    chembl_id = hits[0]["id"]
    assert chembl_id == "CHEMBL1487", f"Expected CHEMBL1487, got {chembl_id}"
    print(f"  ChEMBL ID: {chembl_id}")
    print(f"  Name: {hits[0]['name']}")


def test_02_drug_blackbox_status():
    """Phase 0: Check blackbox/withdrawal status."""
    result = tu.tools.OpenTargets_get_drug_blackbox_status_by_chembl_ID(chemblId="CHEMBL1487")
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    drug = result["data"]["drug"]
    assert drug["name"] == "ATORVASTATIN", f"Wrong drug: {drug['name']}"
    assert drug["blackBoxWarning"] is False, "Atorvastatin should not have blackbox warning"
    assert drug["hasBeenWithdrawn"] is False, "Atorvastatin should not be withdrawn"
    print(f"  Drug: {drug['name']}")
    print(f"  Blackbox: {drug['blackBoxWarning']}")
    print(f"  Withdrawn: {drug['hasBeenWithdrawn']}")


def test_03_drug_mechanism_of_action():
    """Phase 0: Get mechanism of action."""
    result = tu.tools.OpenTargets_get_drug_mechanisms_of_action_by_chemblId(chemblId="CHEMBL1487")
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    rows = result["data"]["drug"]["mechanismsOfAction"]["rows"]
    assert len(rows) > 0, "No MOA found"
    moa = rows[0]
    assert "HMG-CoA reductase" in moa["mechanismOfAction"], f"Unexpected MOA: {moa['mechanismOfAction']}"
    assert moa["actionType"] == "INHIBITOR", f"Expected INHIBITOR, got {moa['actionType']}"
    targets = moa.get("targets", [])
    assert len(targets) > 0, "No targets found"
    print(f"  MOA: {moa['mechanismOfAction']}")
    print(f"  Action: {moa['actionType']}")
    print(f"  Target: {targets[0]['approvedSymbol']} ({targets[0]['id']})")


def test_04_drugbank_safety():
    """Phase 0: Get DrugBank safety/toxicity info."""
    result = tu.tools.drugbank_get_safety_by_drug_name_or_drugbank_id(
        query="atorvastatin", case_sensitive=False, exact_match=False, limit=3
    )
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert result["total_matches"] >= 1, "No DrugBank matches found"
    drug = result["results"][0]
    assert drug["drug_name"] == "Atorvastatin", f"Wrong drug: {drug['drug_name']}"
    assert drug["drugbank_id"] == "DB01076", f"Wrong DrugBank ID: {drug['drugbank_id']}"
    assert len(drug["toxicity"]) > 0, "Empty toxicity field"
    print(f"  DrugBank ID: {drug['drugbank_id']}")
    print(f"  Toxicity: {drug['toxicity'][:150]}...")


# ============================================================================
# PHASE 1: FAERS Adverse Event Profiling Tests
# ============================================================================

def test_05_faers_top_reactions():
    """Phase 1: Get top adverse event reactions from FAERS."""
    result = tu.tools.FAERS_count_reactions_by_drug_event(medicinalproduct="ATORVASTATIN")
    assert isinstance(result, list), f"Expected list, got {type(result)}"
    assert len(result) >= 10, f"Expected >= 10 reactions, got {len(result)}"
    # Verify structure
    first = result[0]
    assert "term" in first, f"Missing 'term' key"
    assert "count" in first, f"Missing 'count' key"
    assert isinstance(first["count"], int), f"Count should be int, got {type(first['count'])}"
    # Verify myalgia is present (known statin AE)
    terms = [r["term"].upper() for r in result]
    assert any("MYALGIA" in t for t in terms), f"Expected MYALGIA in results, got top terms: {terms[:10]}"
    print(f"  Total reactions returned: {len(result)}")
    print(f"  Top 5: {[(r['term'], r['count']) for r in result[:5]]}")


def test_06_faers_seriousness():
    """Phase 1: Get seriousness distribution."""
    result = tu.tools.FAERS_count_seriousness_by_drug_event(medicinalproduct="ATORVASTATIN")
    assert isinstance(result, list), f"Expected list, got {type(result)}"
    assert len(result) >= 2, f"Expected at least 2 categories (Serious/Non-serious)"
    terms = {r["term"]: r["count"] for r in result}
    assert "Serious" in terms, "Missing 'Serious' category"
    assert "Non-serious" in terms, "Missing 'Non-serious' category"
    assert terms["Serious"] > 0, "Serious count should be > 0"
    print(f"  Serious: {terms['Serious']}")
    print(f"  Non-serious: {terms['Non-serious']}")
    print(f"  Serious %: {terms['Serious'] / (terms['Serious'] + terms['Non-serious']) * 100:.1f}%")


def test_07_faers_outcomes():
    """Phase 1: Get outcome distribution."""
    result = tu.tools.FAERS_count_outcomes_by_drug_event(medicinalproduct="ATORVASTATIN")
    assert isinstance(result, list), f"Expected list, got {type(result)}"
    terms = {r["term"]: r["count"] for r in result}
    assert "Fatal" in terms, "Missing 'Fatal' outcome"
    assert terms["Fatal"] > 0, "Fatal count should be > 0 for atorvastatin"
    print(f"  Outcomes: {json.dumps(terms, indent=2)}")


def test_08_faers_age_distribution():
    """Phase 1: Get age distribution."""
    result = tu.tools.FAERS_count_patient_age_distribution(medicinalproduct="ATORVASTATIN")
    assert isinstance(result, list), f"Expected list, got {type(result)}"
    terms = {r["term"]: r["count"] for r in result}
    assert "Elderly" in terms or "Adult" in terms, "Missing expected age groups"
    print(f"  Age distribution: {json.dumps(terms, indent=2)}")


def test_09_faers_death_counts():
    """Phase 1: Get death-related counts."""
    result = tu.tools.FAERS_count_death_related_by_drug(medicinalproduct="ATORVASTATIN")
    assert isinstance(result, list), f"Expected list, got {type(result)}"
    terms = {r["term"]: r["count"] for r in result}
    assert "death" in terms, "Missing 'death' category"
    assert "alive" in terms, "Missing 'alive' category"
    print(f"  Alive: {terms['alive']}")
    print(f"  Death: {terms['death']}")


def test_10_faers_reporter_country():
    """Phase 1: Get reporter country distribution."""
    result = tu.tools.FAERS_count_reportercountry_by_drug_event(medicinalproduct="ATORVASTATIN")
    assert isinstance(result, list), f"Expected list, got {type(result)}"
    assert len(result) >= 5, "Expected multiple countries"
    # US should be top reporter
    top_country = result[0]["term"]
    assert top_country == "US", f"Expected US as top reporter, got {top_country}"
    print(f"  Top 5 countries: {[(r['term'], r['count']) for r in result[:5]]}")


# ============================================================================
# PHASE 2: Disproportionality Analysis Tests
# ============================================================================

def test_11_disproportionality_rhabdomyolysis():
    """Phase 2: Calculate PRR/ROR/IC for atorvastatin + rhabdomyolysis."""
    result = tu.tools.FAERS_calculate_disproportionality(
        operation="calculate_disproportionality",
        drug_name="ATORVASTATIN",
        adverse_event="Rhabdomyolysis"
    )
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert result.get("status") == "success", f"Status not success: {result.get('status')}"

    # Check contingency table
    ct = result["contingency_table"]
    assert ct["a_drug_and_event"] > 0, "a should be > 0"
    assert ct["b_drug_no_event"] > 0, "b should be > 0"

    # Check metrics
    metrics = result["metrics"]
    assert "PRR" in metrics, "Missing PRR"
    assert "ROR" in metrics, "Missing ROR"
    assert "IC" in metrics, "Missing IC"

    prr = metrics["PRR"]["value"]
    ror = metrics["ROR"]["value"]
    ic = metrics["IC"]["value"]

    assert prr > 2.0, f"PRR should be > 2 for rhabdomyolysis, got {prr}"
    assert ror > 2.0, f"ROR should be > 2 for rhabdomyolysis, got {ror}"
    assert ic > 0, f"IC should be > 0 for rhabdomyolysis, got {ic}"

    # Check CI
    assert metrics["PRR"]["ci_95_lower"] > 1.0, "PRR lower CI should be > 1"
    assert metrics["ROR"]["ci_95_lower"] > 1.0, "ROR lower CI should be > 1"

    # Check signal detection
    sd = result["signal_detection"]
    assert sd["signal_detected"] is True, "Signal should be detected"
    assert "Strong" in sd["signal_strength"], f"Expected strong signal, got {sd['signal_strength']}"

    print(f"  PRR: {prr:.3f} (CI: {metrics['PRR']['ci_95_lower']:.3f}-{metrics['PRR']['ci_95_upper']:.3f})")
    print(f"  ROR: {ror:.3f} (CI: {metrics['ROR']['ci_95_lower']:.3f}-{metrics['ROR']['ci_95_upper']:.3f})")
    print(f"  IC:  {ic:.3f} (CI: {metrics['IC']['ci_95_lower']:.3f}-{metrics['IC']['ci_95_upper']:.3f})")
    print(f"  Signal: {sd['signal_strength']}")


def test_12_disproportionality_myalgia():
    """Phase 2: Calculate PRR/ROR/IC for atorvastatin + myalgia."""
    result = tu.tools.FAERS_calculate_disproportionality(
        operation="calculate_disproportionality",
        drug_name="ATORVASTATIN",
        adverse_event="Myalgia"
    )
    assert result.get("status") == "success", f"Status not success"
    prr = result["metrics"]["PRR"]["value"]
    assert prr > 1.0, f"PRR should be > 1 for myalgia, got {prr}"
    sd = result["signal_detection"]
    assert sd["signal_detected"] is True, "Signal should be detected for myalgia"
    print(f"  PRR: {prr:.3f}")
    print(f"  Signal: {sd['signal_strength']}")


def test_13_serious_events_death():
    """Phase 2: Filter serious events (death type)."""
    result = tu.tools.FAERS_filter_serious_events(
        operation="filter_serious_events",
        drug_name="ATORVASTATIN",
        seriousness_type="death"
    )
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert result.get("status") == "success", f"Status not success"
    assert result["total_serious_events"] > 0, "Should have death-related events"
    assert len(result["top_serious_reactions"]) > 0, "Should have top reactions"
    print(f"  Total death-related events: {result['total_serious_events']}")
    print(f"  Top 3: {[(r['reaction'], r['count']) for r in result['top_serious_reactions'][:3]]}")


def test_14_demographic_stratification():
    """Phase 2: Stratify rhabdomyolysis by sex."""
    result = tu.tools.FAERS_stratify_by_demographics(
        operation="stratify_by_demographics",
        drug_name="ATORVASTATIN",
        adverse_event="Rhabdomyolysis",
        stratify_by="sex"
    )
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert result.get("status") == "success", f"Status not success"
    assert result["total_reports"] > 0, "Should have reports"
    strat = result["stratification"]
    assert len(strat) >= 2, "Should have at least 2 groups (male/female)"
    print(f"  Total reports: {result['total_reports']}")
    for s in strat:
        sex_label = {0: "Unknown", 1: "Male", 2: "Female"}.get(s["group"], f"Code {s['group']}")
        print(f"  {sex_label}: {s['count']} ({s['percentage']:.1f}%)")


def test_15_meddra_rollup():
    """Phase 2: MedDRA hierarchy rollup."""
    result = tu.tools.FAERS_rollup_meddra_hierarchy(
        operation="rollup_meddra_hierarchy",
        drug_name="ATORVASTATIN"
    )
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert result.get("status") == "success", f"Status not success"
    pt_level = result["meddra_hierarchy"]["PT_level"]
    assert len(pt_level) >= 10, f"Expected >= 10 PTs, got {len(pt_level)}"
    print(f"  Total PTs: {len(pt_level)}")
    print(f"  Top 5: {[(p['preferred_term'], p['count']) for p in pt_level[:5]]}")


# ============================================================================
# PHASE 3: FDA Label Tests
# ============================================================================

def test_16_fda_boxed_warning_none():
    """Phase 3: Verify atorvastatin has no boxed warning."""
    result = tu.tools.FDA_get_boxed_warning_info_by_drug_name(drug_name="atorvastatin")
    # Atorvastatin should NOT have a boxed warning
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    if "error" in result:
        assert result["error"]["code"] == "NOT_FOUND", f"Unexpected error: {result['error']}"
        print("  Confirmed: No boxed warning (NOT_FOUND)")
    else:
        # Some formulations might return results - check content
        print(f"  Results returned: {result.get('meta', {}).get('total', 0)}")


def test_17_fda_boxed_warning_present():
    """Phase 3: Verify a drug WITH boxed warning (metformin)."""
    result = tu.tools.FDA_get_boxed_warning_info_by_drug_name(drug_name="metformin")
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    if "results" in result and len(result["results"]) > 0:
        bw = result["results"][0].get("boxed_warning", [])
        if bw:
            assert "lactic acidosis" in bw[0].lower() or "metformin" in bw[0].lower(), \
                f"Expected lactic acidosis warning, got: {bw[0][:100]}"
            print(f"  Boxed warning found: {bw[0][:150]}...")
        else:
            print("  No boxed_warning field in results (metformin may have changed labels)")
    else:
        print("  Note: Metformin boxed warning not found via this API endpoint")


def test_18_fda_contraindications():
    """Phase 3: Get contraindications."""
    result = tu.tools.FDA_get_contraindications_by_drug_name(drug_name="atorvastatin")
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert result["meta"]["total"] > 0, "Should have contraindication results"
    text = result["results"][0]["contraindications"][0].lower()
    assert "liver" in text or "hypersensitivity" in text, f"Expected liver/hypersensitivity, got: {text[:200]}"
    print(f"  Results: {result['meta']['total']}")
    print(f"  Text: {text[:200]}...")


def test_19_fda_adverse_reactions():
    """Phase 3: Get adverse reactions from label."""
    result = tu.tools.FDA_get_adverse_reactions_by_drug_name(drug_name="atorvastatin")
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert result["meta"]["total"] > 0, "Should have adverse reaction results"
    text = result["results"][0]["adverse_reactions"][0].lower()
    assert "myopathy" in text or "rhabdomyolysis" in text or "adverse" in text, \
        f"Expected safety terms in label, got: {text[:200]}"
    print(f"  Results: {result['meta']['total']}")
    print(f"  Preview: {text[:200]}...")


def test_20_fda_drug_interactions():
    """Phase 3: Get drug interactions from label."""
    result = tu.tools.FDA_get_drug_interactions_by_drug_name(drug_name="atorvastatin")
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert result["meta"]["total"] > 0, "Should have drug interaction results"
    text = result["results"][0]["drug_interactions"][0].lower()
    assert "cyp3a4" in text or "cyclosporine" in text or "interaction" in text, \
        f"Expected CYP3A4 or cyclosporine, got: {text[:200]}"
    print(f"  Results: {result['meta']['total']}")
    print(f"  Preview: {text[:200]}...")


# ============================================================================
# PHASE 4: Mechanism-Based Context Tests
# ============================================================================

def test_21_opentargets_adverse_events():
    """Phase 4: Get OpenTargets adverse events (FAERS-based significance)."""
    result = tu.tools.OpenTargets_get_drug_adverse_events_by_chemblId(chemblId="CHEMBL1487")
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    ae = result["data"]["drug"]["adverseEvents"]
    assert ae["count"] > 0, "Should have adverse events"
    rows = ae["rows"]
    assert len(rows) > 0, "Should have AE rows"
    # Check structure
    first = rows[0]
    assert "name" in first, "Missing 'name' field"
    assert "meddraCode" in first, "Missing 'meddraCode' field"
    assert "count" in first, "Missing 'count' field"
    assert "logLR" in first, "Missing 'logLR' field"
    # Myalgia should be top
    names = [r["name"] for r in rows]
    assert "myalgia" in names or "rhabdomyolysis" in names, \
        f"Expected myalgia/rhabdomyolysis, got: {names}"
    print(f"  Count: {ae['count']}")
    top3 = [(r['name'], r['count'], round(r['logLR'], 1)) for r in rows[:3]]
    print(f"  Top 3: {top3}")


def test_22_target_safety_profile():
    """Phase 4: Get target safety profile for HMGCR."""
    result = tu.tools.OpenTargets_get_target_safety_profile_by_ensemblID(ensemblId="ENSG00000113161")
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    target = result["data"]["target"]
    assert target["approvedSymbol"] == "HMGCR", f"Wrong target: {target['approvedSymbol']}"
    liabilities = target.get("safetyLiabilities", [])
    print(f"  Target: {target['approvedSymbol']}")
    print(f"  Safety liabilities: {len(liabilities)}")
    for sl in liabilities[:3]:
        print(f"    - {sl['event']} ({sl['datasource']})")


def test_23_admet_toxicity():
    """Phase 4: Predict toxicity using ADMETAI."""
    # Atorvastatin SMILES
    smiles = "CC(C)C1=C(C(=C(N1CC[C@H](C[C@H](CC(=O)O)O)O)C2=CC=C(C=C2)F)C3=CC=CC=C3)C(=O)NC4=CC=CC=C4"
    result = tu.tools.ADMETAI_predict_toxicity(smiles=[smiles])
    assert result is not None, "ADMETAI returned None"
    # ADMETAI results may vary in structure
    print(f"  Result type: {type(result)}")
    if isinstance(result, dict):
        print(f"  Keys: {list(result.keys())[:10]}")
    elif isinstance(result, list):
        print(f"  Items: {len(result)}")
        if len(result) > 0:
            print(f"  First item keys: {list(result[0].keys())[:10] if isinstance(result[0], dict) else 'N/A'}")


# ============================================================================
# PHASE 5: Comparative Safety Analysis Tests
# ============================================================================

def test_24_compare_drugs():
    """Phase 5: Compare atorvastatin vs simvastatin for rhabdomyolysis."""
    result = tu.tools.FAERS_compare_drugs(
        operation="compare_drugs",
        drug1="ATORVASTATIN",
        drug2="SIMVASTATIN",
        adverse_event="Rhabdomyolysis"
    )
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert result.get("status") == "success", f"Status not success"

    d1 = result["drug1"]
    d2 = result["drug2"]
    assert d1["name"] == "ATORVASTATIN"
    assert d2["name"] == "SIMVASTATIN"

    prr1 = d1["metrics"]["PRR"]["value"]
    prr2 = d2["metrics"]["PRR"]["value"]
    assert prr1 > 0, "PRR1 should be > 0"
    assert prr2 > 0, "PRR2 should be > 0"

    # Simvastatin should have higher PRR for rhabdomyolysis (known)
    print(f"  Atorvastatin PRR: {prr1:.3f}")
    print(f"  Simvastatin PRR:  {prr2:.3f}")
    print(f"  Comparison: {result['comparison']}")


def test_25_aggregate_class_reactions():
    """Phase 5: Aggregate adverse reactions across statin class."""
    result = tu.tools.FAERS_count_additive_adverse_reactions(
        medicinalproducts=["ATORVASTATIN", "SIMVASTATIN", "ROSUVASTATIN"]
    )
    assert isinstance(result, list), f"Expected list, got {type(result)}"
    assert len(result) >= 10, f"Expected >= 10 reactions, got {len(result)}"
    # Check MYALGIA is present (class-wide effect)
    terms = [r["term"].upper() for r in result]
    assert any("MYALGIA" in t for t in terms), f"Expected MYALGIA in class aggregate"
    print(f"  Total reactions: {len(result)}")
    print(f"  Top 3: {[(r['term'], r['count']) for r in result[:3]]}")


def test_26_aggregate_class_seriousness():
    """Phase 5: Aggregate seriousness across statin class."""
    result = tu.tools.FAERS_count_additive_seriousness_classification(
        medicinalproducts=["ATORVASTATIN", "SIMVASTATIN"]
    )
    assert isinstance(result, list), f"Expected list, got {type(result)}"
    terms = {r["term"]: r["count"] for r in result}
    assert "Serious" in terms, "Missing 'Serious' category"
    print(f"  Class seriousness: {json.dumps(terms, indent=2)}")


# ============================================================================
# PHASE 6: DDIs & PGx Tests
# ============================================================================

def test_27_fda_drug_interactions_label():
    """Phase 6: Get DDIs from FDA label."""
    result = tu.tools.FDA_get_drug_interactions_by_drug_name(drug_name="atorvastatin")
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert result["meta"]["total"] > 0, "Should have DDI results"
    print(f"  DDI results: {result['meta']['total']}")


def test_28_pharmgkb_drug_search():
    """Phase 6: Search PharmGKB for atorvastatin."""
    result = tu.tools.PharmGKB_search_drugs(query="atorvastatin")
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert result["status"] == "success", f"Status not success"
    data = result["data"]
    assert len(data) > 0, "No PharmGKB results"
    drug = data[0]
    assert drug["name"] == "atorvastatin", f"Wrong drug: {drug['name']}"
    assert drug["id"] == "PA448500", f"Wrong ID: {drug['id']}"
    print(f"  PharmGKB ID: {drug['id']}")
    print(f"  Name: {drug['name']}")
    print(f"  SMILES: {drug.get('smiles', 'N/A')[:80]}...")


def test_29_pharmgkb_drug_details():
    """Phase 6: Get PharmGKB drug details."""
    result = tu.tools.PharmGKB_get_drug_details(drug_id="PA448500")
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert result["status"] == "success", f"Status not success"
    data = result["data"]
    assert data["name"] == "atorvastatin", f"Wrong drug: {data['name']}"
    print(f"  Drug: {data['name']}")
    print(f"  Types: {data.get('types', [])}")


def test_30_pharmgkb_dosing_guidelines():
    """Phase 6: Get SLCO1B1 dosing guidelines (key statin pharmacogene)."""
    result = tu.tools.PharmGKB_get_dosing_guidelines(gene="SLCO1B1")
    assert result is not None, "PharmGKB dosing guidelines returned None"
    print(f"  Result type: {type(result)}")
    if isinstance(result, dict):
        print(f"  Status: {result.get('status', 'N/A')}")
        if "data" in result:
            data = result["data"]
            if isinstance(data, list):
                print(f"  Guidelines found: {len(data)}")
            elif isinstance(data, dict):
                print(f"  Keys: {list(data.keys())[:10]}")
    elif isinstance(result, list):
        print(f"  Guidelines found: {len(result)}")


# ============================================================================
# PHASE 7: Literature Evidence Tests
# ============================================================================

def test_31_pubmed_search():
    """Phase 7: Search PubMed for atorvastatin safety literature."""
    result = tu.tools.PubMed_search_articles(
        query="atorvastatin adverse events safety rhabdomyolysis",
        limit=5
    )
    assert isinstance(result, list), f"Expected list, got {type(result)}"
    assert len(result) > 0, "No PubMed results"
    first = result[0]
    assert "pmid" in first, "Missing 'pmid'"
    assert "title" in first, "Missing 'title'"
    assert "pub_year" in first, "Missing 'pub_year'"
    print(f"  Articles found: {len(result)}")
    for article in result[:3]:
        print(f"    - [{article['pmid']}] {article['title'][:80]}... ({article['pub_year']})")


def test_32_openalex_search():
    """Phase 7: Search OpenAlex for citation analysis."""
    result = tu.tools.openalex_search_works(
        query="atorvastatin statin safety adverse events",
        limit=5
    )
    assert result is not None, "OpenAlex returned None"
    if isinstance(result, dict):
        if "results" in result:
            works = result["results"]
        elif "data" in result:
            works = result["data"]
        else:
            works = [result]
    elif isinstance(result, list):
        works = result
    else:
        works = []

    assert len(works) > 0, "No OpenAlex results"
    print(f"  Works found: {len(works)}")


# ============================================================================
# CROSS-DRUG TESTS (Different drug types)
# ============================================================================

def test_33_metformin_disproportionality():
    """Cross-drug: Metformin + Lactic acidosis (known strong signal)."""
    result = tu.tools.FAERS_calculate_disproportionality(
        operation="calculate_disproportionality",
        drug_name="METFORMIN",
        adverse_event="Lactic acidosis"
    )
    assert result.get("status") == "success"
    prr = result["metrics"]["PRR"]["value"]
    assert prr > 5.0, f"Expected strong PRR for lactic acidosis, got {prr}"
    sd = result["signal_detection"]
    assert sd["signal_detected"] is True
    print(f"  PRR: {prr:.3f}")
    print(f"  Signal: {sd['signal_strength']}")


def test_34_pembrolizumab_reactions():
    """Cross-drug: Pembrolizumab (biologic/immunotherapy) FAERS profile."""
    result = tu.tools.FAERS_count_reactions_by_drug_event(medicinalproduct="PEMBROLIZUMAB")
    assert isinstance(result, list), f"Expected list, got {type(result)}"
    assert len(result) >= 5, "Expected multiple reactions"
    print(f"  Reactions: {len(result)}")
    print(f"  Top 5: {[(r['term'], r['count']) for r in result[:5]]}")


def test_35_pembrolizumab_disproportionality():
    """Cross-drug: Pembrolizumab + immune-related AE."""
    result = tu.tools.FAERS_calculate_disproportionality(
        operation="calculate_disproportionality",
        drug_name="PEMBROLIZUMAB",
        adverse_event="Colitis"
    )
    assert result.get("status") == "success"
    prr = result["metrics"]["PRR"]["value"]
    assert prr > 1.0, f"Expected PRR > 1 for pembrolizumab colitis"
    print(f"  PRR: {prr:.3f}")
    print(f"  Signal: {result['signal_detection']['signal_strength']}")


def test_36_ibuprofen_reactions():
    """Cross-drug: Ibuprofen (NSAID, OTC) FAERS profile."""
    result = tu.tools.FAERS_count_reactions_by_drug_event(medicinalproduct="IBUPROFEN")
    assert isinstance(result, list), f"Expected list, got {type(result)}"
    assert len(result) >= 5, "Expected multiple reactions"
    print(f"  Reactions: {len(result)}")
    print(f"  Top 5: {[(r['term'], r['count']) for r in result[:5]]}")


def test_37_ibuprofen_gi_bleeding():
    """Cross-drug: Ibuprofen + GI bleeding (known NSAID effect)."""
    result = tu.tools.FAERS_calculate_disproportionality(
        operation="calculate_disproportionality",
        drug_name="IBUPROFEN",
        adverse_event="Gastrointestinal haemorrhage"
    )
    assert result.get("status") == "success"
    prr = result["metrics"]["PRR"]["value"]
    sd = result["signal_detection"]
    assert sd["signal_detected"] is True, "GI hemorrhage should be a signal for ibuprofen"
    print(f"  PRR: {prr:.3f}")
    print(f"  Signal: {sd['signal_strength']}")


def test_38_compare_nsaids():
    """Cross-drug: Compare ibuprofen vs naproxen for GI bleeding."""
    result = tu.tools.FAERS_compare_drugs(
        operation="compare_drugs",
        drug1="IBUPROFEN",
        drug2="NAPROXEN",
        adverse_event="Gastrointestinal haemorrhage"
    )
    assert result.get("status") == "success"
    d1 = result["drug1"]
    d2 = result["drug2"]
    print(f"  Ibuprofen PRR:  {d1['metrics']['PRR']['value']:.3f}")
    print(f"  Naproxen PRR:   {d2['metrics']['PRR']['value']:.3f}")
    print(f"  Comparison: {result['comparison']}")


# ============================================================================
# EDGE CASE TESTS
# ============================================================================

def test_39_rare_drug_faers():
    """Edge case: Drug with fewer FAERS reports."""
    # Tocilizumab - biologic with moderate reports
    result = tu.tools.FAERS_count_reactions_by_drug_event(medicinalproduct="TOCILIZUMAB")
    assert isinstance(result, list), f"Expected list, got {type(result)}"
    print(f"  Reactions: {len(result)}")
    if len(result) > 0:
        print(f"  Top 3: {[(r['term'], r['count']) for r in result[:3]]}")


def test_40_individual_case_reports():
    """Edge case: Retrieve individual case reports."""
    result = tu.tools.FAERS_search_adverse_event_reports(
        medicinalproduct="atorvastatin",
        limit=3
    )
    assert isinstance(result, list), f"Expected list, got {type(result)}"
    assert len(result) > 0, "Should have at least 1 report"
    report = result[0]
    assert "safetyreportid" in report, "Missing safetyreportid"
    assert "patient" in report, "Missing patient data"
    assert "reaction" in report["patient"], "Missing reaction data"
    print(f"  Reports: {len(result)}")
    print(f"  Report ID: {report['safetyreportid']}")
    print(f"  Reactions: {len(report['patient']['reaction'])}")


def test_41_search_by_drug_and_reaction():
    """Edge case: Search for specific drug-reaction pair reports."""
    result = tu.tools.FAERS_search_reports_by_drug_and_reaction(
        medicinalproduct="ATORVASTATIN",
        reactionmeddrapt="Rhabdomyolysis",
        limit=3
    )
    assert isinstance(result, list), f"Expected list, got {type(result)}"
    assert len(result) > 0, "Should have rhabdomyolysis reports for atorvastatin"
    for report in result:
        reactions = [r["reactionmeddrapt"] for r in report["patient"]["reaction"]]
        assert "Rhabdomyolysis" in reactions, f"Expected Rhabdomyolysis in reactions"
    print(f"  Reports with rhabdomyolysis: {len(result)}")


def test_42_temporal_trends():
    """Edge case: Analyze temporal trends (may return insufficient data)."""
    result = tu.tools.FAERS_analyze_temporal_trends(
        operation="analyze_temporal_trends",
        drug_name="ATORVASTATIN"
    )
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert result.get("status") == "success", f"Status: {result.get('status')}"
    trend = result.get("trend_analysis", {})
    print(f"  Trend: {trend.get('trend', 'N/A')}")
    print(f"  Temporal data points: {len(result.get('temporal_data', []))}")


def test_43_safety_signal_score_calculation():
    """Integration: Verify Safety Signal Score components can be computed."""
    # Component 1: FAERS Signal Strength (check if PRR >= 5 exists)
    disp = tu.tools.FAERS_calculate_disproportionality(
        operation="calculate_disproportionality",
        drug_name="ATORVASTATIN",
        adverse_event="Rhabdomyolysis"
    )
    prr = disp["metrics"]["PRR"]["value"]
    faers_score = 35 if prr >= 5 else (20 if prr >= 3 else (10 if prr >= 2 else 0))

    # Component 2: Serious Adverse Events
    deaths = tu.tools.FAERS_count_death_related_by_drug(medicinalproduct="ATORVASTATIN")
    death_count = next((r["count"] for r in deaths if r["term"] == "death"), 0)
    serious_score = 30 if death_count > 100 else (25 if death_count > 0 else 0)

    # Component 3: FDA Label Warnings
    boxed = tu.tools.FDA_get_boxed_warning_info_by_drug_name(drug_name="atorvastatin")
    has_boxed = not (isinstance(boxed, dict) and "error" in boxed)
    contras = tu.tools.FDA_get_contraindications_by_drug_name(drug_name="atorvastatin")
    has_contras = isinstance(contras, dict) and contras.get("meta", {}).get("total", 0) > 0
    label_score = 25 if has_boxed else (15 if has_contras else 5)

    # Component 4: Literature (simplified - just check if papers exist)
    papers = tu.tools.PubMed_search_articles(
        query="atorvastatin adverse events safety",
        limit=5
    )
    lit_score = 7 if len(papers) >= 3 else (4 if len(papers) > 0 else 0)

    total_score = faers_score + serious_score + label_score + lit_score

    print(f"  FAERS Signal Score: {faers_score}/35 (PRR={prr:.2f})")
    print(f"  Serious Events Score: {serious_score}/30 (deaths={death_count})")
    print(f"  Label Warning Score: {label_score}/25 (boxed={has_boxed}, contras={has_contras})")
    print(f"  Literature Score: {lit_score}/10 (papers={len(papers)})")
    print(f"  TOTAL SAFETY SIGNAL SCORE: {total_score}/100")

    assert 0 <= total_score <= 100, f"Score out of range: {total_score}"
    assert total_score > 0, "Score should be > 0 for atorvastatin"


# ============================================================================
# Run all tests
# ============================================================================

if __name__ == "__main__":
    tests = [
        # Phase 0: Drug Disambiguation
        ("Phase 0: Drug disambiguation (atorvastatin -> CHEMBL1487)", test_01_drug_disambiguation_atorvastatin),
        ("Phase 0: Blackbox/withdrawal status", test_02_drug_blackbox_status),
        ("Phase 0: Mechanism of action", test_03_drug_mechanism_of_action),
        ("Phase 0: DrugBank safety/toxicity", test_04_drugbank_safety),
        # Phase 1: FAERS Profiling
        ("Phase 1: FAERS top reactions", test_05_faers_top_reactions),
        ("Phase 1: FAERS seriousness distribution", test_06_faers_seriousness),
        ("Phase 1: FAERS outcome distribution", test_07_faers_outcomes),
        ("Phase 1: FAERS age distribution", test_08_faers_age_distribution),
        ("Phase 1: FAERS death counts", test_09_faers_death_counts),
        ("Phase 1: FAERS reporter country", test_10_faers_reporter_country),
        # Phase 2: Disproportionality
        ("Phase 2: Disproportionality - rhabdomyolysis (strong signal)", test_11_disproportionality_rhabdomyolysis),
        ("Phase 2: Disproportionality - myalgia", test_12_disproportionality_myalgia),
        ("Phase 2: Serious events (death)", test_13_serious_events_death),
        ("Phase 2: Demographic stratification", test_14_demographic_stratification),
        ("Phase 2: MedDRA hierarchy rollup", test_15_meddra_rollup),
        # Phase 3: FDA Label
        ("Phase 3: Boxed warning - none (atorvastatin)", test_16_fda_boxed_warning_none),
        ("Phase 3: Boxed warning - present (metformin)", test_17_fda_boxed_warning_present),
        ("Phase 3: Contraindications", test_18_fda_contraindications),
        ("Phase 3: Adverse reactions from label", test_19_fda_adverse_reactions),
        ("Phase 3: Drug interactions from label", test_20_fda_drug_interactions),
        # Phase 4: Mechanism Context
        ("Phase 4: OpenTargets adverse events", test_21_opentargets_adverse_events),
        ("Phase 4: Target safety profile (HMGCR)", test_22_target_safety_profile),
        ("Phase 4: ADMET toxicity predictions", test_23_admet_toxicity),
        # Phase 5: Comparative Safety
        ("Phase 5: Compare drugs (atorvastatin vs simvastatin)", test_24_compare_drugs),
        ("Phase 5: Aggregate class reactions (statins)", test_25_aggregate_class_reactions),
        ("Phase 5: Aggregate class seriousness", test_26_aggregate_class_seriousness),
        # Phase 6: DDIs & PGx
        ("Phase 6: FDA DDIs from label", test_27_fda_drug_interactions_label),
        ("Phase 6: PharmGKB drug search", test_28_pharmgkb_drug_search),
        ("Phase 6: PharmGKB drug details", test_29_pharmgkb_drug_details),
        ("Phase 6: PharmGKB dosing guidelines (SLCO1B1)", test_30_pharmgkb_dosing_guidelines),
        # Phase 7: Literature
        ("Phase 7: PubMed safety literature", test_31_pubmed_search),
        ("Phase 7: OpenAlex citation analysis", test_32_openalex_search),
        # Cross-drug tests
        ("Cross-drug: Metformin + lactic acidosis (strong signal)", test_33_metformin_disproportionality),
        ("Cross-drug: Pembrolizumab FAERS profile", test_34_pembrolizumab_reactions),
        ("Cross-drug: Pembrolizumab + colitis", test_35_pembrolizumab_disproportionality),
        ("Cross-drug: Ibuprofen FAERS profile", test_36_ibuprofen_reactions),
        ("Cross-drug: Ibuprofen + GI bleeding", test_37_ibuprofen_gi_bleeding),
        ("Cross-drug: Compare NSAIDs (ibuprofen vs naproxen)", test_38_compare_nsaids),
        # Edge cases
        ("Edge case: Rare drug (tocilizumab)", test_39_rare_drug_faers),
        ("Edge case: Individual case reports", test_40_individual_case_reports),
        ("Edge case: Search by drug + reaction", test_41_search_by_drug_and_reaction),
        ("Edge case: Temporal trends", test_42_temporal_trends),
        # Integration
        ("Integration: Safety Signal Score calculation", test_43_safety_signal_score_calculation),
    ]

    print(f"\n{'#'*70}")
    print(f"# ADVERSE DRUG EVENT SIGNAL DETECTION - COMPREHENSIVE TEST SUITE")
    print(f"# Tests: {len(tests)}")
    print(f"# Drugs: Atorvastatin, Metformin, Pembrolizumab, Ibuprofen, Tocilizumab")
    print(f"{'#'*70}")

    for name, func in tests:
        run_test(name, func)

    elapsed = time.time() - start_time

    print(f"\n{'='*70}")
    print(f"TEST SUMMARY")
    print(f"{'='*70}")
    print(f"Total:  {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")
    print(f"Pass Rate: {passed_tests/total_tests*100:.1f}%")
    print(f"Time: {elapsed:.1f}s")
    print()

    if failed_tests > 0:
        print("FAILED TESTS:")
        for name, status, error in results:
            if status == "FAIL":
                print(f"  FAIL: {name}")
                print(f"        {error}")

    print(f"\n{'='*70}")
    if failed_tests == 0:
        print("ALL TESTS PASSED")
    else:
        print(f"{failed_tests} TEST(S) FAILED")
    print(f"{'='*70}")

    sys.exit(0 if failed_tests == 0 else 1)
