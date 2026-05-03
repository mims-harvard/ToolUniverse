# Diagnostic Workflow: Detailed Procedures

Detailed diagnostic algorithms, code examples, and phase-by-phase procedures for the Rare Disease Diagnosis skill.

---

## Phase 1: Phenotype Standardization

### 1.1 Convert Symptoms to HPO Terms

```python
def standardize_phenotype(tu, symptoms_list):
    """Convert clinical descriptions to HPO terms."""
    hpo_terms = []

    for symptom in symptoms_list:
        # Search HPO for matching terms
        results = tu.tools.HPO_search_terms(query=symptom)
        if results:
            hpo_terms.append({
                'original': symptom,
                'hpo_id': results[0]['id'],
                'hpo_name': results[0]['name'],
                'confidence': 'exact' if symptom.lower() in results[0]['name'].lower() else 'partial'
            })

    return hpo_terms
```

### 1.2 Phenotype Categories

| Category | Examples | Weight |
|----------|----------|--------|
| **Core features** | Always present in disease | High |
| **Variable features** | Present in >50% | Medium |
| **Occasional features** | Present in <50% | Low |
| **Age-specific** | Onset-dependent | Context |

---

## Phase 2: Disease Matching

### 2.1 Orphanet Disease Search

```python
def match_diseases_orphanet(tu, symptom_keywords):
    """Find rare diseases matching symptoms using Orphanet."""
    candidate_diseases = []

    # Search Orphanet by disease keywords
    for keyword in symptom_keywords:
        results = tu.tools.Orphanet_search_diseases(
            operation="search_diseases",
            query=keyword
        )
        if results.get('status') == 'success':
            candidate_diseases.extend(results['data']['results'])

    # Get genes for each disease
    for disease in candidate_diseases:
        orpha_code = disease.get('ORPHAcode')
        genes = tu.tools.Orphanet_get_genes(
            operation="get_genes",
            orpha_code=orpha_code
        )
        disease['genes'] = genes.get('data', {}).get('genes', [])

    return deduplicate_and_rank(candidate_diseases)
```

### 2.2 OMIM Cross-Reference

```python
def cross_reference_omim(tu, orphanet_diseases, gene_symbols):
    """Get OMIM details for diseases and genes."""
    omim_data = {}

    for gene in gene_symbols:
        search_result = tu.tools.OMIM_search(
            operation="search",
            query=gene,
            limit=5
        )
        if search_result.get('status') == 'success':
            for entry in search_result['data'].get('entries', []):
                mim_number = entry.get('mimNumber')

                details = tu.tools.OMIM_get_entry(
                    operation="get_entry",
                    mim_number=str(mim_number)
                )

                synopsis = tu.tools.OMIM_get_clinical_synopsis(
                    operation="get_clinical_synopsis",
                    mim_number=str(mim_number)
                )

                omim_data[gene] = {
                    'mim_number': mim_number,
                    'details': details.get('data', {}),
                    'clinical_synopsis': synopsis.get('data', {})
                }

    return omim_data
```

### 2.3 DisGeNET Gene-Disease Associations

```python
def get_gene_disease_associations(tu, gene_symbols):
    """Get gene-disease associations from DisGeNET."""
    associations = {}

    for gene in gene_symbols:
        result = tu.tools.DisGeNET_search_gene(
            operation="search_gene",
            gene=gene,
            limit=20
        )

        if result.get('status') == 'success':
            associations[gene] = result['data'].get('associations', [])

    return associations

def get_disease_genes_disgenet(tu, disease_name):
    """Get all genes associated with a disease."""
    result = tu.tools.DisGeNET_search_disease(
        operation="search_disease",
        disease=disease_name,
        limit=30
    )
    return result.get('data', {}).get('associations', [])
```

### 2.4 Phenotype Overlap Scoring

| Match Level | Score | Criteria |
|-------------|-------|----------|
| **Excellent** | >80% | Most core + variable features match |
| **Good** | 60-80% | Core features match, some variable |
| **Possible** | 40-60% | Some overlap, needs consideration |
| **Unlikely** | <40% | Poor phenotype fit |

