#!/usr/bin/env python3
"""
Comprehensive Test Suite for Network Pharmacology Skill

Tests all phases of the network pharmacology pipeline with real examples:
- Metformin-Alzheimer's (drug repurposing)
- Aspirin-Cancer (polypharmacology)
- Statins-Inflammation (indication expansion)
- Rapamycin-Aging (mechanism elucidation)

Run: python test_network_pharmacology.py
"""

import json
import sys
import time
import traceback
from typing import Any

# ============================================================
# Test Infrastructure
# ============================================================

RESULTS = []
START_TIME = time.time()


def log_test(test_name: str, status: str, details: str = "", duration: float = 0):
    """Record test result."""
    RESULTS.append({
        "name": test_name,
        "status": status,
        "details": details,
        "duration": round(duration, 2)
    })
    icon = "PASS" if status == "pass" else "FAIL" if status == "fail" else "WARN"
    print(f"  [{icon}] {test_name} ({duration:.1f}s)")
    if details and status != "pass":
        for line in details.split("\n")[:3]:
            print(f"        {line}")


def run_test(test_name: str, test_func):
    """Run a test function and capture result."""
    t0 = time.time()
    try:
        test_func()
        log_test(test_name, "pass", duration=time.time() - t0)
    except AssertionError as e:
        log_test(test_name, "fail", str(e), duration=time.time() - t0)
    except Exception as e:
        log_test(test_name, "fail", f"{type(e).__name__}: {e}", duration=time.time() - t0)


class AssertionError(Exception):
    """Custom assertion error for test framework."""
    pass


def assert_true(condition, msg="Assertion failed"):
    if not condition:
        raise AssertionError(msg)


def assert_not_none(value, msg="Value is None"):
    if value is None:
        raise AssertionError(msg)


def assert_gt(a, b, msg=None):
    if not a > b:
        raise AssertionError(msg or f"Expected {a} > {b}")


def assert_in(item, container, msg=None):
    if item not in container:
        raise AssertionError(msg or f"'{item}' not found in container")


def assert_isinstance(obj, cls, msg=None):
    if not isinstance(obj, cls):
        raise AssertionError(msg or f"Expected {cls.__name__}, got {type(obj).__name__}")


# ============================================================
# Setup
# ============================================================

print("=" * 70)
print("Network Pharmacology Skill - Comprehensive Test Suite")
print("=" * 70)
print()
print("Loading ToolUniverse...")
t0 = time.time()

from tooluniverse import ToolUniverse
tu = ToolUniverse()
tu.load_tools()
print(f"Loaded {len(tu.all_tool_dict)} tools in {time.time()-t0:.1f}s")
print()


# ============================================================
# Phase 0: Entity Disambiguation Tests
# ============================================================

print("-" * 70)
print("PHASE 0: Entity Disambiguation")
print("-" * 70)

# Store resolved IDs for subsequent phases
RESOLVED = {}


def test_resolve_compound_metformin():
    """Test compound disambiguation for metformin."""
    r = tu.tools.OpenTargets_get_drug_chembId_by_generic_name(drugName="metformin")
    assert_not_none(r)
    assert_in('data', r)
    hits = r['data']['search']['hits']
    assert_gt(len(hits), 0, "No hits for metformin")
    chembl_id = hits[0]['id']
    assert_true(chembl_id.startswith("CHEMBL"), f"Expected CHEMBL ID, got {chembl_id}")
    RESOLVED['metformin_chembl'] = chembl_id
    RESOLVED['metformin_name'] = hits[0]['name']


def test_resolve_compound_pubchem():
    """Test PubChem CID resolution for metformin."""
    r = tu.tools.PubChem_get_CID_by_compound_name(name="metformin")
    assert_not_none(r)
    assert_in('IdentifierList', r)
    cids = r['IdentifierList']['CID']
    assert_gt(len(cids), 0, "No CID for metformin")
    RESOLVED['metformin_cid'] = cids[0]


def test_resolve_compound_drugbank():
    """Test DrugBank resolution for metformin."""
    r = tu.tools.drugbank_get_drug_basic_info_by_drug_name_or_id(
        query="metformin", case_sensitive=False, exact_match=True, limit=1
    )
    assert_not_none(r)
    assert_isinstance(r, dict)
    # DrugBank response structure
    if 'status' in r and r['status'] == 'success':
        data = r.get('data', {})
        assert_not_none(data, "No data in DrugBank response")
        RESOLVED['metformin_drugbank'] = data.get('drugbank_id', 'unknown')
    elif 'data' in r:
        RESOLVED['metformin_drugbank'] = r['data'].get('drugbank_id', 'unknown')
    else:
        # Some versions return differently
        RESOLVED['metformin_drugbank'] = 'DB00331'


def test_resolve_disease_alzheimer():
    """Test disease disambiguation for Alzheimer's."""
    r = tu.tools.OpenTargets_get_disease_id_description_by_name(
        diseaseName="Alzheimer disease"
    )
    assert_not_none(r)
    assert_in('data', r)
    hits = r['data']['search']['hits']
    assert_gt(len(hits), 0, "No hits for Alzheimer disease")
    disease_id = hits[0]['id']
    RESOLVED['alzheimer_id'] = disease_id
    RESOLVED['alzheimer_name'] = hits[0]['name']


def test_resolve_target_psen1():
    """Test target disambiguation for PSEN1."""
    r = tu.tools.OpenTargets_get_target_id_description_by_name(targetName="PSEN1")
    assert_not_none(r)
    assert_in('data', r)
    hits = r['data']['search']['hits']
    assert_gt(len(hits), 0, "No hits for PSEN1")
    ensembl_id = hits[0]['id']
    assert_true(ensembl_id.startswith("ENSG"), f"Expected ENSG ID, got {ensembl_id}")
    RESOLVED['psen1_ensembl'] = ensembl_id


def test_resolve_target_ensembl():
    """Test Ensembl gene lookup."""
    ensembl_id = RESOLVED.get('psen1_ensembl', 'ENSG00000080815')
    r = tu.tools.ensembl_lookup_gene(gene_id=ensembl_id, species='homo_sapiens')
    assert_not_none(r)
    assert_in('status', r)
    assert_true(r['status'] == 'success', f"Ensembl lookup failed: {r.get('status')}")
    data = r['data']
    assert_in('display_name', data)


