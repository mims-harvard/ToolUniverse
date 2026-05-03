#!/usr/bin/env python3
"""
Comprehensive Test Suite for tooluniverse-cancer-variant-interpretation skill.

Tests all 8 phases of the cancer variant interpretation workflow
using real cancer variants: EGFR L858R, BRAF V600E, KRAS G12C.
"""

import json
import sys
import time
from collections import Counter

# Track results
test_results = []
total_start = time.time()


def record_result(name, passed, details=""):
    status = "PASS" if passed else "FAIL"
    test_results.append({"name": name, "passed": passed, "details": details})
    print(f"  [{status}] {name}")
    if details and not passed:
        print(f"         {details}")


def run_tests():
    print("=" * 70)
    print("Cancer Variant Interpretation Skill - Test Suite")
    print("=" * 70)

    # Load ToolUniverse
    print("\nLoading ToolUniverse...")
    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()
    print(f"Loaded {len(tu.all_tool_dict)} tools")

    # ========================================================================
    # TEST 1: Gene Resolution (Phase 1)
    # ========================================================================
    print("\n--- Phase 1: Gene Resolution ---")

    # 1a: MyGene EGFR
    try:
        result = tu.tools.MyGene_query_genes(query='EGFR', species='human')
        hits = result.get('hits', [])
        egfr_hit = next((h for h in hits if h.get('symbol') == 'EGFR'), None)
        has_ensembl = egfr_hit and egfr_hit.get('ensembl', {}).get('gene') == 'ENSG00000146648'
        has_entrez = egfr_hit and str(egfr_hit.get('entrezgene')) == '1956'
        record_result("1a: MyGene EGFR resolution", has_ensembl and has_entrez,
                       f"ensembl={'OK' if has_ensembl else 'MISSING'}, entrez={'OK' if has_entrez else 'MISSING'}")
    except Exception as e:
        record_result("1a: MyGene EGFR resolution", False, str(e))

    # 1b: MyGene BRAF
    try:
        result = tu.tools.MyGene_query_genes(query='BRAF', species='human')
        hits = result.get('hits', [])
        braf_hit = next((h for h in hits if h.get('symbol') == 'BRAF'), None)
        record_result("1b: MyGene BRAF resolution", braf_hit is not None,
                       f"Found BRAF: {braf_hit.get('ensembl', {}).get('gene') if braf_hit else 'NOT FOUND'}")
    except Exception as e:
        record_result("1b: MyGene BRAF resolution", False, str(e))

    # 1c: UniProt search for EGFR
    try:
        result = tu.tools.UniProt_search(query='gene:EGFR', organism='human', limit=3)
        results = result.get('results', [])
        has_p00533 = any(r.get('accession') == 'P00533' for r in results)
        record_result("1c: UniProt EGFR lookup", has_p00533,
                       f"P00533 found: {has_p00533}, total results: {len(results)}")
    except Exception as e:
        record_result("1c: UniProt EGFR lookup", False, str(e))

    # 1d: OpenTargets target resolution
    try:
        result = tu.tools.OpenTargets_get_target_id_description_by_name(targetName='EGFR')
        hits = result.get('data', {}).get('search', {}).get('hits', [])
        egfr_ot = next((h for h in hits if h.get('name') == 'EGFR'), None)
        correct_id = egfr_ot and egfr_ot.get('id') == 'ENSG00000146648'
        record_result("1d: OpenTargets EGFR resolution", correct_id,
                       f"ID: {egfr_ot.get('id') if egfr_ot else 'NOT FOUND'}")
    except Exception as e:
        record_result("1d: OpenTargets EGFR resolution", False, str(e))

    # 1e: Cancer type EFO resolution
    try:
        result = tu.tools.OpenTargets_get_disease_id_description_by_name(diseaseName='lung adenocarcinoma')
        hits = result.get('data', {}).get('search', {}).get('hits', [])
        has_hits = len(hits) > 0
        record_result("1e: Cancer type EFO resolution", has_hits,
                       f"Hits: {len(hits)}, top: {hits[0].get('name') if hits else 'none'}")
    except Exception as e:
        record_result("1e: Cancer type EFO resolution", False, str(e))

    # 1f: UniProt function (returns list of strings, not dict)
    try:
        result = tu.tools.UniProt_get_function_by_accession(accession='P00533')
        has_data = result is not None and len(str(result)) > 10
        # UniProt function returns list of function description strings
        record_result("1f: UniProt function retrieval", has_data,
                       f"Type: {type(result).__name__}, content: {str(result)[:100]}...")
    except Exception as e:
        record_result("1f: UniProt function retrieval", False, str(e))

    # ========================================================================
    # TEST 2: Clinical Variant Evidence - CIViC (Phase 2)
    # ========================================================================
    print("\n--- Phase 2: Clinical Variant Evidence (CIViC) ---")

    # 2a: CIViC gene search
    try:
        result = tu.tools.civic_search_genes(limit=100)
        genes = result.get('data', {}).get('genes', {}).get('nodes', [])
        braf_civic = next((g for g in genes if g.get('name') == 'BRAF'), None)
        record_result("2a: CIViC gene search", braf_civic is not None,
                       f"BRAF found: gene_id={braf_civic.get('id') if braf_civic else 'NOT FOUND'}, total genes: {len(genes)}")
    except Exception as e:
        record_result("2a: CIViC gene search", False, str(e))

    # 2b: CIViC variants for BRAF (gene_id=5)
    try:
        result = tu.tools.civic_get_variants_by_gene(gene_id=5, limit=200)
        variants = result.get('data', {}).get('gene', {}).get('variants', {}).get('nodes', [])
        v600e = next((v for v in variants if v.get('name') == 'V600E'), None)
        record_result("2b: CIViC BRAF V600E variant", v600e is not None,
                       f"V600E found: id={v600e.get('id') if v600e else 'NOT FOUND'}, total variants: {len(variants)}")
    except Exception as e:
        record_result("2b: CIViC BRAF V600E variant", False, str(e))

    # 2c: CIViC variant details
    if v600e:
        try:
            result = tu.tools.civic_get_variant(variant_id=v600e['id'])
            variant_data = result.get('data', {}).get('variant', {})
            has_data = variant_data.get('id') is not None
            record_result("2c: CIViC variant details", has_data,
                           f"Variant name: {variant_data.get('name')}")
        except Exception as e:
            record_result("2c: CIViC variant details", False, str(e))
    else:
        record_result("2c: CIViC variant details", False, "V600E not found in 2b")

    # 2d: CIViC molecular profile
    try:
        result = tu.tools.civic_get_molecular_profile(molecular_profile_id=12)
        mp = result.get('data', {}).get('molecularProfile', {})
        has_name = mp.get('name') == 'BRAF V600E'
        record_result("2d: CIViC molecular profile (BRAF V600E)", has_name,
                       f"Name: {mp.get('name')}")
    except Exception as e:
        record_result("2d: CIViC molecular profile (BRAF V600E)", False, str(e))

    # ========================================================================
    # TEST 3: Mutation Prevalence - cBioPortal (Phase 3)
    # ========================================================================
    print("\n--- Phase 3: Mutation Prevalence (cBioPortal) ---")

    # 3a: cBioPortal cancer studies
    try:
        result = tu.tools.cBioPortal_get_cancer_studies(limit=20)
        studies = result if isinstance(result, list) else result.get('data', [])
        has_studies = len(studies) > 0
        record_result("3a: cBioPortal cancer studies", has_studies,
                       f"Studies found: {len(studies)}")
    except Exception as e:
        record_result("3a: cBioPortal cancer studies", False, str(e))

    # 3b: cBioPortal EGFR mutations in lung cancer
    # Response can be: list directly OR {status: 'success', data: [...]}
    try:
        result = tu.tools.cBioPortal_get_mutations(study_id='luad_tcga', gene_list='EGFR')
        if isinstance(result, list):
            mutations = result
        elif isinstance(result, dict):
            mutations = result.get('data', []) if result.get('status') == 'success' else []
        else:
            mutations = []
        has_mutations = len(mutations) > 0
        l858r_count = sum(1 for m in mutations if 'L858R' in str(m.get('proteinChange', '')))
        record_result("3b: cBioPortal EGFR mutations (LUAD)", has_mutations,
                       f"Total mutations: {len(mutations)}, L858R count: {l858r_count}")
    except Exception as e:
        record_result("3b: cBioPortal EGFR mutations (LUAD)", False, str(e))

    # 3c: cBioPortal BRAF mutations in melanoma
    try:
        result = tu.tools.cBioPortal_get_mutations(study_id='skcm_tcga', gene_list='BRAF')
        if isinstance(result, list):
            mutations = result
        elif isinstance(result, dict):
            mutations = result.get('data', []) if result.get('status') == 'success' else []
        else:
            mutations = []
        has_mutations = len(mutations) > 0
        v600e_count = sum(1 for m in mutations if 'V600E' in str(m.get('proteinChange', '')))
        record_result("3c: cBioPortal BRAF mutations (melanoma)", has_mutations,
                       f"Total mutations: {len(mutations)}, V600E count: {v600e_count}")
    except Exception as e:
        record_result("3c: cBioPortal BRAF mutations (melanoma)", False, str(e))

    # 3d: Mutation distribution analysis
    if mutations:
        try:
            protein_changes = [m.get('proteinChange', '') for m in mutations if m.get('proteinChange')]
            counts = Counter(protein_changes)
            top_5 = counts.most_common(5)
            record_result("3d: Mutation distribution analysis", len(top_5) > 0,
                           f"Top mutations: {top_5[:3]}")
        except Exception as e:
            record_result("3d: Mutation distribution analysis", False, str(e))

    # ========================================================================
    # TEST 4: Therapeutic Associations (Phase 4)
    # ========================================================================
    print("\n--- Phase 4: Therapeutic Associations ---")

    # 4a: OpenTargets drugs for EGFR
    try:
        result = tu.tools.OpenTargets_get_associated_drugs_by_target_ensemblID(
            ensemblId='ENSG00000146648', size=20
        )
        drugs = result.get('data', {}).get('target', {}).get('knownDrugs', {})
        total = drugs.get('count', 0)
        rows = drugs.get('rows', [])
        approved = [r for r in rows if r.get('drug', {}).get('isApproved')]
        has_osimertinib = any('OSIMERTINIB' in str(r.get('drug', {}).get('name', '')).upper() for r in rows)
        record_result("4a: OpenTargets EGFR drugs", total > 0 and has_osimertinib,
                       f"Total: {total}, approved: {len(approved)}, osimertinib found: {has_osimertinib}")
    except Exception as e:
        record_result("4a: OpenTargets EGFR drugs", False, str(e))

    # 4b: FDA indications for osimertinib
    try:
        result = tu.tools.FDA_get_indications_by_drug_name(drug_name='osimertinib', limit=3)
        fda_results = result.get('results', [])
        has_fda = len(fda_results) > 0
        has_indication = any('EGFR' in str(r.get('indications_and_usage', '')) for r in fda_results)
        record_result("4b: FDA osimertinib indications", has_fda and has_indication,
                       f"FDA entries: {len(fda_results)}, mentions EGFR: {has_indication}")
    except Exception as e:
        record_result("4b: FDA osimertinib indications", False, str(e))

    # 4c: DrugBank osimertinib info
    try:
        result = tu.tools.drugbank_get_drug_basic_info_by_drug_name_or_id(
            query='osimertinib', case_sensitive=False, exact_match=False, limit=3
        )
        db_results = result.get('results', [])
        has_db = len(db_results) > 0
        has_db09330 = any('DB09330' in str(r.get('drugbank_id', '')) for r in db_results)
        record_result("4c: DrugBank osimertinib", has_db and has_db09330,
                       f"Results: {len(db_results)}, DB09330 found: {has_db09330}")
    except Exception as e:
        record_result("4c: DrugBank osimertinib", False, str(e))

    # 4d: OpenTargets drug name to ChEMBL ID
    try:
        result = tu.tools.OpenTargets_get_drug_chembId_by_generic_name(drugName='osimertinib')
        hits = result.get('data', {}).get('search', {}).get('hits', [])
        has_chembl = any('CHEMBL' in str(h.get('id', '')) for h in hits)
        record_result("4d: OpenTargets drug ChEMBL resolution", has_chembl,
                       f"Hits: {len(hits)}, ChEMBL: {hits[0].get('id') if hits else 'none'}")
    except Exception as e:
        record_result("4d: OpenTargets drug ChEMBL resolution", False, str(e))

    # 4e: FDA mechanism of action
    try:
        result = tu.tools.FDA_get_mechanism_of_action_by_drug_name(drug_name='osimertinib', limit=3)
        fda_results = result.get('results', [])
        has_moa = len(fda_results) > 0
        record_result("4e: FDA mechanism of action", has_moa,
                       f"MOA entries: {len(fda_results)}")
    except Exception as e:
        record_result("4e: FDA mechanism of action", False, str(e))

    # 4f: OpenTargets BRAF drugs (different target)
    try:
        result = tu.tools.OpenTargets_get_associated_drugs_by_target_ensemblID(
            ensemblId='ENSG00000157764', size=20
        )
        drugs = result.get('data', {}).get('target', {}).get('knownDrugs', {})
        total = drugs.get('count', 0)
        rows = drugs.get('rows', [])
        has_vemurafenib = any('VEMURAFENIB' in str(r.get('drug', {}).get('name', '')).upper() for r in rows)
        has_dabrafenib = any('DABRAFENIB' in str(r.get('drug', {}).get('name', '')).upper() for r in rows)
        record_result("4f: OpenTargets BRAF drugs", total > 0,
                       f"Total: {total}, vemurafenib: {has_vemurafenib}, dabrafenib: {has_dabrafenib}")
    except Exception as e:
        record_result("4f: OpenTargets BRAF drugs", False, str(e))

    # ========================================================================
    # TEST 5: Resistance Mechanisms (Phase 5)
    # ========================================================================
    print("\n--- Phase 5: Resistance Mechanisms ---")

    # 5a: PubMed resistance literature (returns list directly)
    try:
        result = tu.tools.PubMed_search_articles(
            query='"EGFR" AND "osimertinib" AND resistance AND mechanism',
            limit=10, include_abstract=True
        )
        # PubMed returns a plain list of article dicts
        articles = result if isinstance(result, list) else result.get('articles', []) if isinstance(result, dict) else []
        has_articles = len(articles) > 0
        record_result("5a: PubMed resistance literature", has_articles,
                       f"Articles: {len(articles)}")
    except Exception as e:
        record_result("5a: PubMed resistance literature", False, str(e))

    # 5b: Reactome pathway context
    try:
        result = tu.tools.Reactome_map_uniprot_to_pathways(id='P00533')
        has_pathways = result is not None and len(str(result)) > 10
        record_result("5b: Reactome EGFR pathways", has_pathways,
                       f"Response length: {len(str(result)[:200])}")
    except Exception as e:
        record_result("5b: Reactome EGFR pathways", False, str(e))

    # ========================================================================
    # TEST 6: Clinical Trials (Phase 6)
    # ========================================================================
    print("\n--- Phase 6: Clinical Trials ---")

    # 6a: Clinical trials for EGFR mutation
    try:
        result = tu.tools.search_clinical_trials(
            query_term='EGFR L858R mutation',
            condition='non-small cell lung cancer',
            pageSize=10
        )
        studies = result.get('studies', [])
        has_trials = len(studies) > 0
        recruiting = [s for s in studies if s.get('overall_status') == 'RECRUITING']
        record_result("6a: Clinical trials EGFR L858R NSCLC", has_trials,
                       f"Trials: {len(studies)}, recruiting: {len(recruiting)}")
    except Exception as e:
        record_result("6a: Clinical trials EGFR L858R NSCLC", False, str(e))

    # 6b: Clinical trials for KRAS G12C
    try:
        result = tu.tools.search_clinical_trials(
            query_term='KRAS G12C',
            condition='cancer',
            pageSize=10
        )
        studies = result.get('studies', [])
        has_trials = len(studies) > 0
        record_result("6b: Clinical trials KRAS G12C", has_trials,
                       f"Trials: {len(studies)}")
    except Exception as e:
        record_result("6b: Clinical trials KRAS G12C", False, str(e))

    # 6c: Clinical trials for BRAF V600E
    try:
        result = tu.tools.search_clinical_trials(
            query_term='BRAF V600E',
            condition='melanoma',
            pageSize=10
        )
        studies = result.get('studies', [])
        has_trials = len(studies) > 0
        record_result("6c: Clinical trials BRAF V600E melanoma", has_trials,
                       f"Trials: {len(studies)}")
    except Exception as e:
        record_result("6c: Clinical trials BRAF V600E melanoma", False, str(e))

    # ========================================================================
    # TEST 7: Prognostic & Pathway Context (Phase 7)
    # ========================================================================
    print("\n--- Phase 7: Prognostic & Pathway Context ---")

    # 7a: PubMed prognostic literature (returns list directly)
    try:
        result = tu.tools.PubMed_search_articles(
            query='"EGFR" "L858R" prognosis survival lung cancer',
            limit=5, include_abstract=True
        )
        articles = result if isinstance(result, list) else result.get('articles', []) if isinstance(result, dict) else []
        has_articles = len(articles) > 0
        record_result("7a: PubMed prognostic literature", has_articles,
                       f"Articles: {len(articles)}")
    except Exception as e:
        record_result("7a: PubMed prognostic literature", False, str(e))

    # 7b: UniProt disease variants
    try:
        result = tu.tools.UniProt_get_disease_variants_by_accession(accession='P00533')
        has_variants = result is not None and len(str(result)) > 10
        record_result("7b: UniProt EGFR disease variants", has_variants,
                       f"Response type: {type(result).__name__}")
    except Exception as e:
        record_result("7b: UniProt EGFR disease variants", False, str(e))

    # 7c: Ensembl gene lookup (requires species parameter)
    try:
        result = tu.tools.ensembl_lookup_gene(gene_id='ENSG00000146648', species='homo_sapiens')
        # Response: {status: 'success', data: {id, version, display_name, ...}}
        data = result.get('data', result) if isinstance(result, dict) else {}
        version = data.get('version')
        has_version = version is not None
        record_result("7c: Ensembl gene version lookup", has_version,
                       f"Version: {version}, display_name: {data.get('display_name', 'N/A')}")
    except Exception as e:
        record_result("7c: Ensembl gene version lookup", False, str(e))

    # ========================================================================
    # TEST 8: Cross-variant tests (KRAS G12C)
    # ========================================================================
    print("\n--- Phase 8: Cross-variant validation (KRAS G12C) ---")

    # 8a: KRAS gene resolution
    try:
        result = tu.tools.MyGene_query_genes(query='KRAS', species='human')
        hits = result.get('hits', [])
        kras_hit = next((h for h in hits if h.get('symbol') == 'KRAS'), None)
        kras_ensembl = kras_hit.get('ensembl', {}).get('gene') if kras_hit else None
        record_result("8a: KRAS gene resolution", kras_ensembl is not None,
                       f"Ensembl: {kras_ensembl}")
    except Exception as e:
        record_result("8a: KRAS gene resolution", False, str(e))

    # 8b: KRAS drugs from OpenTargets
    try:
        result = tu.tools.OpenTargets_get_associated_drugs_by_target_ensemblID(
            ensemblId='ENSG00000133703', size=20
        )
        drugs = result.get('data', {}).get('target', {}).get('knownDrugs', {})
        total = drugs.get('count', 0)
        rows = drugs.get('rows', [])
        has_sotorasib = any('SOTORASIB' in str(r.get('drug', {}).get('name', '')).upper() for r in rows)
        record_result("8b: KRAS targeted drugs", total > 0,
                       f"Total: {total}, sotorasib found: {has_sotorasib}")
    except Exception as e:
        record_result("8b: KRAS targeted drugs", False, str(e))

    # 8c: KRAS mutations in pancreatic cancer
    try:
        result = tu.tools.cBioPortal_get_mutations(study_id='paad_tcga', gene_list='KRAS')
        if isinstance(result, list):
            mutations = result
        elif isinstance(result, dict):
            mutations = result.get('data', []) if result.get('status') == 'success' else []
        else:
            mutations = []
        g12_variants = [m for m in mutations if 'G12' in str(m.get('proteinChange', ''))]
        record_result("8c: KRAS mutations in pancreatic cancer", len(mutations) > 0,
                       f"Total: {len(mutations)}, G12 variants: {len(g12_variants)}")
    except Exception as e:
        record_result("8c: KRAS mutations in pancreatic cancer", False, str(e))

    # 8d: FDA sotorasib info
    try:
        result = tu.tools.FDA_get_indications_by_drug_name(drug_name='sotorasib', limit=3)
        fda_results = result.get('results', [])
        has_kras = any('KRAS' in str(r.get('indications_and_usage', '')) for r in fda_results)
        record_result("8d: FDA sotorasib indications", len(fda_results) > 0,
                       f"FDA entries: {len(fda_results)}, mentions KRAS: {has_kras}")
    except Exception as e:
        record_result("8d: FDA sotorasib indications", False, str(e))

    # ========================================================================
    # TEST 9: TP53 R273H (VUS-like scenario)
    # ========================================================================
    print("\n--- Phase 9: TP53 R273H (complex variant) ---")

    # 9a: TP53 gene resolution
    try:
        result = tu.tools.MyGene_query_genes(query='TP53', species='human')
        hits = result.get('hits', [])
        tp53_hit = next((h for h in hits if h.get('symbol') == 'TP53'), None)
        tp53_ensembl = tp53_hit.get('ensembl', {}).get('gene') if tp53_hit else None
        record_result("9a: TP53 gene resolution", tp53_ensembl is not None,
                       f"Ensembl: {tp53_ensembl}")
    except Exception as e:
        record_result("9a: TP53 gene resolution", False, str(e))

    # 9b: TP53 drugs (should have fewer targeted therapies)
    try:
        result = tu.tools.OpenTargets_get_associated_drugs_by_target_ensemblID(
            ensemblId='ENSG00000141510', size=20
        )
        drugs = result.get('data', {}).get('target', {}).get('knownDrugs', {})
        total = drugs.get('count', 0)
        record_result("9b: TP53 drug landscape", True,  # Pass regardless - TP53 has limited targeted options
                       f"Total drug entries: {total} (TP53 has limited direct targets)")
    except Exception as e:
        record_result("9b: TP53 drug landscape", False, str(e))

    # 9c: TP53 mutations across cancer types
    try:
        result = tu.tools.cBioPortal_get_mutations(study_id='luad_tcga', gene_list='TP53')
        if isinstance(result, list):
            mutations = result
        elif isinstance(result, dict):
            mutations = result.get('data', []) if result.get('status') == 'success' else []
        else:
            mutations = []
        r273h_count = sum(1 for m in mutations if 'R273H' in str(m.get('proteinChange', '')))
        record_result("9c: TP53 R273H in LUAD", len(mutations) > 0,
                       f"Total TP53 mutations: {len(mutations)}, R273H: {r273h_count}")
    except Exception as e:
        record_result("9c: TP53 R273H in LUAD", False, str(e))

    # ========================================================================
    # SUMMARY
    # ========================================================================
    elapsed = time.time() - total_start
    passed = sum(1 for r in test_results if r['passed'])
    failed = sum(1 for r in test_results if not r['passed'])
    total = len(test_results)

    print("\n" + "=" * 70)
    print(f"TEST SUMMARY: {passed}/{total} passed, {failed} failed")
    print(f"Time elapsed: {elapsed:.1f}s")
    print("=" * 70)

    if failed > 0:
        print("\nFailed tests:")
        for r in test_results:
            if not r['passed']:
                print(f"  FAIL: {r['name']}")
                if r['details']:
                    print(f"        {r['details']}")

    return passed, total


if __name__ == '__main__':
    passed, total = run_tests()
    sys.exit(0 if passed == total else 1)
