# SV Analysis Procedures

Detailed implementation guidance for each phase of the structural variant analysis workflow. These are pseudocode examples showing how to use ToolUniverse tools for SV interpretation.

---

## Phase 2: Gene Content Analysis

### Gene Categories

1. **Fully contained genes** - Entire gene within SV boundaries
   - Deletion: Complete loss of one copy (haploinsufficiency)
   - Duplication: Extra copy (triplosensitivity)

2. **Partially disrupted genes** - Breakpoint within gene
   - Likely loss-of-function for affected allele
   - Check if critical domains disrupted

3. **Flanking genes** - Within 1 Mb of breakpoints
   - May be affected by position effects
   - Regulatory disruption possible

### Implementation

```python
def analyze_gene_content(tu, chrom, sv_start, sv_end, sv_type):
    """
    Identify and annotate all genes within SV region.
    """
    genes = {
        'fully_contained': [],
        'partially_disrupted': [],
        'flanking': []
    }

    for gene in genes_in_region:
        gene_start = gene['start']
        gene_end = gene['end']

        if gene_start >= sv_start and gene_end <= sv_end:
            gene_info = annotate_gene(tu, gene['symbol'])
            genes['fully_contained'].append(gene_info)
        elif (gene_start < sv_start < gene_end) or (gene_start < sv_end < gene_end):
            gene_info = annotate_gene(tu, gene['symbol'])
            genes['partially_disrupted'].append(gene_info)
        elif abs(gene_start - sv_end) < 1000000 or abs(gene_end - sv_start) < 1000000:
            gene_info = annotate_gene(tu, gene['symbol'])
            genes['flanking'].append(gene_info)

    return genes

def annotate_gene(tu, gene_symbol):
    """Comprehensive gene annotation."""
    omim = tu.tools.OMIM_search(operation="search", query=gene_symbol, limit=5)
    disgenet = tu.tools.DisGeNET_search_gene(operation="search_gene", gene=gene_symbol, limit=10)
    ncbi = tu.tools.NCBIGene_search(term=gene_symbol, organism="human")
    return {'symbol': gene_symbol, 'omim': omim, 'disgenet': disgenet, 'ncbi': ncbi}
```

---

## Phase 3: Dosage Sensitivity Assessment

### Implementation

```python
def assess_dosage_sensitivity(tu, gene_list):
    """Assess dosage sensitivity for all genes in SV."""
    dosage_data = []

    for gene_symbol in gene_list:
        # ClinGen dosage sensitivity (gold standard)
        clingen = tu.tools.ClinGen_search_dosage_sensitivity(gene=gene_symbol)
        hi_score, ts_score = None, None
        if clingen.get('data'):
            for entry in clingen['data']:
                hi_score = entry.get('Haploinsufficiency Score')
                ts_score = entry.get('Triplosensitivity Score')
                break

        # ClinGen gene validity
        validity = tu.tools.ClinGen_search_gene_validity(gene=gene_symbol)
        validity_level = None
        if validity.get('data'):
            for entry in validity['data']:
                validity_level = entry.get('Classification')
                break

        # OMIM inheritance pattern
        omim = tu.tools.OMIM_search(operation="search", query=gene_symbol, limit=3)

        dosage_data.append({
            'gene': gene_symbol,
            'hi_score': hi_score,
            'ts_score': ts_score,
            'validity_level': validity_level,
            'is_dosage_sensitive': (hi_score == '3' or ts_score == '3'),
        })

    return dosage_data
```

---

## Phase 4: Population Frequency Assessment

### Implementation

