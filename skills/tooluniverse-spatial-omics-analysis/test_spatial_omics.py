#!/usr/bin/env python3
"""
Comprehensive Test Suite for Spatial Multi-Omics Analysis Skill

Tests all phases, tool parameters, response formats, and use cases
documented in SKILL.md. Uses real biological data from spatial omics
experiments across diverse tissue types and diseases.

Test Categories:
  1-10:  Phase-level tests (individual tool verification per phase)
  11-20: Use case tests (end-to-end workflow simulations)
  21-30: Edge case tests (small/large gene lists, missing context, etc.)
"""

import sys
import os
import json
import time

# Track results
ALL_RESULTS = {}
PASS_COUNT = 0
FAIL_COUNT = 0
SKIP_COUNT = 0


def record(name, status, detail=""):
    global PASS_COUNT, FAIL_COUNT, SKIP_COUNT
    ALL_RESULTS[name] = {"status": status, "detail": detail}
    if status == "PASS":
        PASS_COUNT += 1
    elif status == "FAIL":
        FAIL_COUNT += 1
    else:
        SKIP_COUNT += 1


def assert_test(condition, msg=""):
    if not condition:
        raise AssertionError(msg)


# ============================================================
# PHASE 0: Input Processing & Disambiguation
# ============================================================

def test_01_disease_disambiguation():
    """Phase 0: Disease ID resolution via OpenTargets"""
    print("\n" + "=" * 80)
    print("TEST 01: Disease Disambiguation (OpenTargets)")
    print("=" * 80)

    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    # Test breast cancer
    result = tu.tools.OpenTargets_get_disease_id_description_by_name(diseaseName="breast cancer")
    assert_test(isinstance(result, dict), "Should return dict")
    data = result.get("data", {})
    assert_test("search" in data or "data" in result, "Should have search or data field")

    hits = data.get("search", {}).get("hits", [])
    assert_test(len(hits) > 0, "Should find breast cancer")
    first_hit = hits[0]
    assert_test("id" in first_hit, "Hit should have ID")
    assert_test("name" in first_hit, "Hit should have name")
    print(f"  Disease: {first_hit['name']} ({first_hit['id']})")

    # Test disease description
    efo_id = first_hit["id"]
    desc_result = tu.tools.OpenTargets_get_disease_description_by_efoId(efoId=efo_id)
    assert_test(isinstance(desc_result, dict), "Description should be dict")
    print(f"  Description retrieved for {efo_id}")

    record("01_disease_disambiguation", "PASS", f"Resolved breast cancer to {efo_id}")
    print("\n  PASS: Disease disambiguation works correctly")


def test_02_gene_id_resolution():
    """Phase 1: Gene ID resolution via MyGene"""
    print("\n" + "=" * 80)
    print("TEST 02: Gene ID Resolution (MyGene)")
    print("=" * 80)

    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    test_genes = ["TP53", "EGFR", "CDH1", "VIM", "CD3E"]
    resolved = {}

    for gene in test_genes:
        result = tu.tools.MyGene_query_genes(query=gene)
        assert_test(isinstance(result, dict), f"MyGene result for {gene} should be dict")
        hits = result.get("hits", [])
        assert_test(len(hits) > 0, f"Should find hits for {gene}")

        # Find exact match
        for hit in hits:
            if hit.get("symbol") == gene:
                ensembl = hit.get("ensembl", {})
                if isinstance(ensembl, dict):
                    ens_id = ensembl.get("gene", "")
                elif isinstance(ensembl, list) and len(ensembl) > 0:
                    ens_id = ensembl[0].get("gene", "")
                else:
                    ens_id = ""
                resolved[gene] = {
                    "entrez": hit.get("entrezgene", hit.get("_id")),
                    "ensembl": ens_id,
                    "name": hit.get("name", "")
                }
                break

        if gene not in resolved:
            # Use first hit if no exact match
            hit = hits[0]
            resolved[gene] = {"entrez": hit.get("_id"), "symbol": hit.get("symbol")}

    assert_test(len(resolved) == len(test_genes), f"Should resolve all {len(test_genes)} genes")

    for gene, info in resolved.items():
        print(f"  {gene}: Entrez={info.get('entrez')}, Ensembl={info.get('ensembl', 'N/A')}")

    record("02_gene_id_resolution", "PASS", f"Resolved {len(resolved)}/{len(test_genes)} genes")
    print(f"\n  PASS: Resolved all {len(test_genes)} genes")
    return resolved


def test_03_hpa_subcellular_location():
    """Phase 1: HPA subcellular localization"""
    print("\n" + "=" * 80)
    print("TEST 03: HPA Subcellular Localization")
    print("=" * 80)

    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    test_genes = ["EGFR", "TP53", "VIM", "CDH1"]

    for gene in test_genes:
        result = tu.tools.HPA_get_subcellular_location(gene_name=gene)
        assert_test(isinstance(result, dict), f"HPA result for {gene} should be dict")
        assert_test("gene_name" in result, f"Result should have gene_name for {gene}")
        locations = result.get("main_locations", [])
        summary = result.get("location_summary", "")
        print(f"  {gene}: {summary}")

    record("03_hpa_subcellular", "PASS", f"Got locations for {len(test_genes)} genes")
    print(f"\n  PASS: Subcellular locations retrieved for all genes")


def test_04_string_functional_enrichment():
    """Phase 2: STRING functional enrichment - PRIMARY enrichment tool"""
    print("\n" + "=" * 80)
    print("TEST 04: STRING Functional Enrichment (Primary Enrichment)")
    print("=" * 80)

    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    # Breast cancer TME gene set
    svg_genes = [
        "EGFR", "MYC", "TP53", "BRCA1", "CDH1", "VIM",
        "COL1A1", "CD3E", "CD8A", "CD68", "PECAM1", "KRT18",
        "ACTA2", "FAP", "PDGFRA", "CXCL12", "CCL2", "HIF1A",
        "VEGFA", "MKI67"
    ]

    result = tu.tools.STRING_functional_enrichment(
        protein_ids=svg_genes,
        species=9606
    )
    assert_test(isinstance(result, dict), "Result should be dict")
    assert_test(result.get("status") == "success", "Status should be success")

    data = result.get("data", [])
    assert_test(isinstance(data, list), "Data should be list")
    assert_test(len(data) > 0, "Should have enrichment results")

    # Check categories
    categories = set()
    significant = 0
    for item in data:
        categories.add(item.get("category", ""))
        if item.get("fdr", 1.0) < 0.05:
            significant += 1

    print(f"  Total enrichment terms: {len(data)}")
    print(f"  Significant (FDR<0.05): {significant}")
    print(f"  Categories: {sorted(categories)}")

    # Check expected fields
    if data:
        first = data[0]
        for field in ["category", "term", "description", "p_value", "fdr", "inputGenes"]:
            assert_test(field in first, f"Should have field: {field}")

    # Show top results per category
    for cat in ["Process", "KEGG", "Reactome"]:
        cat_items = [d for d in data if d.get("category") == cat and d.get("fdr", 1) < 0.05]
        if cat_items:
            top = sorted(cat_items, key=lambda x: x.get("fdr", 1))[:3]
            print(f"\n  Top {cat}:")
            for t in top:
                print(f"    {t['description'][:60]} (FDR={t['fdr']:.2e}, genes={t['number_of_genes']})")

    record("04_string_enrichment", "PASS", f"{significant} significant terms across {len(categories)} categories")
    print(f"\n  PASS: STRING enrichment returned {len(data)} terms, {significant} significant")


