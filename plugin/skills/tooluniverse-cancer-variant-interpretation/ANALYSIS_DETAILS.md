# Cancer Variant Interpretation - Detailed Analysis Procedures

## Phase 1: Gene Disambiguation & ID Resolution

### 1.1 MyGene ID Resolution (PRIMARY)

```python
def resolve_gene_ids(tu, gene_symbol):
    """Resolve gene symbol to Ensembl, Entrez, UniProt IDs."""
    result = tu.tools.MyGene_query_genes(query=gene_symbol, species='human')

    hits = result.get('hits', [])
    # Take the top hit where symbol matches exactly
    gene_hit = None
    for hit in hits:
        if hit.get('symbol', '').upper() == gene_symbol.upper():
            gene_hit = hit
            break
    if not gene_hit and hits:
        gene_hit = hits[0]

    ids = {
        'symbol': gene_hit.get('symbol'),
        'entrez_id': gene_hit.get('entrezgene'),
        'ensembl_id': gene_hit.get('ensembl', {}).get('gene'),
        'name': gene_hit.get('name'),
    }
    return ids
```

**Response structure**: `{took, total, max_score, hits: [{_id, _score, ensembl: {gene}, entrezgene, name, symbol}]}`

### 1.2 UniProt Accession

```python
def get_uniprot_id(tu, gene_symbol):
    """Get UniProt accession for gene."""
    result = tu.tools.UniProt_search(query=f'gene:{gene_symbol}', organism='human', limit=3)
    # Response: {total_results, returned, results: [{accession, id, protein_name, gene_names, organism, length}]}
    results = result.get('results', [])
    if results:
        return results[0].get('accession')
    return None
```

### 1.3 OpenTargets Target Resolution

```python
def get_opentargets_info(tu, gene_symbol):
    """Resolve gene to OpenTargets ensemblId and description."""
    result = tu.tools.OpenTargets_get_target_id_description_by_name(targetName=gene_symbol)
    # Response: {data: {search: {hits: [{id (ensemblId), name, description}]}}}
    hits = result.get('data', {}).get('search', {}).get('hits', [])
    for hit in hits:
        if hit.get('name', '').upper() == gene_symbol.upper():
            return hit
    return hits[0] if hits else None
```

### 1.4 Cancer Type EFO Resolution (if cancer type provided)

```python
def resolve_cancer_type(tu, cancer_type):
    """Resolve cancer type to EFO ID for OpenTargets queries."""
    result = tu.tools.OpenTargets_get_disease_id_description_by_name(diseaseName=cancer_type)
    hits = result.get('data', {}).get('search', {}).get('hits', [])
    return hits[0] if hits else None
```

### 1.5 Gene Function Context

```python
def get_gene_function(tu, uniprot_accession):
    """Get protein function from UniProt.
    NOTE: Returns a list of function description strings, NOT a dict.
    """
    result = tu.tools.UniProt_get_function_by_accession(accession=uniprot_accession)
    return result
```

### 1.6 CIViC Gene ID Resolution

**IMPORTANT**: The `civic_search_genes` tool does NOT support name filtering in its GraphQL query. To find a gene in CIViC, either:
1. Paginate through results (inefficient, genes sorted alphabetically)
2. Use the Entrez ID from MyGene to construct a CIViC gene lookup

**Workaround**: Use `civic_search_genes` with `limit=100` and search the results client-side.

**Known CIViC Gene IDs** (for common cancer genes):
| Gene | CIViC Gene ID | Entrez ID |
|------|--------------|-----------|
| BRAF | 5 | 673 |
| ABL1 | 4 | 25 |
| ALK | 1 | 238 |

---

## Phase 2: Clinical Variant Evidence (CIViC)

### 2.1 Get Gene Variants from CIViC

```python
def get_civic_variants(tu, civic_gene_id):
    """Get all variants for a gene in CIViC."""
    result = tu.tools.civic_get_variants_by_gene(gene_id=civic_gene_id, limit=200)
    variants = result.get('data', {}).get('gene', {}).get('variants', {}).get('nodes', [])
    return variants
```

### 2.2 Match Specific Variant

```python
def find_variant_in_civic(variants, variant_name):
    """Find the specific variant in CIViC results."""
    normalized = variant_name.replace('p.', '').strip()
    for v in variants:
        if v.get('name', '').upper() == normalized.upper():
            return v
    for v in variants:
        if normalized.upper() in v.get('name', '').upper():
            return v
    return None
```

### 2.3 Get Variant Details

```python
def get_variant_details(tu, variant_id):
    """Get detailed variant information from CIViC."""
    result = tu.tools.civic_get_variant(variant_id=variant_id)
    return result.get('data', {}).get('variant', {})
```

### 2.4 Get Molecular Profile Evidence

```python
def get_molecular_profile(tu, molecular_profile_id):
    """Get molecular profile details (for evidence items)."""
    result = tu.tools.civic_get_molecular_profile(molecular_profile_id=molecular_profile_id)
    return result.get('data', {}).get('molecularProfile', {})
```