```python
def assess_population_frequency(tu, chrom, sv_start, sv_end, sv_type):
    """Check population databases for overlapping SVs."""
    # ClinVar for known pathogenic/benign SVs
    clinvar = tu.tools.ClinVar_search_variants(
        chromosome=str(chrom), start=sv_start, stop=sv_end, variant_type=sv_type.upper()
    )

    known_svs = []
    if clinvar.get('data'):
        for variant in clinvar['data']:
            known_svs.append({
                'database': 'ClinVar',
                'classification': variant.get('clinical_significance'),
                'review_status': variant.get('review_status'),
            })

    # DECIPHER for similar patient cases
    decipher_search = tu.tools.DECIPHER_search(
        query=f"chr{chrom}:{sv_start}-{sv_end}", search_type="region"
    )

    return {
        'clinvar_matches': known_svs,
        'decipher_cases': decipher_search.get('data', []),
        'frequency_interpretation': interpret_frequency(known_svs)
    }

def interpret_frequency(known_svs):
    """Interpret frequency based on ClinVar matches."""
    if any(sv['classification'] == 'Benign' for sv in known_svs):
        return {'acmg_code': 'BA1 or BS1', 'interpretation': 'Likely benign'}
    elif any(sv['classification'] == 'Pathogenic' for sv in known_svs):
        return {'acmg_code': 'PS1', 'interpretation': 'Pathogenic match found'}
    else:
        return {'acmg_code': 'PM2', 'interpretation': 'Rare, not in databases'}
```

---

## Phase 5: Pathogenicity Scoring

### Implementation

```python
def calculate_pathogenicity_score(gene_content, dosage_data, frequency_data, clinical_data):
    """Calculate comprehensive pathogenicity score (0-10 scale)."""
    breakdown = {}

    # Gene content scoring (max 40 pts -> scaled to 4)
    gene_score = 0
    for gene in gene_content['fully_contained'] + gene_content['partially_disrupted']:
        dosage_info = next((d for d in dosage_data if d['gene'] == gene['symbol']), None)
        if dosage_info:
            if dosage_info['hi_score'] == '3': gene_score += 10
            elif dosage_info['hi_score'] == '2': gene_score += 5
            elif gene.get('omim_disease'): gene_score += 2
    breakdown['gene_content'] = min(gene_score, 40) / 40 * 4

    # Dosage sensitivity scoring (max 30 pts -> scaled to 3)
    definitive = sum(1 for d in dosage_data if d['hi_score'] == '3')
    if definitive >= 2: dosage_score = 30
    elif definitive == 1: dosage_score = 20
    else: dosage_score = sum(1 for d in dosage_data if d['hi_score'] == '2') * 5
    breakdown['dosage_sensitivity'] = min(dosage_score, 30) / 30 * 3

    # Population frequency scoring (max 20 pts -> scaled to 2)
    freq = frequency_data.get('frequency')
    if freq is None: freq_score = 20
    elif freq < 0.0001: freq_score = 10
    elif freq > 0.01: freq_score = -20
    else: freq_score = 0
    breakdown['population_frequency'] = freq_score / 20 * 2

    # Clinical evidence scoring (max 10 pts -> scaled to 1)
    if clinical_data.get('clinvar_pathogenic'): clinical_score = 10
    elif clinical_data.get('decipher_matching_phenotype'): clinical_score = 8
    elif clinical_data.get('literature_support'): clinical_score = 5
    else: clinical_score = 0
    breakdown['clinical_evidence'] = min(clinical_score, 10) / 10

    total = sum(breakdown.values())
    total = max(0, min(10, total))
    return {'total_score': round(total, 1), 'breakdown': breakdown}
```

---

## Phase 6: Literature Search

### Search Strategies

```python
def comprehensive_literature_search(tu, genes, sv_type, phenotype):
    """Search literature for SV evidence."""
    literature = []
    for gene in genes:
        dosage_papers = tu.tools.PubMed_search_articles(
            query=f'"{gene}" AND (haploinsufficiency OR dosage sensitivity OR deletion syndrome)',
            max_results=20
        )
        case_papers = tu.tools.PubMed_search_articles(
            query=f'"{gene}" AND deletion AND {phenotype}', max_results=15
        )
        literature.append({'gene': gene, 'dosage_papers': dosage_papers, 'case_reports': case_papers})

    # DECIPHER cases
    decipher_cases = [tu.tools.DECIPHER_search(query=gene, search_type="gene") for gene in genes]

    return {'gene_literature': literature, 'decipher_cases': decipher_cases}
```

