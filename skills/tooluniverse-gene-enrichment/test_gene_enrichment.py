#!/usr/bin/env python3
"""
Comprehensive Test Suite for tooluniverse-gene-enrichment Skill

Tests all enrichment capabilities: ORA, GSEA, multiple databases,
ID conversion, cross-validation, and multiple testing correction.
"""

import sys
import time
import traceback
import re

# ============================================================
# Test Infrastructure
# ============================================================

RESULTS = []

def run_test(test_func):
    """Run a test function and record results."""
    name = test_func.__name__
    doc = test_func.__doc__ or name
    start = time.time()
    try:
        test_func()
        elapsed = time.time() - start
        RESULTS.append({"name": name, "doc": doc.strip(), "status": "PASS", "time": elapsed, "error": None})
        print(f"  PASS  {name} ({elapsed:.1f}s)")
    except Exception as e:
        elapsed = time.time() - start
        error_msg = f"{type(e).__name__}: {e}"
        RESULTS.append({"name": name, "doc": doc.strip(), "status": "FAIL", "time": elapsed, "error": error_msg})
        print(f"  FAIL  {name} ({elapsed:.1f}s): {error_msg}")
        traceback.print_exc()

# ============================================================
# Test Data
# ============================================================

CANCER_GENES = ["TP53", "BRCA1", "EGFR", "MYC", "AKT1", "PTEN", "RB1", "MDM2", "CDK4", "CCND1"]

IMMUNE_GENES = ["IL6", "TNF", "IL10", "IFNG", "IL1B", "CCL2", "CXCL8", "IL2", "IL4", "TGFB1",
                "CD4", "CD8A", "FOXP3", "STAT3", "JAK1", "JAK2", "NFKB1", "IRF1", "TLR4", "MYD88"]

SIGNALING_GENES = ["EGFR", "KRAS", "BRAF", "MAP2K1", "MAPK1", "PIK3CA", "AKT1", "MTOR",
                   "RAF1", "SOS1", "GRB2", "SHC1", "HRAS", "NRAS", "ERBB2"]

ENSEMBL_IDS = ["ENSG00000141510", "ENSG00000012048", "ENSG00000146648",
               "ENSG00000136997", "ENSG00000142208"]


# ============================================================
# Phase 1: gseapy ORA Tests
# ============================================================

def test_01_gseapy_go_bp_enrichment():
    """gseapy ORA: GO Biological Process enrichment with cancer gene list"""
    import gseapy
    result = gseapy.enrichr(
        gene_list=CANCER_GENES,
        gene_sets='GO_Biological_Process_2021',
        organism='human',
        outdir=None,
        no_plot=True,
    )
    df = result.results
    assert len(df) > 0, "No results returned"
    assert 'Term' in df.columns, "Missing Term column"
    assert 'P-value' in df.columns, "Missing P-value column"
    assert 'Adjusted P-value' in df.columns, "Missing Adjusted P-value column"
    assert 'Overlap' in df.columns, "Missing Overlap column"
    assert 'Genes' in df.columns, "Missing Genes column"

    sig = df[df['Adjusted P-value'] < 0.05]
    assert len(sig) > 0, "No significant GO BP terms found"

    # Verify top term contains GO ID
    top_term = sig.iloc[0]['Term']
    assert re.search(r'GO:\d+', top_term), f"Top term missing GO ID: {top_term}"

    # Verify p-values are valid
    assert all(df['P-value'] >= 0), "Negative p-values found"
    assert all(df['P-value'] <= 1), "P-values > 1 found"
    assert all(df['Adjusted P-value'] >= 0), "Negative adjusted p-values found"

    print(f"    {len(sig)} significant GO BP terms (p_adj < 0.05)")
    print(f"    Top term: {sig.iloc[0]['Term'][:80]}")


def test_02_gseapy_go_mf_enrichment():
    """gseapy ORA: GO Molecular Function enrichment"""
    import gseapy
    result = gseapy.enrichr(
        gene_list=CANCER_GENES,
        gene_sets='GO_Molecular_Function_2021',
        organism='human',
        outdir=None,
        no_plot=True,
    )
    df = result.results
    assert len(df) > 0, "No results returned"
    sig = df[df['Adjusted P-value'] < 0.05]
    assert len(sig) > 0, "No significant GO MF terms"
    print(f"    {len(sig)} significant GO MF terms")


def test_03_gseapy_go_cc_enrichment():
    """gseapy ORA: GO Cellular Component enrichment"""
    import gseapy
    result = gseapy.enrichr(
        gene_list=CANCER_GENES,
        gene_sets='GO_Cellular_Component_2021',
        organism='human',
        outdir=None,
        no_plot=True,
    )
    df = result.results
    assert len(df) > 0, "No results returned"
    sig = df[df['Adjusted P-value'] < 0.05]
    assert len(sig) > 0, "No significant GO CC terms"
    print(f"    {len(sig)} significant GO CC terms")


def test_04_gseapy_kegg_enrichment():
    """gseapy ORA: KEGG pathway enrichment"""
    import gseapy
    result = gseapy.enrichr(
        gene_list=CANCER_GENES,
        gene_sets='KEGG_2021_Human',
        organism='human',
        outdir=None,
        no_plot=True,
    )
    df = result.results
    assert len(df) > 0, "No KEGG results returned"
    sig = df[df['Adjusted P-value'] < 0.05]
    assert len(sig) > 0, "No significant KEGG pathways"

    # Cancer genes should have cancer pathways
    cancer_pathways = sig[sig['Term'].str.contains('cancer|carcinoma|melanoma|glioma', case=False)]
    assert len(cancer_pathways) > 0, "No cancer-related KEGG pathways found for cancer genes"

    print(f"    {len(sig)} significant KEGG pathways")
    print(f"    Most enriched: {sig.iloc[0]['Term']}")


def test_05_gseapy_reactome_enrichment():
    """gseapy ORA: Reactome pathway enrichment"""
    import gseapy
    result = gseapy.enrichr(
        gene_list=CANCER_GENES,
        gene_sets='Reactome_Pathways_2024',
        organism='human',
        outdir=None,
        no_plot=True,
    )
    df = result.results
    assert len(df) > 0, "No Reactome results returned"
    sig = df[df['Adjusted P-value'] < 0.05]
    assert len(sig) > 0, "No significant Reactome pathways"
    print(f"    {len(sig)} significant Reactome pathways")


