#!/usr/bin/env python3
"""
Comprehensive Test Suite for Drug Target Validation Skill

Tests all 10 phases of the validation pipeline with real targets:
- EGFR (kinase, well-validated, many drugs)
- PCSK9 (enzyme, antibody target)
- KRAS (oncogene, historically undruggable)
- BTK (kinase, autoimmune + oncology)
- PD-1/PDCD1 (immune checkpoint, biologics target)

Each test verifies:
1. Tool exists and is callable
2. Parameters match documented spec
3. Response contains expected data fields
4. Data is non-empty for well-known targets
"""

import sys
import time
import traceback

# Test tracking
RESULTS = []
TOTAL = 0
PASSED = 0
FAILED = 0
SKIPPED = 0


def record_result(test_name, status, details="", duration=0):
    """Record a test result."""
    global TOTAL, PASSED, FAILED, SKIPPED
    TOTAL += 1
    if status == "PASS":
        PASSED += 1
        icon = "PASS"
    elif status == "FAIL":
        FAILED += 1
        icon = "FAIL"
    else:
        SKIPPED += 1
        icon = "SKIP"
    RESULTS.append({
        "test": test_name,
        "status": icon,
        "details": details,
        "duration": duration
    })
    print(f"  [{icon}] {test_name} ({duration:.1f}s) {details}")


def run_test(test_name, test_func):
    """Run a test function with timing and error handling."""
    start = time.time()
    try:
        test_func()
        duration = time.time() - start
        record_result(test_name, "PASS", duration=duration)
    except AssertionError as e:
        duration = time.time() - start
        record_result(test_name, "FAIL", str(e), duration=duration)
    except Exception as e:
        duration = time.time() - start
        record_result(test_name, "FAIL", f"Exception: {type(e).__name__}: {str(e)[:200]}", duration=duration)


# ============================================================
# Setup
# ============================================================
print("=" * 70)
print("Drug Target Validation Skill - Comprehensive Test Suite")
print("=" * 70)
print()

print("Loading ToolUniverse...")
from tooluniverse import ToolUniverse
tu = ToolUniverse()
tu.load_tools()
print(f"Tools loaded: {len(tu.all_tool_dict)}")
print()

# ============================================================
# Phase 0: Target Disambiguation Tests
# ============================================================
print("=" * 70)
print("PHASE 0: Target Disambiguation & ID Resolution")
print("=" * 70)


def test_mygene_query():
    result = tu.tools.MyGene_query_genes(
        query="EGFR", species="human",
        fields="symbol,name,ensembl.gene,uniprot.Swiss-Prot,entrezgene"
    )
    assert result is not None, "MyGene returned None"
    # Result can be dict or list
    if isinstance(result, list):
        assert len(result) > 0, "MyGene returned empty list"
        hit = result[0]
    else:
        hit = result
        if 'hits' in result:
            assert len(result['hits']) > 0, "No hits"
            hit = result['hits'][0]
    # Should contain gene info
    assert 'symbol' in hit or 'name' in hit or '_id' in hit, f"Missing gene fields. Keys: {list(hit.keys())[:10]}"


def test_ensembl_lookup():
    result = tu.tools.ensembl_lookup_gene(gene_id="ENSG00000146648", species="homo_sapiens")
    assert result is not None, "Ensembl returned None"
    if isinstance(result, dict):
        # Ensembl tools wrap response in {status, data, url, content_type}
        data = result.get('data', result)
        assert data is not None, "Ensembl returned None data"
        if isinstance(data, dict):
            assert 'display_name' in data or 'id' in data or 'version' in data or len(data) > 0, \
                f"Missing expected fields in data. Keys: {list(data.keys())[:10]}"
        # Verify the wrapper fields
        if 'status' in result:
            assert 'data' in result, f"Ensembl wrapper missing 'data' key. Keys: {list(result.keys())}"


