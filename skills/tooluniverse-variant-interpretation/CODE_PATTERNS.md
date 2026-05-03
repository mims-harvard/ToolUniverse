# Code Patterns for Variant Interpretation

Reusable code patterns for each phase of the variant interpretation workflow.

---

## Phase 2: Clinical Database Code Patterns

### 2.1 COSMIC Somatic Context

```python
def get_somatic_context(tu, gene_symbol, variant_aa):
    """Get somatic mutation context from COSMIC."""

    # Search for specific mutation
    cosmic = tu.tools.COSMIC_search_mutations(
        operation="search",
        terms=f"{gene_symbol} {variant_aa}",
        max_results=20,
        genome_build=38
    )

    # Get all gene mutations for context
    gene_mutations = tu.tools.COSMIC_get_mutations_by_gene(
        operation="get_by_gene",
        gene=gene_symbol,
        max_results=100
    )

    # Determine if it's a hotspot
    mutation_counts = Counter(m['MutationAA'] for m in gene_mutations.get('results', []))
    is_hotspot = variant_aa in [m[0] for m in mutation_counts.most_common(10)]

    return {
        'cosmic_hits': cosmic.get('results', []),
        'is_somatic_hotspot': is_hotspot,
        'cancer_types': [m['PrimarySite'] for m in cosmic.get('results', [])],
        'total_cosmic_count': cosmic.get('total_count', 0)
    }
```

### 2.2 OMIM Gene-Disease Context

```python
def get_omim_context(tu, gene_symbol):
    """Get OMIM gene-disease associations."""

    search = tu.tools.OMIM_search(
        operation="search",
        query=gene_symbol,
        limit=5
    )

    omim_data = []
    for entry in search.get('data', {}).get('entries', []):
        mim = entry.get('mimNumber')

        details = tu.tools.OMIM_get_entry(
            operation="get_entry",
            mim_number=str(mim)
        )

        synopsis = tu.tools.OMIM_get_clinical_synopsis(
            operation="get_clinical_synopsis",
            mim_number=str(mim)
        )

        omim_data.append({
            'mim_number': mim,
            'title': details.get('data', {}).get('titles', {}),
            'inheritance': synopsis.get('data', {}).get('inheritance'),
            'clinical_features': synopsis.get('data', {})
        })

    return omim_data
```

### 2.3 DisGeNET Gene-Disease Evidence

```python
def get_disgenet_context(tu, gene_symbol, variant_rsid=None):
    """Get gene-disease associations from DisGeNET."""

    gda = tu.tools.DisGeNET_search_gene(
        operation="search_gene",
        gene=gene_symbol,
        limit=20
    )

    vda = None
    if variant_rsid:
        vda = tu.tools.DisGeNET_get_vda(
            operation="get_vda",
            variant=variant_rsid,
            limit=20
        )

    return {
        'gene_associations': gda.get('data', {}).get('associations', []),
        'variant_associations': vda.get('data', {}).get('associations', []) if vda else []
    }
```

### 2.4 ClinGen Gene Validity & Dosage Sensitivity

```python
def get_clingen_evidence(tu, gene_symbol):
    """
    Get ClinGen gene validity and dosage sensitivity data.
    CRITICAL for ACMG classification - establishes gene-disease validity.
    """

    validity = tu.tools.ClinGen_search_gene_validity(gene=gene_symbol)

    validity_data = []
    if validity.get('data'):
        for entry in validity.get('data', []):
            validity_data.append({
                'disease': entry.get('Disease Label'),
                'classification': entry.get('Classification'),
                'inheritance': entry.get('Inheritance'),
                'mondo_id': entry.get('Disease ID (MONDO)')
            })

    dosage = tu.tools.ClinGen_search_dosage_sensitivity(gene=gene_symbol)

    dosage_data = {}
    if dosage.get('data'):
        for entry in dosage.get('data', []):
            dosage_data = {
                'haploinsufficiency_score': entry.get('Haploinsufficiency Score'),
                'triplosensitivity_score': entry.get('Triplosensitivity Score'),
                'disease': entry.get('Disease')
            }
            break

    actionability = tu.tools.ClinGen_search_actionability(gene=gene_symbol)

    return {
        'gene_validity': validity_data,
        'dosage_sensitivity': dosage_data,
        'actionability': actionability.get('data', {}),
        'has_definitive_validity': any(v['classification'] == 'Definitive' for v in validity_data),
        'is_haploinsufficient': dosage_data.get('haploinsufficiency_score') == '3'
    }
```

### 2.5 SpliceAI Splice Variant Prediction