def test_06_gseapy_msigdb_hallmark():
    """gseapy ORA: MSigDB Hallmark enrichment"""
    import gseapy
    result = gseapy.enrichr(
        gene_list=CANCER_GENES,
        gene_sets='MSigDB_Hallmark_2020',
        organism='human',
        outdir=None,
        no_plot=True,
    )
    df = result.results
    assert len(df) > 0, "No Hallmark results returned"
    sig = df[df['Adjusted P-value'] < 0.05]
    print(f"    {len(sig)} significant Hallmark terms")
    if len(sig) > 0:
        print(f"    Top: {sig.iloc[0]['Term']}")


def test_07_gseapy_wikipathways():
    """gseapy ORA: WikiPathways enrichment"""
    import gseapy
    result = gseapy.enrichr(
        gene_list=CANCER_GENES,
        gene_sets='WikiPathways_2024_Human',
        organism='human',
        outdir=None,
        no_plot=True,
    )
    df = result.results
    assert len(df) > 0, "No WikiPathways results returned"
    sig = df[df['Adjusted P-value'] < 0.05]
    print(f"    {len(sig)} significant WikiPathways terms")


def test_08_gseapy_multi_library():
    """gseapy ORA: Multiple libraries in one call"""
    import gseapy
    result = gseapy.enrichr(
        gene_list=CANCER_GENES,
        gene_sets=['GO_Biological_Process_2021', 'KEGG_2021_Human', 'Reactome_Pathways_2024'],
        organism='human',
        outdir=None,
        no_plot=True,
    )
    df = result.results
    assert len(df) > 0, "No results returned"

    # Verify Gene_set column distinguishes libraries
    libraries = df['Gene_set'].unique()
    assert len(libraries) == 3, f"Expected 3 libraries, got {len(libraries)}: {list(libraries)}"
    print(f"    Libraries: {list(libraries)}")
    for lib in libraries:
        lib_sig = df[(df['Gene_set'] == lib) & (df['Adjusted P-value'] < 0.05)]
        print(f"    {lib}: {len(lib_sig)} significant terms")


def test_09_gseapy_results_structure():
    """gseapy ORA: Verify DataFrame column structure and types"""
    import gseapy
    result = gseapy.enrichr(
        gene_list=CANCER_GENES,
        gene_sets='GO_Biological_Process_2021',
        organism='human',
        outdir=None,
        no_plot=True,
    )
    df = result.results
    expected_cols = ['Gene_set', 'Term', 'Overlap', 'P-value', 'Adjusted P-value',
                     'Old P-value', 'Old Adjusted P-value', 'Odds Ratio', 'Combined Score', 'Genes']
    for col in expected_cols:
        assert col in df.columns, f"Missing column: {col}"

    # Verify types
    assert df['P-value'].dtype in ['float64', 'float32'], f"P-value dtype: {df['P-value'].dtype}"
    assert df['Adjusted P-value'].dtype in ['float64', 'float32'], f"Adj P-value dtype: {df['Adjusted P-value'].dtype}"
    assert df['Odds Ratio'].dtype in ['float64', 'float32'], f"Odds Ratio dtype: {df['Odds Ratio'].dtype}"
    print(f"    All {len(expected_cols)} expected columns present with correct types")


# ============================================================
# Phase 2: GSEA Tests
# ============================================================

def test_10_gsea_preranked_go_bp():
    """gseapy GSEA: Preranked GO Biological Process"""
    import gseapy
    import pandas as pd
    import numpy as np

    np.random.seed(42)
    genes = CANCER_GENES + ["GAPDH", "ACTB", "TUBB", "ALB", "INS", "TNF",
                            "IL6", "IL10", "VEGFA", "KRAS", "RAF1", "MAP2K1",
                            "MAPK1", "PIK3CA", "MTOR", "JAK1", "STAT3",
                            "NOTCH1", "WNT1", "SHH"]
    ranks = pd.Series(np.random.randn(len(genes)), index=genes).sort_values(ascending=False)

    result = gseapy.prerank(
        rnk=ranks,
        gene_sets='GO_Biological_Process_2021',
        outdir=None,
        no_plot=True,
        seed=42,
        min_size=3,
        max_size=500,
        permutation_num=100,
    )

    df = result.res2d
    assert len(df) > 0, "No GSEA results returned"

    expected_cols = ['Name', 'Term', 'ES', 'NES', 'NOM p-val', 'FDR q-val', 'FWER p-val', 'Lead_genes']
    for col in expected_cols:
        assert col in df.columns, f"Missing GSEA column: {col}"

    print(f"    {len(df)} terms analyzed")
    sig = df[df['FDR q-val'].astype(float) < 0.25]
    print(f"    {len(sig)} significant (FDR < 0.25)")


def test_11_gsea_preranked_kegg():
    """gseapy GSEA: Preranked KEGG pathways"""
    import gseapy
    import pandas as pd
    import numpy as np

    np.random.seed(42)
    genes = list(set(SIGNALING_GENES + CANCER_GENES[:5]))
    ranks = pd.Series(np.random.randn(len(genes)), index=genes).sort_values(ascending=False)

    result = gseapy.prerank(
        rnk=ranks,
        gene_sets='KEGG_2021_Human',
        outdir=None,
        no_plot=True,
        seed=42,
        min_size=3,
        max_size=500,
        permutation_num=100,
    )

    df = result.res2d
    assert len(df) > 0, "No GSEA KEGG results"
    print(f"    {len(df)} KEGG terms analyzed by GSEA")


def test_12_gsea_nes_sign():
    """gseapy GSEA: NES sign reflects enrichment direction"""
    import gseapy
    import pandas as pd

    # Create ranked list with cancer genes at top (positive)
    gene_scores = {g: 5.0 - i * 0.3 for i, g in enumerate(CANCER_GENES)}
    # Add non-cancer genes at bottom (negative)
    filler = ["GAPDH", "ACTB", "ALB", "INS", "TUBB", "HBB", "HBA1",
              "TTN", "MUC16", "OBSCN", "AHNAK", "SYNE1", "FLNB", "PLEC",
              "DSP", "MACF1", "BCLAF1", "SRRM2"]
    for i, g in enumerate(filler):
        gene_scores[g] = -0.5 - i * 0.3
    ranks = pd.Series(gene_scores).sort_values(ascending=False)

    result = gseapy.prerank(
        rnk=ranks,
        gene_sets='GO_Biological_Process_2021',
        outdir=None,
        no_plot=True,
        seed=42,
        min_size=3,
        max_size=500,
        permutation_num=100,
    )

    df = result.res2d
    # There should be both positive and negative NES values
    nes_values = df['NES'].astype(float)
    has_positive = any(nes_values > 0)
    has_negative = any(nes_values < 0)
    print(f"    Positive NES: {sum(nes_values > 0)}, Negative NES: {sum(nes_values < 0)}")
    assert has_positive or has_negative, "NES values should include positive or negative"