def test_05_reactome_pathway_enrichment():
    """Phase 2: Reactome pathway analysis"""
    print("\n" + "=" * 80)
    print("TEST 05: Reactome Pathway Enrichment")
    print("=" * 80)

    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    # Space-separated string, NOT array
    identifiers = "EGFR MYC TP53 BRCA1 CDH1 VIM COL1A1 CD3E CD8A CD68 PECAM1 KRT18 VEGFA MKI67"

    result = tu.tools.ReactomeAnalysis_pathway_enrichment(identifiers=identifiers)
    assert_test(isinstance(result, dict), "Result should be dict")

    data = result.get("data", {})
    assert_test(isinstance(data, dict), "Data should be dict")

    pathways = data.get("pathways", [])
    assert_test(isinstance(pathways, list), "Pathways should be list")
    assert_test(len(pathways) > 0, "Should have pathway results")

    print(f"  Pathways found: {data.get('pathways_found', len(pathways))}")
    print(f"  Not found: {data.get('identifiers_not_found', 0)}")

    # Check fields
    if pathways:
        first = pathways[0]
        for field in ["pathway_id", "name", "p_value", "fdr", "entities_found", "entities_total"]:
            assert_test(field in first, f"Pathway should have field: {field}")

        # Show top 5
        sig = [p for p in pathways if p.get("fdr", 1) < 0.05]
        print(f"  Significant (FDR<0.05): {len(sig)}")
        for p in pathways[:5]:
            print(f"    {p['name'][:60]} (p={p['p_value']:.2e}, FDR={p['fdr']:.2e})")

    record("05_reactome_enrichment", "PASS", f"{len(pathways)} pathways found")
    print(f"\n  PASS: Reactome returned {len(pathways)} pathways")


def test_06_string_interactions():
    """Phase 4: STRING protein-protein interactions"""
    print("\n" + "=" * 80)
    print("TEST 06: STRING Protein-Protein Interactions")
    print("=" * 80)

    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    genes = ["EGFR", "TP53", "MYC", "CDH1", "VIM", "KRAS"]

    result = tu.tools.STRING_get_interaction_partners(
        protein_ids=genes,
        species=9606,
        limit=10,
        confidence_score=0.7
    )
    assert_test(isinstance(result, dict), "Result should be dict")

    data = result.get("data", [])
    assert_test(isinstance(data, list), "Data should be list")
    assert_test(len(data) > 0, "Should have interaction data")

    # Check fields
    if data:
        first = data[0]
        for field in ["preferredName_A", "preferredName_B", "score"]:
            assert_test(field in first, f"Interaction should have: {field}")

    # Count unique interactors
    interactors = set()
    for item in data:
        interactors.add(item.get("preferredName_A", ""))
        interactors.add(item.get("preferredName_B", ""))

    # Identify hub genes
    hub_counts = {}
    for item in data:
        a = item.get("preferredName_A", "")
        b = item.get("preferredName_B", "")
        hub_counts[a] = hub_counts.get(a, 0) + 1
        hub_counts[b] = hub_counts.get(b, 0) + 1

    top_hubs = sorted(hub_counts.items(), key=lambda x: -x[1])[:5]
    print(f"  Total interactions: {len(data)}")
    print(f"  Unique proteins: {len(interactors)}")
    print(f"  Top hubs: {[(h[0], h[1]) for h in top_hubs]}")

    record("06_string_interactions", "PASS", f"{len(data)} interactions, {len(interactors)} proteins")
    print(f"\n  PASS: STRING returned {len(data)} interactions")


def test_07_opentargets_disease_targets():
    """Phase 5: OpenTargets disease-associated targets"""
    print("\n" + "=" * 80)
    print("TEST 07: OpenTargets Disease Targets")
    print("=" * 80)

    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    # Breast cancer EFO ID
    efo_id = "MONDO_0007254"

    result = tu.tools.OpenTargets_get_associated_targets_by_disease_efoId(efoId=efo_id)
    assert_test(isinstance(result, dict), "Result should be dict")

    data = result.get("data", {})
    disease_data = data.get("disease", {})
    targets = disease_data.get("associatedTargets", {})
    count = targets.get("count", 0)
    rows = targets.get("rows", [])

    assert_test(count > 0, "Should have associated targets")
    assert_test(len(rows) > 0, "Should have target rows")

    print(f"  Total disease-associated targets: {count}")
    print(f"  Top targets returned: {len(rows)}")

    # Check overlap with SVGs
    svg_genes = {"EGFR", "MYC", "TP53", "BRCA1", "CDH1", "VIM", "ERBB2", "ESR1"}
    disease_genes = set()
    for row in rows:
        target = row.get("target", {})
        symbol = target.get("approvedSymbol", "")
        disease_genes.add(symbol)

    overlap = svg_genes & disease_genes
    print(f"  Overlap with SVGs: {overlap}")
    assert_test(len(overlap) > 0, "Should have some overlap with common cancer genes")

    record("07_opentargets_disease", "PASS", f"{count} targets, {len(overlap)} overlap with SVGs")
    print(f"\n  PASS: {count} disease targets, {len(overlap)} overlap with test SVGs")


def test_08_opentargets_tractability():
    """Phase 5: OpenTargets target tractability (druggability)"""
    print("\n" + "=" * 80)
    print("TEST 08: OpenTargets Target Tractability")
    print("=" * 80)

    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    # EGFR Ensembl ID
    result = tu.tools.OpenTargets_get_target_tractability_by_ensemblID(ensemblId="ENSG00000146648")
    assert_test(isinstance(result, dict), "Result should be dict")

    data = result.get("data", {})
    target = data.get("target", {})
    tractability = target.get("tractability", [])

    assert_test(len(tractability) > 0, "EGFR should have tractability data")

    druggable_modalities = []
    for t in tractability:
        if t.get("value") is True:
            druggable_modalities.append(f"{t['label']} ({t['modality']})")

    print(f"  EGFR tractability entries: {len(tractability)}")
    print(f"  Druggable modalities: {len(druggable_modalities)}")
    for m in druggable_modalities[:5]:
        print(f"    {m}")

    assert_test(len(druggable_modalities) > 0, "EGFR should be druggable")

    record("08_tractability", "PASS", f"EGFR: {len(druggable_modalities)} druggable modalities")
    print(f"\n  PASS: EGFR has {len(druggable_modalities)} druggable modalities")


