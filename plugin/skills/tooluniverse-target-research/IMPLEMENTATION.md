# Target Intelligence Implementation Details

Detailed code implementations for each research path. See SKILL.md for the workflow overview.

## Identifier Resolution

**CRITICAL**: Resolve ALL identifiers before any research path.

```python
def resolve_target_ids(tu, query):
    """
    Resolve target query to ALL needed identifiers.
    Returns dict with: query, uniprot, ensembl, ensembl_version, symbol,
    entrez, chembl_target, hgnc
    """
    ids = {
        'query': query,
        'uniprot': None,
        'ensembl': None,
        'ensembl_versioned': None,  # For GTEx
        'symbol': None,
        'entrez': None,
        'chembl_target': None,
        'hgnc': None,
        'full_name': None,
        'synonyms': []
    }

    # [Resolution logic based on input type]
    # ... (see current implementation)

    # CRITICAL: Get versioned Ensembl ID for GTEx
    if ids['ensembl']:
        gene_info = tu.tools.ensembl_lookup_gene(id=ids['ensembl'], species="human")
        if gene_info and gene_info.get('version'):
            ids['ensembl_versioned'] = f"{ids['ensembl']}.{gene_info['version']}"

        # Also get synonyms for literature collision detection
        ids['full_name'] = gene_info.get('description', '').split(' [')[0]

    # Get UniProt alternative names for synonyms
    if ids['uniprot']:
        alt_names = tu.tools.UniProt_get_alternative_names_by_accession(accession=ids['uniprot'])
        if alt_names:
            ids['synonyms'].extend(alt_names)

    return ids
```

## GPCR Target Detection

~35% of approved drugs target GPCRs. After identifier resolution, check if target is a GPCR:

```python
def check_gpcr_target(tu, ids):
    """
    Check if target is a GPCR and retrieve specialized data.
    Call after identifier resolution.
    """
    symbol = ids.get('symbol', '')

    # Build GPCRdb entry name
    entry_name = f"{symbol.lower()}_human"

    gpcr_info = tu.tools.GPCRdb_get_protein(
        operation="get_protein",
        protein=entry_name
    )

    if gpcr_info.get('status') == 'success':
        # Target is a GPCR - get specialized data
        structures = tu.tools.GPCRdb_get_structures(
            operation="get_structures",
            protein=entry_name
        )
        ligands = tu.tools.GPCRdb_get_ligands(
            operation="get_ligands",
            protein=entry_name
        )
        mutations = tu.tools.GPCRdb_get_mutations(
            operation="get_mutations",
            protein=entry_name
        )

        return {
            'is_gpcr': True,
            'gpcr_family': gpcr_info['data'].get('family'),
            'gpcr_class': gpcr_info['data'].get('receptor_class'),
            'structures': structures.get('data', {}).get('structures', []),
            'ligands': ligands.get('data', {}).get('ligands', []),
            'mutations': mutations.get('data', {}).get('mutations', []),
            'ballesteros_numbering': True
        }

    return {'is_gpcr': False}
```

**GPCRdb Report Section** (add to Section 2 for GPCR targets):

```markdown
### 2.x GPCR-Specific Data (GPCRdb)

**Receptor Class**: Class A (Rhodopsin-like)
**GPCR Family**: Adrenoceptors

**Structures by State**:
| PDB ID | State | Resolution | Ligand | Year |
|--------|-------|------------|--------|------|
| 3SN6 | Active | 3.2A | Agonist (BI-167107) | 2011 |
| 2RH1 | Inactive | 2.4A | Antagonist (carazolol) | 2007 |

**Known Ligands**: 45 agonists, 32 antagonists, 8 allosteric modulators
**Key Binding Site Residues** (Ballesteros-Weinstein): 3.32, 5.42, 6.48, 7.39
```

## Collision Detection for Literature Search

Before literature search, detect naming collisions:

```python
def detect_collisions(tu, symbol, full_name):
    """
    Detect if gene symbol has naming collisions in literature.
    Returns negative filter terms if collisions found.
    """
    results = tu.tools.PubMed_search_articles(
        query=f'"{symbol}"[Title]',
        limit=20
    )

    off_topic_terms = []
    for paper in results.get('articles', []):
        title = paper.get('title', '').lower()
        bio_terms = ['protein', 'gene', 'cell', 'expression', 'mutation', 'kinase', 'receptor']
        if not any(term in title for term in bio_terms):
            pass  # Extract potential collision terms

    collision_filter = ""
    if off_topic_terms:
        collision_filter = " NOT " + " NOT ".join(off_topic_terms)

    return collision_filter
```

## PATH 0: Open Targets Foundation

```python
def path_0_open_targets(tu, ids):
    """
    Open Targets foundation data - fills gaps for sections 5, 6, 8, 9, 10, 11.
    ALWAYS run this first.
    """
    ensembl_id = ids['ensembl']
    if not ensembl_id:
        return {'status': 'skipped', 'reason': 'No Ensembl ID'}

    results = {}

    # 1. Diseases & Phenotypes (Section 8)
    diseases = tu.tools.OpenTargets_get_diseases_phenotypes_by_target_ensemblId(
        ensemblId=ensembl_id
    )
    results['diseases'] = diseases if diseases else {'note': 'No disease associations returned'}

    # 2. Tractability (Section 9)
    tractability = tu.tools.OpenTargets_get_target_tractability_by_ensemblId(
        ensemblId=ensembl_id
    )
    results['tractability'] = tractability if tractability else {'note': 'No tractability data returned'}

    # 3. Safety Profile (Section 10)
    safety = tu.tools.OpenTargets_get_target_safety_profile_by_ensemblId(
        ensemblId=ensembl_id
    )
    results['safety'] = safety if safety else {'note': 'No safety liabilities identified'}

    # 4. Interactions (Section 6)
    interactions = tu.tools.OpenTargets_get_target_interactions_by_ensemblId(
        ensemblId=ensembl_id
    )
    results['interactions'] = interactions if interactions else {'note': 'No interactions returned'}

    # 5. GO Annotations (Section 5)
    go_terms = tu.tools.OpenTargets_get_target_gene_ontology_by_ensemblId(
        ensemblId=ensembl_id
    )
    results['go_terms'] = go_terms if go_terms else {'note': 'No GO annotations returned'}

    # 6. Publications (Section 11)
    publications = tu.tools.OpenTargets_get_publications_by_target_ensemblId(
        ensemblId=ensembl_id
    )
    results['publications'] = publications if publications else {'note': 'No publications returned'}

    # 7. Mouse Models (Section 8/10)
    mouse_models = tu.tools.OpenTargets_get_biological_mouse_models_by_ensemblId(
        ensemblId=ensembl_id
    )
    results['mouse_models'] = mouse_models if mouse_models else {'note': 'No mouse model data returned'}

    # 8. Chemical Probes (Section 9)
    probes = tu.tools.OpenTargets_get_chemical_probes_by_target_ensemblId(
        ensemblId=ensembl_id
    )
    results['chemical_probes'] = probes if probes else {'note': 'No chemical probes available'}

    # 9. Associated Drugs (Section 9)
    drugs = tu.tools.OpenTargets_get_associated_drugs_by_target_ensemblId(
        ensemblId=ensembl_id
    )
    results['drugs'] = drugs if drugs else {'note': 'No approved/trial drugs found'}

    return results
```

### Negative Results Are Data

Always document when a query returns empty:

```markdown
### 9.3 Chemical Probes

**Status**: No validated chemical probes available for this target.
*Source: OpenTargets_get_chemical_probes_by_target_ensemblId returned empty*

**Implication**: Tool compound development would be needed for chemical biology studies.
```

## PATH 2: Structure & Domains (3-Step Chain)

**Do NOT rely solely on PDB text search.** Use this chain:

```python
def path_structure_robust(tu, ids):
    """Robust structure search using 3-step chain."""
    structures = {'pdb': [], 'alphafold': None, 'domains': [], 'method_notes': []}

    # STEP 1: UniProt PDB Cross-References (most reliable)
    if ids['uniprot']:
        entry = tu.tools.UniProt_get_entry_by_accession(accession=ids['uniprot'])
        pdb_xrefs = [x for x in entry.get('uniProtKBCrossReferences', [])
                    if x.get('database') == 'PDB']
        for xref in pdb_xrefs:
            pdb_id = xref.get('id')
            pdb_info = tu.tools.get_protein_metadata_by_pdb_id(pdb_id=pdb_id)
            if pdb_info:
                structures['pdb'].append(pdb_info)
        structures['method_notes'].append(f"Step 1: {len(pdb_xrefs)} PDB cross-refs from UniProt")

    # STEP 2: Sequence-based PDB Search (catches missing annotations)
    if ids['uniprot'] and len(structures['pdb']) < 5:
        sequence = tu.tools.UniProt_get_sequence_by_accession(accession=ids['uniprot'])
        if sequence and len(sequence) < 1000:
            similar = tu.tools.PDB_search_similar_structures(
                sequence=sequence[:500],
                identity_cutoff=0.7
            )
            if similar:
                for hit in similar[:10]:
                    if hit['pdb_id'] not in [s.get('pdb_id') for s in structures['pdb']]:
                        structures['pdb'].append(hit)
        structures['method_notes'].append(f"Step 2: Sequence search (identity >= 70%)")

    # STEP 3: Domain-based Search (for multi-domain proteins)
    if ids['uniprot']:
        domains = tu.tools.InterPro_get_protein_domains(uniprot_accession=ids['uniprot'])
        structures['domains'] = domains if domains else []

    # AlphaFold (always check)
    alphafold = tu.tools.alphafold_get_prediction(uniprot_accession=ids['uniprot'])
    structures['alphafold'] = alphafold if alphafold else {'note': 'No AlphaFold prediction'}

    # Document limitations
    if not structures['pdb']:
        structures['limitation'] = "No direct PDB hit does NOT mean no structure exists. Check: (1) structures under different UniProt entries, (2) homolog structures, (3) domain-only structures."

    return structures
```

## PATH 5: Expression Profile (GTEx Versioned ID Fallback)

```python
def path_expression(tu, ids):
    """Expression data with GTEx versioned ID fallback."""
    results = {'gtex': None, 'hpa': None, 'failed_tools': []}

    ensembl_id = ids['ensembl']
    versioned_id = ids.get('ensembl_versioned')

    # Try unversioned first
    gtex_result = tu.tools.GTEx_get_median_gene_expression(
        gencode_id=ensembl_id,
        operation="median"
    )

    # Fallback to versioned if empty
    if not gtex_result or gtex_result.get('data') == []:
        if versioned_id:
            gtex_result = tu.tools.GTEx_get_median_gene_expression(
                gencode_id=versioned_id,
                operation="median"
            )
            if gtex_result and gtex_result.get('data'):
                results['gtex'] = gtex_result
                results['gtex_note'] = f"Used versioned ID: {versioned_id}"

        if not results.get('gtex'):
            results['failed_tools'].append({
                'tool': 'GTEx_get_median_gene_expression',
                'tried': [ensembl_id, versioned_id],
                'fallback': 'See HPA data below'
            })
    else:
        results['gtex'] = gtex_result

    # HPA (always query as backup)
    hpa_result = tu.tools.HPA_get_rna_expression_by_source(ensembl_id=ensembl_id)
    results['hpa'] = hpa_result if hpa_result else {'note': 'No HPA RNA data'}

    return results
```

### HPA Extended Expression