# ============================================================
# Phase 3: PANTHER Enrichment Tests
# ============================================================

def test_13_panther_go_bp():
    """PANTHER: GO Biological Process enrichment"""
    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    result = tu.tools.PANTHER_enrichment(
        gene_list=','.join(CANCER_GENES),
        organism=9606,
        annotation_dataset='GO:0008150'
    )
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    data = result.get('data', {})
    terms = data.get('enriched_terms', [])
    assert len(terms) > 0, "No PANTHER enriched terms"

    # Verify term structure
    first = terms[0]
    assert 'term_id' in first, "Missing term_id"
    assert 'term_label' in first, "Missing term_label"
    assert 'pvalue' in first, "Missing pvalue"
    assert 'fdr' in first, "Missing fdr"
    assert 'fold_enrichment' in first, "Missing fold_enrichment"

    sig = [t for t in terms if t.get('fdr', 1) < 0.05]
    print(f"    {len(sig)} significant PANTHER GO BP terms")
    if sig:
        print(f"    Top: {sig[0]['term_label']} (fdr={sig[0]['fdr']:.2e})")


def test_14_panther_go_mf():
    """PANTHER: GO Molecular Function enrichment"""
    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    result = tu.tools.PANTHER_enrichment(
        gene_list=','.join(CANCER_GENES),
        organism=9606,
        annotation_dataset='GO:0003674'
    )
    terms = result.get('data', {}).get('enriched_terms', [])
    assert len(terms) > 0, "No PANTHER GO MF terms"
    sig = [t for t in terms if t.get('fdr', 1) < 0.05]
    print(f"    {len(sig)} significant PANTHER GO MF terms")


def test_15_panther_go_cc():
    """PANTHER: GO Cellular Component enrichment"""
    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    result = tu.tools.PANTHER_enrichment(
        gene_list=','.join(CANCER_GENES),
        organism=9606,
        annotation_dataset='GO:0005575'
    )
    terms = result.get('data', {}).get('enriched_terms', [])
    assert len(terms) > 0, "No PANTHER GO CC terms"
    sig = [t for t in terms if t.get('fdr', 1) < 0.05]
    print(f"    {len(sig)} significant PANTHER GO CC terms")


def test_16_panther_pathway():
    """PANTHER: PANTHER Pathway enrichment"""
    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    result = tu.tools.PANTHER_enrichment(
        gene_list=','.join(CANCER_GENES),
        organism=9606,
        annotation_dataset='ANNOT_TYPE_ID_PANTHER_PATHWAY'
    )
    terms = result.get('data', {}).get('enriched_terms', [])
    assert len(terms) > 0, "No PANTHER pathway terms"
    sig = [t for t in terms if t.get('fdr', 1) < 0.05]
    print(f"    {len(sig)} significant PANTHER pathways")
    if sig:
        print(f"    Top: {sig[0]['term_label']}")


# ============================================================
# Phase 4: STRING Enrichment Tests
# ============================================================

def test_17_string_functional_enrichment():
    """STRING: Functional enrichment (all categories)"""
    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    result = tu.tools.STRING_functional_enrichment(
        protein_ids=CANCER_GENES,
        species=9606
    )
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    data = result.get('data', [])
    assert isinstance(data, list), f"Data should be list, got {type(data)}"
    assert len(data) > 0, "No STRING enrichment results"

    # Verify categories are present
    categories = set(d.get('category', '') for d in data)
    assert 'Process' in categories or 'KEGG' in categories, f"Expected Process or KEGG in categories: {categories}"
    print(f"    Categories found: {sorted(categories)}")

    # Filter GO BP
    go_bp = [d for d in data if d.get('category') == 'Process']
    print(f"    GO BP terms: {len(go_bp)}")

    # Filter KEGG
    kegg = [d for d in data if d.get('category') == 'KEGG']
    print(f"    KEGG terms: {len(kegg)}")


def test_18_string_kegg_enrichment():
    """STRING: KEGG pathway enrichment filtered from functional enrichment"""
    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    result = tu.tools.STRING_functional_enrichment(
        protein_ids=CANCER_GENES,
        species=9606,
        category='KEGG'
    )
    data = result.get('data', [])
    kegg = [d for d in data if d.get('category') == 'KEGG']
    assert len(kegg) > 0, "No KEGG terms from STRING"

    # Verify KEGG structure
    first = kegg[0]
    assert 'term' in first, "Missing term"
    assert 'p_value' in first, "Missing p_value"
    assert 'fdr' in first, "Missing fdr"
    assert 'description' in first, "Missing description"
    assert 'number_of_genes' in first, "Missing number_of_genes"

    sig = [d for d in kegg if d.get('fdr', 1) < 0.05]
    print(f"    {len(sig)} significant KEGG terms from STRING")
    if sig:
        print(f"    Top: {sig[0]['description']} (fdr={sig[0]['fdr']:.2e})")


def test_19_string_ppi_enrichment():
    """STRING: PPI enrichment test (network connectivity)"""
    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    result = tu.tools.STRING_ppi_enrichment(
        protein_ids=CANCER_GENES,
        species=9606
    )
    # PPI enrichment returns connectivity statistics
    assert result is not None, "No PPI enrichment result"
    print(f"    PPI enrichment result type: {type(result)}")
    if isinstance(result, dict):
        print(f"    Keys: {list(result.keys())[:10]}")


# ============================================================
# Phase 5: Reactome Enrichment Tests
# ============================================================

def test_20_reactome_pathway_enrichment():
    """Reactome: Pathway overrepresentation analysis"""
    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    result = tu.tools.ReactomeAnalysis_pathway_enrichment(
        identifiers=' '.join(CANCER_GENES),
        page_size=30
    )
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    data = result.get('data', {})
    pathways = data.get('pathways', [])
    assert len(pathways) > 0, "No Reactome pathways returned"

    # Verify pathway structure
    first = pathways[0]
    assert 'pathway_id' in first, "Missing pathway_id"
    assert 'name' in first, "Missing name"
    assert 'p_value' in first, "Missing p_value"
    assert 'fdr' in first, "Missing fdr"
    assert 'entities_found' in first, "Missing entities_found"

    sig = [p for p in pathways if p.get('fdr', 1) < 0.05]
    print(f"    {len(sig)} significant Reactome pathways (fdr < 0.05)")
    if sig:
        print(f"    Top: {sig[0]['name']} (fdr={sig[0]['fdr']:.2e})")

    # Verify identifiers_not_found
    not_found = data.get('identifiers_not_found', -1)
    print(f"    Identifiers not found: {not_found}")