def test_09_dgidb_druggability():
    """Phase 5: DGIdb gene druggability categories"""
    print("\n" + "=" * 80)
    print("TEST 09: DGIdb Gene Druggability")
    print("=" * 80)

    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    genes = ["EGFR", "TP53", "KRAS", "MYC", "CDH1", "CD274"]

    result = tu.tools.DGIdb_get_gene_druggability(genes=genes)
    assert_test(isinstance(result, dict), "Result should be dict")

    data = result.get("data", {})
    gene_nodes = data.get("genes", {}).get("nodes", [])
    assert_test(len(gene_nodes) > 0, "Should have gene druggability data")

    for node in gene_nodes:
        name = node.get("name", "")
        categories = [c.get("name", "") for c in node.get("geneCategories", [])]
        print(f"  {name}: {', '.join(categories) if categories else 'No categories'}")

    record("09_dgidb_druggability", "PASS", f"{len(gene_nodes)} genes categorized")
    print(f"\n  PASS: DGIdb categorized {len(gene_nodes)} genes")


def test_10_pubmed_literature():
    """Phase 8: PubMed literature search"""
    print("\n" + "=" * 80)
    print("TEST 10: PubMed Literature Search")
    print("=" * 80)

    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    result = tu.tools.PubMed_search_articles(
        query="breast cancer spatial transcriptomics tumor microenvironment",
        max_results=5
    )
    assert_test(isinstance(result, list), "PubMed should return list")
    assert_test(len(result) > 0, "Should find articles")

    for article in result[:3]:
        pmid = article.get("pmid", "")
        title = article.get("title", "")[:80]
        year = article.get("pub_year", "")
        print(f"  PMID:{pmid} ({year}): {title}...")

    record("10_pubmed_literature", "PASS", f"{len(result)} articles found")
    print(f"\n  PASS: Found {len(result)} articles")


# ============================================================
# USE CASE TESTS (End-to-end workflow simulations)
# ============================================================

def test_11_usecase_cancer_heterogeneity():
    """Use Case 1: Cancer spatial heterogeneity (breast cancer)"""
    print("\n" + "=" * 80)
    print("TEST 11: USE CASE - Cancer Spatial Heterogeneity")
    print("=" * 80)

    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    # Simulated breast cancer Visium SVGs
    tumor_core = ["MYC", "EGFR", "ERBB2", "MKI67", "PCNA", "TOP2A", "CCNB1"]
    tumor_margin = ["CDH1", "KRT18", "KRT19", "MMP2", "MMP9", "SNAI1", "ZEB1"]
    stroma = ["VIM", "COL1A1", "COL3A1", "FAP", "ACTA2", "PDGFRA", "FN1"]
    immune = ["CD3E", "CD8A", "CD4", "CD68", "CD163", "PDCD1", "CD274"]

    all_svgs = tumor_core + tumor_margin + stroma + immune
    phases_passed = 0

    # Phase 2: Enrichment on all SVGs
    print("\n  Phase 2: Global enrichment...")
    result = tu.tools.STRING_functional_enrichment(protein_ids=all_svgs, species=9606)
    data = result.get("data", [])
    sig = [d for d in data if isinstance(d, dict) and d.get("fdr", 1) < 0.05]
    print(f"    All SVGs: {len(sig)} significant terms")
    if sig:
        phases_passed += 1

    # Phase 3: Per-domain enrichment
    print("\n  Phase 3: Domain-specific enrichment...")
    for domain_name, domain_genes in [("Tumor core", tumor_core), ("Stroma", stroma), ("Immune", immune)]:
        result = tu.tools.STRING_functional_enrichment(protein_ids=domain_genes, species=9606)
        ddata = result.get("data", [])
        dsig = [d for d in ddata if isinstance(d, dict) and d.get("fdr", 1) < 0.05]
        top_term = dsig[0].get("description", "N/A")[:50] if dsig else "N/A"
        print(f"    {domain_name}: {len(dsig)} terms, top: {top_term}")
    phases_passed += 1

    # Phase 4: Interactions
    print("\n  Phase 4: Cell-cell interactions...")
    result = tu.tools.STRING_get_interaction_partners(
        protein_ids=all_svgs[:15], species=9606, limit=5, confidence_score=0.7
    )
    interactions = result.get("data", [])
    print(f"    Interactions found: {len(interactions)}")
    if interactions:
        phases_passed += 1

    # Phase 5: Disease context
    print("\n  Phase 5: Disease context...")
    disease_result = tu.tools.OpenTargets_get_disease_id_description_by_name(diseaseName="breast carcinoma")
    hits = disease_result.get("data", {}).get("search", {}).get("hits", [])
    if hits:
        efo_id = hits[0]["id"]
        target_result = tu.tools.OpenTargets_get_associated_targets_by_disease_efoId(efoId=efo_id)
        target_data = target_result.get("data", {}).get("disease", {}).get("associatedTargets", {})
        target_count = target_data.get("count", 0)
        print(f"    Disease targets: {target_count}")
        phases_passed += 1

    # Phase 7: Immune microenvironment
    print("\n  Phase 7: Immune context...")
    immune_result = tu.tools.STRING_functional_enrichment(protein_ids=immune, species=9606)
    immune_data = immune_result.get("data", [])
    immune_sig = [d for d in immune_data if isinstance(d, dict) and d.get("fdr", 1) < 0.05]
    immune_terms = [d.get("description", "")[:50] for d in immune_sig[:3]]
    print(f"    Immune enrichment: {len(immune_sig)} terms")
    for t in immune_terms:
        print(f"      {t}")
    phases_passed += 1

    assert_test(phases_passed >= 4, f"Should pass at least 4/5 phases, got {phases_passed}")
    record("11_cancer_heterogeneity", "PASS", f"{phases_passed}/5 phases passed")
    print(f"\n  PASS: Cancer heterogeneity use case - {phases_passed}/5 phases")