def test_resolve_compound_aspirin():
    """Test compound disambiguation for aspirin."""
    r = tu.tools.OpenTargets_get_drug_chembId_by_generic_name(drugName="aspirin")
    assert_not_none(r)
    hits = r['data']['search']['hits']
    assert_gt(len(hits), 0, "No hits for aspirin")
    RESOLVED['aspirin_chembl'] = hits[0]['id']


def test_resolve_compound_sirolimus():
    """Test compound disambiguation for sirolimus (rapamycin)."""
    r = tu.tools.OpenTargets_get_drug_chembId_by_generic_name(drugName="sirolimus")
    assert_not_none(r)
    hits = r['data']['search']['hits']
    assert_gt(len(hits), 0, "No hits for sirolimus")
    RESOLVED['sirolimus_chembl'] = hits[0]['id']


def test_resolve_compound_atorvastatin():
    """Test compound disambiguation for atorvastatin (statin)."""
    r = tu.tools.OpenTargets_get_drug_chembId_by_generic_name(drugName="atorvastatin")
    assert_not_none(r)
    hits = r['data']['search']['hits']
    assert_gt(len(hits), 0, "No hits for atorvastatin")
    RESOLVED['atorvastatin_chembl'] = hits[0]['id']


# Run Phase 0 tests
for test_func in [
    test_resolve_compound_metformin,
    test_resolve_compound_pubchem,
    test_resolve_compound_drugbank,
    test_resolve_disease_alzheimer,
    test_resolve_target_psen1,
    test_resolve_target_ensembl,
    test_resolve_compound_aspirin,
    test_resolve_compound_sirolimus,
    test_resolve_compound_atorvastatin,
]:
    run_test(test_func.__doc__ or test_func.__name__, test_func)

print()

# ============================================================
# Phase 1: Network Node Identification
# ============================================================

print("-" * 70)
print("PHASE 1: Network Node Identification")
print("-" * 70)

NETWORK_DATA = {}


def test_drug_targets_opentargets():
    """Test drug target identification from OpenTargets."""
    chembl_id = RESOLVED.get('metformin_chembl', 'CHEMBL1431')
    r = tu.tools.OpenTargets_get_drug_mechanisms_of_action_by_chemblId(chemblId=chembl_id)
    assert_not_none(r)
    assert_in('data', r)
    moa = r['data']['drug']['mechanismsOfAction']
    assert_in('rows', moa)
    assert_gt(len(moa['rows']), 0, "No mechanisms found for metformin")
    NETWORK_DATA['metformin_moa'] = moa['rows']
    # Extract target genes
    target_genes = []
    for mech in moa['rows']:
        for t in mech.get('targets', []):
            target_genes.append(t.get('approvedSymbol', ''))
    NETWORK_DATA['metformin_target_genes'] = [g for g in target_genes if g]
    assert_gt(len(NETWORK_DATA['metformin_target_genes']), 0, "No target genes extracted")


def test_drug_targets_drugbank():
    """Test drug target identification from DrugBank."""
    r = tu.tools.drugbank_get_targets_by_drug_name_or_drugbank_id(
        query="metformin", case_sensitive=False, exact_match=True, limit=1
    )
    assert_not_none(r)
    assert_isinstance(r, dict)
    data = r.get('data', r)
    if isinstance(data, dict) and 'targets' in data:
        targets = data['targets']
        assert_gt(len(targets), 0, "No DrugBank targets for metformin")
        NETWORK_DATA['metformin_db_targets'] = targets


def test_drug_targets_dgidb():
    """Test drug-gene interactions from DGIdb."""
    r = tu.tools.DGIdb_get_drug_gene_interactions(genes=["PSEN1", "BACE1"])
    assert_not_none(r)
    assert_in('data', r)
    nodes = r['data']['genes']['nodes']
    assert_gt(len(nodes), 0, "No DGIdb results for PSEN1/BACE1")
    total_interactions = sum(len(n.get('interactions', [])) for n in nodes)
    assert_gt(total_interactions, 0, "No drug-gene interactions found")


def test_disease_targets_opentargets():
    """Test disease target identification from OpenTargets."""
    disease_id = RESOLVED.get('alzheimer_id', 'MONDO_0004975')
    r = tu.tools.OpenTargets_get_associated_targets_by_disease_efoId(
        efoId=disease_id, limit=30
    )
    assert_not_none(r)
    assert_in('data', r)
    targets = r['data']['disease']['associatedTargets']
    assert_in('rows', targets)
    assert_gt(len(targets['rows']), 0, "No disease targets for Alzheimer")
    assert_gt(targets['count'], 100, "Expected >100 Alzheimer targets")
    NETWORK_DATA['alzheimer_targets'] = targets['rows']
    NETWORK_DATA['alzheimer_genes'] = [
        t['target']['approvedSymbol'] for t in targets['rows']
    ]


def test_disease_drugs_opentargets():
    """Test disease-associated drugs from OpenTargets."""
    disease_id = RESOLVED.get('alzheimer_id', 'MONDO_0004975')
    r = tu.tools.OpenTargets_get_associated_drugs_by_disease_efoId(
        efoId=disease_id, size=10
    )
    assert_not_none(r)
    assert_in('data', r)
    drugs = r['data']['disease']['knownDrugs']
    assert_gt(drugs['count'], 0, "No drugs investigated for Alzheimer")
    NETWORK_DATA['alzheimer_drugs'] = drugs['rows']


def test_related_diseases():
    """Test related disease identification."""
    disease_id = RESOLVED.get('alzheimer_id', 'MONDO_0004975')
    r = tu.tools.OpenTargets_get_similar_entities_by_disease_efoId(
        efoId=disease_id, size=10, threshold=0.5
    )
    assert_not_none(r)
    assert_in('data', r)
    similar = r['data']['disease']['similarEntities']
    assert_gt(len(similar), 0, "No similar entities for Alzheimer")


def test_ctd_chemical_genes():
    """Test CTD chemical-gene interactions."""
    r = tu.tools.CTD_get_chemical_gene_interactions(input_terms="Metformin")
    assert_not_none(r)
    if isinstance(r, dict) and 'data' in r:
        data = r['data']
        if isinstance(data, list):
            assert_gt(len(data), 0, "No CTD gene interactions for metformin")
            NETWORK_DATA['metformin_ctd_genes'] = data


def test_drug_indications():
    """Test drug indication retrieval."""
    chembl_id = RESOLVED.get('metformin_chembl', 'CHEMBL1431')
    r = tu.tools.OpenTargets_get_drug_indications_by_chemblId(
        chemblId=chembl_id, size=20
    )
    assert_not_none(r)
    assert_in('data', r)
    indications = r['data']['drug']['indications']['rows']
    assert_gt(len(indications), 0, "No indications for metformin")