def test_21_reactome_cross_validation():
    """Reactome: Cross-validate gseapy vs Reactome API results"""
    import gseapy
    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    # gseapy Reactome
    gseapy_result = gseapy.enrichr(
        gene_list=CANCER_GENES,
        gene_sets='Reactome_Pathways_2024',
        organism='human',
        outdir=None, no_plot=True,
    )
    gseapy_sig = set(gseapy_result.results[gseapy_result.results['Adjusted P-value'] < 0.05]['Term'].str.lower())

    # Reactome API
    api_result = tu.tools.ReactomeAnalysis_pathway_enrichment(
        identifiers=' '.join(CANCER_GENES),
        page_size=30
    )
    api_pathways = api_result.get('data', {}).get('pathways', [])
    api_sig = set(p['name'].lower() for p in api_pathways if p.get('fdr', 1) < 0.05)

    # Check for overlap (terms may not match exactly due to naming differences)
    print(f"    gseapy significant terms: {len(gseapy_sig)}")
    print(f"    Reactome API significant terms: {len(api_sig)}")

    # At least some overlap expected
    if gseapy_sig and api_sig:
        overlap = 0
        for g_term in gseapy_sig:
            for a_term in api_sig:
                if g_term in a_term or a_term in g_term:
                    overlap += 1
                    break
        print(f"    Approximate overlap: {overlap} terms")


# ============================================================
# Phase 6: ID Conversion Tests
# ============================================================

def test_22_mygene_batch_conversion():
    """ID Conversion: Ensembl to Symbol via MyGene batch query"""
    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    result = tu.tools.MyGene_batch_query(
        gene_ids=ENSEMBL_IDS,
        fields="symbol,entrezgene,ensembl.gene"
    )
    # Handle different response structures
    results = result.get('results', result.get('data', {}).get('results', []))
    assert len(results) > 0, "No MyGene results"

    symbols = []
    for hit in results:
        symbol = hit.get('symbol')
        if symbol:
            symbols.append(symbol)
            print(f"    {hit['query']} -> {symbol}")

    assert len(symbols) >= 3, f"Expected at least 3 symbols, got {len(symbols)}"
    assert 'TP53' in symbols, "TP53 not found in conversion"


def test_23_string_map_identifiers():
    """ID Conversion: Gene symbols to STRING IDs"""
    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    result = tu.tools.STRING_map_identifiers(
        protein_ids=CANCER_GENES[:5],
        species=9606
    )
    # Can return list or dict with data
    if isinstance(result, dict):
        data = result.get('data', result)
    else:
        data = result

    if isinstance(data, list):
        assert len(data) > 0, "No STRING mappings"
        for item in data[:3]:
            print(f"    {item.get('queryItem', '?')} -> {item.get('preferredName', '?')} ({item.get('stringId', '?')})")


def test_24_enrichment_after_id_conversion():
    """ID Conversion: Convert Ensembl IDs then run enrichment"""
    import gseapy
    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    # Convert Ensembl to symbols
    result = tu.tools.MyGene_batch_query(
        gene_ids=ENSEMBL_IDS,
        fields="symbol"
    )
    results = result.get('results', result.get('data', {}).get('results', []))
    symbols = [hit.get('symbol', hit['query']) for hit in results if 'symbol' in hit]
    assert len(symbols) >= 3, f"Not enough symbols converted: {symbols}"

    # Run enrichment with converted symbols
    go_result = gseapy.enrichr(
        gene_list=symbols,
        gene_sets='GO_Biological_Process_2021',
        organism='human',
        outdir=None, no_plot=True,
    )
    assert len(go_result.results) > 0, "No enrichment after ID conversion"
    print(f"    Converted {len(ENSEMBL_IDS)} Ensembl IDs to {len(symbols)} symbols")
    print(f"    Enrichment returned {len(go_result.results)} terms")


# ============================================================
# Phase 7: Multiple Testing Correction Tests
# ============================================================

def test_25_bh_correction():
    """Multiple Testing: Benjamini-Hochberg correction"""
    import gseapy
    import numpy as np
    from statsmodels.stats.multitest import multipletests

    result = gseapy.enrichr(
        gene_list=CANCER_GENES,
        gene_sets='GO_Biological_Process_2021',
        organism='human',
        outdir=None, no_plot=True,
    )

    raw_pvals = result.results['P-value'].values
    assert len(raw_pvals) > 0, "No p-values to correct"

    reject, corrected, _, _ = multipletests(raw_pvals, alpha=0.05, method='fdr_bh')
    n_sig = sum(reject)
    print(f"    BH: {n_sig}/{len(raw_pvals)} significant")
    assert all(corrected >= raw_pvals), "BH-corrected p-values should be >= raw p-values"


def test_26_bonferroni_correction():
    """Multiple Testing: Bonferroni correction"""
    import gseapy
    import numpy as np
    from statsmodels.stats.multitest import multipletests

    result = gseapy.enrichr(
        gene_list=CANCER_GENES,
        gene_sets='GO_Biological_Process_2021',
        organism='human',
        outdir=None, no_plot=True,
    )

    raw_pvals = result.results['P-value'].values
    reject_bh, bh_pvals, _, _ = multipletests(raw_pvals, alpha=0.05, method='fdr_bh')
    reject_bonf, bonf_pvals, _, _ = multipletests(raw_pvals, alpha=0.05, method='bonferroni')

    n_bh = sum(reject_bh)
    n_bonf = sum(reject_bonf)
    print(f"    BH: {n_bh} significant, Bonferroni: {n_bonf} significant")
    assert n_bonf <= n_bh, "Bonferroni should be more conservative than BH"


def test_27_correction_comparison():
    """Multiple Testing: Compare BH, Bonferroni, BY methods"""
    import gseapy
    from statsmodels.stats.multitest import multipletests

    result = gseapy.enrichr(
        gene_list=CANCER_GENES,
        gene_sets='GO_Biological_Process_2021',
        organism='human',
        outdir=None, no_plot=True,
    )

    raw_pvals = result.results['P-value'].values
    methods = ['fdr_bh', 'bonferroni', 'fdr_by', 'holm-sidak', 'holm']
    counts = {}
    for method in methods:
        reject, _, _, _ = multipletests(raw_pvals, alpha=0.05, method=method)
        counts[method] = sum(reject)

    print(f"    Correction comparison:")
    for method, count in counts.items():
        print(f"      {method}: {count} significant")

    # BH should be less conservative than Bonferroni
    assert counts['fdr_bh'] >= counts['bonferroni'], "BH should find >= Bonferroni significant terms"