### 2.5 CIViC Evidence Limitations and Fallback

The current CIViC tools return limited field sets from GraphQL. If CIViC data is sparse:
- **Fallback to literature**: Use PubMed to search for "{gene} {variant} clinical significance cancer"
- **Fallback to OpenTargets**: Use `OpenTargets_target_disease_evidence` for target-disease evidence

---

## Phase 3: Mutation Prevalence (cBioPortal)

### 3.1 Find Relevant Studies

```python
def find_cancer_studies(tu, cancer_keyword=None):
    """Find relevant cBioPortal studies."""
    result = tu.tools.cBioPortal_get_cancer_studies(limit=50)
    studies = result if isinstance(result, list) else result.get('data', [])
    if cancer_keyword:
        filtered = [s for s in studies
                    if cancer_keyword.lower() in str(s.get('name', '')).lower()
                    or cancer_keyword.lower() in str(s.get('cancerTypeId', '')).lower()]
        return filtered
    return studies
```

### 3.2 Get Mutation Data

```python
def get_mutation_prevalence(tu, gene_symbol, study_id):
    """Get mutation data for a gene in a specific study."""
    result = tu.tools.cBioPortal_get_mutations(study_id=study_id, gene_list=gene_symbol)
    if isinstance(result, list):
        mutations = result
    elif isinstance(result, dict):
        mutations = result.get('data', []) if result.get('status') == 'success' else []
    else:
        mutations = []
    return mutations
```

### 3.3 Analyze Mutation Distribution

```python
def analyze_mutation_distribution(mutations, target_variant):
    """Count how many samples have the target variant vs. others."""
    from collections import Counter
    protein_changes = [m.get('proteinChange', '') for m in mutations]
    counts = Counter(protein_changes)
    total_mutated = len(mutations)
    target_count = sum(1 for m in mutations
                       if target_variant.upper() in str(m.get('proteinChange', '')).upper())
    return {
        'total_mutated_samples': total_mutated,
        'target_variant_count': target_count,
        'target_variant_frequency': target_count / total_mutated if total_mutated > 0 else 0,
        'top_variants': counts.most_common(10),
    }
```

### Key cBioPortal Studies for Common Cancer Types

| Cancer Type | Study ID | Description |
|-------------|----------|-------------|
| Lung adenocarcinoma | luad_tcga | TCGA Lung Adenocarcinoma |
| Breast cancer | brca_tcga | TCGA Breast Cancer |
| Colorectal cancer | coadread_tcga | TCGA Colorectal |
| Melanoma | skcm_tcga | TCGA Melanoma |
| Pancreatic cancer | paad_tcga | TCGA Pancreatic |
| Glioblastoma | gbm_tcga | TCGA Glioblastoma |
| Prostate cancer | prad_tcga | TCGA Prostate |
| Ovarian cancer | ov_tcga | TCGA Ovarian |

---

## Phase 4: Therapeutic Associations

### 4.1 OpenTargets Drug-Target Associations (PRIMARY)

```python
def get_target_drugs(tu, ensembl_id, size=50):
    """Get all drugs associated with a target from OpenTargets."""
    result = tu.tools.OpenTargets_get_associated_drugs_by_target_ensemblID(
        ensemblId=ensembl_id, size=size
    )
    drugs = result.get('data', {}).get('target', {}).get('knownDrugs', {})
    rows = drugs.get('rows', [])
    approved = [r for r in rows if r.get('drug', {}).get('isApproved')]
    phase3 = [r for r in rows if r.get('phase') == 3 and not r.get('drug', {}).get('isApproved')]
    phase2 = [r for r in rows if r.get('phase') == 2]
    return {
        'total': drugs.get('count', 0),
        'approved': approved,
        'phase3': phase3,
        'phase2': phase2,
        'all_rows': rows
    }
```

### 4.2 OpenTargets Drug Mechanisms

```python
def get_drug_mechanism(tu, chembl_id):
    """Get mechanism of action for a drug."""
    result = tu.tools.OpenTargets_get_drug_mechanisms_of_action_by_chemblId(chemblId=chembl_id)
    return result
```

### 4.3 FDA Label Information

```python
def get_fda_label(tu, drug_name):
    """Get FDA-approved indications and label info."""
    indications = tu.tools.FDA_get_indications_by_drug_name(drug_name=drug_name, limit=3)
    warnings = tu.tools.FDA_get_boxed_warning_info_by_drug_name(drug_name=drug_name, limit=3)
    moa = tu.tools.FDA_get_mechanism_of_action_by_drug_name(drug_name=drug_name, limit=3)
    return {'indications': indications, 'warnings': warnings, 'mechanism': moa}
```

### 4.4 DrugBank Drug Information

```python
def get_drugbank_info(tu, drug_name):
    """Get drug information from DrugBank."""
    result = tu.tools.drugbank_get_drug_basic_info_by_drug_name_or_id(
        query=drug_name, case_sensitive=False, exact_match=False, limit=3
    )
    return result
```

### 4.5 ChEMBL Drug Mechanism