---

## Phase 3: Gene Panel Identification

### 3.1 Extract Disease Genes

```python
def build_gene_panel(tu, candidate_diseases):
    """Build prioritized gene panel from candidate diseases."""
    genes = {}

    for disease in candidate_diseases:
        for gene in disease['genes']:
            if gene not in genes:
                genes[gene] = {
                    'symbol': gene,
                    'diseases': [],
                    'evidence_level': 'unknown'
                }
            genes[gene]['diseases'].append(disease['name'])

    return genes
```

### 3.2 ClinGen Gene-Disease Validity Check

**Critical**: Always verify gene-disease validity through ClinGen before including in panel.

```python
def get_clingen_gene_evidence(tu, gene_symbol):
    """
    Get ClinGen gene-disease validity and dosage sensitivity.
    ESSENTIAL for rare disease gene panel prioritization.
    """

    # 1. Gene-disease validity classification
    validity = tu.tools.ClinGen_search_gene_validity(gene=gene_symbol)

    validity_levels = []
    diseases_with_validity = []
    if validity.get('data'):
        for entry in validity.get('data', []):
            validity_levels.append(entry.get('Classification'))
            diseases_with_validity.append({
                'disease': entry.get('Disease Label'),
                'mondo_id': entry.get('Disease ID (MONDO)'),
                'classification': entry.get('Classification'),
                'inheritance': entry.get('Inheritance')
            })

    # 2. Dosage sensitivity (critical for CNV interpretation)
    dosage = tu.tools.ClinGen_search_dosage_sensitivity(gene=gene_symbol)

    hi_score = None
    ts_score = None
    if dosage.get('data'):
        for entry in dosage.get('data', []):
            hi_score = entry.get('Haploinsufficiency Score')
            ts_score = entry.get('Triplosensitivity Score')
            break

    # 3. Clinical actionability (return of findings context)
    actionability = tu.tools.ClinGen_search_actionability(gene=gene_symbol)
    is_actionable = (actionability.get('adult_count', 0) > 0 or
                     actionability.get('pediatric_count', 0) > 0)

    # Determine best evidence level
    level_priority = ['Definitive', 'Strong', 'Moderate', 'Limited', 'Disputed', 'Refuted']
    best_level = 'Not curated'
    for level in level_priority:
        if level in validity_levels:
            best_level = level
            break

    return {
        'gene': gene_symbol,
        'evidence_level': best_level,
        'diseases_curated': diseases_with_validity,
        'haploinsufficiency_score': hi_score,
        'triplosensitivity_score': ts_score,
        'is_actionable': is_actionable,
        'include_in_panel': best_level in ['Definitive', 'Strong', 'Moderate']
    }

def prioritize_genes_with_clingen(tu, gene_list):
    """Prioritize genes using ClinGen evidence levels."""

    prioritized = []
    for gene in gene_list:
        evidence = get_clingen_gene_evidence(tu, gene)

        score = 0
        if evidence['evidence_level'] == 'Definitive':
            score = 5
        elif evidence['evidence_level'] == 'Strong':
            score = 4
        elif evidence['evidence_level'] == 'Moderate':
            score = 3
        elif evidence['evidence_level'] == 'Limited':
            score = 1

        if evidence['haploinsufficiency_score'] == '3':
            score += 1
        if evidence['is_actionable']:
            score += 1

        prioritized.append({
            **evidence,
            'priority_score': score
        })

    return sorted(prioritized, key=lambda x: x['priority_score'], reverse=True)
```

**ClinGen Classification Impact on Panel**:

| Classification | Include in Panel? | Priority |
|----------------|-------------------|----------|
| **Definitive** | YES - mandatory | Highest |
| **Strong** | YES - highly recommended | High |
| **Moderate** | YES | Medium |
| **Limited** | Include but flag | Low |
| **Disputed** | Exclude or separate | Avoid |
| **Refuted** | EXCLUDE | Do not test |
| **Not curated** | Use other evidence | Variable |