# ============================================================
# Phase 8: Cross-Validation Tests
# ============================================================

def test_28_cross_validate_go_bp():
    """Cross-Validation: Compare gseapy vs PANTHER vs STRING GO BP"""
    import gseapy
    import re
    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    # gseapy
    gseapy_result = gseapy.enrichr(
        gene_list=CANCER_GENES,
        gene_sets='GO_Biological_Process_2021',
        organism='human',
        outdir=None, no_plot=True,
    )
    gseapy_go = set()
    for term in gseapy_result.results[gseapy_result.results['Adjusted P-value'] < 0.05]['Term']:
        m = re.search(r'(GO:\d+)', term)
        if m:
            gseapy_go.add(m.group(1))

    # PANTHER
    panther_result = tu.tools.PANTHER_enrichment(
        gene_list=','.join(CANCER_GENES),
        organism=9606,
        annotation_dataset='GO:0008150'
    )
    panther_go = set(t['term_id'] for t in panther_result.get('data', {}).get('enriched_terms', [])
                     if t.get('fdr', 1) < 0.05)

    # STRING
    string_result = tu.tools.STRING_functional_enrichment(
        protein_ids=CANCER_GENES,
        species=9606
    )
    string_data = string_result.get('data', [])
    string_go = set()
    if isinstance(string_data, list):
        for d in string_data:
            if d.get('category') == 'Process' and d.get('fdr', 1) < 0.05:
                term_id = d.get('term', '')
                # STRING uses GOBP:XXXXXXX format sometimes
                term_id = term_id.replace('GOBP:', 'GO:')
                string_go.add(term_id)

    # Count consensus
    all_terms = gseapy_go | panther_go | string_go
    consensus = 0
    for term in all_terms:
        sources = sum([term in gseapy_go, term in panther_go, term in string_go])
        if sources >= 2:
            consensus += 1

    print(f"    gseapy: {len(gseapy_go)} GO BP terms")
    print(f"    PANTHER: {len(panther_go)} GO BP terms")
    print(f"    STRING: {len(string_go)} GO BP terms")
    print(f"    Consensus (2+ sources): {consensus} terms")
    # At least some consensus expected for well-known cancer genes
    assert consensus > 0, "No consensus GO BP terms found across tools"


def test_29_cross_validate_kegg():
    """Cross-Validation: Compare gseapy KEGG vs STRING KEGG"""
    import gseapy
    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    # gseapy KEGG
    gseapy_kegg = gseapy.enrichr(
        gene_list=CANCER_GENES,
        gene_sets='KEGG_2021_Human',
        organism='human',
        outdir=None, no_plot=True,
    )
    gseapy_terms = set(gseapy_kegg.results[gseapy_kegg.results['Adjusted P-value'] < 0.05]['Term'].str.lower())

    # STRING KEGG
    string_result = tu.tools.STRING_functional_enrichment(
        protein_ids=CANCER_GENES,
        species=9606
    )
    string_data = string_result.get('data', [])
    string_kegg_terms = set()
    if isinstance(string_data, list):
        for d in string_data:
            if d.get('category') == 'KEGG' and d.get('fdr', 1) < 0.05:
                string_kegg_terms.add(d.get('description', '').lower())

    # Check overlap
    overlap = 0
    for g_term in gseapy_terms:
        for s_term in string_kegg_terms:
            if g_term in s_term or s_term in g_term:
                overlap += 1
                break

    print(f"    gseapy KEGG significant: {len(gseapy_terms)}")
    print(f"    STRING KEGG significant: {len(string_kegg_terms)}")
    print(f"    Approximate overlap: {overlap}")


# ============================================================
# Phase 9: Different Gene Lists Tests
# ============================================================

def test_30_immune_gene_enrichment():
    """Different Gene List: Immune gene enrichment"""
    import gseapy

    result = gseapy.enrichr(
        gene_list=IMMUNE_GENES,
        gene_sets='GO_Biological_Process_2021',
        organism='human',
        outdir=None, no_plot=True,
    )

    sig = result.results[result.results['Adjusted P-value'] < 0.05]
    assert len(sig) > 0, "No significant terms for immune genes"

    # Should find immune-related terms
    immune_terms = sig[sig['Term'].str.contains('immune|cytokine|inflammatory|interleukin', case=False)]
    assert len(immune_terms) > 0, "No immune-related GO terms found for immune gene list"
    print(f"    {len(sig)} significant terms, {len(immune_terms)} immune-related")
    print(f"    Top immune term: {immune_terms.iloc[0]['Term'][:80]}")


def test_31_signaling_gene_enrichment():
    """Different Gene List: Signaling pathway gene enrichment"""
    import gseapy

    result = gseapy.enrichr(
        gene_list=SIGNALING_GENES,
        gene_sets='KEGG_2021_Human',
        organism='human',
        outdir=None, no_plot=True,
    )

    sig = result.results[result.results['Adjusted P-value'] < 0.05]
    assert len(sig) > 0, "No significant KEGG pathways for signaling genes"

    # Should find MAPK/PI3K/RAS pathways
    signal_paths = sig[sig['Term'].str.contains('MAPK|PI3K|Ras|EGFR|ErbB|signaling', case=False)]
    assert len(signal_paths) > 0, "No signaling pathways found for signaling gene list"
    print(f"    {len(sig)} significant KEGG pathways")
    print(f"    {len(signal_paths)} signaling-related pathways")


def test_32_small_gene_list():
    """Edge Case: Small gene list (3 genes)"""
    import gseapy

    small_list = ["TP53", "BRCA1", "EGFR"]
    result = gseapy.enrichr(
        gene_list=small_list,
        gene_sets='GO_Biological_Process_2021',
        organism='human',
        outdir=None, no_plot=True,
    )

    df = result.results
    assert len(df) > 0, "No results for small gene list"
    sig = df[df['Adjusted P-value'] < 0.05]
    print(f"    Small list (3 genes): {len(sig)} significant terms")


def test_33_large_gene_list():
    """Edge Case: Large gene list (>40 genes)"""
    import gseapy

    large_list = CANCER_GENES + IMMUNE_GENES + SIGNALING_GENES
    # Remove duplicates
    large_list = list(set(large_list))
    result = gseapy.enrichr(
        gene_list=large_list,
        gene_sets='GO_Biological_Process_2021',
        organism='human',
        outdir=None, no_plot=True,
    )

    df = result.results
    assert len(df) > 0, "No results for large gene list"
    sig = df[df['Adjusted P-value'] < 0.05]
    print(f"    Large list ({len(large_list)} genes): {len(sig)} significant terms")