```python
def get_chembl_mechanism(tu, chembl_drug_id):
    """Get drug mechanism from ChEMBL."""
    result = tu.tools.ChEMBL_get_drug_mechanisms(drug_chembl_id__exact=chembl_drug_id, limit=10)
    return result
```

### 4.6 Disease-Specific Drug Filtering

```python
def get_disease_specific_drugs(tu, efo_id, size=30):
    """Get drugs associated with a specific disease/cancer type."""
    result = tu.tools.OpenTargets_get_associated_drugs_by_disease_efoId(efoId=efo_id, size=size)
    return result
```

---

## Phase 5: Resistance Mechanisms

### 5.1 CIViC Resistance Evidence

Search CIViC for variants with resistance significance for the target gene. Get all variants and look for those with "Resistance" in the name or description.

### 5.2 Literature-Based Resistance Search

```python
def search_resistance_literature(tu, gene_symbol, drug_name):
    """Search PubMed for resistance mechanisms.
    NOTE: PubMed returns a plain list of article dicts, NOT {articles: [...]}.
    """
    result = tu.tools.PubMed_search_articles(
        query=f'"{gene_symbol}" AND "{drug_name}" AND resistance AND mechanism',
        limit=15, include_abstract=True
    )
    articles = result if isinstance(result, list) else result.get('articles', []) if isinstance(result, dict) else []
    return articles
```

### 5.3 Pathway-Based Bypass Resistance

```python
def get_bypass_pathways(tu, uniprot_id):
    """Get pathways that could mediate bypass resistance."""
    result = tu.tools.Reactome_map_uniprot_to_pathways(id=uniprot_id)
    return result
```

### Known Resistance Patterns (Reference)

| Primary Target | Primary Drug | Resistance Mutation | Mechanism | Strategy |
|---------------|-------------|-------------------|-----------|----------|
| EGFR L858R | Erlotinib/Gefitinib | T790M | Steric hindrance | Osimertinib (3rd-gen TKI) |
| EGFR T790M | Osimertinib | C797S | Covalent bond loss | 4th-gen TKI trials |
| BRAF V600E | Vemurafenib | Splice variants | Paradoxical activation | BRAF+MEK combination |
| ALK fusion | Crizotinib | L1196M, G1269A | Kinase domain mutations | Alectinib, Lorlatinib |
| KRAS G12C | Sotorasib | Y96D, R68S | Drug binding loss | KRAS G12C combo trials |

---

## Phase 6: Clinical Trials

### 6.1 Search Strategy

```python
def find_clinical_trials(tu, gene_symbol, variant_name, cancer_type=None):
    """Find clinical trials for this mutation."""
    query1 = f'{gene_symbol} {variant_name}'
    result1 = tu.tools.search_clinical_trials(
        query_term=query1, condition=cancer_type or 'cancer', pageSize=20
    )
    result2 = tu.tools.search_clinical_trials(
        query_term=f'{gene_symbol} mutation',
        condition=cancer_type or 'cancer', pageSize=20
    )
    return {'variant_specific': result1, 'gene_level': result2}
```

**Response structure**: `{studies: [{NCT ID, brief_title, brief_summary, overall_status, condition, phase}], nextPageToken, total_count}`

### 6.2 Trial Filtering

Prioritize trials that:
1. Are **RECRUITING** or **NOT_YET_RECRUITING** status
2. Match the specific variant (not just gene)
3. Are Phase 2 or 3 (closer to approval)
4. Have the right cancer type

---

## Phase 7: Prognostic Impact & Pathway Context

### 7.1 Literature Evidence

```python
def get_prognostic_literature(tu, gene_symbol, variant_name, cancer_type=None):
    """Search for prognostic associations."""
    query = f'"{gene_symbol}" "{variant_name}" prognosis survival'
    if cancer_type:
        query += f' "{cancer_type}"'
    result = tu.tools.PubMed_search_articles(query=query, limit=10, include_abstract=True)
    return result
```

### 7.2 Pathway Context (Reactome)

```python
def get_pathway_context(tu, uniprot_id):
    """Get pathway context from Reactome."""
    result = tu.tools.Reactome_map_uniprot_to_pathways(id=uniprot_id)
    return result
```

### 7.3 Gene Expression (GTEx)

```python
def get_expression_context(tu, ensembl_id):
    """Get tissue expression data from GTEx."""
    gene_info = tu.tools.ensembl_lookup_gene(gene_id=ensembl_id, species='homo_sapiens')
    data = gene_info.get('data', gene_info) if isinstance(gene_info, dict) else {}
    version = data.get('version', 1)
    versioned_id = f"{ensembl_id}.{version}"
    result = tu.tools.GTEx_get_median_gene_expression(
        gencode_id=versioned_id, operation='median'
    )
    return result
```

### 7.4 UniProt Disease Variants

```python
def get_known_disease_variants(tu, uniprot_accession):
    """Get known disease-associated variants from UniProt."""
    result = tu.tools.UniProt_get_disease_variants_by_accession(accession=uniprot_accession)
    return result
```