```python
def get_hpa_comprehensive_expression(tu, gene_symbol):
    """
    Get comprehensive expression data from Human Protein Atlas.
    Provides tissue expression, subcellular localization, cell line comparison, tissue specificity.
    """
    gene_info = tu.tools.HPA_search_genes_by_query(search_query=gene_symbol)
    if not gene_info:
        return {'error': f'Gene {gene_symbol} not found in HPA'}

    tissue_search = tu.tools.HPA_generic_search(
        search_query=gene_symbol,
        columns="g,gs,rnat,rnatsm,scml,scal",
        format="json"
    )

    cell_lines = ['a549', 'mcf7', 'hela', 'hepg2', 'pc3']
    cell_line_expression = {}
    for cell_line in cell_lines:
        try:
            expr = tu.tools.HPA_get_comparative_expression_by_gene_and_cellline(
                gene_name=gene_symbol,
                cell_line=cell_line
            )
            cell_line_expression[cell_line] = expr
        except:
            continue

    return {
        'gene_info': gene_info,
        'tissue_data': tissue_search,
        'cell_line_expression': cell_line_expression,
        'source': 'Human Protein Atlas'
    }
```

## PATH 6: Variants & Disease

### DisGeNET Integration

DisGeNET provides curated gene-disease associations with evidence scores. **Requires**: `DISGENET_API_KEY`

```python
def get_disgenet_associations(tu, ids):
    """Get gene-disease associations from DisGeNET."""
    symbol = ids.get('symbol')
    if not symbol:
        return {'status': 'skipped', 'reason': 'No gene symbol'}

    gda = tu.tools.DisGeNET_search_gene(
        operation="search_gene",
        gene=symbol,
        limit=50
    )

    if gda.get('status') != 'success':
        return {'status': 'error', 'message': 'DisGeNET query failed'}

    associations = gda.get('data', {}).get('associations', [])
    strong, moderate, weak = [], [], []

    for assoc in associations:
        score = assoc.get('score', 0)
        entry = {
            'disease': assoc.get('disease_name', ''),
            'umls_cui': assoc.get('disease_id', ''),
            'score': score,
            'evidence_index': assoc.get('ei'),
            'dsi': assoc.get('dsi'),
            'dpi': assoc.get('dpi')
        }
        if score >= 0.7:
            strong.append(entry)
        elif score >= 0.4:
            moderate.append(entry)
        else:
            weak.append(entry)

    return {
        'total_associations': len(associations),
        'strong_associations': strong,
        'moderate_associations': moderate,
        'weak_associations': weak[:10],
        'disease_pleiotropy': len(associations)
    }
```

**Evidence Tier Assignment**:
- DisGeNET Score >= 0.7 -> Consider T2 evidence (multiple validated sources)
- DisGeNET Score 0.4-0.7 -> Consider T3 evidence
- DisGeNET Score < 0.4 -> T4 evidence only

## PATH 7: Druggability & Target Validation

### Pharos/TCRD - Target Development Level

```python
def get_pharos_target_info(tu, ids):
    """Get Pharos/TCRD target development level and druggability."""
    gene_symbol = ids.get('symbol')
    uniprot = ids.get('uniprot')

    if gene_symbol:
        result = tu.tools.Pharos_get_target(gene=gene_symbol)
    elif uniprot:
        result = tu.tools.Pharos_get_target(uniprot=uniprot)
    else:
        return {'status': 'error', 'message': 'Need gene symbol or UniProt'}

    if result.get('status') == 'success' and result.get('data'):
        target = result['data']
        return {
            'name': target.get('name'),
            'symbol': target.get('sym'),
            'tdl': target.get('tdl'),
            'family': target.get('fam'),
            'novelty': target.get('novelty'),
            'description': target.get('description'),
            'publications': target.get('publicationCount'),
            'interpretation': interpret_tdl(target.get('tdl'))
        }
    return None

def interpret_tdl(tdl):
    interpretations = {
        'Tclin': 'Approved drug target - highest confidence for druggability',
        'Tchem': 'Small molecule active - good chemical tractability',
        'Tbio': 'Biologically characterized - may require novel modalities',
        'Tdark': 'Understudied - limited data, high novelty potential'
    }
    return interpretations.get(tdl, 'Unknown')

def search_disease_targets(tu, disease_name):
    """Find targets associated with a disease via Pharos."""
    result = tu.tools.Pharos_get_disease_targets(disease=disease_name, top=50)
    if result.get('status') == 'success':
        targets = result['data'].get('targets', [])
        by_tdl = {'Tclin': [], 'Tchem': [], 'Tbio': [], 'Tdark': []}
        for t in targets:
            tdl = t.get('tdl', 'Unknown')
            if tdl in by_tdl:
                by_tdl[tdl].append(t)
        return by_tdl
    return None
```