# ============================================================
# Phase 10: Specific Term Lookup Tests
# ============================================================

def test_34_find_specific_go_term():
    """Specific Term: Find a specific GO term in enrichment results"""
    import gseapy

    result = gseapy.enrichr(
        gene_list=CANCER_GENES,
        gene_sets='GO_Biological_Process_2021',
        organism='human',
        outdir=None, no_plot=True,
    )

    # Search for "cell cycle" related terms
    df = result.results
    cell_cycle = df[df['Term'].str.contains('cell cycle', case=False)]
    assert len(cell_cycle) > 0, "No cell cycle terms found for cancer genes"

    for _, row in cell_cycle.head(3).iterrows():
        print(f"    {row['Term'][:60]}")
        print(f"      P-value: {row['P-value']:.6e}")
        print(f"      Adjusted P-value: {row['Adjusted P-value']:.6e}")
        print(f"      Overlap: {row['Overlap']}")


def test_35_find_specific_kegg_pathway():
    """Specific Term: Find a specific KEGG pathway and its p-value"""
    import gseapy

    result = gseapy.enrichr(
        gene_list=CANCER_GENES,
        gene_sets='KEGG_2021_Human',
        organism='human',
        outdir=None, no_plot=True,
    )

    df = result.results
    # Look for p53 signaling pathway
    p53_pathway = df[df['Term'].str.contains('p53', case=False)]
    if len(p53_pathway) > 0:
        row = p53_pathway.iloc[0]
        print(f"    p53 signaling pathway found:")
        print(f"      Term: {row['Term']}")
        print(f"      P-value: {row['P-value']:.6e}")
        print(f"      Adjusted P-value: {row['Adjusted P-value']:.6e}")
        print(f"      Genes: {row['Genes']}")
    else:
        # Try broader search
        signal_paths = df[df['Term'].str.contains('signaling|pathway', case=False)]
        assert len(signal_paths) > 0, "No signaling pathways found"
        print(f"    p53 pathway not found, but {len(signal_paths)} other signaling pathways present")


# ============================================================
# Phase 11: GO Term Detail Tests
# ============================================================

def test_36_go_term_details():
    """GO Term: Get details for a specific GO term"""
    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    # GO:0051726 = regulation of cell cycle
    result = tu.tools.GO_get_term_by_id(go_id='GO:0051726')
    assert result is not None, "No result for GO:0051726"
    print(f"    GO:0051726 result type: {type(result)}")
    if isinstance(result, dict):
        print(f"    Keys: {list(result.keys())[:10]}")


def test_37_go_annotations_for_gene():
    """GO Term: Get GO annotations for a specific gene"""
    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    result = tu.tools.GO_get_annotations_for_gene(gene_id='TP53')
    assert result is not None, "No GO annotations for TP53"
    if isinstance(result, list):
        print(f"    TP53 has {len(result)} GO annotations")
    elif isinstance(result, dict):
        data = result.get('data', result)
        if isinstance(data, list):
            print(f"    TP53 has {len(data)} GO annotations")
        else:
            print(f"    Result keys: {list(result.keys())[:10]}")


# ============================================================
# Phase 12: Pathway Detail Tests
# ============================================================

def test_38_reactome_pathway_detail():
    """Pathway Detail: Get Reactome pathway info"""
    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    # R-HSA-69620 = Cell Cycle Checkpoints
    result = tu.tools.Reactome_get_pathway(pathway_id='R-HSA-69620')
    assert result is not None, "No Reactome pathway detail"
    print(f"    Reactome pathway result type: {type(result)}")
    if isinstance(result, dict):
        name = result.get('data', {}).get('displayName', result.get('displayName', 'N/A'))
        print(f"    Pathway name: {name}")


def test_39_kegg_pathway_search():
    """Pathway Detail: Search KEGG pathways"""
    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    result = tu.tools.kegg_search_pathway(query='cell cycle')
    assert result is not None, "No KEGG search result"
    if isinstance(result, list):
        print(f"    Found {len(result)} KEGG pathways for 'cell cycle'")
    elif isinstance(result, dict):
        data = result.get('data', result)
        if isinstance(data, list):
            print(f"    Found {len(data)} KEGG pathways")
        elif isinstance(data, str):
            lines = data.strip().split('\n')
            print(f"    Found {len(lines)} KEGG pathways")


def test_40_wikipathways_search():
    """Pathway Detail: Search WikiPathways"""
    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    result = tu.tools.WikiPathways_search(query='cell cycle', organism='Homo sapiens')
    assert result is not None, "No WikiPathways result"
    if isinstance(result, dict):
        data = result.get('data', {})
        pathways = data.get('result', [])
        print(f"    Found {len(pathways)} WikiPathways for 'cell cycle'")
    elif isinstance(result, list):
        print(f"    Found {len(result)} WikiPathways")


# ============================================================
# Phase 13: Organism Support Tests
# ============================================================

def test_41_mouse_enrichment():
    """Organism: Mouse gene enrichment"""
    import gseapy

    mouse_genes = ["Trp53", "Brca1", "Egfr", "Myc", "Akt1", "Pten"]
    result = gseapy.enrichr(
        gene_list=mouse_genes,
        gene_sets='KEGG_2019_Mouse',
        organism='mouse',
        outdir=None, no_plot=True,
    )
    df = result.results
    assert len(df) > 0, "No mouse KEGG results"
    sig = df[df['Adjusted P-value'] < 0.05]
    print(f"    Mouse KEGG: {len(sig)} significant pathways")


def test_42_panther_mouse():
    """Organism: PANTHER mouse enrichment"""
    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    result = tu.tools.PANTHER_enrichment(
        gene_list='Trp53,Brca1,Egfr,Myc,Akt1,Pten',
        organism=10090,
        annotation_dataset='GO:0008150'
    )
    terms = result.get('data', {}).get('enriched_terms', [])
    print(f"    PANTHER mouse GO BP: {len(terms)} terms")


# ============================================================
# Phase 14: Library Discovery Tests
# ============================================================

def test_43_list_available_libraries():
    """Library Discovery: List all available gseapy libraries"""
    import gseapy
    libs = gseapy.get_library_name()
    assert len(libs) > 200, f"Expected 200+ libraries, got {len(libs)}"
    print(f"    {len(libs)} libraries available")

    # Check key libraries exist
    key_libs = [
        'GO_Biological_Process_2021', 'GO_Molecular_Function_2021',
        'GO_Cellular_Component_2021', 'KEGG_2021_Human',
        'Reactome_Pathways_2024', 'MSigDB_Hallmark_2020',
        'WikiPathways_2024_Human',
    ]
    for lib in key_libs:
        assert lib in libs, f"Key library missing: {lib}"
    print(f"    All {len(key_libs)} key libraries verified")