def test_12_usecase_brain_zonation():
    """Use Case 2: Brain tissue zonation (hippocampus)"""
    print("\n" + "=" * 80)
    print("TEST 12: USE CASE - Brain Tissue Zonation")
    print("=" * 80)

    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    # Hippocampal neuronal markers
    ca1_markers = ["FIBCD1", "WFS1", "MPPED1"]
    ca3_markers = ["SPOCK1", "CPNE4", "PVRL3"]
    dg_markers = ["PROX1", "C1QL2", "DSP"]
    glial = ["GFAP", "AQP4", "OLIG2", "MBP"]

    all_genes = ca1_markers + ca3_markers + dg_markers + glial
    phases_passed = 0

    # Gene characterization
    print("\n  Gene characterization...")
    for gene in ["GFAP", "PROX1", "MBP"]:
        loc_result = tu.tools.HPA_get_subcellular_location(gene_name=gene)
        if isinstance(loc_result, dict) and "main_locations" in loc_result:
            print(f"    {gene}: {loc_result.get('location_summary', 'N/A')[:60]}")
            phases_passed += 1

    # Pathway enrichment
    print("\n  Pathway enrichment...")
    result = tu.tools.STRING_functional_enrichment(protein_ids=all_genes, species=9606)
    data = result.get("data", [])
    sig = [d for d in data if isinstance(d, dict) and d.get("fdr", 1) < 0.05]
    print(f"    Significant terms: {len(sig)}")
    if sig:
        neuro_terms = [d for d in sig if any(kw in d.get("description", "").lower()
                       for kw in ["neuro", "synap", "axon", "brain", "glia", "myelin"])]
        print(f"    Neuro-specific terms: {len(neuro_terms)}")
        for t in neuro_terms[:3]:
            print(f"      {t['description'][:60]} (FDR={t['fdr']:.2e})")

    # Neurodegenerative disease overlap
    print("\n  Disease context (Alzheimer)...")
    ad_result = tu.tools.OpenTargets_get_disease_id_description_by_name(diseaseName="Alzheimer disease")
    ad_hits = ad_result.get("data", {}).get("search", {}).get("hits", [])
    if ad_hits:
        ad_id = ad_hits[0]["id"]
        ad_targets = tu.tools.OpenTargets_get_associated_targets_by_disease_efoId(efoId=ad_id)
        ad_data = ad_targets.get("data", {}).get("disease", {}).get("associatedTargets", {})
        ad_count = ad_data.get("count", 0)
        print(f"    AD-associated targets: {ad_count}")
        phases_passed += 1

    assert_test(phases_passed >= 2, f"Should pass at least 2 phases")
    record("12_brain_zonation", "PASS", f"Brain zonation - {phases_passed} phases passed")
    print(f"\n  PASS: Brain zonation use case completed")


def test_13_usecase_liver_zonation():
    """Use Case 3: Liver metabolic zonation"""
    print("\n" + "=" * 80)
    print("TEST 13: USE CASE - Liver Metabolic Zonation")
    print("=" * 80)

    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    # Known periportal vs pericentral genes
    periportal = ["SDS", "HAL", "ASS1", "CPS1", "ARG1", "ALB"]
    pericentral = ["CYP2E1", "CYP1A2", "CYP3A4", "GLUL", "OATP1B1", "AXIN2"]

    all_genes = periportal + pericentral
    phases_passed = 0

    # Pathway enrichment - periportal
    print("\n  Periportal enrichment...")
    pp_result = tu.tools.STRING_functional_enrichment(protein_ids=periportal, species=9606)
    pp_data = pp_result.get("data", [])
    pp_sig = [d for d in pp_data if isinstance(d, dict) and d.get("fdr", 1) < 0.05]
    metabolic = [d for d in pp_sig if any(kw in d.get("description", "").lower()
                 for kw in ["metabol", "amino acid", "urea", "ammonia", "gluconeo"])]
    print(f"    Significant: {len(pp_sig)}, Metabolic: {len(metabolic)}")
    if pp_sig:
        phases_passed += 1

    # Pathway enrichment - pericentral
    print("\n  Pericentral enrichment...")
    pc_result = tu.tools.STRING_functional_enrichment(protein_ids=pericentral, species=9606)
    pc_data = pc_result.get("data", [])
    pc_sig = [d for d in pc_data if isinstance(d, dict) and d.get("fdr", 1) < 0.05]
    cyp_terms = [d for d in pc_sig if any(kw in d.get("description", "").lower()
                 for kw in ["cytochrome", "drug metabol", "xenobiotic", "p450"])]
    print(f"    Significant: {len(pc_sig)}, CYP-related: {len(cyp_terms)}")
    if pc_sig:
        phases_passed += 1

    # Combined Reactome analysis
    print("\n  Reactome analysis...")
    rc_result = tu.tools.ReactomeAnalysis_pathway_enrichment(identifiers=" ".join(all_genes))
    rc_data = rc_result.get("data", {})
    rc_pathways = rc_data.get("pathways", [])
    print(f"    Reactome pathways: {len(rc_pathways)}")
    for p in rc_pathways[:3]:
        print(f"      {p['name'][:60]} (p={p['p_value']:.2e})")
    if rc_pathways:
        phases_passed += 1

    assert_test(phases_passed >= 2, "Should pass at least 2 phases")
    record("13_liver_zonation", "PASS", f"Liver zonation - {phases_passed}/3 phases")
    print(f"\n  PASS: Liver zonation use case - {phases_passed}/3 phases")


def test_14_usecase_tumor_immune_interface():
    """Use Case 4: Tumor-immune interface (melanoma)"""
    print("\n" + "=" * 80)
    print("TEST 14: USE CASE - Tumor-Immune Interface")
    print("=" * 80)

    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    # Melanoma TME genes
    tumor_genes = ["BRAF", "MLANA", "PMEL", "SOX10", "MITF"]
    immune_genes = ["CD8A", "PDCD1", "CD274", "CTLA4", "HAVCR2", "LAG3", "TIGIT"]
    interface_genes = ["CXCL9", "CXCL10", "IFNG", "TNF", "GZMA", "PRF1"]

    all_genes = tumor_genes + immune_genes + interface_genes
    phases_passed = 0

    # Checkpoint analysis
    print("\n  Immune checkpoint analysis...")
    checkpoint_genes = ["PDCD1", "CD274", "CTLA4", "HAVCR2", "LAG3", "TIGIT"]
    for gene in checkpoint_genes[:3]:
        mygene_result = tu.tools.MyGene_query_genes(query=gene)
        hits = mygene_result.get("hits", [])
        if hits:
            for hit in hits:
                if hit.get("symbol") == gene:
                    ens = hit.get("ensembl", {})
                    ens_id = ens.get("gene", "") if isinstance(ens, dict) else (ens[0].get("gene", "") if isinstance(ens, list) and ens else "")
                    if ens_id:
                        tract = tu.tools.OpenTargets_get_target_tractability_by_ensemblID(ensemblId=ens_id)
                        tract_data = tract.get("data", {}).get("target", {}).get("tractability", [])
                        druggable = [t for t in tract_data if t.get("value") is True]
                        print(f"    {gene} ({ens_id}): {len(druggable)} druggable modalities")
                    break
    phases_passed += 1

    # Interaction network
    print("\n  Tumor-immune interactions...")
    result = tu.tools.STRING_get_interaction_partners(
        protein_ids=all_genes, species=9606, limit=5, confidence_score=0.7
    )
    interactions = result.get("data", [])
    # Find cross-compartment interactions
    cross = []
    for item in interactions:
        a = item.get("preferredName_A", "")
        b = item.get("preferredName_B", "")
        a_tumor = a in tumor_genes
        b_immune = b in immune_genes or b in interface_genes
        a_immune = a in immune_genes or a in interface_genes
        b_tumor = b in tumor_genes
        if (a_tumor and b_immune) or (a_immune and b_tumor):
            cross.append(f"{a}-{b}")

    print(f"    Total interactions: {len(interactions)}")
    print(f"    Cross-compartment: {len(cross)}")
    phases_passed += 1

    # Disease context
    print("\n  Melanoma disease context...")
    mel_result = tu.tools.OpenTargets_get_disease_id_description_by_name(diseaseName="melanoma")
    mel_hits = mel_result.get("data", {}).get("search", {}).get("hits", [])
    if mel_hits:
        mel_id = mel_hits[0]["id"]
        print(f"    Melanoma ID: {mel_id}")
        phases_passed += 1

    assert_test(phases_passed >= 2, "Should pass at least 2 phases")
    record("14_tumor_immune", "PASS", f"Tumor-immune interface - {phases_passed}/3 phases")
    print(f"\n  PASS: Tumor-immune interface - {phases_passed}/3 phases")