---

## Phase 7: ACMG Classification

### Implementation

```python
def apply_acmg_criteria(gene_content, dosage_data, frequency_data, clinical_data, inheritance):
    """Apply ACMG SV criteria and calculate classification."""
    evidence = {'pathogenic': [], 'benign': []}

    # PVS1: Complete deletion of HI gene
    hi_genes = [d for d in dosage_data if d['hi_score'] == '3']
    if hi_genes and gene_content['fully_contained']:
        evidence['pathogenic'].append({'code': 'PVS1', 'strength': 'Very Strong',
            'rationale': f"Complete deletion of HI gene(s): {', '.join(g['gene'] for g in hi_genes)}"})

    # PS1: Same as known pathogenic SV
    if clinical_data.get('clinvar_pathogenic_match'):
        evidence['pathogenic'].append({'code': 'PS1', 'strength': 'Strong',
            'rationale': f">=70% overlap with ClinVar pathogenic SV"})

    # PS2: De novo with phenotype match
    if inheritance == 'de_novo' and clinical_data.get('phenotype_match'):
        evidence['pathogenic'].append({'code': 'PS2', 'strength': 'Strong',
            'rationale': "De novo with consistent phenotype"})

    # PM2: Absent from controls
    if frequency_data.get('frequency') is None or frequency_data.get('frequency') == 0:
        evidence['pathogenic'].append({'code': 'PM2', 'strength': 'Moderate',
            'rationale': "Absent from gnomAD SV and DGV"})

    # PP4: Phenotype consistent
    if clinical_data.get('phenotype_consistent'):
        evidence['pathogenic'].append({'code': 'PP4', 'strength': 'Supporting',
            'rationale': "Patient phenotype consistent with gene-disease association"})

    # BA1/BS1: Common variant
    freq = frequency_data.get('frequency', 0)
    if freq > 0.05:
        evidence['benign'].append({'code': 'BA1', 'strength': 'Stand-Alone',
            'rationale': f"Frequency {freq:.3f} too high"})
    elif freq > 0.01:
        evidence['benign'].append({'code': 'BS1', 'strength': 'Strong',
            'rationale': f"Frequency {freq:.3f} exceeds expected"})

    return {'evidence': evidence, 'classification': determine_classification(evidence)}

def determine_classification(evidence):
    """Apply ACMG classification rules."""
    path = evidence['pathogenic']
    ben = evidence['benign']

    vs = len([e for e in path if e['strength'] == 'Very Strong'])
    s_p = len([e for e in path if e['strength'] == 'Strong'])
    m_p = len([e for e in path if e['strength'] == 'Moderate'])
    sup_p = len([e for e in path if e['strength'] == 'Supporting'])
    sa_b = len([e for e in ben if e['strength'] == 'Stand-Alone'])
    s_b = len([e for e in ben if e['strength'] == 'Strong'])
    sup_b = len([e for e in ben if e['strength'] == 'Supporting'])

    if sa_b >= 1: return 'Benign'
    if s_b >= 2: return 'Benign'
    if s_b >= 1 and sup_b >= 1: return 'Likely Benign'
    if sup_b >= 2: return 'Likely Benign'
    if vs >= 1 and s_p >= 1: return 'Pathogenic'
    if s_p >= 2: return 'Pathogenic'
    if vs >= 1 and m_p >= 1: return 'Likely Pathogenic'
    if s_p >= 1 and m_p >= 2: return 'Likely Pathogenic'
    if s_p >= 1 and m_p >= 1 and sup_p >= 1: return 'Likely Pathogenic'
    if m_p >= 3: return 'Likely Pathogenic'
    return 'VUS'
```
