# Matching Algorithms

Detailed algorithms for patient profile standardization, biomarker parsing, molecular eligibility matching, and drug-biomarker alignment.

## Phase 1: Patient Profile Standardization

### 1.1 Disease Resolution

```python
def resolve_disease(tu, disease_name):
    """Resolve disease name to EFO ID and standard terminology."""
    # OpenTargets disease search
    result = tu.tools.OpenTargets_get_disease_id_description_by_name(diseaseName=disease_name)
    hits = result.get('data', {}).get('search', {}).get('hits', [])

    if hits:
        disease_info = hits[0]
        return {
            'efo_id': disease_info.get('id'),
            'name': disease_info.get('name'),
            'description': disease_info.get('description'),
            'original_input': disease_name
        }

    # Fallback: OLS EFO search
    ols_result = tu.tools.ols_search_efo_terms(query=disease_name, limit=5)
    ols_terms = ols_result.get('data', {}).get('terms', [])
    if ols_terms:
        term = ols_terms[0]
        return {
            'efo_id': term.get('short_form'),
            'name': term.get('label'),
            'description': term.get('description', [''])[0] if term.get('description') else '',
            'original_input': disease_name
        }

    return {'efo_id': None, 'name': disease_name, 'description': '', 'original_input': disease_name}
```

### 1.2 Gene/Biomarker Resolution

```python
def resolve_gene(tu, gene_symbol):
    """Resolve gene symbol to cross-database IDs."""
    alias_map = {
        'HER2': 'ERBB2', 'HER-2': 'ERBB2',
        'PD-L1': 'CD274', 'PDL1': 'CD274',
        'PD-1': 'PDCD1', 'PD1': 'PDCD1',
        'VEGF': 'VEGFA',
    }
    normalized = alias_map.get(gene_symbol.upper(), gene_symbol)

    result = tu.tools.MyGene_query_genes(query=normalized, species='human')
    hits = result.get('hits', [])

    gene_hit = None
    for hit in hits:
        if hit.get('symbol', '').upper() == normalized.upper():
            gene_hit = hit
            break
    if not gene_hit and hits:
        gene_hit = hits[0]

    if gene_hit:
        ensembl = gene_hit.get('ensembl', {})
        ensembl_id = ensembl.get('gene') if isinstance(ensembl, dict) else (ensembl[0].get('gene') if isinstance(ensembl, list) and ensembl else None)
        return {
            'symbol': gene_hit.get('symbol'),
            'entrez_id': gene_hit.get('entrezgene'),
            'ensembl_id': ensembl_id,
            'name': gene_hit.get('name'),
            'original_input': gene_symbol
        }

    return {'symbol': gene_symbol, 'entrez_id': None, 'ensembl_id': None, 'name': None, 'original_input': gene_symbol}
```

### 1.3 Biomarker Actionability Classification

```python
def classify_biomarker_actionability(tu, gene_symbol, alteration):
    """Classify biomarker as FDA-approved, guideline, or investigational."""
    fda_result = tu.tools.fda_pharmacogenomic_biomarkers()
    fda_biomarkers = fda_result.get('results', [])

    fda_match = [b for b in fda_biomarkers if gene_symbol.upper() in str(b.get('Biomarker', '')).upper()]

    if fda_match:
        return {
            'level': 'FDA-approved',
            'drugs': [b.get('Drug') for b in fda_match],
            'labeling_sections': [b.get('LabelingSection') for b in fda_match]
        }

    return {'level': 'investigational', 'drugs': [], 'labeling_sections': []}
```

### 1.4 Biomarker Parsing