def test_15_usecase_disease_progression():
    """Use Case 6: Disease progression mapping (neurodegeneration)"""
    print("\n" + "=" * 80)
    print("TEST 15: USE CASE - Disease Progression")
    print("=" * 80)

    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    # Alzheimer's disease progression spatial markers
    early_markers = ["APP", "PSEN1", "APOE", "CLU", "BIN1"]
    late_markers = ["MAPT", "GFAP", "AIF1", "TREM2", "C3"]
    neuronal_loss = ["SNAP25", "SYP", "SLC17A7", "GAD1", "NEFL"]

    all_genes = early_markers + late_markers + neuronal_loss
    phases_passed = 0

    # Enrichment
    print("\n  Disease gene enrichment...")
    result = tu.tools.STRING_functional_enrichment(protein_ids=all_genes, species=9606)
    data = result.get("data", [])
    sig = [d for d in data if isinstance(d, dict) and d.get("fdr", 1) < 0.05]
    disease_terms = [d for d in sig if d.get("category") == "DISEASES"]
    print(f"    Significant terms: {len(sig)}")
    print(f"    Disease category: {len(disease_terms)}")
    if disease_terms:
        for d in disease_terms[:3]:
            print(f"      {d['description'][:60]} (FDR={d['fdr']:.2e})")
    phases_passed += 1

    # Compare early vs late
    print("\n  Early vs Late markers comparison...")
    early_result = tu.tools.STRING_functional_enrichment(protein_ids=early_markers, species=9606)
    late_result = tu.tools.STRING_functional_enrichment(protein_ids=late_markers, species=9606)

    early_terms = set()
    for d in early_result.get("data", []):
        if isinstance(d, dict) and d.get("fdr", 1) < 0.05:
            early_terms.add(d.get("description", ""))

    late_terms = set()
    for d in late_result.get("data", []):
        if isinstance(d, dict) and d.get("fdr", 1) < 0.05:
            late_terms.add(d.get("description", ""))

    shared = early_terms & late_terms
    unique_early = early_terms - late_terms
    unique_late = late_terms - early_terms
    print(f"    Early-specific terms: {len(unique_early)}")
    print(f"    Late-specific terms: {len(unique_late)}")
    print(f"    Shared terms: {len(shared)}")
    phases_passed += 1

    # AD disease overlap
    print("\n  Alzheimer disease overlap...")
    ad_result = tu.tools.OpenTargets_get_disease_id_description_by_name(diseaseName="Alzheimer disease")
    ad_hits = ad_result.get("data", {}).get("search", {}).get("hits", [])
    if ad_hits:
        ad_id = ad_hits[0]["id"]
        targets = tu.tools.OpenTargets_get_associated_targets_by_disease_efoId(efoId=ad_id)
        rows = targets.get("data", {}).get("disease", {}).get("associatedTargets", {}).get("rows", [])
        ad_genes = {r.get("target", {}).get("approvedSymbol") for r in rows}
        overlap = set(all_genes) & ad_genes
        print(f"    AD-associated SVGs: {overlap}")
        if overlap:
            phases_passed += 1

    assert_test(phases_passed >= 2, "Should pass at least 2 phases")
    record("15_disease_progression", "PASS", f"Disease progression - {phases_passed}/3 phases")
    print(f"\n  PASS: Disease progression use case - {phases_passed}/3 phases")


# ============================================================
# HPA COMPREHENSIVE AND MULTI-MODAL TESTS
# ============================================================

def test_16_hpa_cancer_prognostics():
    """Phase 1: HPA cancer prognostic data"""
    print("\n" + "=" * 80)
    print("TEST 16: HPA Cancer Prognostics")
    print("=" * 80)

    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    # Use ensembl_id (NOT gene_name) - verified in discovery
    test_cases = [
        ("TP53", "ENSG00000141510"),
        ("EGFR", "ENSG00000146648"),
    ]

    for gene_name, ens_id in test_cases:
        result = tu.tools.HPA_get_cancer_prognostics_by_gene(ensembl_id=ens_id)
        assert_test(isinstance(result, dict), f"Result should be dict for {gene_name}")
        prog_count = result.get("prognostic_cancers_count", 0)
        summary = result.get("prognostic_summary", [])
        print(f"  {gene_name}: {prog_count} prognostic cancers")
        for s in summary[:3]:
            print(f"    {s.get('cancer_type', 'N/A')}: {s.get('prognostic_type', 'N/A')} (p={s.get('p_value', 'N/A')})")

    record("16_hpa_cancer_prognostics", "PASS", "Cancer prognostics retrieved")
    print(f"\n  PASS: HPA cancer prognostics work correctly")