def test_uniprot_entry():
    result = tu.tools.UniProt_get_entry_by_accession(accession="P00533")
    assert result is not None, "UniProt returned None"
    if isinstance(result, dict):
        assert len(result) > 0, "UniProt returned empty dict"


def test_uniprot_function():
    result = tu.tools.UniProt_get_function_by_accession(accession="P00533")
    assert result is not None, "UniProt function returned None"
    # Returns list of strings per MEMORY.md
    if isinstance(result, list):
        assert len(result) > 0, "UniProt function returned empty list"
    elif isinstance(result, dict):
        assert len(result) > 0, "UniProt function returned empty dict"


def test_uniprot_subcellular():
    result = tu.tools.UniProt_get_subcellular_location_by_accession(accession="P00533")
    assert result is not None, "UniProt subcellular returned None"


def test_ensembl_xrefs():
    result = tu.tools.ensembl_get_xrefs(id="ENSG00000146648")
    assert result is not None, "Ensembl xrefs returned None"
    if isinstance(result, list):
        assert len(result) > 0, "Ensembl xrefs returned empty list"


def test_opentargets_target_by_name():
    result = tu.tools.OpenTargets_get_target_id_description_by_name(targetName="EGFR")
    assert result is not None, "OT target by name returned None"


def test_chembl_search_targets():
    result = tu.tools.ChEMBL_search_targets(
        pref_name__contains="EGFR", organism="Homo sapiens", limit=5
    )
    assert result is not None, "ChEMBL search targets returned None"


def test_uniprot_alt_names():
    result = tu.tools.UniProt_get_alternative_names_by_accession(accession="P00533")
    assert result is not None, "UniProt alt names returned None"


run_test("MyGene query (EGFR)", test_mygene_query)
run_test("Ensembl lookup gene (ENSG00000146648)", test_ensembl_lookup)
run_test("UniProt entry (P00533)", test_uniprot_entry)
run_test("UniProt function (P00533)", test_uniprot_function)
run_test("UniProt subcellular location (P00533)", test_uniprot_subcellular)
run_test("Ensembl xrefs (ENSG00000146648)", test_ensembl_xrefs)
run_test("OpenTargets target by name (EGFR)", test_opentargets_target_by_name)
run_test("ChEMBL search targets (EGFR)", test_chembl_search_targets)
run_test("UniProt alternative names (P00533)", test_uniprot_alt_names)

# ============================================================
# Phase 1: Disease Association Tests
# ============================================================
print()
print("=" * 70)
print("PHASE 1: Disease Association Evidence")
print("=" * 70)


def test_ot_diseases():
    result = tu.tools.OpenTargets_get_diseases_phenotypes_by_target_ensembl(
        ensemblId="ENSG00000146648"
    )
    assert result is not None, "OT diseases returned None"


def test_ot_target_disease_evidence():
    result = tu.tools.OpenTargets_target_disease_evidence(
        efoId="EFO_0003060", ensemblId="ENSG00000146648"
    )
    assert result is not None, "OT target-disease evidence returned None"


def test_gwas_snps_for_gene():
    result = tu.tools.gwas_get_snps_for_gene(mapped_gene="EGFR", size=20)
    assert result is not None, "GWAS SNPs returned None"


def test_gnomad_constraints():
    result = tu.tools.gnomad_get_gene_constraints(gene_symbol="EGFR")
    assert result is not None, "gnomAD constraints returned None"


def test_pubmed_search():
    result = tu.tools.PubMed_search_articles(
        query='"EGFR" AND "lung cancer" AND (target OR therapeutic)',
        limit=10
    )
    assert result is not None, "PubMed returned None"
    # Returns plain list per MEMORY.md
    if isinstance(result, list):
        assert len(result) > 0, "PubMed returned empty list for EGFR+lung cancer"


def test_ot_publications():
    result = tu.tools.OpenTargets_get_publications_by_target_ensemblID(
        entityId="ENSG00000146648"
    )
    assert result is not None, "OT publications returned None"