### DepMap - Target Essentiality

```python
def assess_target_essentiality(tu, ids):
    """
    Is this target essential for cancer cell survival?
    Negative effect scores = gene is essential (cells die upon KO)
    """
    gene_symbol = ids.get('symbol')
    if not gene_symbol:
        return {'status': 'error', 'message': 'Need gene symbol'}

    deps = tu.tools.DepMap_get_gene_dependencies(gene_symbol=gene_symbol)

    if deps.get('status') == 'success':
        return {
            'gene': gene_symbol,
            'data': deps.get('data', {}),
            'interpretation': 'Negative scores indicate gene is essential for cell survival',
            'note': 'Score < -0.5 is strongly essential, < -1.0 is extremely essential'
        }
    return None
```

### InterProScan - Novel Domain Prediction

For uncharacterized proteins, run InterProScan to predict domains and function:

```python
def predict_protein_domains(tu, sequence, title="Query protein"):
    """
    Run InterProScan for de novo domain prediction.
    Use when: Novel/uncharacterized proteins, custom sequences, sparse InterPro annotations.
    """
    result = tu.tools.InterProScan_scan_sequence(
        sequence=sequence,
        title=title,
        go_terms=True,
        pathways=True
    )

    if result.get('status') == 'success':
        data = result.get('data', {})
        if data.get('job_status') == 'RUNNING':
            return {
                'job_id': data.get('job_id'),
                'status': 'running',
                'note': 'Use InterProScan_get_job_results to retrieve when ready'
            }
        return {
            'domains': data.get('domains', []),
            'domain_count': data.get('domain_count', 0),
            'go_annotations': data.get('go_annotations', []),
            'pathways': data.get('pathways', []),
            'sequence_length': data.get('sequence_length')
        }
    return None
```

### BindingDB - Known Ligands & Binding Data

```python
def get_bindingdb_ligands(tu, uniprot_id, affinity_cutoff=10000):
    """
    Get ligands with measured binding affinities from BindingDB.
    Critical for identifying chemical starting points and assessing tractability.
    """
    result = tu.tools.BindingDB_get_ligands_by_uniprot(
        uniprot=uniprot_id,
        affinity_cutoff=affinity_cutoff
    )

    if result:
        ligands = []
        for entry in result:
            ligands.append({
                'smiles': entry.get('smile'),
                'affinity_type': entry.get('affinity_type'),
                'affinity_nM': entry.get('affinity'),
                'monomer_id': entry.get('monomerid'),
                'pmid': entry.get('pmid')
            })
        ligands.sort(key=lambda x: float(x['affinity_nM']) if x['affinity_nM'] else float('inf'))
        return {
            'total_ligands': len(ligands),
            'ligands': ligands[:20],
            'best_affinity': ligands[0]['affinity_nM'] if ligands else None
        }

    return {'total_ligands': 0, 'ligands': [], 'note': 'No ligands found in BindingDB'}
```

**Affinity Interpretation**:
| Range | Level | Drug Potential |
|-------|-------|----------------|
| <1 nM | Ultra-potent | Clinical candidate |
| 1-10 nM | Highly potent | Drug-like |
| 10-100 nM | Potent | Good starting point |
| 100-1000 nM | Moderate | Needs optimization |
| >1000 nM | Weak | Early hit only |

### PubChem BioAssay - Screening Data

```python
def get_pubchem_assays_for_target(tu, gene_symbol):
    """Get bioassays targeting a gene from PubChem."""
    assays = tu.tools.PubChem_search_assays_by_target_gene(gene_symbol=gene_symbol)

    assay_info = []
    if assays.get('data', {}).get('aids'):
        for aid in assays['data']['aids'][:10]:
            summary = tu.tools.PubChem_get_assay_summary(aid=aid)
            targets = tu.tools.PubChem_get_assay_targets(aid=aid)
            assay_info.append({
                'aid': aid,
                'summary': summary.get('data', {}),
                'targets': targets.get('data', {})
            })

    return {
        'total_assays': len(assays.get('data', {}).get('aids', [])),
        'assay_details': assay_info
    }
```