```python
def parse_biomarker(biomarker_text):
    """Parse free-text biomarker into structured components."""
    import re

    # Pattern: "GENE VARIANT" (e.g., "EGFR L858R")
    mutation_match = re.match(r'(\w+)\s+([A-Z]\d+[A-Z])', biomarker_text, re.IGNORECASE)
    if mutation_match:
        return {'gene': mutation_match.group(1), 'alteration': mutation_match.group(2), 'type': 'mutation'}

    # Pattern: "GENE exon N deletion/insertion"
    exon_match = re.match(r'(\w+)\s+exon\s+(\d+)\s+(\w+)', biomarker_text, re.IGNORECASE)
    if exon_match:
        return {'gene': exon_match.group(1), 'alteration': f'exon {exon_match.group(2)} {exon_match.group(3)}', 'type': 'exon_alteration'}

    # Pattern: "GENE1-GENE2 fusion" or "GENE1/GENE2"
    fusion_match = re.match(r'(\w+)[-/](\w+)\s*(fusion)?', biomarker_text, re.IGNORECASE)
    if fusion_match:
        return {'gene': fusion_match.group(2), 'alteration': f'{fusion_match.group(1)}-{fusion_match.group(2)}', 'type': 'fusion', 'partner': fusion_match.group(1)}

    # Pattern: "GENE amplification"
    amp_match = re.match(r'(\w+)\s+amplification', biomarker_text, re.IGNORECASE)
    if amp_match:
        return {'gene': amp_match.group(1), 'alteration': 'amplification', 'type': 'amplification'}

    # Pattern: "PD-L1 XX%"
    expression_match = re.match(r'([\w-]+)\s+(\d+%|high|low|positive|negative)', biomarker_text, re.IGNORECASE)
    if expression_match:
        return {'gene': expression_match.group(1), 'alteration': expression_match.group(2), 'type': 'expression'}

    # Pattern: "MSI-high", "TMB-high"
    status_match = re.match(r'(MSI|TMB|dMMR|MMR)[-\s]*(high|low|stable|deficient|proficient)', biomarker_text, re.IGNORECASE)
    if status_match:
        return {'gene': status_match.group(1), 'alteration': status_match.group(2), 'type': 'status'}

    # Fallback
    return {'gene': biomarker_text.split()[0], 'alteration': ' '.join(biomarker_text.split()[1:]), 'type': 'unknown'}
```

### Gene Symbol Normalization

| Common Alias | Official Symbol | Notes |
|-------------|----------------|-------|
| HER2 | ERBB2 | Search both in trials |
| PD-L1 | CD274 | Often searched as "PD-L1" in trials |
| ALK | ALK | EML4-ALK is a fusion |
| VEGF | VEGFA | Often searched as "VEGF" |
| PD-1 | PDCD1 | Search as "PD-1" in trials |
| BRCA | BRCA1/BRCA2 | Specify which BRCA gene |

### Biomarker Parsing Rules

| Input Format | Parsed As | Example |
|-------------|-----------|---------|
| Gene + amino acid change | Specific mutation | EGFR L858R |
| Gene + exon notation | Exon-level alteration | EGFR exon 19 deletion |
| Gene + fusion partner | Fusion | EML4-ALK fusion |
| Gene + amplification | Copy number gain | HER2 amplification |
| Gene + expression level | Expression biomarker | PD-L1 50% |
| Gene + status | Status biomarker | MSI-high, TMB-high |
| Gene + resistance | Resistance mutation | EGFR T790M |

## Phase 4: Molecular Eligibility Matching

### Extract Biomarker Requirements from Eligibility Text