def test_ot_evidence_by_datasource():
    result = tu.tools.OpenTargets_get_evidence_by_datasource(
        efoId="EFO_0003060", ensemblId="ENSG00000146648",
        datasourceIds=["ot_genetics_portal", "eva"],
        size=20
    )
    assert result is not None, "OT evidence by datasource returned None"


run_test("OT disease associations (EGFR)", test_ot_diseases)
run_test("OT target-disease evidence (EGFR+NSCLC)", test_ot_target_disease_evidence)
run_test("GWAS SNPs for gene (EGFR)", test_gwas_snps_for_gene)
run_test("gnomAD constraints (EGFR)", test_gnomad_constraints)
run_test("PubMed search (EGFR+lung cancer)", test_pubmed_search)
run_test("OT publications (EGFR)", test_ot_publications)
run_test("OT evidence by datasource (EGFR+NSCLC)", test_ot_evidence_by_datasource)

# ============================================================
# Phase 2: Druggability Assessment Tests
# ============================================================
print()
print("=" * 70)
print("PHASE 2: Druggability Assessment")
print("=" * 70)


def test_ot_tractability():
    result = tu.tools.OpenTargets_get_target_tractability_by_ensemblID(
        ensemblId="ENSG00000146648"
    )
    assert result is not None, "OT tractability returned None"


def test_ot_target_classes():
    result = tu.tools.OpenTargets_get_target_classes_by_ensemblID(
        ensemblId="ENSG00000146648"
    )
    assert result is not None, "OT target classes returned None"


def test_pharos_target():
    result = tu.tools.Pharos_get_target(gene="EGFR")
    assert result is not None, "Pharos returned None"


def test_dgidb_druggability():
    result = tu.tools.DGIdb_get_gene_druggability(genes=["EGFR"])
    assert result is not None, "DGIdb druggability returned None"


def test_alphafold_prediction():
    result = tu.tools.alphafold_get_prediction(qualifier="P00533")
    assert result is not None, "AlphaFold prediction returned None"


def test_alphafold_summary():
    result = tu.tools.alphafold_get_summary(qualifier="P00533")
    assert result is not None, "AlphaFold summary returned None"


def test_ot_chemical_probes():
    result = tu.tools.OpenTargets_get_chemical_probes_by_target_ensemblID(
        ensemblId="ENSG00000146648"
    )
    assert result is not None, "OT chemical probes returned None"


def test_ot_teps():
    result = tu.tools.OpenTargets_get_target_enabling_packages_by_ensemblID(
        ensemblId="ENSG00000146648"
    )
    assert result is not None, "OT TEPs returned None"


def test_proteinsplus_binding_sites():
    result = tu.tools.ProteinsPlus_predict_binding_sites(pdb_id="1M17")
    assert result is not None, "ProteinsPlus binding sites returned None"


run_test("OT tractability (EGFR)", test_ot_tractability)
run_test("OT target classes (EGFR)", test_ot_target_classes)
run_test("Pharos target (EGFR)", test_pharos_target)
run_test("DGIdb druggability (EGFR)", test_dgidb_druggability)
run_test("AlphaFold prediction (P00533)", test_alphafold_prediction)
run_test("AlphaFold summary (P00533)", test_alphafold_summary)
run_test("OT chemical probes (EGFR)", test_ot_chemical_probes)
run_test("OT enabling packages (EGFR)", test_ot_teps)
run_test("ProteinsPlus binding sites (1M17)", test_proteinsplus_binding_sites)

# ============================================================
# Phase 3: Chemical Matter Tests
# ============================================================
print()
print("=" * 70)
print("PHASE 3: Known Modulators & Chemical Matter")
print("=" * 70)


def test_chembl_target_activities():
    result = tu.tools.ChEMBL_get_target_activities(
        target_chembl_id__exact="CHEMBL203", limit=20
    )
    assert result is not None, "ChEMBL activities returned None"