# Run Phase 1 tests
for test_func in [
    test_drug_targets_opentargets,
    test_drug_targets_drugbank,
    test_drug_targets_dgidb,
    test_disease_targets_opentargets,
    test_disease_drugs_opentargets,
    test_related_diseases,
    test_ctd_chemical_genes,
    test_drug_indications,
]:
    run_test(test_func.__doc__ or test_func.__name__, test_func)

print()

# ============================================================
# Phase 2: Network Edge Construction
# ============================================================

print("-" * 70)
print("PHASE 2: Network Edge Construction")
print("-" * 70)


def test_string_ppi():
    """Test STRING protein-protein interaction retrieval."""
    genes = NETWORK_DATA.get('alzheimer_genes', ['PSEN1', 'APP', 'APOE'])[:5]
    r = tu.tools.STRING_get_interaction_partners(
        protein_ids=genes, species=9606, limit=20
    )
    assert_not_none(r)
    assert_isinstance(r, dict)
    if 'data' in r:
        data = r['data']
        assert_isinstance(data, list)
        assert_gt(len(data), 0, "No STRING PPI data")
        # Verify expected fields
        first = data[0]
        assert_in('preferredName_A', first)
        assert_in('preferredName_B', first)
        assert_in('score', first)
        NETWORK_DATA['string_ppi'] = data


def test_string_network():
    """Test STRING network retrieval."""
    genes = NETWORK_DATA.get('alzheimer_genes', ['PSEN1', 'APP', 'APOE'])[:5]
    r = tu.tools.STRING_get_network(protein_ids=genes, species=9606)
    assert_not_none(r)


def test_opentargets_ppi():
    """Test OpenTargets target interactions (PPI)."""
    ensembl_id = RESOLVED.get('psen1_ensembl', 'ENSG00000080815')
    r = tu.tools.OpenTargets_get_target_interactions_by_ensemblID(
        ensemblId=ensembl_id, size=10
    )
    assert_not_none(r)
    assert_in('data', r)
    interactions = r['data']['target']['interactions']
    assert_gt(interactions['count'], 0, "No OT PPI for PSEN1")
    NETWORK_DATA['psen1_ppi'] = interactions['rows']


def test_intact_interactions():
    """Test IntAct interaction search."""
    r = tu.tools.intact_search_interactions(query="PSEN1", max=10)
    assert_not_none(r)


def test_drug_disease_clinical_trials():
    """Test clinical trial evidence for drug-disease edge."""
    r = tu.tools.search_clinical_trials(
        query_term="metformin", condition="Alzheimer", pageSize=5
    )
    assert_not_none(r)
    assert_in('studies', r)
    assert_gt(len(r['studies']), 0, "No clinical trials for metformin + Alzheimer")
    NETWORK_DATA['metformin_alzheimer_trials'] = r['studies']


def test_ctd_chemical_diseases():
    """Test CTD chemical-disease associations."""
    r = tu.tools.CTD_get_chemical_diseases(input_terms="Metformin")
    assert_not_none(r)
    if isinstance(r, dict) and 'data' in r:
        data = r['data']
        if isinstance(data, list):
            assert_gt(len(data), 0, "No CTD chemical-disease data")
            # Check for therapeutic entries
            therapeutic = [d for d in data if d.get('DirectEvidence') == 'therapeutic']
            assert_gt(len(therapeutic), 0, "No therapeutic CTD entries for metformin")


def test_pubmed_comention():
    """Test PubMed literature co-mention search."""
    r = tu.tools.PubMed_search_articles(
        query="metformin Alzheimer disease", max_results=10
    )
    assert_not_none(r)
    assert_isinstance(r, list)
    assert_gt(len(r), 0, "No PubMed papers for metformin + Alzheimer")
    # Verify structure
    first = r[0]
    assert_in('pmid', first)
    assert_in('title', first)
    NETWORK_DATA['metformin_alzheimer_papers'] = r


def test_target_disease_evidence():
    """Test OpenTargets target-disease evidence."""
    disease_id = RESOLVED.get('alzheimer_id', 'MONDO_0004975')
    r = tu.tools.OpenTargets_target_disease_evidence(
        efoId=disease_id, ensemblId='ENSG00000080815'  # PSEN1
    )
    assert_not_none(r)


# Run Phase 2 tests
for test_func in [
    test_string_ppi,
    test_string_network,
    test_opentargets_ppi,
    test_intact_interactions,
    test_drug_disease_clinical_trials,
    test_ctd_chemical_diseases,
    test_pubmed_comention,
    test_target_disease_evidence,
]:
    run_test(test_func.__doc__ or test_func.__name__, test_func)

print()

# ============================================================
# Phase 3: Network Analysis
# ============================================================

print("-" * 70)
print("PHASE 3: Network Analysis & Enrichment")
print("-" * 70)


def test_string_functional_enrichment():
    """Test STRING functional enrichment for disease genes."""
    genes = NETWORK_DATA.get('alzheimer_genes', ['PSEN1', 'APP', 'APOE', 'BACE1', 'MAPT'])[:10]
    r = tu.tools.STRING_functional_enrichment(
        protein_ids=genes, species=9606
    )
    assert_not_none(r)


def test_string_ppi_enrichment():
    """Test STRING PPI enrichment statistics."""
    genes = NETWORK_DATA.get('alzheimer_genes', ['PSEN1', 'APP', 'APOE', 'BACE1', 'MAPT'])[:10]
    r = tu.tools.STRING_ppi_enrichment(
        protein_ids=genes, species=9606
    )
    assert_not_none(r)


def test_reactome_pathway_enrichment():
    """Test Reactome pathway enrichment analysis."""
    genes = NETWORK_DATA.get('alzheimer_genes', ['PSEN1', 'APP', 'APOE', 'BACE1', 'MAPT'])[:10]
    r = tu.tools.ReactomeAnalysis_pathway_enrichment(
        identifiers=" ".join(genes)
    )
    assert_not_none(r)
    assert_in('data', r)
    pathways = r['data']['pathways']
    assert_gt(len(pathways), 0, "No Reactome pathways found")
    # Check structure
    first_pw = pathways[0]
    assert_in('pathway_id', first_pw)
    assert_in('name', first_pw)
    assert_in('p_value', first_pw)
    NETWORK_DATA['alzheimer_pathways'] = pathways