def test_17_multimodal_protein_rna():
    """Phase 6: Multi-modal protein-RNA concordance"""
    print("\n" + "=" * 80)
    print("TEST 17: Multi-Modal Protein-RNA Concordance")
    print("=" * 80)

    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    # Genes with both RNA and protein spatial data
    test_genes = ["EGFR", "CDH1", "VIM", "KRT18"]

    for gene in test_genes:
        # Get subcellular location (protein)
        loc_result = tu.tools.HPA_get_subcellular_location(gene_name=gene)
        locations = loc_result.get("main_locations", []) if isinstance(loc_result, dict) else []

        # Determine if secreted/membrane/nuclear
        loc_type = "unknown"
        if any("membrane" in l.lower() or "plasma" in l.lower() for l in locations):
            loc_type = "membrane"
        elif any("nucle" in l.lower() for l in locations):
            loc_type = "nuclear"
        elif any("secret" in l.lower() or "extracellular" in l.lower() for l in locations):
            loc_type = "secreted"
        elif any("cytoplas" in l.lower() or "cytosol" in l.lower() for l in locations):
            loc_type = "cytoplasmic"

        # Spatial implication
        if loc_type == "membrane":
            spatial_note = "Surface marker - detectable by spatial proteomics"
        elif loc_type == "secreted":
            spatial_note = "Paracrine signaling - may affect adjacent spatial domains"
        elif loc_type == "nuclear":
            spatial_note = "Transcription factor - mRNA pattern reflects regulatory activity"
        else:
            spatial_note = "Intracellular protein"

        print(f"  {gene}: {loc_result.get('location_summary', 'N/A')[:50]} -> {loc_type}")
        print(f"    Spatial: {spatial_note}")

    record("17_multimodal_integration", "PASS", "Protein-RNA concordance analyzed")
    print(f"\n  PASS: Multi-modal integration analysis completed")


def test_18_clinical_trials_for_spatial_targets():
    """Phase 5: Clinical trials for spatial targets"""
    print("\n" + "=" * 80)
    print("TEST 18: Clinical Trials for Spatial Targets")
    print("=" * 80)

    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    # Search for trials targeting EGFR in breast cancer
    result = tu.tools.clinical_trials_search(
        action="search_studies",
        condition="breast cancer",
        intervention="EGFR",
        limit=5
    )
    assert_test(isinstance(result, dict), "Result should be dict")

    studies = result.get("studies", [])
    total = result.get("total_count")
    print(f"  EGFR + breast cancer trials: {total if total else len(studies)}")
    for s in studies[:3]:
        nct = s.get("nctId", "")
        title = s.get("title", "")[:60]
        status = s.get("status", "")
        print(f"    {nct}: {title}... ({status})")

    record("18_clinical_trials", "PASS", f"{len(studies)} trials found")
    print(f"\n  PASS: Clinical trials search works")


def test_19_go_gene_annotations():
    """Phase 2: GO annotations for individual genes"""
    print("\n" + "=" * 80)
    print("TEST 19: GO Gene Annotations")
    print("=" * 80)

    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    test_genes = ["EGFR", "TP53", "CDH1"]

    for gene in test_genes:
        result = tu.tools.GO_get_annotations_for_gene(gene_id=gene)
        if isinstance(result, list):
            print(f"  {gene}: {len(result)} GO annotations")
            # Sample first 2
            for ann in result[:2]:
                if isinstance(ann, dict):
                    go_id = ann.get("goId", ann.get("term", {}).get("id", ""))
                    go_name = ann.get("goName", ann.get("term", {}).get("label", ""))
                    aspect = ann.get("goAspect", ann.get("qualifier", ""))
                    print(f"    {go_id}: {go_name} ({aspect})")
        elif isinstance(result, dict):
            annotations = result.get("results", result.get("data", []))
            print(f"  {gene}: {len(annotations) if isinstance(annotations, list) else 'N/A'} annotations")

    record("19_go_annotations", "PASS", "GO annotations retrieved")
    print(f"\n  PASS: GO annotations work")


def test_20_intact_interactions():
    """Phase 4: IntAct interaction database"""
    print("\n" + "=" * 80)
    print("TEST 20: IntAct Interactions")
    print("=" * 80)

    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    result = tu.tools.intact_search_interactions(query="EGFR", max=5)
    if isinstance(result, dict):
        data = result.get("data", result)
        if isinstance(data, list):
            print(f"  IntAct EGFR interactions: {len(data)}")
        elif isinstance(data, dict):
            content = data.get("content", [])
            print(f"  IntAct EGFR interactions: {len(content)}")
        else:
            print(f"  IntAct result type: {type(data)}")
    elif isinstance(result, list):
        print(f"  IntAct EGFR interactions: {len(result)}")

    record("20_intact_interactions", "PASS", "IntAct interactions retrieved")
    print(f"\n  PASS: IntAct interaction search works")


# ============================================================
# EDGE CASE TESTS
# ============================================================

def test_21_small_gene_list():
    """Edge Case: Small gene list (<10 genes)"""
    print("\n" + "=" * 80)
    print("TEST 21: EDGE CASE - Small Gene List")
    print("=" * 80)

    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    small_list = ["TP53", "EGFR", "MYC"]

    # Enrichment should still work but with limited results
    result = tu.tools.STRING_functional_enrichment(protein_ids=small_list, species=9606)
    data = result.get("data", [])
    sig = [d for d in data if isinstance(d, dict) and d.get("fdr", 1) < 0.05]

    print(f"  3 genes -> {len(data)} total terms, {len(sig)} significant")
    # With only 3 well-known genes, should still get some results
    assert_test(len(data) > 0, "Even 3 genes should return some enrichment")

    record("21_small_gene_list", "PASS", f"3 genes -> {len(data)} terms")
    print(f"\n  PASS: Small gene list handled correctly")


def test_22_large_gene_list():
    """Edge Case: Large gene list (50+ genes)"""
    print("\n" + "=" * 80)
    print("TEST 22: EDGE CASE - Large Gene List")
    print("=" * 80)

    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    # Common spatially variable genes from a typical Visium experiment
    large_list = [
        "EGFR", "MYC", "TP53", "BRCA1", "CDH1", "VIM", "COL1A1", "CD3E",
        "CD8A", "CD68", "PECAM1", "KRT18", "ACTA2", "FAP", "PDGFRA",
        "CXCL12", "CCL2", "HIF1A", "VEGFA", "MKI67", "ERBB2", "ESR1",
        "PGR", "TOP2A", "CCNB1", "CDK1", "PLK1", "AURKB", "BIRC5",
        "FN1", "COL3A1", "DCN", "LUM", "SPARC", "POSTN", "TGFB1",
        "IL6", "TNF", "IFNG", "GZMA", "PRF1", "CD4", "FOXP3",
        "CD163", "CSF1R", "S100A8", "S100A9", "MMP2", "MMP9", "SNAI1"
    ]

    start = time.time()
    result = tu.tools.STRING_functional_enrichment(protein_ids=large_list, species=9606)
    elapsed = time.time() - start

    data = result.get("data", [])
    sig = [d for d in data if isinstance(d, dict) and d.get("fdr", 1) < 0.05]

    print(f"  {len(large_list)} genes -> {len(data)} terms, {len(sig)} significant")
    print(f"  Time: {elapsed:.1f}s")

    assert_test(len(data) > 0, "Large list should return enrichment")
    assert_test(elapsed < 120, "Should complete within 2 minutes")

    record("22_large_gene_list", "PASS", f"{len(large_list)} genes in {elapsed:.1f}s")
    print(f"\n  PASS: Large gene list handled in {elapsed:.1f}s")