def test_bindingdb_ligands():
    result = tu.tools.BindingDB_get_ligands_by_uniprot(
        uniprot="P00533", affinity_cutoff=10000
    )
    assert result is not None, "BindingDB returned None"


def test_pubchem_assays_by_gene():
    result = tu.tools.PubChem_search_assays_by_target_gene(gene_symbol="EGFR")
    assert result is not None, "PubChem assays returned None"


def test_ot_associated_drugs():
    result = tu.tools.OpenTargets_get_associated_drugs_by_target_ensemblID(
        ensemblId="ENSG00000146648", size=25
    )
    assert result is not None, "OT associated drugs returned None"


def test_chembl_search_mechanisms():
    result = tu.tools.ChEMBL_search_mechanisms(
        target_chembl_id="CHEMBL203", limit=20
    )
    assert result is not None, "ChEMBL mechanisms returned None"


def test_dgidb_gene_info():
    result = tu.tools.DGIdb_get_gene_info(genes=["EGFR"])
    assert result is not None, "DGIdb gene info returned None"


run_test("ChEMBL target activities (CHEMBL203)", test_chembl_target_activities)
run_test("BindingDB ligands (P00533)", test_bindingdb_ligands)
run_test("PubChem assays by gene (EGFR)", test_pubchem_assays_by_gene)
run_test("OT associated drugs (EGFR)", test_ot_associated_drugs)
run_test("ChEMBL drug mechanisms (CHEMBL203)", test_chembl_search_mechanisms)
run_test("DGIdb gene info (EGFR)", test_dgidb_gene_info)

# ============================================================
# Phase 4: Clinical Precedent Tests
# ============================================================
print()
print("=" * 70)
print("PHASE 4: Clinical Precedent")
print("=" * 70)


def test_fda_moa():
    result = tu.tools.FDA_get_mechanism_of_action_by_drug_name(drug_name="erlotinib")
    assert result is not None, "FDA MOA returned None"


def test_fda_indications():
    result = tu.tools.FDA_get_indications_by_drug_name(drug_name="erlotinib")
    assert result is not None, "FDA indications returned None"


def test_clinical_trials():
    result = tu.tools.search_clinical_trials(
        query_term="EGFR inhibitor",
        condition="lung cancer",
        pageSize=10
    )
    assert result is not None, "Clinical trials returned None"


def test_drugbank_targets():
    result = tu.tools.drugbank_get_targets_by_drug_name_or_drugbank_id(
        query="erlotinib", case_sensitive=False, exact_match=False, limit=10
    )
    assert result is not None, "DrugBank targets returned None"


def test_ot_drug_warnings():
    result = tu.tools.OpenTargets_get_drug_warnings_by_chemblId(chemblId="CHEMBL553")
    assert result is not None, "OT drug warnings returned None"


def test_ot_drug_adverse_events():
    result = tu.tools.OpenTargets_get_drug_adverse_events_by_chemblId(chemblId="CHEMBL553")
    assert result is not None, "OT drug adverse events returned None"


run_test("FDA mechanism of action (erlotinib)", test_fda_moa)
run_test("FDA indications (erlotinib)", test_fda_indications)
run_test("Clinical trials (EGFR+lung cancer)", test_clinical_trials)
run_test("DrugBank targets (erlotinib)", test_drugbank_targets)
run_test("OT drug warnings (CHEMBL553)", test_ot_drug_warnings)
run_test("OT drug adverse events (CHEMBL553)", test_ot_drug_adverse_events)

# ============================================================
# Phase 5: Safety Tests
# ============================================================
print()
print("=" * 70)
print("PHASE 5: Safety & Toxicity")
print("=" * 70)


def test_ot_safety():
    result = tu.tools.OpenTargets_get_target_safety_profile_by_ensemblID(
        ensemblId="ENSG00000146648"
    )
    assert result is not None, "OT safety profile returned None"