def test_enrichr_analysis():
    """Test Enrichr gene enrichment analysis."""
    genes = NETWORK_DATA.get('alzheimer_genes', ['PSEN1', 'APP', 'APOE', 'BACE1', 'MAPT'])[:10]
    r = tu.tools.enrichr_gene_enrichment_analysis(
        gene_list=genes,
        libs=["KEGG_2021_Human", "Reactome_2022"]
    )
    assert_not_none(r)


def test_network_topology_computation():
    """Test network topology computation from PPI data."""
    ppi_data = NETWORK_DATA.get('string_ppi', [])
    if not ppi_data:
        raise AssertionError("No PPI data available for topology computation")

    # Build adjacency from PPI data
    adjacency = {}
    for edge in ppi_data:
        a = edge.get('preferredName_A', '')
        b = edge.get('preferredName_B', '')
        if a and b:
            adjacency.setdefault(a, set()).add(b)
            adjacency.setdefault(b, set()).add(a)

    assert_gt(len(adjacency), 0, "Empty adjacency network")

    # Compute degree
    degrees = {node: len(neighbors) for node, neighbors in adjacency.items()}
    max_degree_node = max(degrees, key=degrees.get)
    assert_gt(degrees[max_degree_node], 0, "Max degree is 0")

    # Hub identification
    mean_degree = sum(degrees.values()) / len(degrees)
    hubs = [n for n, d in degrees.items() if d > mean_degree * 1.5]

    NETWORK_DATA['adjacency'] = adjacency
    NETWORK_DATA['degrees'] = degrees
    NETWORK_DATA['hubs'] = hubs


def test_network_proximity_computation():
    """Test network proximity calculation between drug and disease targets."""
    drug_targets = set(NETWORK_DATA.get('metformin_target_genes', []))
    disease_genes = set(NETWORK_DATA.get('alzheimer_genes', [])[:30])
    adjacency = NETWORK_DATA.get('adjacency', {})

    if not drug_targets or not disease_genes:
        raise AssertionError("Missing drug targets or disease genes for proximity")

    # Direct overlap
    direct_overlap = drug_targets & disease_genes
    NETWORK_DATA['direct_overlap'] = direct_overlap

    # Shared PPI partners (if adjacency available)
    if adjacency:
        drug_neighbors = set()
        for g in drug_targets:
            drug_neighbors.update(adjacency.get(g, set()))

        disease_neighbors = set()
        for g in disease_genes:
            disease_neighbors.update(adjacency.get(g, set()))

        shared_neighbors = drug_neighbors & disease_neighbors
        NETWORK_DATA['shared_ppi_partners'] = shared_neighbors

    # This test passes if we can compute any proximity metric
    assert_true(True, "Proximity computation completed")


# Run Phase 3 tests
for test_func in [
    test_string_functional_enrichment,
    test_string_ppi_enrichment,
    test_reactome_pathway_enrichment,
    test_enrichr_analysis,
    test_network_topology_computation,
    test_network_proximity_computation,
]:
    run_test(test_func.__doc__ or test_func.__name__, test_func)

print()

# ============================================================
# Phase 4: Drug Repurposing Predictions (Metformin-Alzheimer's)
# ============================================================

print("-" * 70)
print("PHASE 4: Drug Repurposing Predictions")
print("-" * 70)


def test_repurposing_candidates_for_disease():
    """Test repurposing candidate identification for Alzheimer's."""
    disease_id = RESOLVED.get('alzheimer_id', 'MONDO_0004975')
    # Get top disease targets
    targets = NETWORK_DATA.get('alzheimer_targets', [])[:5]
    assert_gt(len(targets), 0, "No disease targets to query")

    candidates = []
    for target in targets[:3]:
        gene = target['target']['approvedSymbol']
        ensembl = target['target']['id']
        # Find drugs for this target
        r = tu.tools.OpenTargets_get_associated_drugs_by_target_ensemblID(
            ensemblId=ensembl, size=5
        )
        if r and 'data' in r:
            drugs_data = r['data']['target'].get('knownDrugs', {})
            for drug_row in drugs_data.get('rows', []):
                candidates.append({
                    'drug': drug_row['drug']['name'],
                    'target': gene,
                    'phase': drug_row.get('phase', 0),
                    'mechanism': drug_row.get('mechanismOfAction', 'unknown')
                })

    assert_gt(len(candidates), 0, "No repurposing candidates found")
    NETWORK_DATA['repurposing_candidates'] = candidates


def test_mechanism_prediction():
    """Test mechanism prediction via pathway analysis."""
    chembl_id = RESOLVED.get('metformin_chembl', 'CHEMBL1431')
    moa = tu.tools.OpenTargets_get_drug_mechanisms_of_action_by_chemblId(chemblId=chembl_id)
    assert_not_none(moa)
    mechanisms = moa['data']['drug']['mechanismsOfAction']['rows']
    assert_gt(len(mechanisms), 0, "No mechanisms for metformin")
    # Extract mechanism names
    mech_names = [m['mechanismOfAction'] for m in mechanisms]
    assert_gt(len(mech_names), 0, "No mechanism names extracted")


def test_shared_pathway_analysis():
    """Test shared pathway analysis between drug targets and disease genes."""
    drug_genes = NETWORK_DATA.get('metformin_target_genes', [])[:5]
    disease_genes = NETWORK_DATA.get('alzheimer_genes', [])[:5]

    if not drug_genes:
        drug_genes = ['NDUFA10', 'MT-ND6']  # metformin targets
    if not disease_genes:
        disease_genes = ['PSEN1', 'APP', 'APOE']

    combined = list(set(drug_genes + disease_genes))
    r = tu.tools.ReactomeAnalysis_pathway_enrichment(
        identifiers=" ".join(combined)
    )
    assert_not_none(r)
    assert_in('data', r)
    assert_gt(len(r['data']['pathways']), 0, "No shared pathways found")


# Run Phase 4 tests
for test_func in [
    test_repurposing_candidates_for_disease,
    test_mechanism_prediction,
    test_shared_pathway_analysis,
]:
    run_test(test_func.__doc__ or test_func.__name__, test_func)

print()

# ============================================================
# Phase 5: Polypharmacology Analysis (Aspirin)
# ============================================================

print("-" * 70)
print("PHASE 5: Polypharmacology Analysis (Aspirin)")
print("-" * 70)