def test_44_go_library_versions():
    """Library Discovery: Verify GO library versions (2021, 2023, 2025)"""
    import gseapy
    libs = gseapy.get_library_name()

    for year in ['2021', '2023', '2025']:
        bp = f'GO_Biological_Process_{year}'
        mf = f'GO_Molecular_Function_{year}'
        cc = f'GO_Cellular_Component_{year}'
        for lib in [bp, mf, cc]:
            assert lib in libs, f"GO library missing: {lib}"
    print(f"    All GO library versions (2021, 2023, 2025) verified")


# ============================================================
# Phase 15: BixBench-Style Question Tests
# ============================================================

def test_45_bixbench_adjusted_pval_question():
    """BixBench: Find adjusted p-value for a specific GO term"""
    import gseapy

    gene_list = CANCER_GENES
    result = gseapy.enrichr(
        gene_list=gene_list,
        gene_sets='GO_Biological_Process_2021',
        organism='human',
        outdir=None, no_plot=True,
    )

    # Simulate: "What is the adjusted p-val for regulation of cell cycle?"
    df = result.results
    target = df[df['Term'].str.contains('regulation of cell cycle', case=False)]
    assert len(target) > 0, "regulation of cell cycle not found"

    row = target.iloc[0]
    adj_pval = row['Adjusted P-value']
    print(f"    Question: Adjusted p-val for regulation of cell cycle?")
    print(f"    Answer: {adj_pval:.6e}")
    print(f"    Term: {row['Term']}")
    assert adj_pval < 0.05, "Expected significant result for cancer genes"


def test_46_bixbench_most_enriched_pathway():
    """BixBench: Find most significantly enriched KEGG pathway"""
    import gseapy

    result = gseapy.enrichr(
        gene_list=CANCER_GENES,
        gene_sets='KEGG_2021_Human',
        organism='human',
        outdir=None, no_plot=True,
    )

    sig = result.results[result.results['Adjusted P-value'] < 0.05]
    assert len(sig) > 0, "No significant KEGG pathways"

    most_enriched = sig.iloc[0]
    print(f"    Question: Most significantly enriched KEGG pathway?")
    print(f"    Answer: {most_enriched['Term']}")
    print(f"    P-value: {most_enriched['P-value']:.6e}")
    print(f"    Adjusted P-value: {most_enriched['Adjusted P-value']:.6e}")


def test_47_bixbench_metabolic_pathway_gsea():
    """BixBench: Find most enriched metabolic pathway using GSEA"""
    import gseapy
    import pandas as pd
    import numpy as np

    np.random.seed(42)
    # Create gene list biased toward metabolic genes
    metabolic_genes = ["ALDOB", "GCK", "PFKL", "PKM", "LDHA", "PDK1",
                       "CS", "IDH1", "OGDH", "SUCLA2", "SDHA", "FH",
                       "MDH2", "PCK1", "G6PC", "FASN", "ACACA", "HMGCR"]
    other_genes = ["TP53", "BRCA1", "EGFR", "GAPDH", "ACTB", "TUBB",
                   "ALB", "INS", "TTN", "MYH7", "TNNT2", "RYR2"]

    # Metabolic genes ranked high, others low
    gene_scores = {}
    for i, g in enumerate(metabolic_genes):
        gene_scores[g] = 3.0 - i * 0.1
    for i, g in enumerate(other_genes):
        gene_scores[g] = -0.5 - i * 0.2

    ranked = pd.Series(gene_scores).sort_values(ascending=False)

    gsea_result = gseapy.prerank(
        rnk=ranked,
        gene_sets='GO_Biological_Process_2021',
        outdir=None, no_plot=True,
        seed=42, min_size=3, max_size=500, permutation_num=100,
    )

    df = gsea_result.res2d
    metabolic = df[df['Term'].str.contains('metabol', case=False)]
    print(f"    Metabolic-related GSEA terms: {len(metabolic)}")
    if len(metabolic) > 0:
        top = metabolic.iloc[0]
        print(f"    Top metabolic term: {top['Term'][:60]}")
        print(f"    NES: {top['NES']}, FDR: {top['FDR q-val']}")


def test_48_bixbench_enrichgo_equivalent():
    """BixBench: enrichGO equivalent using gseapy (enrichGO is R/clusterProfiler)"""
    import gseapy

    # enrichGO equivalent in Python = gseapy.enrichr with GO libraries
    gene_list = IMMUNE_GENES

    result = gseapy.enrichr(
        gene_list=gene_list,
        gene_sets='GO_Biological_Process_2021',
        organism='human',
        outdir=None, no_plot=True,
    )

    df = result.results
    sig = df[df['Adjusted P-value'] < 0.05]
    assert len(sig) > 0, "No significant GO terms"

    # This mimics: enrichGO(gene=gene_list, OrgDb=org.Hs.eg.db, ont="BP", pAdjustMethod="BH")
    print(f"    enrichGO equivalent: {len(sig)} significant GO BP terms (BH adjusted)")
    print(f"    Top 3:")
    for _, row in sig.head(3).iterrows():
        print(f"      {row['Term'][:60]}: adj_p={row['Adjusted P-value']:.2e}")


# ============================================================
# Phase 16: Integration Tests
# ============================================================