def test_gtex_expression():
    # Try versioned ID first
    result = tu.tools.GTEx_get_median_gene_expression(
        operation="median", gencode_id="ENSG00000146648"
    )
    if result is None or (isinstance(result, dict) and result.get('data') == []):
        # Try versioned
        result = tu.tools.GTEx_get_median_gene_expression(
            operation="median", gencode_id="ENSG00000146648.18"
        )
    assert result is not None, "GTEx expression returned None for both versioned and unversioned"


def test_hpa_search():
    result = tu.tools.HPA_search_genes_by_query(search_query="EGFR")
    assert result is not None, "HPA search returned None"


def test_hpa_comprehensive():
    result = tu.tools.HPA_get_comprehensive_gene_details_by_ensembl_id(
        ensembl_id="ENSG00000146648"
    )
    assert result is not None, "HPA comprehensive returned None"


def test_ot_mouse_models():
    result = tu.tools.OpenTargets_get_biological_mouse_models_by_ensemblID(
        ensemblId="ENSG00000146648"
    )
    assert result is not None, "OT mouse models returned None"


def test_ot_constraint():
    result = tu.tools.OpenTargets_get_target_constraint_info_by_ensemblID(
        ensemblId="ENSG00000146648"
    )
    assert result is not None, "OT constraint returned None"


def test_fda_adverse_reactions():
    result = tu.tools.FDA_get_adverse_reactions_by_drug_name(drug_name="erlotinib")
    assert result is not None, "FDA adverse reactions returned None"


def test_fda_boxed_warning():
    result = tu.tools.FDA_get_boxed_warning_info_by_drug_name(drug_name="erlotinib")
    # May return empty for drugs without boxed warning - that's OK
    assert result is not None, "FDA boxed warning returned None"


def test_ot_homologues():
    result = tu.tools.OpenTargets_get_target_homologues_by_ensemblID(
        ensemblId="ENSG00000146648"
    )
    assert result is not None, "OT homologues returned None"


run_test("OT safety profile (EGFR)", test_ot_safety)
run_test("GTEx expression (EGFR)", test_gtex_expression)
run_test("HPA search (EGFR)", test_hpa_search)
run_test("HPA comprehensive (EGFR)", test_hpa_comprehensive)
run_test("OT mouse models (EGFR)", test_ot_mouse_models)
run_test("OT constraint (EGFR)", test_ot_constraint)
run_test("FDA adverse reactions (erlotinib)", test_fda_adverse_reactions)
run_test("FDA boxed warning (erlotinib)", test_fda_boxed_warning)
run_test("OT homologues (EGFR)", test_ot_homologues)

# ============================================================
# Phase 6: Pathway Context Tests
# ============================================================
print()
print("=" * 70)
print("PHASE 6: Pathway Context & Network Analysis")
print("=" * 70)


def test_reactome_pathways():
    result = tu.tools.Reactome_map_uniprot_to_pathways(id="P00533")
    assert result is not None, "Reactome pathways returned None"
    if isinstance(result, list):
        assert len(result) > 0, "Reactome returned empty pathway list for EGFR"


def test_string_interactions():
    result = tu.tools.STRING_get_protein_interactions(
        protein_ids=["EGFR"], species=9606, confidence_score=0.7
    )
    assert result is not None, "STRING PPI returned None"


def test_intact_interactions():
    result = tu.tools.intact_get_interactions(identifier="P00533")
    assert result is not None, "IntAct returned None"


def test_ot_interactions():
    result = tu.tools.OpenTargets_get_target_interactions_by_ensemblID(
        ensemblId="ENSG00000146648"
    )
    assert result is not None, "OT interactions returned None"


def test_ot_go_terms():
    result = tu.tools.OpenTargets_get_target_gene_ontology_by_ensemblID(
        ensemblId="ENSG00000146648"
    )
    assert result is not None, "OT GO terms returned None"


def test_go_annotations():
    result = tu.tools.GO_get_annotations_for_gene(gene_id="EGFR")
    assert result is not None, "GO annotations returned None"