### 3.3 Gene Prioritization Criteria

| Priority | Criteria | Points |
|----------|----------|--------|
| **Tier 1** | Gene causes #1 ranked disease | +5 |
| **Tier 2** | Gene causes multiple candidates | +3 |
| **Tier 3** | ClinGen "Definitive" evidence | +3 |
| **Tier 4** | Expressed in affected tissue | +2 |
| **Tier 5** | Constraint score pLI >0.9 | +1 |

### 3.4 Expression Validation

```python
def validate_expression(tu, gene_symbol, affected_tissue):
    """Check if gene is expressed in relevant tissue."""
    gene_info = tu.tools.MyGene_query_genes(q=gene_symbol, species="human")
    ensembl_id = gene_info.get('ensembl', {}).get('gene')

    expression = tu.tools.GTEx_get_median_gene_expression(
        gencode_id=f"{ensembl_id}.latest"
    )

    return expression.get(affected_tissue, 0) > 1  # TPM > 1
```

---

## Phase 3.5: Expression & Tissue Context

### Cell-Type Specific Expression (CELLxGENE)

```python
def get_cell_type_expression(tu, gene_symbol, affected_tissues):
    """Get single-cell expression to validate tissue relevance."""

    expression = tu.tools.CELLxGENE_get_expression_data(
        gene=gene_symbol,
        tissue=affected_tissues[0] if affected_tissues else "all"
    )

    cell_metadata = tu.tools.CELLxGENE_get_cell_metadata(
        gene=gene_symbol
    )

    high_expression = [
        ct for ct in expression
        if ct.get('mean_expression', 0) > 1.0
    ]

    return {
        'expression_data': expression,
        'high_expression_cells': high_expression,
        'total_cell_types': len(cell_metadata)
    }
```

### Regulatory Context (ChIPAtlas)

```python
def get_regulatory_context(tu, gene_symbol):
    """Get transcription factor binding for candidate genes."""

    tf_binding = tu.tools.ChIPAtlas_enrichment_analysis(
        gene=gene_symbol,
        cell_type="all"
    )

    peaks = tu.tools.ChIPAtlas_get_peak_data(
        gene=gene_symbol,
        experiment_type="TF"
    )

    return {
        'transcription_factors': tf_binding,
        'regulatory_peaks': peaks
    }
```

---

## Phase 3.6: Pathway Analysis

### KEGG Pathway Context

```python
def get_pathway_context(tu, gene_symbols):
    """Get pathway context for candidate genes."""

    pathways = {}
    for gene in gene_symbols:
        kegg_genes = tu.tools.kegg_find_genes(query=f"hsa:{gene}")

        if kegg_genes:
            gene_info = tu.tools.kegg_get_gene_info(gene_id=kegg_genes[0]['id'])
            pathways[gene] = gene_info.get('pathways', [])

    return pathways
```

### Protein-Protein Interactions (IntAct)

```python
def get_protein_interactions(tu, gene_symbol):
    """Get interaction partners for candidate genes."""

    interactions = tu.tools.intact_search_interactions(
        query=gene_symbol,
        species="human"
    )

    network = tu.tools.intact_get_interaction_network(
        gene=gene_symbol,
        depth=1
    )

    return {
        'interactions': interactions,
        'network': network,
        'interactor_count': len(interactions)
    }
```

---

## Phase 4: Variant Interpretation

### 4.1 ClinVar Lookup

```python
def interpret_variant(tu, variant_hgvs):
    """Get ClinVar interpretation for variant."""
    result = tu.tools.ClinVar_search_variants(query=variant_hgvs)

    return {
        'clinvar_id': result.get('id'),
        'classification': result.get('clinical_significance'),
        'review_status': result.get('review_status'),
        'conditions': result.get('conditions'),
        'last_evaluated': result.get('last_evaluated')
    }
```

### 4.2 Population Frequency