## PATH 8: Literature (Collision-Aware)

```python
def path_literature_collision_aware(tu, ids):
    """Literature search with collision detection and filtering."""
    symbol = ids['symbol']
    full_name = ids.get('full_name', '')
    uniprot = ids['uniprot']
    synonyms = ids.get('synonyms', [])

    # Step 1: Detect collisions
    collision_filter = detect_collisions(tu, symbol, full_name)

    # Step 2: Build high-precision seed queries
    seed_queries = [
        f'"{symbol}"[Title] AND (protein OR gene OR expression)',
        f'"{full_name}"[Title]' if full_name else None,
        f'"UniProt:{uniprot}"' if uniprot else None,
    ]
    seed_queries = [q for q in seed_queries if q]
    for syn in synonyms[:3]:
        seed_queries.append(f'"{syn}"[Title]')

    # Step 3: Execute seed queries and collect PMIDs
    seed_pmids = set()
    for query in seed_queries:
        if collision_filter:
            query = f"({query}){collision_filter}"
        results = tu.tools.PubMed_search_articles(query=query, limit=30)
        for article in results.get('articles', []):
            seed_pmids.add(article.get('pmid'))

    # Step 4: Expand via citation network (for sparse targets)
    if len(seed_pmids) < 30:
        expanded_pmids = set()
        for pmid in list(seed_pmids)[:10]:
            related = tu.tools.PubMed_get_related(pmid=pmid, limit=20)
            for r in related.get('articles', []):
                expanded_pmids.add(r.get('pmid'))
            citing = tu.tools.EuropePMC_get_citations(pmid=pmid, limit=20)
            for c in citing.get('citations', []):
                expanded_pmids.add(c.get('pmid'))
        seed_pmids.update(expanded_pmids)

    # Step 5: Classify papers by evidence tier
    papers_by_tier = {'T1': [], 'T2': [], 'T3': [], 'T4': []}

    return {
        'total_papers': len(seed_pmids),
        'collision_filter_applied': collision_filter if collision_filter else 'None needed',
        'seed_queries': seed_queries,
        'papers_by_tier': papers_by_tier
    }
```

## Retry Logic & Fallback Chains

### Retry Policy

```python
def call_with_retry(tu, tool_name, params, max_retries=3):
    """Call tool with retry logic."""
    for attempt in range(max_retries):
        try:
            result = getattr(tu.tools, tool_name)(**params)
            if result and not result.get('error'):
                return result
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                return {'error': str(e), 'tool': tool_name, 'attempts': max_retries}
    return None
```

### Fallback Chains

| Primary Tool | Fallback 1 | Fallback 2 | Failure Action |
|--------------|------------|------------|----------------|
| `ChEMBL_get_target_activities` | `GtoPdb_search_ligands` | `OpenTargets drugs` | Note in report |
| `intact_get_interactions` | `STRING_get_protein_interactions` | `OpenTargets interactions` | Note in report |
| `GO_get_annotations_for_gene` | `OpenTargets GO` | `MyGene GO` | Note in report |
| `GTEx_get_median_gene_expression` | `HPA_get_rna_expression_by_source` | Note as unavailable | Document in report |
| `gnomad_get_gene_constraints` | `OpenTargets constraint` | - | Note in report |
| `DGIdb_get_drug_gene_interactions` | `OpenTargets drugs` | `GtoPdb` | Note in report |

### Failure Surfacing Rule

**NEVER silently skip failed tools.** Always document:

```markdown
### 7.1 Tissue Expression

**GTEx Data**: Unavailable (API timeout after 3 attempts)
**Fallback Data (HPA)**:
| Tissue | Expression Level | Specificity |
|--------|-----------------|-------------|
| Liver | High | Enhanced |
| Kidney | Medium | - |

*Note: For complete GTEx data, query directly at gtexportal.org*
```