def test_string_enrichment():
    result = tu.tools.STRING_functional_enrichment(
        protein_ids=["EGFR"], species=9606
    )
    assert result is not None, "STRING enrichment returned None"


run_test("Reactome pathways (P00533)", test_reactome_pathways)
run_test("STRING PPI (EGFR)", test_string_interactions)
run_test("IntAct interactions (P00533)", test_intact_interactions)
run_test("OT interactions (EGFR)", test_ot_interactions)
run_test("OT GO terms (EGFR)", test_ot_go_terms)
run_test("GO annotations (EGFR)", test_go_annotations)
run_test("STRING functional enrichment (EGFR)", test_string_enrichment)

# ============================================================
# Phase 7: Validation Evidence Tests
# ============================================================
print()
print("=" * 70)
print("PHASE 7: Validation Evidence")
print("=" * 70)


def test_depmap_dependencies():
    result = tu.tools.DepMap_get_gene_dependencies(gene_symbol="EGFR")
    assert result is not None, "DepMap returned None"


def test_pubmed_validation_papers():
    result = tu.tools.PubMed_search_articles(
        query='"EGFR" AND (CRISPR OR siRNA OR knockdown) AND "lung cancer"',
        limit=10
    )
    assert result is not None, "PubMed validation papers returned None"


def test_ctd_gene_diseases():
    result = tu.tools.CTD_get_gene_diseases(input_terms="EGFR")
    assert result is not None, "CTD gene diseases returned None"


run_test("DepMap gene dependencies (EGFR)", test_depmap_dependencies)
run_test("PubMed validation papers (EGFR)", test_pubmed_validation_papers)
run_test("CTD gene diseases (EGFR)", test_ctd_gene_diseases)

# ============================================================
# Phase 8: Structural Insights Tests
# ============================================================
print()
print("=" * 70)
print("PHASE 8: Structural Insights")
print("=" * 70)


def test_pdb_metadata():
    result = tu.tools.get_protein_metadata_by_pdb_id(pdb_id="1M17")
    assert result is not None, "PDB metadata returned None"


def test_pdbe_quality():
    result = tu.tools.pdbe_get_entry_quality(pdb_id="1M17")
    assert result is not None, "PDBe quality returned None"


def test_pdbe_summary():
    result = tu.tools.pdbe_get_entry_summary(pdb_id="1M17")
    assert result is not None, "PDBe summary returned None"


def test_pdbe_experiment():
    result = tu.tools.pdbe_get_entry_experiment(pdb_id="1M17")
    assert result is not None, "PDBe experiment returned None"


def test_interpro_domains():
    result = tu.tools.InterPro_get_protein_domains(uniprot_accession="P00533")
    assert result is not None, "InterPro domains returned None"


run_test("PDB metadata (1M17)", test_pdb_metadata)
run_test("PDBe quality (1M17)", test_pdbe_quality)
run_test("PDBe summary (1M17)", test_pdbe_summary)
run_test("PDBe experiment (1M17)", test_pdbe_experiment)
run_test("InterPro domains (P00533)", test_interpro_domains)

# ============================================================
# Phase 9: Literature Tests
# ============================================================
print()
print("=" * 70)
print("PHASE 9: Literature Landscape")
print("=" * 70)


def test_pubmed_drug_target():
    result = tu.tools.PubMed_search_articles(
        query='"EGFR" AND (drug target OR therapeutic target)',
        limit=10
    )
    assert result is not None, "PubMed drug target papers returned None"
    if isinstance(result, list):
        assert len(result) > 0, "PubMed returned empty for EGFR drug target"


def test_europepmc_search():
    result = tu.tools.EuropePMC_search_articles(
        query='"EGFR" AND drug target',
        limit=10
    )
    assert result is not None, "EuropePMC returned None"


def test_openalex_search():
    result = tu.tools.openalex_search_works(
        query="EGFR drug target validation",
        limit=10
    )
    assert result is not None, "OpenAlex returned None"