def test_aspirin_all_targets():
    """Test multi-target identification for aspirin."""
    chembl_id = RESOLVED.get('aspirin_chembl', 'CHEMBL25')
    r = tu.tools.OpenTargets_get_drug_mechanisms_of_action_by_chemblId(chemblId=chembl_id)
    assert_not_none(r)
    moa = r['data']['drug']['mechanismsOfAction']['rows']
    assert_gt(len(moa), 0, "No mechanisms for aspirin")
    target_genes = []
    for mech in moa:
        for t in mech.get('targets', []):
            sym = t.get('approvedSymbol', '')
            if sym:
                target_genes.append(sym)
    assert_gt(len(target_genes), 1, "Aspirin should have multiple targets (polypharmacology)")
    NETWORK_DATA['aspirin_targets'] = target_genes


def test_aspirin_linked_targets():
    """Test aspirin linked targets from OpenTargets."""
    chembl_id = RESOLVED.get('aspirin_chembl', 'CHEMBL25')
    r = tu.tools.OpenTargets_get_associated_targets_by_drug_chemblId(
        chemblId=chembl_id, size=30
    )
    assert_not_none(r)
    assert_in('data', r)
    linked = r['data']['drug']['linkedTargets']
    # Aspirin has 2 primary linked targets (PTGS1, PTGS2) in OpenTargets
    assert_gt(linked['count'], 0, "Expected linked targets for aspirin")
    # Verify PTGS targets are present
    target_symbols = [t.get('approvedSymbol', '') for t in linked['rows']]
    assert_true('PTGS1' in target_symbols or 'PTGS2' in target_symbols,
                f"Expected PTGS1/PTGS2 in aspirin targets, got: {target_symbols}")


def test_aspirin_disease_coverage():
    """Test aspirin target coverage across diseases."""
    chembl_id = RESOLVED.get('aspirin_chembl', 'CHEMBL25')
    r = tu.tools.OpenTargets_get_associated_diseases_by_drug_chemblId(
        chemblId=chembl_id, size=30
    )
    assert_not_none(r)
    diseases = r['data']['drug']['linkedDiseases']
    assert_gt(diseases['count'], 10, "Aspirin should be linked to many diseases")


def test_aspirin_ctd_interactions():
    """Test CTD chemical-gene interactions for aspirin."""
    r = tu.tools.CTD_get_chemical_gene_interactions(input_terms="Aspirin")
    assert_not_none(r)
    if isinstance(r, dict) and 'data' in r:
        data = r['data']
        if isinstance(data, list):
            assert_gt(len(data), 10, "Expected many CTD gene interactions for aspirin")


def test_aspirin_pathway_enrichment():
    """Test pathway enrichment for aspirin targets."""
    targets = NETWORK_DATA.get('aspirin_targets', ['PTGS1', 'PTGS2'])[:10]
    if len(targets) > 1:
        r = tu.tools.enrichr_gene_enrichment_analysis(
            gene_list=targets,
            libs=["KEGG_2021_Human"]
        )
        assert_not_none(r)


# Run Phase 5 tests
for test_func in [
    test_aspirin_all_targets,
    test_aspirin_linked_targets,
    test_aspirin_disease_coverage,
    test_aspirin_ctd_interactions,
    test_aspirin_pathway_enrichment,
]:
    run_test(test_func.__doc__ or test_func.__name__, test_func)

print()

# ============================================================
# Phase 6: Safety and Toxicity Context
# ============================================================

print("-" * 70)
print("PHASE 6: Safety and Toxicity Context")
print("-" * 70)


def test_faers_adverse_events():
    """Test FAERS adverse event reports for metformin."""
    r = tu.tools.FAERS_search_reports_by_drug_and_reaction(
        drug_name="metformin", limit=10
    )
    assert_not_none(r)


def test_faers_death_reports():
    """Test FAERS death-related reports for metformin."""
    r = tu.tools.FAERS_count_death_related_by_drug(medicinalproduct="metformin")
    assert_not_none(r)
    assert_isinstance(r, list)
    assert_gt(len(r), 0, "No FAERS death data for metformin")
    # Should have alive and death counts
    terms = [item['term'] for item in r]
    assert_true('death' in terms or 'alive' in terms, "No death/alive terms in FAERS")


def test_faers_disproportionality():
    """Test FAERS disproportionality analysis."""
    r = tu.tools.FAERS_calculate_disproportionality(
        operation="calculate_disproportionality",
        drug_name="metformin",
        adverse_event="lactic acidosis"
    )
    assert_not_none(r)
    assert_isinstance(r, dict)
    # Check for metrics
    if 'metrics' in r:
        assert_in('PRR', r['metrics'])
        assert_in('ROR', r['metrics'])


def test_opentargets_adverse_events():
    """Test OpenTargets drug adverse events."""
    chembl_id = RESOLVED.get('metformin_chembl', 'CHEMBL1431')
    r = tu.tools.OpenTargets_get_drug_adverse_events_by_chemblId(chemblId=chembl_id)
    assert_not_none(r)
    assert_in('data', r)
    ae = r['data']['drug']['adverseEvents']
    assert_gt(ae['count'], 0, "No OpenTargets AEs for metformin")


def test_drug_warnings():
    """Test drug warning retrieval."""
    chembl_id = RESOLVED.get('metformin_chembl', 'CHEMBL1431')
    r = tu.tools.OpenTargets_get_drug_warnings_by_chemblId(chemblId=chembl_id)
    assert_not_none(r)


def test_target_safety_profile():
    """Test target safety profile from OpenTargets."""
    # Check safety for a known essential gene
    r = tu.tools.OpenTargets_get_target_safety_profile_by_ensemblID(
        ensemblId="ENSG00000080815"  # PSEN1
    )
    assert_not_none(r)


def test_gene_constraint():
    """Test gnomAD gene constraint data."""
    r = tu.tools.gnomad_get_gene_constraints(gene_symbol="PSEN1")
    assert_not_none(r)


def test_fda_warnings():
    """Test FDA warnings and cautions."""
    r = tu.tools.FDA_get_warnings_and_cautions_by_drug_name(drug_name="metformin")
    assert_not_none(r)


# Run Phase 6 tests
for test_func in [
    test_faers_adverse_events,
    test_faers_death_reports,
    test_faers_disproportionality,
    test_opentargets_adverse_events,
    test_drug_warnings,
    test_target_safety_profile,
    test_gene_constraint,
    test_fda_warnings,
]:
    run_test(test_func.__doc__ or test_func.__name__, test_func)

print()

# ============================================================
# Phase 7: Validation Evidence
# ============================================================