```python
def check_population_frequency(tu, variant_id):
    """Get gnomAD allele frequency."""
    freq = tu.tools.gnomAD_get_variant_frequencies(variant_id=variant_id)

    if freq['allele_frequency'] < 0.00001:
        rarity = "Ultra-rare"
    elif freq['allele_frequency'] < 0.0001:
        rarity = "Rare"
    elif freq['allele_frequency'] < 0.01:
        rarity = "Low frequency"
    else:
        rarity = "Common (likely benign)"

    return freq, rarity
```

### 4.3 Computational Pathogenicity Prediction

Use multiple prediction tools for VUS interpretation:

```python
def comprehensive_vus_prediction(tu, variant_info):
    """
    Combine multiple prediction tools for VUS classification.
    Critical for rare disease variants not in ClinVar.
    """
    predictions = {}

    # 1. CADD - Deleteriousness
    cadd = tu.tools.CADD_get_variant_score(
        chrom=variant_info['chrom'],
        pos=variant_info['pos'],
        ref=variant_info['ref'],
        alt=variant_info['alt'],
        version="GRCh38-v1.7"
    )
    if cadd.get('status') == 'success':
        predictions['cadd'] = {
            'score': cadd['data'].get('phred_score'),
            'interpretation': cadd['data'].get('interpretation'),
            'acmg': 'PP3' if cadd['data'].get('phred_score', 0) >= 20 else 'neutral'
        }

    # 2. AlphaMissense - DeepMind pathogenicity
    if variant_info.get('uniprot_id') and variant_info.get('aa_change'):
        am = tu.tools.AlphaMissense_get_variant_score(
            uniprot_id=variant_info['uniprot_id'],
            variant=variant_info['aa_change']
        )
        if am.get('status') == 'success' and am.get('data'):
            classification = am['data'].get('classification')
            predictions['alphamissense'] = {
                'score': am['data'].get('pathogenicity_score'),
                'classification': classification,
                'acmg': 'PP3 (strong)' if classification == 'pathogenic' else (
                    'BP4 (strong)' if classification == 'benign' else 'neutral'
                )
            }

    # 3. EVE - Evolutionary prediction
    eve = tu.tools.EVE_get_variant_score(
        chrom=variant_info['chrom'],
        pos=variant_info['pos'],
        ref=variant_info['ref'],
        alt=variant_info['alt']
    )
    if eve.get('status') == 'success':
        eve_scores = eve['data'].get('eve_scores', [])
        if eve_scores:
            predictions['eve'] = {
                'score': eve_scores[0].get('eve_score'),
                'classification': eve_scores[0].get('classification'),
                'acmg': 'PP3' if eve_scores[0].get('eve_score', 0) > 0.5 else 'BP4'
            }

    # 4. SpliceAI - Splice variant prediction
    variant_str = f"chr{variant_info['chrom']}-{variant_info['pos']}-{variant_info['ref']}-{variant_info['alt']}"
    splice = tu.tools.SpliceAI_predict_splice(
        variant=variant_str,
        genome="38"
    )
    if splice.get('data'):
        max_score = splice['data'].get('max_delta_score', 0)
        interpretation = splice['data'].get('interpretation', '')

        if max_score >= 0.8:
            splice_acmg = 'PP3 (strong) - high splice impact'
        elif max_score >= 0.5:
            splice_acmg = 'PP3 (moderate) - splice impact'
        elif max_score >= 0.2:
            splice_acmg = 'PP3 (supporting) - possible splice effect'
        else:
            splice_acmg = 'BP7 (if synonymous) - no splice impact'

        predictions['spliceai'] = {
            'max_delta_score': max_score,
            'interpretation': interpretation,
            'scores': splice['data'].get('scores', []),
            'acmg': splice_acmg
        }

    # Consensus for PP3/BP4
    damaging = sum(1 for p in predictions.values() if 'PP3' in p.get('acmg', ''))
    benign = sum(1 for p in predictions.values() if 'BP4' in p.get('acmg', ''))

    return {
        'predictions': predictions,
        'consensus': {
            'damaging_count': damaging,
            'benign_count': benign,
            'pp3_applicable': damaging >= 2 and benign == 0,
            'bp4_applicable': benign >= 2 and damaging == 0
        }
    }
```