```python
def get_spliceai_prediction(tu, chrom, pos, ref, alt, genome="38"):
    """
    Get SpliceAI splice effect predictions.

    Delta scores: DS_AG (Acceptor gain), DS_AL (Acceptor loss),
                  DS_DG (Donor gain), DS_DL (Donor loss)
    """

    variant = f"chr{chrom}-{pos}-{ref}-{alt}"

    result = tu.tools.SpliceAI_predict_splice(
        variant=variant,
        genome=genome
    )

    if result.get('data'):
        max_score = result['data'].get('max_delta_score', 0)
        interpretation = result['data'].get('interpretation', '')

        if max_score >= 0.8:
            acmg = 'PP3 (strong) - high splice impact'
        elif max_score >= 0.5:
            acmg = 'PP3 (supporting) - moderate splice impact'
        elif max_score >= 0.2:
            acmg = 'PP3 (weak) - possible splice impact'
        else:
            acmg = 'BP7 (if synonymous) - splice benign'

        return {
            'max_delta_score': max_score,
            'interpretation': interpretation,
            'acmg_support': acmg,
            'scores': result['data'].get('scores', [])
        }
    return None

def quick_splice_check(tu, variant, genome="38"):
    """Quick triage using max delta score only."""
    result = tu.tools.SpliceAI_get_max_delta(variant=variant, genome=genome)
    return result.get('data', {})
```

**When to Use SpliceAI**:
- Intronic variants near splice sites (+/-50bp)
- Synonymous variants (may still affect splicing)
- Exonic variants near splice junctions
- Variants creating cryptic splice sites

---

## Phase 2.5: Regulatory Context (Non-Coding Variants)

```python
def assess_regulatory_impact(tu, variant_position, gene_symbol):
    """Assess regulatory impact of non-coding variant."""

    tf_binding = tu.tools.ChIPAtlas_enrichment_analysis(
        gene=gene_symbol,
        cell_type="all"
    )

    peaks = tu.tools.ChIPAtlas_get_peak_data(
        gene=gene_symbol,
        experiment_type="TF"
    )

    encode_data = tu.tools.ENCODE_search_experiments(
        assay_title="ATAC-seq",
        biosample="all"
    )

    binding_disrupted = check_motif_disruption(variant_position, peaks)

    return {
        'tf_binding': tf_binding,
        'regulatory_peaks': peaks,
        'encode_annotations': encode_data,
        'likely_regulatory': binding_disrupted
    }
```

---

## Phase 3: Computational Predictions

### 3.1 CADD Scoring

```python
def get_cadd_score(tu, chrom, pos, ref, alt):
    """Get CADD deleteriousness score for a variant."""

    result = tu.tools.CADD_get_variant_score(
        chrom=str(chrom),
        pos=pos,
        ref=ref,
        alt=alt,
        version="GRCh38-v1.7"
    )

    if result.get('status') == 'success':
        phred = result['data'].get('phred_score')
        return {
            'score': phred,
            'interpretation': result['data'].get('interpretation'),
            'acmg_support': 'PP3' if phred >= 20 else ('BP4' if phred < 15 else 'neutral')
        }
    return None
```

### 3.2 AlphaMissense Pathogenicity

```python
def get_alphamissense_score(tu, uniprot_id, variant):
    """
    Get AlphaMissense pathogenicity score.
    variant format: 'R123H' or 'p.R123H'

    Thresholds: Pathogenic >0.564, Ambiguous 0.34-0.564, Benign <0.34
    """

    result = tu.tools.AlphaMissense_get_variant_score(
        uniprot_id=uniprot_id,
        variant=variant
    )

    if result.get('status') == 'success' and result.get('data'):
        score = result['data'].get('pathogenicity_score')
        classification = result['data'].get('classification')

        if classification == 'pathogenic':
            acmg = 'PP3 (strong)'
        elif classification == 'benign':
            acmg = 'BP4 (strong)'
        else:
            acmg = 'neutral'

        return {
            'score': score,
            'classification': classification,
            'acmg_support': acmg
        }
    return None
```

### 3.3 EVE Evolutionary Prediction

```python
def get_eve_score(tu, chrom, pos, ref, alt):
    """Get EVE evolutionary pathogenicity score. Threshold: >0.5 = likely pathogenic."""

    result = tu.tools.EVE_get_variant_score(
        chrom=str(chrom), pos=pos, ref=ref, alt=alt
    )

    if result.get('status') == 'success':
        eve_scores = result['data'].get('eve_scores', [])
        if eve_scores:
            best_score = eve_scores[0]
            return {
                'score': best_score.get('eve_score'),
                'classification': best_score.get('classification'),
                'gene': best_score.get('gene_symbol'),
                'acmg_support': 'PP3' if best_score.get('eve_score', 0) > 0.5 else 'BP4'
            }
    return None
```

### 3.4 Integrated Prediction Strategy