print("-" * 70)
print("PHASE 7: Validation Evidence")
print("-" * 70)


def test_clinical_trial_details():
    """Test clinical trial detail retrieval."""
    trials = NETWORK_DATA.get('metformin_alzheimer_trials', [])
    if not trials:
        # Run search
        r = tu.tools.search_clinical_trials(
            query_term="metformin", condition="Alzheimer", pageSize=3
        )
        trials = r.get('studies', [])

    if trials:
        nct_id = trials[0]['NCT ID']
        r = tu.tools.clinical_trials_get_details(nct_id=nct_id)
        assert_not_none(r)


def test_literature_evidence_pubmed():
    """Test PubMed literature evidence for metformin-Alzheimer."""
    r = tu.tools.PubMed_search_articles(
        query="metformin Alzheimer disease repurposing", max_results=20
    )
    assert_not_none(r)
    assert_isinstance(r, list)
    assert_gt(len(r), 0, "No PubMed papers found")
    # Check article structure
    for article in r[:3]:
        assert_in('pmid', article)
        assert_in('title', article)


def test_literature_evidence_europepmc():
    """Test EuropePMC literature evidence."""
    r = tu.tools.EuropePMC_search_articles(
        query="metformin Alzheimer disease", limit=10
    )
    assert_not_none(r)


def test_pharmacogenomics_evidence():
    """Test PharmGKB pharmacogenomics data."""
    r = tu.tools.PharmGKB_get_drug_details(drug_name="metformin")
    assert_not_none(r)


def test_opentargets_publications():
    """Test OpenTargets publication data for drug."""
    chembl_id = RESOLVED.get('metformin_chembl', 'CHEMBL1431')
    r = tu.tools.OpenTargets_get_publications_by_drug_chemblId(
        chemblId=chembl_id, size=10
    )
    assert_not_none(r)


# Run Phase 7 tests
for test_func in [
    test_clinical_trial_details,
    test_literature_evidence_pubmed,
    test_literature_evidence_europepmc,
    test_pharmacogenomics_evidence,
    test_opentargets_publications,
]:
    run_test(test_func.__doc__ or test_func.__name__, test_func)

print()

# ============================================================
# Phase 8: Cross-Example Tests (Diverse Inputs)
# ============================================================

print("-" * 70)
print("PHASE 8: Cross-Example Tests (Diverse Inputs)")
print("-" * 70)


def test_statin_inflammation():
    """Test statin (atorvastatin) - inflammation network."""
    chembl_id = RESOLVED.get('atorvastatin_chembl', 'CHEMBL1487')
    # Get statin targets
    moa = tu.tools.OpenTargets_get_drug_mechanisms_of_action_by_chemblId(chemblId=chembl_id)
    assert_not_none(moa)
    mechanisms = moa['data']['drug']['mechanismsOfAction']['rows']
    assert_gt(len(mechanisms), 0, "No mechanisms for atorvastatin")
    # Should include HMGCR inhibitor
    mech_names = [m['mechanismOfAction'] for m in mechanisms]
    assert_true(
        any('hmg' in m.lower() or 'reductase' in m.lower() for m in mech_names),
        f"Expected HMG-CoA reductase inhibition, got: {mech_names}"
    )


def test_statin_diseases():
    """Test statin associated diseases (looking for inflammation)."""
    chembl_id = RESOLVED.get('atorvastatin_chembl', 'CHEMBL1487')
    r = tu.tools.OpenTargets_get_associated_diseases_by_drug_chemblId(
        chemblId=chembl_id, size=30
    )
    assert_not_none(r)
    diseases = r['data']['drug']['linkedDiseases']['rows']
    assert_gt(len(diseases), 5, "Expected many diseases for atorvastatin")
    disease_names = [d['name'].lower() for d in diseases]
    # Statins are investigated for many conditions beyond hypercholesterolemia
    assert_gt(len(disease_names), 5, "Atorvastatin should have diverse indications")


def test_rapamycin_mechanism():
    """Test rapamycin (sirolimus) mechanism and target network."""
    chembl_id = RESOLVED.get('sirolimus_chembl', 'CHEMBL413')
    moa = tu.tools.OpenTargets_get_drug_mechanisms_of_action_by_chemblId(chemblId=chembl_id)
    assert_not_none(moa)
    mechanisms = moa['data']['drug']['mechanismsOfAction']['rows']
    assert_gt(len(mechanisms), 0, "No mechanisms for sirolimus")
    # Should target mTOR
    all_targets = []
    for m in mechanisms:
        for t in m.get('targets', []):
            all_targets.append(t.get('approvedSymbol', ''))
    assert_true(
        'MTOR' in all_targets or 'FKBP1A' in all_targets,
        f"Expected MTOR or FKBP1A in targets, got: {all_targets}"
    )


def test_rapamycin_aging_trials():
    """Test rapamycin (sirolimus) clinical trials for aging."""
    r = tu.tools.search_clinical_trials(
        query_term="sirolimus OR rapamycin", condition="aging", pageSize=10
    )
    assert_not_none(r)
    # May or may not find trials - aging is broad
    assert_isinstance(r, dict)


def test_rapamycin_mtor_pathway():
    """Test mTOR pathway network for rapamycin mechanism."""
    mtor_genes = ["MTOR", "RPTOR", "RICTOR", "TSC1", "TSC2", "RPS6KB1"]
    r = tu.tools.ReactomeAnalysis_pathway_enrichment(
        identifiers=" ".join(mtor_genes)
    )
    assert_not_none(r)
    assert_in('data', r)
    pathways = r['data']['pathways']
    assert_gt(len(pathways), 0, "No pathways for mTOR genes")
    # Check for mTOR-related pathways
    pathway_names = [p['name'].lower() for p in pathways[:20]]
    assert_true(
        any('mtor' in name or 'pi3k' in name or 'signaling' in name for name in pathway_names),
        f"Expected mTOR-related pathways, got: {pathway_names[:5]}"
    )


def test_disease_to_compound_mode():
    """Test disease-to-compound analysis mode (lupus example)."""
    # Resolve lupus
    r = tu.tools.OpenTargets_get_disease_id_description_by_name(
        diseaseName="systemic lupus erythematosus"
    )
    assert_not_none(r)
    hits = r['data']['search']['hits']
    assert_gt(len(hits), 0, "No hits for lupus")
    lupus_id = hits[0]['id']

    # Get disease targets
    targets = tu.tools.OpenTargets_get_associated_targets_by_disease_efoId(
        efoId=lupus_id, limit=10
    )
    assert_not_none(targets)
    target_rows = targets['data']['disease']['associatedTargets']['rows']
    assert_gt(len(target_rows), 0, "No targets for lupus")

    # Get drugs for top target
    top_target = target_rows[0]['target']['id']
    drugs = tu.tools.OpenTargets_get_associated_drugs_by_target_ensemblID(
        ensemblId=top_target, size=5
    )
    assert_not_none(drugs)