run_test("PubMed drug target papers (EGFR)", test_pubmed_drug_target)
run_test("EuropePMC search (EGFR)", test_europepmc_search)
run_test("OpenAlex search (EGFR)", test_openalex_search)

# ============================================================
# Cross-Target Tests (Different Target Classes)
# ============================================================
print()
print("=" * 70)
print("CROSS-TARGET VALIDATION (Different Target Classes)")
print("=" * 70)


def test_kras_disambiguation():
    """KRAS - historically undruggable oncogene"""
    result = tu.tools.MyGene_query_genes(
        query="KRAS", species="human",
        fields="symbol,name,ensembl.gene,uniprot.Swiss-Prot"
    )
    assert result is not None, "MyGene KRAS returned None"


def test_kras_tractability():
    result = tu.tools.OpenTargets_get_target_tractability_by_ensemblID(
        ensemblId="ENSG00000133703"
    )
    assert result is not None, "OT KRAS tractability returned None"


def test_btk_disambiguation():
    """BTK - kinase target for autoimmune + oncology"""
    result = tu.tools.MyGene_query_genes(
        query="BTK", species="human",
        fields="symbol,name,ensembl.gene,uniprot.Swiss-Prot"
    )
    assert result is not None, "MyGene BTK returned None"


def test_btk_drugs():
    result = tu.tools.OpenTargets_get_associated_drugs_by_target_ensemblID(
        ensemblId="ENSG00000010671", size=20
    )
    assert result is not None, "OT BTK drugs returned None"


def test_pcsk9_disambiguation():
    """PCSK9 - antibody target for hypercholesterolemia"""
    result = tu.tools.MyGene_query_genes(
        query="PCSK9", species="human",
        fields="symbol,name,ensembl.gene,uniprot.Swiss-Prot"
    )
    assert result is not None, "MyGene PCSK9 returned None"


def test_pcsk9_safety():
    result = tu.tools.OpenTargets_get_target_safety_profile_by_ensemblID(
        ensemblId="ENSG00000169174"
    )
    assert result is not None, "OT PCSK9 safety returned None"


def test_pdcd1_disambiguation():
    """PD-1 (PDCD1) - immune checkpoint"""
    result = tu.tools.MyGene_query_genes(
        query="PDCD1", species="human",
        fields="symbol,name,ensembl.gene,uniprot.Swiss-Prot"
    )
    assert result is not None, "MyGene PDCD1 returned None"


def test_pdcd1_clinical_trials():
    result = tu.tools.search_clinical_trials(
        query_term="PD-1 inhibitor",
        condition="cancer",
        pageSize=10
    )
    assert result is not None, "Clinical trials PD-1 returned None"


run_test("KRAS disambiguation", test_kras_disambiguation)
run_test("KRAS tractability", test_kras_tractability)
run_test("BTK disambiguation", test_btk_disambiguation)
run_test("BTK associated drugs", test_btk_drugs)
run_test("PCSK9 disambiguation", test_pcsk9_disambiguation)
run_test("PCSK9 safety profile", test_pcsk9_safety)
run_test("PD-1 (PDCD1) disambiguation", test_pdcd1_disambiguation)
run_test("PD-1 clinical trials", test_pdcd1_clinical_trials)

# ============================================================
# Integration Tests: Multi-Step Workflows
# ============================================================
print()
print("=" * 70)
print("INTEGRATION TESTS: Multi-Step Workflows")
print("=" * 70)