```python
def comprehensive_pathogenicity_assessment(tu, variant_info):
    """Combine all prediction tools for robust classification."""
    chrom = variant_info['chrom']
    pos = variant_info['pos']
    ref = variant_info['ref']
    alt = variant_info['alt']
    uniprot_id = variant_info.get('uniprot_id')
    aa_change = variant_info.get('aa_change')

    predictions = {}

    cadd = get_cadd_score(tu, chrom, pos, ref, alt)
    if cadd:
        predictions['cadd'] = cadd

    if uniprot_id and aa_change:
        am = get_alphamissense_score(tu, uniprot_id, aa_change)
        if am:
            predictions['alphamissense'] = am

    eve = get_eve_score(tu, chrom, pos, ref, alt)
    if eve:
        predictions['eve'] = eve

    damaging_count = sum(1 for p in predictions.values()
                         if 'PP3' in p.get('acmg_support', ''))
    benign_count = sum(1 for p in predictions.values()
                       if 'BP4' in p.get('acmg_support', ''))

    if damaging_count >= 2 and benign_count == 0:
        consensus = 'likely_damaging'
        acmg = 'PP3 (multiple predictors concordant)'
    elif benign_count >= 2 and damaging_count == 0:
        consensus = 'likely_benign'
        acmg = 'BP4 (multiple predictors concordant)'
    else:
        consensus = 'uncertain'
        acmg = 'neutral (discordant predictions)'

    return {
        'predictions': predictions,
        'consensus': consensus,
        'acmg_recommendation': acmg
    }
```

---

## Phase 4: Structural Analysis (AlphaFold2)

```python
# 1. Get protein sequence
protein_seq = tu.tools.UniProt_get_protein_sequence(accession=uniprot_id)

# 2. Get/predict structure
try:
    pdb_hits = tu.tools.PDBe_get_uniprot_mappings(uniprot_id=uniprot_id)
    structure = tu.tools.PDB_get_structure(pdb_id=pdb_hits[0]['pdb_id'])
except:
    structure = tu.tools.NvidiaNIM_alphafold2(
        sequence=protein_seq['sequence'],
        algorithm="mmseqs2"
    )

# 3. Analyze variant position
# - Extract pLDDT at residue position
# - Calculate solvent accessibility
# - Check for nearby functional sites
```

**Structural Features to Report**:
- pLDDT at variant position
- Secondary structure (helix/sheet/coil)
- Solvent accessibility (buried/exposed)
- Distance to active site (if applicable)
- Interactions disrupted (H-bonds, salt bridges)

---

## Phase 4.5: Expression Context

```python
def validate_expression_context(tu, gene_symbol, phenotype_tissues):
    """Validate gene is expressed in phenotype-relevant tissues."""

    sc_expression = tu.tools.CELLxGENE_get_expression_data(
        gene=gene_symbol,
        tissue=phenotype_tissues[0] if phenotype_tissues else "all"
    )

    gtex = tu.tools.GTEx_get_median_gene_expression(gene=gene_symbol)

    relevant_expression = {
        tissue: gtex.get(tissue, 0)
        for tissue in phenotype_tissues
    }

    return {
        'single_cell': sc_expression,
        'gtex': relevant_expression,
        'expressed_in_phenotype_tissue': any(v > 1 for v in relevant_expression.values())
    }
```

---

## Phase 5: Literature Search

```python
def comprehensive_literature_search(tu, gene, variant, phenotype):
    """Search across all literature sources."""

    pubmed = tu.tools.PubMed_search_articles(
        query=f'"{gene}" AND ("{variant}" OR functional)',
        max_results=30
    )

    biorxiv = tu.tools.BioRxiv_list_recent_preprints(
        query=f"{gene} {phenotype}",
        limit=10
    )

    medrxiv = tu.tools.MedRxiv_get_preprint(
        query=f"{gene} variant {phenotype}",
        limit=10
    )

    key_papers = pubmed[:5]
    for paper in key_papers:
        citations = tu.tools.openalex_search_works(
            query=paper['title'],
            limit=1
        )
        paper['citation_count'] = citations[0].get('cited_by_count', 0) if citations else 0

    return {
        'pubmed': pubmed,
        'preprints': biorxiv + medrxiv,
        'key_papers_with_citations': key_papers
    }
```

**Search Query Templates**:
```
# Gene + variant specific
"{GENE} AND ({HGVS_p} OR {AA_change})"

# Functional studies
"{GENE} AND (functional OR functional study OR mutagenesis)"

# Clinical reports
"{GENE} AND (case report OR patient) AND {phenotype}"

# Preprint-specific
"{GENE} genetics 2024" (for recent preprints)
```

**Warning**: Always flag preprints as NOT peer-reviewed in reports.