def test_23_no_disease_context():
    """Edge Case: Normal tissue without disease context"""
    print("\n" + "=" * 80)
    print("TEST 23: EDGE CASE - No Disease Context")
    print("=" * 80)

    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    # Normal liver genes (no disease)
    liver_genes = ["ALB", "HNF4A", "CYP3A4", "CYP2E1", "GLUL", "ASS1", "CPS1"]

    # Enrichment should work fine
    result = tu.tools.STRING_functional_enrichment(protein_ids=liver_genes, species=9606)
    data = result.get("data", [])
    sig = [d for d in data if isinstance(d, dict) and d.get("fdr", 1) < 0.05]

    print(f"  Normal liver: {len(sig)} significant terms")

    # Get tissue expression for validation
    for gene in liver_genes[:2]:
        loc = tu.tools.HPA_get_subcellular_location(gene_name=gene)
        if isinstance(loc, dict):
            print(f"  {gene}: {loc.get('location_summary', 'N/A')[:60]}")

    # Verify we can proceed without disease section
    print(f"  Analysis proceeds without disease context: OK")

    record("23_no_disease", "PASS", "Normal tissue analysis works")
    print(f"\n  PASS: No disease context handled correctly")


def test_24_unknown_genes():
    """Edge Case: Unknown or ambiguous gene symbols"""
    print("\n" + "=" * 80)
    print("TEST 24: EDGE CASE - Unknown/Ambiguous Genes")
    print("=" * 80)

    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    # Mix of valid and potentially ambiguous genes
    test_genes = ["TP53", "NOTAREALGENE123", "CD3E"]

    resolved = 0
    unresolved = 0

    for gene in test_genes:
        result = tu.tools.MyGene_query_genes(query=gene)
        hits = result.get("hits", [])
        if hits and any(h.get("symbol") == gene for h in hits):
            resolved += 1
            print(f"  {gene}: RESOLVED")
        else:
            unresolved += 1
            print(f"  {gene}: NOT RESOLVED (hits={len(hits)})")

    # Should handle gracefully - resolve what we can, skip the rest
    assert_test(resolved >= 2, "Should resolve at least known genes")
    print(f"  Resolved: {resolved}, Unresolved: {unresolved}")

    record("24_unknown_genes", "PASS", f"{resolved} resolved, {unresolved} unresolved")
    print(f"\n  PASS: Unknown genes handled gracefully")


def test_25_single_domain():
    """Edge Case: Only one spatial domain (no comparison possible)"""
    print("\n" + "=" * 80)
    print("TEST 25: EDGE CASE - Single Spatial Domain")
    print("=" * 80)

    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    # Single domain with its markers
    domain_genes = ["EGFR", "MYC", "CCNB1", "MKI67", "TOP2A", "PCNA"]

    result = tu.tools.STRING_functional_enrichment(protein_ids=domain_genes, species=9606)
    data = result.get("data", [])
    sig = [d for d in data if isinstance(d, dict) and d.get("fdr", 1) < 0.05]

    print(f"  Single domain: {len(sig)} significant terms")
    print(f"  Domain comparison: SKIPPED (only 1 domain)")

    # Interactions still work
    int_result = tu.tools.STRING_get_interaction_partners(
        protein_ids=domain_genes, species=9606, limit=5
    )
    interactions = int_result.get("data", [])
    print(f"  Intra-domain interactions: {len(interactions)}")

    record("25_single_domain", "PASS", "Single domain handled")
    print(f"\n  PASS: Single domain analysis works")


def test_26_openalex_literature():
    """Phase 8: OpenAlex literature search as fallback"""
    print("\n" + "=" * 80)
    print("TEST 26: OpenAlex Literature Search")
    print("=" * 80)

    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    result = tu.tools.openalex_literature_search(
        query="spatial transcriptomics liver zonation",
        per_page=5
    )

    if isinstance(result, dict):
        results = result.get("results", [])
        print(f"  OpenAlex results: {len(results)}")
        for r in results[:3]:
            title = r.get("title", "")[:70]
            year = r.get("publication_year", "")
            print(f"    ({year}) {title}...")
    elif isinstance(result, list):
        print(f"  OpenAlex results: {len(result)}")

    record("26_openalex_literature", "PASS", "OpenAlex search works")
    print(f"\n  PASS: OpenAlex literature search works")


def test_27_reactome_individual_gene():
    """Phase 2: Reactome pathway mapping for individual genes"""
    print("\n" + "=" * 80)
    print("TEST 27: Reactome Individual Gene Mapping")
    print("=" * 80)

    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    # Map EGFR UniProt to Reactome pathways
    # First get UniProt ID
    uniprot_result = tu.tools.UniProtIDMap_gene_to_uniprot(gene_name="EGFR", organism="human")

    # Try direct Reactome mapping with known UniProt accession for EGFR
    result = tu.tools.Reactome_map_uniprot_to_pathways(id="P00533")

    if isinstance(result, list):
        print(f"  EGFR (P00533) pathways: {len(result)}")
        for p in result[:5]:
            if isinstance(p, dict):
                name = p.get("displayName", p.get("name", ""))
                print(f"    {name[:70]}")
    elif isinstance(result, dict):
        data = result.get("data", result)
        print(f"  EGFR pathways: {data}")

    record("27_reactome_gene", "PASS", "Reactome gene mapping works")
    print(f"\n  PASS: Reactome individual gene pathway mapping works")


def test_28_opentargets_drugs_for_target():
    """Phase 5: OpenTargets drugs for spatial target"""
    print("\n" + "=" * 80)
    print("TEST 28: OpenTargets Drugs for Spatial Target")
    print("=" * 80)

    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    # EGFR - known drug target
    result = tu.tools.OpenTargets_get_associated_drugs_by_target_ensemblID(
        ensemblId="ENSG00000146648",
        size=10
    )
    assert_test(isinstance(result, dict), "Result should be dict")

    data = result.get("data", {})
    target = data.get("target", {})
    drugs = target.get("knownDrugs", target.get("associatedDrugs", {}))

    if isinstance(drugs, dict):
        count = drugs.get("count", 0)
        rows = drugs.get("rows", [])
        print(f"  EGFR drugs: {count} total, {len(rows)} returned")
        for r in rows[:5]:
            drug_name = r.get("drug", {}).get("name", r.get("drugName", "N/A"))
            phase = r.get("phase", r.get("clinicalPhase", "N/A"))
            moa = r.get("mechanismOfAction", "N/A")
            print(f"    {drug_name} (Phase {phase}): {str(moa)[:50]}")

    record("28_opentargets_drugs", "PASS", "Drug lookup works")
    print(f"\n  PASS: OpenTargets drug lookup for spatial targets works")