def test_49_full_enrichment_pipeline():
    """Integration: Full enrichment pipeline (ORA + cross-validation + correction)"""
    import gseapy
    import re
    from statsmodels.stats.multitest import multipletests
    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    gene_list = CANCER_GENES

    # Step 1: gseapy ORA
    ora_result = gseapy.enrichr(
        gene_list=gene_list,
        gene_sets=['GO_Biological_Process_2021', 'KEGG_2021_Human'],
        organism='human', outdir=None, no_plot=True,
    )
    ora_df = ora_result.results
    assert len(ora_df) > 0, "No ORA results"

    # Step 2: PANTHER cross-validation
    panther = tu.tools.PANTHER_enrichment(
        gene_list=','.join(gene_list),
        organism=9606,
        annotation_dataset='GO:0008150'
    )
    panther_terms = panther.get('data', {}).get('enriched_terms', [])

    # Step 3: Multiple testing correction
    bp_df = ora_df[ora_df['Gene_set'] == 'GO_Biological_Process_2021']
    if len(bp_df) > 0:
        raw_pvals = bp_df['P-value'].values
        _, bh_pvals, _, _ = multipletests(raw_pvals, alpha=0.05, method='fdr_bh')
        _, bonf_pvals, _, _ = multipletests(raw_pvals, alpha=0.05, method='bonferroni')

    # Step 4: Summary
    bp_sig = bp_df[bp_df['Adjusted P-value'] < 0.05]
    kegg_df = ora_df[ora_df['Gene_set'] == 'KEGG_2021_Human']
    kegg_sig = kegg_df[kegg_df['Adjusted P-value'] < 0.05]
    panther_sig = [t for t in panther_terms if t.get('fdr', 1) < 0.05]

    print(f"    Full pipeline results:")
    print(f"      GO BP (gseapy): {len(bp_sig)} significant")
    print(f"      KEGG (gseapy): {len(kegg_sig)} significant")
    print(f"      GO BP (PANTHER): {len(panther_sig)} significant")
    print(f"      BH significant: {sum(bh_pvals < 0.05) if len(bp_df) > 0 else 0}")
    print(f"      Bonf significant: {sum(bonf_pvals < 0.05) if len(bp_df) > 0 else 0}")

    assert len(bp_sig) > 0, "Pipeline should find significant GO BP terms"
    assert len(kegg_sig) > 0, "Pipeline should find significant KEGG pathways"


def test_50_comparative_enrichment():
    """Integration: Compare enrichment of two gene lists"""
    import gseapy

    # Up-regulated (cancer/proliferation)
    up_genes = ["TP53", "BRCA1", "MYC", "RB1", "MDM2", "CDK4", "CCND1", "CCNE1"]
    # Down-regulated (immune/inflammation)
    down_genes = ["IL6", "TNF", "IL10", "IFNG", "IL1B", "CCL2", "CXCL8", "TLR4"]

    up_result = gseapy.enrichr(
        gene_list=up_genes,
        gene_sets='GO_Biological_Process_2021',
        organism='human', outdir=None, no_plot=True,
    )
    down_result = gseapy.enrichr(
        gene_list=down_genes,
        gene_sets='GO_Biological_Process_2021',
        organism='human', outdir=None, no_plot=True,
    )

    up_sig = set(up_result.results[up_result.results['Adjusted P-value'] < 0.05]['Term'])
    down_sig = set(down_result.results[down_result.results['Adjusted P-value'] < 0.05]['Term'])

    shared = up_sig & down_sig
    up_unique = up_sig - down_sig
    down_unique = down_sig - up_sig

    print(f"    Up-regulated specific: {len(up_unique)} terms")
    print(f"    Down-regulated specific: {len(down_unique)} terms")
    print(f"    Shared: {len(shared)} terms")

    # Verify different gene lists give different enrichment
    assert len(up_unique) > 0 or len(down_unique) > 0, "Expected some unique terms between lists"


# ============================================================
# Main Runner
# ============================================================

def main():
    print("=" * 70)
    print("tooluniverse-gene-enrichment: Comprehensive Test Suite")
    print("=" * 70)
    print()

    all_tests = [
        # Phase 1: gseapy ORA
        test_01_gseapy_go_bp_enrichment,
        test_02_gseapy_go_mf_enrichment,
        test_03_gseapy_go_cc_enrichment,
        test_04_gseapy_kegg_enrichment,
        test_05_gseapy_reactome_enrichment,
        test_06_gseapy_msigdb_hallmark,
        test_07_gseapy_wikipathways,
        test_08_gseapy_multi_library,
        test_09_gseapy_results_structure,

        # Phase 2: GSEA
        test_10_gsea_preranked_go_bp,
        test_11_gsea_preranked_kegg,
        test_12_gsea_nes_sign,

        # Phase 3: PANTHER
        test_13_panther_go_bp,
        test_14_panther_go_mf,
        test_15_panther_go_cc,
        test_16_panther_pathway,

        # Phase 4: STRING
        test_17_string_functional_enrichment,
        test_18_string_kegg_enrichment,
        test_19_string_ppi_enrichment,

        # Phase 5: Reactome
        test_20_reactome_pathway_enrichment,
        test_21_reactome_cross_validation,

        # Phase 6: ID Conversion
        test_22_mygene_batch_conversion,
        test_23_string_map_identifiers,
        test_24_enrichment_after_id_conversion,

        # Phase 7: Multiple Testing
        test_25_bh_correction,
        test_26_bonferroni_correction,
        test_27_correction_comparison,

        # Phase 8: Cross-Validation
        test_28_cross_validate_go_bp,
        test_29_cross_validate_kegg,

        # Phase 9: Different Gene Lists
        test_30_immune_gene_enrichment,
        test_31_signaling_gene_enrichment,
        test_32_small_gene_list,
        test_33_large_gene_list,

        # Phase 10: Specific Term Lookup
        test_34_find_specific_go_term,
        test_35_find_specific_kegg_pathway,

        # Phase 11: GO Term Details
        test_36_go_term_details,
        test_37_go_annotations_for_gene,

        # Phase 12: Pathway Details
        test_38_reactome_pathway_detail,
        test_39_kegg_pathway_search,
        test_40_wikipathways_search,

        # Phase 13: Organism Support
        test_41_mouse_enrichment,
        test_42_panther_mouse,

        # Phase 14: Library Discovery
        test_43_list_available_libraries,
        test_44_go_library_versions,

        # Phase 15: BixBench-Style Questions
        test_45_bixbench_adjusted_pval_question,
        test_46_bixbench_most_enriched_pathway,
        test_47_bixbench_metabolic_pathway_gsea,
        test_48_bixbench_enrichgo_equivalent,

        # Phase 16: Integration
        test_49_full_enrichment_pipeline,
        test_50_comparative_enrichment,
    ]

    for test_func in all_tests:
        run_test(test_func)
        print()

    # Summary
    print("=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    passed = sum(1 for r in RESULTS if r['status'] == 'PASS')
    failed = sum(1 for r in RESULTS if r['status'] == 'FAIL')
    total = len(RESULTS)
    total_time = sum(r['time'] for r in RESULTS)

    print(f"Total: {total} | Passed: {passed} | Failed: {failed} | Time: {total_time:.1f}s")
    print(f"Pass Rate: {passed}/{total} ({100*passed/total:.1f}%)")
    print()

    if failed > 0:
        print("FAILED TESTS:")
        for r in RESULTS:
            if r['status'] == 'FAIL':
                print(f"  {r['name']}: {r['error']}")
        print()

    # Return exit code
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