```python
def extract_biomarker_requirements(eligibility_text):
    """Extract biomarker requirements from eligibility criteria text."""
    import re

    requirements = {
        'required_biomarkers': [],
        'excluded_biomarkers': [],
        'biomarker_agnostic': False
    }

    if not eligibility_text:
        return requirements

    text_upper = eligibility_text.upper()

    inclusion_section = eligibility_text.split('Exclusion Criteria')[0] if 'Exclusion Criteria' in eligibility_text else eligibility_text
    exclusion_section = eligibility_text.split('Exclusion Criteria')[1] if 'Exclusion Criteria' in eligibility_text else ''

    gene_patterns = [
        r'(?:EGFR|KRAS|BRAF|ALK|ROS1|RET|MET|NTRK|HER2|ERBB2|PIK3CA|BRCA|PD-?L1|MSI|TMB|dMMR)',
    ]

    for pattern in gene_patterns:
        for match in re.finditer(pattern, inclusion_section, re.IGNORECASE):
            gene = match.group(0).upper()
            context = inclusion_section[max(0, match.start()-100):match.end()+100]
            requirements['required_biomarkers'].append({
                'gene': gene,
                'context': context.strip()
            })

        for match in re.finditer(pattern, exclusion_section, re.IGNORECASE):
            gene = match.group(0).upper()
            context = exclusion_section[max(0, match.start()-100):match.end()+100]
            requirements['excluded_biomarkers'].append({
                'gene': gene,
                'context': context.strip()
            })

    basket_terms = ['tumor-agnostic', 'histology-independent', 'basket', 'any solid tumor', 'all comers', 'biomarker-selected']
    if any(term in text_upper.lower() for term in basket_terms):
        requirements['biomarker_agnostic'] = True

    return requirements
```

## Phase 5: Drug-Biomarker Alignment

### Get Drug Mechanism Info

```python
def get_drug_mechanism_info(tu, drug_name):
    """Get drug mechanism, targets, and approval status."""
    result = tu.tools.OpenTargets_get_drug_id_description_by_name(drugName=drug_name)
    hits = result.get('data', {}).get('search', {}).get('hits', [])

    if not hits:
        return {'drug_name': drug_name, 'chembl_id': None, 'mechanisms': [], 'is_approved': False}

    drug_info = hits[0]
    chembl_id = drug_info.get('id')

    moa_result = tu.tools.OpenTargets_get_drug_mechanisms_of_action_by_chemblId(chemblId=chembl_id)
    moa_rows = moa_result.get('data', {}).get('drug', {}).get('mechanismsOfAction', {}).get('rows', [])

    mechanisms = []
    for row in moa_rows:
        targets = row.get('targets', [])
        mechanisms.append({
            'mechanism': row.get('mechanismOfAction'),
            'action_type': row.get('actionType'),
            'target_name': row.get('targetName'),
            'target_genes': [t.get('approvedSymbol') for t in targets]
        })

    return {
        'drug_name': drug_name,
        'chembl_id': chembl_id,
        'description': drug_info.get('description'),
        'mechanisms': mechanisms,
        'is_approved': 'approved' in drug_info.get('description', '').lower()
    }
```

### FDA Approval Evidence

```python
def check_fda_approval(tu, drug_name, disease_name):
    """Check FDA approval status and labeled indications."""
    result = tu.tools.FDA_get_indications_by_drug_name(drug_name=drug_name, limit=3)

    indications = result.get('results', [])
    for ind in indications:
        ind_text = str(ind.get('indications_and_usage', ''))
        if any(term.lower() in ind_text.lower() for term in disease_name.split()):
            return {
                'approved': True,
                'indication_text': ind_text[:500],
                'brand_name': ind.get('openfda.brand_name', []),
                'evidence_tier': 'T1'
            }

    return {'approved': False, 'indication_text': '', 'brand_name': [], 'evidence_tier': 'T3'}
```

### Literature Evidence

```python
def get_literature_evidence(tu, gene, alteration, drug_name, disease_name):
    """Search PubMed for evidence of drug efficacy for this biomarker."""
    query = f'{gene} {alteration} {drug_name} {disease_name} clinical trial'
    result = tu.tools.PubMed_search_articles(query=query, max_results=5)
    articles = result if isinstance(result, list) else result.get('articles', [])
    return articles
```

### CIViC Evidence

```python
def get_civic_evidence(tu, gene_symbol, civic_gene_id):
    """Get CIViC clinical evidence for gene variants."""
    if not civic_gene_id:
        return []
    result = tu.tools.civic_get_variants_by_gene(gene_id=civic_gene_id, limit=100)
    variants = result.get('data', {}).get('gene', {}).get('variants', {}).get('nodes', [])
    return variants
```