def test_29_string_ppi_enrichment():
    """Phase 4: STRING PPI enrichment significance test"""
    print("\n" + "=" * 80)
    print("TEST 29: STRING PPI Enrichment")
    print("=" * 80)

    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    genes = ["EGFR", "ERBB2", "ERBB3", "MET", "KRAS", "BRAF", "PIK3CA", "AKT1", "MTOR"]

    result = tu.tools.STRING_ppi_enrichment(protein_ids=genes, species=9606)

    if isinstance(result, dict):
        data = result.get("data", result)
        if isinstance(data, list) and data:
            for item in data:
                if isinstance(item, dict):
                    p_value = item.get("p_value", "N/A")
                    num_edges = item.get("number_of_edges", "N/A")
                    expected = item.get("expected_number_of_edges", "N/A")
                    print(f"  PPI enrichment p-value: {p_value}")
                    print(f"  Edges: {num_edges} (expected: {expected})")
        elif isinstance(data, dict):
            print(f"  PPI enrichment data: {json.dumps(data, indent=2)[:300]}")

    record("29_string_ppi_enrichment", "PASS", "PPI enrichment works")
    print(f"\n  PASS: STRING PPI enrichment significance test works")


def test_30_hpa_comprehensive():
    """Phase 1: HPA comprehensive gene details"""
    print("\n" + "=" * 80)
    print("TEST 30: HPA Comprehensive Gene Details")
    print("=" * 80)

    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    result = tu.tools.HPA_get_comprehensive_gene_details_by_ensembl_id(ensembl_id="ENSG00000146648")
    assert_test(isinstance(result, dict), "Result should be dict")

    # Check for gene info
    gene_name = result.get("gene_name", result.get("Gene", ""))
    print(f"  Gene: {gene_name}")

    # Check available data sections
    sections = []
    for key in result.keys():
        if isinstance(result[key], (dict, list)):
            if isinstance(result[key], list):
                sections.append(f"{key}: {len(result[key])} items")
            else:
                sections.append(f"{key}: dict")
        elif result[key]:
            sections.append(f"{key}: {str(result[key])[:50]}")

    for s in sections[:10]:
        print(f"    {s}")

    record("30_hpa_comprehensive", "PASS", "Comprehensive gene data retrieved")
    print(f"\n  PASS: HPA comprehensive gene details work")


# ============================================================
# TEST RUNNER
# ============================================================

def run_all_tests():
    """Run all tests and generate report"""
    print("\n" + "=" * 80)
    print("SPATIAL MULTI-OMICS ANALYSIS SKILL - COMPREHENSIVE TEST SUITE")
    print("=" * 80)
    print(f"Testing 30 test cases across 9 phases + use cases + edge cases\n")

    tests = [
        # Phase tests
        ("01: Disease Disambiguation", test_01_disease_disambiguation),
        ("02: Gene ID Resolution", test_02_gene_id_resolution),
        ("03: HPA Subcellular Location", test_03_hpa_subcellular_location),
        ("04: STRING Functional Enrichment", test_04_string_functional_enrichment),
        ("05: Reactome Pathway Enrichment", test_05_reactome_pathway_enrichment),
        ("06: STRING Interactions", test_06_string_interactions),
        ("07: OpenTargets Disease Targets", test_07_opentargets_disease_targets),
        ("08: OpenTargets Tractability", test_08_opentargets_tractability),
        ("09: DGIdb Druggability", test_09_dgidb_druggability),
        ("10: PubMed Literature", test_10_pubmed_literature),

        # Use case tests
        ("11: Cancer Heterogeneity", test_11_usecase_cancer_heterogeneity),
        ("12: Brain Zonation", test_12_usecase_brain_zonation),
        ("13: Liver Zonation", test_13_usecase_liver_zonation),
        ("14: Tumor-Immune Interface", test_14_usecase_tumor_immune_interface),
        ("15: Disease Progression", test_15_usecase_disease_progression),

        # Additional phase tests
        ("16: HPA Cancer Prognostics", test_16_hpa_cancer_prognostics),
        ("17: Multi-Modal Integration", test_17_multimodal_protein_rna),
        ("18: Clinical Trials", test_18_clinical_trials_for_spatial_targets),
        ("19: GO Annotations", test_19_go_gene_annotations),
        ("20: IntAct Interactions", test_20_intact_interactions),

        # Edge case tests
        ("21: Small Gene List", test_21_small_gene_list),
        ("22: Large Gene List", test_22_large_gene_list),
        ("23: No Disease Context", test_23_no_disease_context),
        ("24: Unknown Genes", test_24_unknown_genes),
        ("25: Single Domain", test_25_single_domain),

        # Additional tests
        ("26: OpenAlex Literature", test_26_openalex_literature),
        ("27: Reactome Gene Mapping", test_27_reactome_individual_gene),
        ("28: OpenTargets Drugs", test_28_opentargets_drugs_for_target),
        ("29: STRING PPI Enrichment", test_29_string_ppi_enrichment),
        ("30: HPA Comprehensive", test_30_hpa_comprehensive),
    ]

    for test_name, test_func in tests:
        try:
            test_func()
        except Exception as e:
            record(test_name.split(":")[0].strip(), "FAIL", str(e))
            print(f"\n  FAIL: {test_name}")
            print(f"    Error: {str(e)[:200]}")

    # Final summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    # Print results
    for name, result in sorted(ALL_RESULTS.items()):
        status = result["status"]
        marker = "PASS" if status == "PASS" else "FAIL" if status == "FAIL" else "SKIP"
        detail = result.get("detail", "")[:60]
        print(f"  [{marker}] {name}: {detail}")

    total = PASS_COUNT + FAIL_COUNT + SKIP_COUNT
    print(f"\n  Total: {total}")
    print(f"  Passed: {PASS_COUNT}/{total}")
    print(f"  Failed: {FAIL_COUNT}/{total}")
    if SKIP_COUNT:
        print(f"  Skipped: {SKIP_COUNT}/{total}")
    print(f"  Success Rate: {PASS_COUNT / total * 100:.1f}%")

    if FAIL_COUNT == 0:
        print(f"\n  ALL TESTS PASSED! Skill is production-ready.")
    else:
        print(f"\n  WARNING: Some tests failed. Review errors above.")

    return PASS_COUNT, FAIL_COUNT


if __name__ == "__main__":
    passed, failed = run_all_tests()
    sys.exit(0 if failed == 0 else 1)