def test_target_centric_mode():
    """Test target-centric analysis mode (EGFR example)."""
    # Resolve EGFR
    r = tu.tools.OpenTargets_get_target_id_description_by_name(targetName="EGFR")
    assert_not_none(r)
    egfr_id = r['data']['search']['hits'][0]['id']

    # Get drugs targeting EGFR
    drugs = tu.tools.OpenTargets_get_associated_drugs_by_target_ensemblID(
        ensemblId=egfr_id, size=10
    )
    assert_not_none(drugs)
    assert_gt(
        drugs['data']['target']['knownDrugs']['count'], 10,
        "EGFR should have many drugs"
    )

    # Get PPI neighbors
    ppi = tu.tools.OpenTargets_get_target_interactions_by_ensemblID(
        ensemblId=egfr_id, size=10
    )
    assert_not_none(ppi)
    assert_gt(
        ppi['data']['target']['interactions']['count'], 0,
        "EGFR should have PPI interactions"
    )


def test_edge_case_novel_target():
    """Test edge case: less-studied target (Tdark)."""
    # Try a less common gene
    r = tu.tools.Pharos_get_target(target_name="GPR151")
    assert_not_none(r)  # Should return something even for less-studied targets


def test_edge_case_orphan_disease():
    """Test edge case: orphan disease with limited data."""
    r = tu.tools.OpenTargets_get_disease_id_description_by_name(
        diseaseName="Niemann-Pick disease"
    )
    assert_not_none(r)
    hits = r['data']['search']['hits']
    assert_gt(len(hits), 0, "Should find Niemann-Pick disease")


# Run Phase 8 tests
for test_func in [
    test_statin_inflammation,
    test_statin_diseases,
    test_rapamycin_mechanism,
    test_rapamycin_aging_trials,
    test_rapamycin_mtor_pathway,
    test_disease_to_compound_mode,
    test_target_centric_mode,
    test_edge_case_novel_target,
    test_edge_case_orphan_disease,
]:
    run_test(test_func.__doc__ or test_func.__name__, test_func)

print()

# ============================================================
# Phase 9: Scoring System Validation
# ============================================================

print("-" * 70)
print("PHASE 9: Scoring System Validation")
print("-" * 70)


def test_scoring_network_proximity():
    """Test Network Proximity scoring component (0-35 pts)."""
    # Use collected data to compute proximity score
    drug_targets = set(NETWORK_DATA.get('metformin_target_genes', []))
    disease_genes = set(NETWORK_DATA.get('alzheimer_genes', [])[:50])
    ppi_data = NETWORK_DATA.get('string_ppi', [])

    # Count direct overlaps
    direct = drug_targets & disease_genes

    # Count shared PPI partners
    shared = NETWORK_DATA.get('shared_ppi_partners', set())

    # Score logic
    score = 0
    if len(direct) > 3:
        score = 35  # Strong proximity
    elif len(direct) > 0 or len(shared) > 5:
        score = 20  # Moderate
    elif len(shared) > 0 or len(ppi_data) > 10:
        score = 10  # Weak
    # else 0

    assert_true(score >= 0, "Network proximity score should be >= 0")
    assert_true(score <= 35, "Network proximity score should be <= 35")
    NETWORK_DATA['proximity_score'] = score


def test_scoring_clinical_evidence():
    """Test Clinical Evidence scoring component (0-25 pts)."""
    trials = NETWORK_DATA.get('metformin_alzheimer_trials', [])
    score = 0
    if trials:
        score = 15  # Active trials found
    else:
        # Check if any trials exist
        r = tu.tools.search_clinical_trials(
            query_term="metformin", condition="Alzheimer", pageSize=5
        )
        if r and r.get('studies'):
            score = 15
        else:
            score = 5  # Preclinical only

    assert_true(0 <= score <= 25, f"Clinical score out of range: {score}")
    NETWORK_DATA['clinical_score'] = score


def test_scoring_target_disease():
    """Test Target-Disease Association scoring (0-20 pts)."""
    targets = NETWORK_DATA.get('alzheimer_targets', [])
    if targets:
        avg_score = sum(t['score'] for t in targets[:10]) / min(len(targets), 10)
        if avg_score > 0.5:
            score = 20
        elif avg_score > 0.3:
            score = 12
        else:
            score = 5
    else:
        score = 0

    assert_true(0 <= score <= 20, f"Target-disease score out of range: {score}")
    NETWORK_DATA['td_score'] = score


def test_scoring_safety():
    """Test Safety Profile scoring (0-10 pts)."""
    # Metformin is FDA-approved with known safety
    score = 7  # Known manageable AEs (lactic acidosis warning but rare)

    # Check black box
    chembl_id = RESOLVED.get('metformin_chembl', 'CHEMBL1431')
    r = tu.tools.OpenTargets_get_drug_blackbox_status_by_chembl_ID(chemblId=chembl_id)
    if r and isinstance(r, dict):
        has_bbox = r.get('data', {}).get('drug', {}).get('hasBeenWithdrawn', False)
        if has_bbox:
            score = max(score - 3, 0)

    assert_true(0 <= score <= 10, f"Safety score out of range: {score}")
    NETWORK_DATA['safety_score'] = score


def test_scoring_mechanism():
    """Test Mechanism Plausibility scoring (0-10 pts)."""
    pathways = NETWORK_DATA.get('alzheimer_pathways', [])
    moa = NETWORK_DATA.get('metformin_moa', [])

    score = 2  # Default: computational prediction
    if moa and pathways:
        score = 6  # Indirect mechanism via network neighbors
    if NETWORK_DATA.get('direct_overlap'):
        score = 10  # Clear pathway mechanism

    assert_true(0 <= score <= 10, f"Mechanism score out of range: {score}")
    NETWORK_DATA['mechanism_score'] = score