### 4.4 ACMG Classification Criteria

| Evidence Type | Criteria | Weight |
|---------------|----------|--------|
| **PVS1** | Null variant in gene where LOF is mechanism | Very Strong |
| **PS1** | Same amino acid change as established pathogenic | Strong |
| **PM2** | Absent from population databases | Moderate |
| **PP3** | Computational evidence supports deleterious (AlphaMissense, CADD, EVE, SpliceAI) | Supporting |
| **BA1** | Allele frequency >5% | Benign standalone |

**Enhanced PP3 Evidence**:
- **AlphaMissense pathogenic** (>0.564) = Strong PP3 support (~90% accuracy)
- **CADD >=20** + **EVE >0.5** = Multiple concordant predictions
- Agreement from 2+ predictors strengthens PP3 evidence

---

## Phase 5: Structure Analysis for VUS

### 5.1 When to Perform Structure Analysis

Perform when:
- Variant is VUS or conflicting interpretations
- Missense variant in critical domain
- Novel variant not in databases
- Additional evidence needed for classification

### 5.2 Structure Prediction (NVIDIA NIM)

```python
def analyze_variant_structure(tu, protein_sequence, variant_position):
    """Predict structure and analyze variant impact."""

    structure = tu.tools.NvidiaNIM_alphafold2(
        sequence=protein_sequence,
        algorithm="mmseqs2",
        relax_prediction=False
    )

    variant_plddt = get_residue_plddt(structure, variant_position)
    confidence = "High" if variant_plddt > 70 else "Low"

    return {
        'structure': structure,
        'variant_plddt': variant_plddt,
        'confidence': confidence
    }
```

### 5.3 Domain Impact Assessment

```python
def assess_domain_impact(tu, uniprot_id, variant_position):
    """Check if variant affects functional domain."""

    domains = tu.tools.InterPro_get_protein_domains(accession=uniprot_id)

    for domain in domains:
        if domain['start'] <= variant_position <= domain['end']:
            return {
                'in_domain': True,
                'domain_name': domain['name'],
                'domain_function': domain['description']
            }

    return {'in_domain': False}
```

---

## Phase 6: Literature Evidence

### 6.1 Published Literature (PubMed)

```python
def search_disease_literature(tu, disease_name, genes):
    """Search for relevant published literature."""

    disease_papers = tu.tools.PubMed_search_articles(
        query=f'"{disease_name}" AND (genetics OR mutation OR variant)',
        limit=20
    )

    gene_papers = []
    for gene in genes[:5]:
        papers = tu.tools.PubMed_search_articles(
            query=f'"{gene}" AND rare disease AND pathogenic',
            limit=10
        )
        gene_papers.extend(papers)

    return {
        'disease_literature': disease_papers,
        'gene_literature': gene_papers
    }
```

### 6.2 Preprint Literature (BioRxiv/MedRxiv)

```python
def search_preprints(tu, disease_name, genes):
    """Search preprints for cutting-edge findings."""

    biorxiv = tu.tools.BioRxiv_list_recent_preprints(
        query=f"{disease_name} genetics",
        limit=10
    )

    arxiv = tu.tools.ArXiv_search_papers(
        query=f"rare disease diagnosis {' OR '.join(genes[:3])}",
        category="q-bio",
        limit=5
    )

    return {
        'biorxiv': biorxiv,
        'arxiv': arxiv
    }
```

### 6.3 Citation Analysis (OpenAlex)

```python
def analyze_citations(tu, key_papers):
    """Analyze citation network for key papers."""

    citation_analysis = []
    for paper in key_papers[:5]:
        work = tu.tools.openalex_search_works(
            query=paper['title'],
            limit=1
        )
        if work:
            citation_analysis.append({
                'title': paper['title'],
                'citations': work[0].get('cited_by_count', 0),
                'year': work[0].get('publication_year')
            })

    return citation_analysis
```