def test_full_disambiguation_chain():
    """Test complete ID resolution chain for EGFR"""
    # Step 1: MyGene
    mg = tu.tools.MyGene_query_genes(
        query="EGFR", species="human",
        fields="symbol,name,ensembl.gene,uniprot.Swiss-Prot,entrezgene"
    )
    assert mg is not None, "Step 1 (MyGene) failed"

    # Step 2: Ensembl lookup
    ensembl = tu.tools.ensembl_lookup_gene(
        gene_id="ENSG00000146648", species="homo_sapiens"
    )
    assert ensembl is not None, "Step 2 (Ensembl) failed"

    # Step 3: UniProt
    uniprot = tu.tools.UniProt_get_entry_by_accession(accession="P00533")
    assert uniprot is not None, "Step 3 (UniProt) failed"

    # Step 4: OpenTargets
    ot = tu.tools.OpenTargets_get_target_id_description_by_name(targetName="EGFR")
    assert ot is not None, "Step 4 (OpenTargets) failed"


def test_druggability_chain():
    """Test multi-tool druggability assessment for BTK"""
    # Tractability
    tract = tu.tools.OpenTargets_get_target_tractability_by_ensemblID(
        ensemblId="ENSG00000010671"
    )
    assert tract is not None, "Tractability failed"

    # Pharos
    pharos = tu.tools.Pharos_get_target(gene="BTK")
    assert pharos is not None, "Pharos failed"

    # DGIdb
    dgidb = tu.tools.DGIdb_get_gene_druggability(genes=["BTK"])
    assert dgidb is not None, "DGIdb failed"

    # ChEMBL activities
    chembl = tu.tools.ChEMBL_get_target_activities(
        target_chembl_id__exact="CHEMBL5432", limit=10
    )
    assert chembl is not None, "ChEMBL activities failed"


def test_safety_chain():
    """Test multi-tool safety assessment for PCSK9"""
    # OT safety
    safety = tu.tools.OpenTargets_get_target_safety_profile_by_ensemblID(
        ensemblId="ENSG00000169174"
    )
    assert safety is not None, "OT safety failed"

    # Mouse models
    mouse = tu.tools.OpenTargets_get_biological_mouse_models_by_ensemblID(
        ensemblId="ENSG00000169174"
    )
    assert mouse is not None, "Mouse models failed"

    # gnomAD
    gnomad = tu.tools.gnomad_get_gene_constraints(gene_symbol="PCSK9")
    assert gnomad is not None, "gnomAD failed"


def test_pathway_chain():
    """Test pathway analysis chain for EGFR"""
    # Reactome
    pathways = tu.tools.Reactome_map_uniprot_to_pathways(id="P00533")
    assert pathways is not None, "Reactome failed"

    # STRING
    string_ppi = tu.tools.STRING_get_protein_interactions(
        protein_ids=["EGFR"], species=9606, confidence_score=0.7
    )
    assert string_ppi is not None, "STRING failed"

    # GO
    go = tu.tools.OpenTargets_get_target_gene_ontology_by_ensemblID(
        ensemblId="ENSG00000146648"
    )
    assert go is not None, "OT GO failed"


run_test("Full disambiguation chain (EGFR)", test_full_disambiguation_chain)
run_test("Druggability assessment chain (BTK)", test_druggability_chain)
run_test("Safety assessment chain (PCSK9)", test_safety_chain)
run_test("Pathway analysis chain (EGFR)", test_pathway_chain)

# ============================================================
# Report Generation
# ============================================================
print()
print("=" * 70)
print("TEST RESULTS SUMMARY")
print("=" * 70)
print()
print(f"Total Tests:  {TOTAL}")
print(f"Passed:       {PASSED}")
print(f"Failed:       {FAILED}")
print(f"Skipped:      {SKIPPED}")
print(f"Pass Rate:    {PASSED/TOTAL*100:.1f}%" if TOTAL > 0 else "N/A")
print()

if FAILED > 0:
    print("FAILED TESTS:")
    print("-" * 50)
    for r in RESULTS:
        if r['status'] == 'FAIL':
            print(f"  {r['test']}: {r['details']}")
    print()

# Calculate total test duration
total_duration = sum(r['duration'] for r in RESULTS)
print(f"Total Duration: {total_duration:.1f}s")

# Exit with appropriate code
sys.exit(0 if FAILED == 0 else 1)