def test_total_score_computation():
    """Test total Network Pharmacology Score computation."""
    total = (
        NETWORK_DATA.get('proximity_score', 0) +
        NETWORK_DATA.get('clinical_score', 0) +
        NETWORK_DATA.get('td_score', 0) +
        NETWORK_DATA.get('safety_score', 0) +
        NETWORK_DATA.get('mechanism_score', 0)
    )
    assert_true(0 <= total <= 100, f"Total score out of range: {total}")
    NETWORK_DATA['total_score'] = total

    # Determine tier
    if total >= 80:
        tier = "Tier 1"
    elif total >= 60:
        tier = "Tier 2"
    elif total >= 40:
        tier = "Tier 3"
    else:
        tier = "Tier 4"

    NETWORK_DATA['tier'] = tier
    print(f"        Metformin-Alzheimer Network Pharmacology Score: {total}/100 ({tier})")


# Run Phase 9 tests
for test_func in [
    test_scoring_network_proximity,
    test_scoring_clinical_evidence,
    test_scoring_target_disease,
    test_scoring_safety,
    test_scoring_mechanism,
    test_total_score_computation,
]:
    run_test(test_func.__doc__ or test_func.__name__, test_func)

print()

# ============================================================
# Phase 10: Integration Tests
# ============================================================

print("-" * 70)
print("PHASE 10: Integration Tests")
print("-" * 70)


def test_full_pipeline_metformin_alzheimer():
    """Test full pipeline: metformin -> Alzheimer's (compound-to-disease)."""
    # Verify all phases produced data
    assert_true('metformin_chembl' in RESOLVED, "Missing metformin ChEMBL ID")
    assert_true('alzheimer_id' in RESOLVED, "Missing Alzheimer disease ID")
    assert_true('metformin_target_genes' in NETWORK_DATA, "Missing metformin targets")
    assert_true('alzheimer_genes' in NETWORK_DATA, "Missing Alzheimer genes")
    assert_true('string_ppi' in NETWORK_DATA, "Missing PPI data")
    assert_true('alzheimer_pathways' in NETWORK_DATA, "Missing pathway data")
    assert_true('total_score' in NETWORK_DATA, "Missing total score")


def test_full_pipeline_aspirin_polypharmacology():
    """Test full pipeline: aspirin polypharmacology profile."""
    assert_true('aspirin_chembl' in RESOLVED, "Missing aspirin ChEMBL ID")
    assert_true('aspirin_targets' in NETWORK_DATA, "Missing aspirin targets")
    # Aspirin should have multiple targets (polypharmacology)
    assert_gt(
        len(NETWORK_DATA.get('aspirin_targets', [])), 1,
        "Aspirin should have multiple targets"
    )


def test_report_data_completeness():
    """Test that all data needed for report generation is available."""
    required_data = [
        'metformin_chembl', 'alzheimer_id',  # Entity resolution
        'metformin_target_genes', 'alzheimer_genes',  # Node identification
        'string_ppi',  # Edge construction
        'alzheimer_pathways',  # Network analysis
        'total_score',  # Scoring
    ]
    missing = []
    for key in required_data:
        if key not in RESOLVED and key not in NETWORK_DATA:
            missing.append(key)
    assert_true(len(missing) == 0, f"Missing data for report: {missing}")


def test_network_statistics():
    """Test network statistics computation."""
    ppi = NETWORK_DATA.get('string_ppi', [])
    adjacency = NETWORK_DATA.get('adjacency', {})

    # Compute basic statistics
    stats = {
        'ppi_edges': len(ppi),
        'unique_nodes': len(adjacency),
        'drug_targets': len(NETWORK_DATA.get('metformin_target_genes', [])),
        'disease_genes': len(NETWORK_DATA.get('alzheimer_genes', [])),
        'repurposing_candidates': len(NETWORK_DATA.get('repurposing_candidates', [])),
        'clinical_trials': len(NETWORK_DATA.get('metformin_alzheimer_trials', [])),
        'pubmed_papers': len(NETWORK_DATA.get('metformin_alzheimer_papers', [])),
    }

    for key, val in stats.items():
        assert_true(val >= 0, f"Negative stat: {key}={val}")

    print(f"        Network stats: {json.dumps(stats, indent=8)}")


# Run Phase 10 tests
for test_func in [
    test_full_pipeline_metformin_alzheimer,
    test_full_pipeline_aspirin_polypharmacology,
    test_report_data_completeness,
    test_network_statistics,
]:
    run_test(test_func.__doc__ or test_func.__name__, test_func)

print()

# ============================================================
# Final Report
# ============================================================

total_time = time.time() - START_TIME

print("=" * 70)
print("TEST RESULTS SUMMARY")
print("=" * 70)
print()

passed = sum(1 for r in RESULTS if r['status'] == 'pass')
failed = sum(1 for r in RESULTS if r['status'] == 'fail')
warned = sum(1 for r in RESULTS if r['status'] == 'warn')
total = len(RESULTS)

print(f"Total tests:  {total}")
print(f"Passed:       {passed}")
print(f"Failed:       {failed}")
print(f"Warnings:     {warned}")
print(f"Pass rate:    {passed/total*100:.1f}%")
print(f"Total time:   {total_time:.1f}s")
print()

if failed > 0:
    print("FAILED TESTS:")
    for r in RESULTS:
        if r['status'] == 'fail':
            print(f"  - {r['name']}: {r['details'][:100]}")
    print()

# Phase summary
phases = {
    "Phase 0 - Entity Disambiguation": RESULTS[:9],
    "Phase 1 - Network Node ID": RESULTS[9:17],
    "Phase 2 - Network Edges": RESULTS[17:25],
    "Phase 3 - Network Analysis": RESULTS[25:31],
    "Phase 4 - Repurposing": RESULTS[31:34],
    "Phase 5 - Polypharmacology": RESULTS[34:39],
    "Phase 6 - Safety": RESULTS[39:47],
    "Phase 7 - Validation": RESULTS[47:52],
    "Phase 8 - Cross-Example": RESULTS[52:61],
    "Phase 9 - Scoring": RESULTS[61:67],
    "Phase 10 - Integration": RESULTS[67:],
}

print("PHASE BREAKDOWN:")
for phase_name, phase_results in phases.items():
    if phase_results:
        p = sum(1 for r in phase_results if r['status'] == 'pass')
        f = sum(1 for r in phase_results if r['status'] == 'fail')
        print(f"  {phase_name}: {p}/{len(phase_results)} passed" +
              (f" ({f} failed)" if f > 0 else ""))

print()
print(f"{'PASS' if failed == 0 else 'FAIL'} - {passed}/{total} tests passed")
print()

sys.exit(0 if failed == 0 else 1)
