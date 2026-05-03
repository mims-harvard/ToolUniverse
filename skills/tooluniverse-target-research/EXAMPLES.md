# Target Intelligence Examples

Detailed examples showing multi-step workflows for comprehensive target analysis.

## Example 1: Complete EGFR Target Profile

**Query**: "Tell me everything about EGFR as a drug target"

### Step 1: Resolve Identifiers

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse(use_cache=True)
tu.load_tools()

# Resolve EGFR to all IDs
# Search UniProt for human EGFR
search_result = tu.tools.UniProt_search(
    query='gene:EGFR AND organism_id:9606',
    limit=1
)
uniprot_id = search_result['results'][0]['primaryAccession']  # P00533

# Map to Ensembl
mapping = tu.tools.UniProt_id_mapping(
    ids=['P00533'],
    from_db='UniProtKB_AC-ID',
    to_db='Ensembl'
)
ensembl_id = mapping['results'][0]['to']  # ENSG00000146648

ids = {
    'symbol': 'EGFR',
    'uniprot': 'P00533',
    'ensembl': 'ENSG00000146648'
}
```

### Step 2: Core Identity (PATH 1)

```python
# Get full UniProt entry
entry = tu.tools.UniProt_get_entry_by_accession(accession='P00533')

# Extract key info
identity = {
    'name': entry.get('proteinDescription', {}).get('recommendedName', {}).get('fullName', {}).get('value'),
    'length': entry.get('sequence', {}).get('length'),
    'organism': entry.get('organism', {}).get('scientificName'),
    'function': tu.tools.UniProt_get_function_by_accession(accession='P00533')
}

# Get gene annotation
gene_info = tu.tools.MyGene_get_gene_annotation(
    gene_id='1956',  # Entrez ID for EGFR
    fields='symbol,name,summary,alias,genomic_pos'
)
```

**Output**:
```
Name: Epidermal growth factor receptor
Symbol: EGFR
Length: 1210 amino acids
Organism: Homo sapiens
Function: Receptor tyrosine kinase binding ligands of the EGF family...
```

### Step 3: Structure & Domains (PATH 2)

```python
# Get PDB structures from UniProt entry
pdb_refs = [xref for xref in entry.get('uniProtKBCrossReferences', []) 
            if xref.get('database') == 'PDB']

# Get details for best structure
best_pdb = '1M17'  # Example: EGFR kinase domain
pdb_info = tu.tools.get_protein_metadata_by_pdb_id(pdb_id='1M17')

# Get AlphaFold prediction
alphafold = tu.tools.alphafold_get_prediction(qualifier='P00533')

# Get domain architecture
domains = tu.tools.InterPro_get_protein_domains(protein_id='P00533')

# Get PTMs and active sites
ptms = tu.tools.UniProt_get_ptm_processing_by_accession(accession='P00533')
```

**Output**:
```
PDB Structures: 150+ entries
Best Resolution: 1.8Å (1M17)
AlphaFold: Available, high confidence
Key Domains:
  - Receptor L domain (EGF binding)
  - Furin-like domain
  - Growth factor receptor domain
  - Protein kinase domain
PTMs: Multiple phosphorylation sites (Y992, Y1068, Y1086...)
```

### Step 4: Function & Pathways (PATH 3)

```python
# GO annotations
go_terms = tu.tools.GO_get_annotations_for_gene(gene_id='UniProtKB:P00533')

# Reactome pathways
reactome_pathways = tu.tools.Reactome_map_uniprot_to_pathways(id='P00533')

# KEGG pathways
kegg_info = tu.tools.kegg_get_gene_info(gene_id='hsa:1956')

# Open Targets GO
ot_go = tu.tools.OpenTargets_get_target_gene_ontology_by_ensemblID(
    ensemblID='ENSG00000146648'
)
```

**Output**:
```
GO Biological Process:
  - Signal transduction (GO:0007165)
  - Cell proliferation (GO:0008283)
  - MAPK cascade (GO:0000165)
  
GO Molecular Function:
  - Protein tyrosine kinase activity (GO:0004713)
  - ATP binding (GO:0005524)
  - Receptor binding (GO:0005102)

Key Pathways:
  - EGFR signaling pathway (Reactome)
  - PI3K-Akt signaling (KEGG hsa04151)
  - MAPK signaling (KEGG hsa04010)
  - ErbB signaling pathway (KEGG hsa04012)
```

### Step 5: Protein Interactions (PATH 4)

```python
# STRING interactions
string_ppi = tu.tools.STRING_get_protein_interactions(
    protein_ids=['EGFR'],
    species=9606,
    confidence_score=0.9,
    limit=50
)

# IntAct experimental interactions
intact_ppi = tu.tools.intact_get_interactions(
    identifier='P00533',
    format='json'
)

# Open Targets interactions
ot_ppi = tu.tools.OpenTargets_get_target_interactions_by_ensemblID(
    ensemblID='ENSG00000146648'
)
```

**Output**:
```
Top STRING Interactors (score > 0.9):
  1. GRB2 (0.999) - Adapter protein
  2. SHC1 (0.999) - Signal transduction
  3. ERBB2 (0.998) - Receptor family
  4. SRC (0.996) - Kinase
  5. STAT3 (0.994) - Transcription factor

IntAct Complexes:
  - EGFR-GRB2-SOS1 complex
  - EGFR-PI3K complex
```

### Step 6: Expression Profile (PATH 5)

```python
# GTEx expression
gtex = tu.tools.GTEx_get_median_gene_expression(
    gencode_id='ENSG00000146648.11'
)

# HPA expression
hpa = tu.tools.HPA_get_comprehensive_gene_details_by_ensembl_id(
    ensembl_id='ENSG00000146648'
)

# Subcellular location
subcell = tu.tools.HPA_get_subcellular_location(
    ensembl_id='ENSG00000146648'
)

# Cancer prognostics
cancer = tu.tools.HPA_get_cancer_prognostics_by_gene(
    gene_symbol='EGFR'
)
```

**Output**:
```
Top Expression Tissues (GTEx TPM):
  1. Skin (150+ TPM)
  2. Esophagus mucosa (120+ TPM)
  3. Kidney cortex (100+ TPM)
  4. Lung (80+ TPM)

Tissue Specificity: Low (broadly expressed)
Subcellular: Plasma membrane, Cytoplasm

Cancer Relevance:
  - Overexpressed in: NSCLC, Glioblastoma, Colorectal
  - Prognostic: Unfavorable in lung cancer
```

### Step 7: Variants & Disease (PATH 6)

```python
# gnomAD constraint scores
constraints = tu.tools.gnomad_get_gene_constraints(gene_symbol='EGFR')

# UniProt disease variants
disease_vars = tu.tools.UniProt_get_disease_variants_by_accession(accession='P00533')

# ClinVar variants
clinvar = tu.tools.clinvar_search_variants(gene='EGFR', max_results=100)

# Open Targets disease associations
diseases = tu.tools.OpenTargets_get_diseases_phenotypes_by_target_ensembl(
    ensemblId='ENSG00000146648'
)
```

**Output**:
```
Constraint Scores:
  - pLI: 0.99 (highly loss-of-function intolerant)
  - LOEUF: 0.18
  - Missense Z: 3.5

Disease Associations (Open Targets):
  1. Non-small cell lung carcinoma (0.95)
  2. Glioblastoma multiforme (0.89)
  3. Colorectal cancer (0.82)
  4. Pancreatic cancer (0.75)
  
ClinVar Pathogenic Variants: 45
  - L858R (common activating mutation)
  - T790M (resistance mutation)
  - Exon 19 deletions
```

### Step 8: Drug Interactions (PATH 7)

```python
# Open Targets tractability
tractability = tu.tools.OpenTargets_get_target_tractability_by_ensemblID(
    ensemblID='ENSG00000146648'
)

# DGIdb druggability
druggability = tu.tools.DGIdb_get_gene_druggability(genes=['EGFR'])

# Known drugs
drugs = tu.tools.OpenTargets_get_associated_drugs_by_target_ensemblID(
    ensemblID='ENSG00000146648'
)

# ChEMBL bioactivity
# First get ChEMBL target ID
chembl_target = tu.tools.ChEMBL_search_targets(
    pref_name__contains='EGFR',
    organism='Homo sapiens',
    limit=1
)
target_chembl_id = chembl_target['targets'][0]['target_chembl_id']  # CHEMBL203

activities = tu.tools.ChEMBL_get_target_activities(
    target_chembl_id__exact='CHEMBL203',
    limit=100
)

# Safety profile
safety = tu.tools.OpenTargets_get_target_safety_profile_by_ensemblID(
    ensemblID='ENSG00000146648'
)

# Chemical probes
probes = tu.tools.OpenTargets_get_chemical_probes_by_target_ensemblID(
    ensemblID='ENSG00000146648'
)
```

**Output**:
```
Tractability:
  - Small Molecule: HIGH (clinical precedence)
  - Antibody: HIGH (approved antibodies)
  - PROTAC: HIGH (structural data available)
  - Other Modalities: MEDIUM

Approved Drugs:
  1. Erlotinib (Tarceva) - TKI
  2. Gefitinib (Iressa) - TKI
  3. Afatinib (Gilotrif) - TKI
  4. Osimertinib (Tagrisso) - 3rd gen TKI
  5. Cetuximab (Erbitux) - mAb
  6. Panitumumab (Vectibix) - mAb

ChEMBL Activities:
  - 50,000+ bioactivity records
  - Best IC50: 0.5 nM (osimertinib)

Safety Liabilities:
  - Skin toxicity (class effect)
  - Diarrhea (common)
  - Interstitial lung disease (rare)

Chemical Probes: 
  - Gefitinib (SGC probe)
```

### Step 9: Literature (PATH 8)

```python
# PubMed publications
pubmed_total = tu.tools.PubMed_search_articles(
    query='EGFR[Gene Name]',
    limit=0  # Just count
)

pubmed_recent = tu.tools.PubMed_search_articles(
    query='EGFR[Gene Name] AND "2024"[Date - Publication]',
    limit=0
)

pubmed_drug = tu.tools.PubMed_search_articles(
    query='EGFR AND drug AND cancer',
    limit=10
)

# Open Targets publications
ot_pubs = tu.tools.OpenTargets_get_publications_by_target_ensemblID(
    ensemblID='ENSG00000146648',
    size=10
)
```

**Output**:
```
Literature Summary:
  - Total publications: 180,000+
  - Recent (2024): 8,000+
  - Drug-related: 45,000+
  - Trend: Stable (mature, well-studied target)

Recent Focus Areas:
  - Resistance mechanisms
  - Third-generation inhibitors
  - Combination therapies
  - Liquid biopsy for monitoring
```

### Final Synthesized Report

```markdown
# Target Intelligence Report: EGFR

## Quick Facts
| Property | Value |
|----------|-------|
| Symbol | EGFR |
| UniProt | P00533 |
| Ensembl | ENSG00000146648 |
| Name | Epidermal growth factor receptor |
| Length | 1210 amino acids |
| Organism | Homo sapiens |

## Druggability Assessment
| Modality | Score | Evidence |
|----------|-------|----------|
| Small molecule | ✅ HIGH | 4+ approved TKIs |
| Antibody | ✅ HIGH | 2+ approved mAbs |
| PROTAC | ✅ HIGH | Structural data |

## Summary by Domain

### Identity & Function
- Receptor tyrosine kinase of the ErbB family
- Regulates cell proliferation, survival, differentiation
- Activates RAS-MAPK and PI3K-AKT pathways

### Structure
- 150+ PDB structures available
- Key domains: Kinase (for TKIs), Extracellular (for mAbs)
- AlphaFold model: High confidence

### Expression
- Broadly expressed (skin, lung, kidney highest)
- Overexpressed in multiple cancers
- Subcellular: Plasma membrane

### Variants & Disease
- Highly constrained (pLI=0.99)
- Major cancer associations: NSCLC, glioblastoma, CRC
- Key mutations: L858R, T790M, exon 19 del

### Drugs
- 6+ approved drugs
- 200+ clinical trials
- Well-characterized safety profile (skin toxicity)

### Research
- Mature target (180K+ publications)
- Active research on resistance mechanisms

## Recommendations
1. [HIGH] Excellent target validation - multiple approved therapies
2. [MEDIUM] Consider resistance mutations in drug design
3. [INFO] Extensive structural data for SBDD available
```

---

## Example 2: Novel Target Assessment (KRAS G12C)

**Query**: "Is KRAS druggable? What's the current state?"

### Multi-Step Workflow

```python
from tooluniverse import ToolUniverse
from concurrent.futures import ThreadPoolExecutor

tu = ToolUniverse(use_cache=True)
tu.load_tools()

# Resolve KRAS
ids = {
    'symbol': 'KRAS',
    'uniprot': 'P01116',
    'ensembl': 'ENSG00000133703'
}

# Parallel execution
def assess_druggability():
    results = {}
    
    # 1. Tractability
    results['tractability'] = tu.tools.OpenTargets_get_target_tractability_by_ensemblID(
        ensemblID=ids['ensembl']
    )
    
    # 2. DGIdb assessment
    results['dgidb'] = tu.tools.DGIdb_get_gene_druggability(genes=['KRAS'])
    
    # 3. Known drugs
    results['drugs'] = tu.tools.OpenTargets_get_associated_drugs_by_target_ensemblID(
        ensemblID=ids['ensembl']
    )
    
    # 4. ChEMBL activities
    chembl = tu.tools.ChEMBL_search_targets(
        pref_name__contains='KRAS',
        organism='Homo sapiens',
        limit=1
    )
    if chembl.get('targets'):
        target_id = chembl['targets'][0]['target_chembl_id']
        results['activities'] = tu.tools.ChEMBL_get_target_activities(
            target_chembl_id__exact=target_id,
            limit=50
        )
    
    # 5. Structures
    results['structures'] = tu.tools.alphafold_get_prediction(qualifier='P01116')
    
    # 6. Safety
    results['safety'] = tu.tools.OpenTargets_get_target_safety_profile_by_ensemblID(
        ensemblID=ids['ensembl']
    )
    
    return results

druggability = assess_druggability()
```

**Output**:
```
KRAS Druggability Assessment:

Tractability:
  - Small Molecule: MEDIUM → HIGH (recent breakthroughs!)
  - Previously "undruggable" - now validated
  
Approved Drugs (G12C-specific):
  - Sotorasib (Lumakras) - 2021
  - Adagrasib (Krazati) - 2022

ChEMBL Activities:
  - 5000+ bioactivity records
  - G12C-specific covalent inhibitors

Structure:
  - Multiple G12C-bound structures
  - Switch II pocket (key for covalent inhibitors)

Recent Breakthrough:
  - Covalent inhibitors targeting G12C mutant
  - Switch II pocket discovered as druggable site
  - Active clinical development for other mutations (G12D, G12V)
```

---

## Example 3: Target Comparison

**Query**: "Compare EGFR vs HER2 as drug targets"

### Parallel Analysis

```python
targets = [
    {'symbol': 'EGFR', 'uniprot': 'P00533', 'ensembl': 'ENSG00000146648'},
    {'symbol': 'ERBB2', 'uniprot': 'P04626', 'ensembl': 'ENSG00000141736'}  # HER2
]

def analyze_target(target):
    result = {
        'symbol': target['symbol'],
        'tractability': tu.tools.OpenTargets_get_target_tractability_by_ensemblID(
            ensemblID=target['ensembl']
        ),
        'drugs': tu.tools.OpenTargets_get_associated_drugs_by_target_ensemblID(
            ensemblID=target['ensembl']
        ),
        'diseases': tu.tools.OpenTargets_get_diseases_phenotypes_by_target_ensembl(
            ensemblId=target['ensembl']
        ),
        'safety': tu.tools.OpenTargets_get_target_safety_profile_by_ensemblID(
            ensemblID=target['ensembl']
        ),
        'ppi': tu.tools.STRING_get_protein_interactions(
            protein_ids=[target['symbol']],
            species=9606,
            confidence_score=0.9,
            limit=20
        )
    }
    return result

# Parallel analysis
with ThreadPoolExecutor(max_workers=2) as executor:
    results = list(executor.map(analyze_target, targets))
```

**Comparison Output**:
```markdown
| Property | EGFR | HER2/ERBB2 |
|----------|------|------------|
| **Approved Drugs** | 6+ | 8+ |
| **TKI Tractability** | HIGH | HIGH |
| **mAb Tractability** | HIGH | HIGH |
| **ADC** | N/A | HIGH (T-DM1, T-DXd) |
| **Primary Indication** | NSCLC | Breast cancer |
| **Key Mutations** | L858R, T790M | Amplification |
| **Safety Concerns** | Skin toxicity | Cardiotoxicity |
```

---

## Example 4: Target Validation Pipeline

**Query**: "Validate CDK4 as a potential drug target for cancer"

### Systematic Validation

```python
def validate_target(gene_symbol, disease_area='cancer'):
    """
    Systematic target validation following industry best practices.
    """
    tu = ToolUniverse(use_cache=True)
    tu.load_tools()
    
    validation_results = {}
    
    # 1. GENETIC EVIDENCE
    # Disease associations
    ensembl_id = 'ENSG00000135446'  # CDK4
    
    disease_assoc = tu.tools.OpenTargets_get_diseases_phenotypes_by_target_ensembl(
        ensemblId=ensembl_id
    )
    validation_results['genetic_evidence'] = {
        'disease_associations': disease_assoc,
        'score': 'HIGH' if any(d.get('score', 0) > 0.5 for d in disease_assoc.get('data', [])) else 'LOW'
    }
    
    # Constraint score
    constraint = tu.tools.gnomad_get_gene_constraints(gene_symbol='CDK4')
    validation_results['constraint'] = constraint
    
    # 2. EXPRESSION EVIDENCE
    # Cancer expression
    hpa_cancer = tu.tools.HPA_get_cancer_prognostics_by_gene(gene_symbol='CDK4')
    validation_results['expression'] = hpa_cancer
    
    # 3. FUNCTIONAL EVIDENCE
    # Pathways
    pathways = tu.tools.Reactome_map_uniprot_to_pathways(id='P11802')
    go_terms = tu.tools.GO_get_annotations_for_gene(gene_id='UniProtKB:P11802')
    validation_results['function'] = {
        'pathways': pathways,
        'go_terms': go_terms
    }
    
    # 4. DRUGGABILITY
    tractability = tu.tools.OpenTargets_get_target_tractability_by_ensemblID(
        ensemblID=ensembl_id
    )
    existing_drugs = tu.tools.OpenTargets_get_associated_drugs_by_target_ensemblID(
        ensemblID=ensembl_id
    )
    validation_results['druggability'] = {
        'tractability': tractability,
        'existing_drugs': existing_drugs
    }
    
    # 5. SAFETY
    safety = tu.tools.OpenTargets_get_target_safety_profile_by_ensemblID(
        ensemblID=ensembl_id
    )
    mouse_models = tu.tools.OpenTargets_get_biological_mouse_models_by_ensemblID(
        ensemblID=ensembl_id
    )
    validation_results['safety'] = {
        'profile': safety,
        'mouse_models': mouse_models
    }
    
    # 6. COMPETITIVE LANDSCAPE
    lit_count = tu.tools.PubMed_search_articles(
        query=f'{gene_symbol} AND drug AND cancer',
        limit=0
    )
    validation_results['competitive'] = {
        'publication_count': lit_count.get('count', 0),
        'maturity': 'mature' if lit_count.get('count', 0) > 1000 else 'emerging'
    }
    
    return validation_results

results = validate_target('CDK4')
```

**Validation Report**:
```markdown
# Target Validation Report: CDK4

## Validation Scorecard

| Criterion | Score | Evidence |
|-----------|-------|----------|
| Genetic Evidence | ✅ HIGH | Strong cancer associations |
| Expression | ✅ HIGH | Overexpressed in multiple cancers |
| Functional Role | ✅ HIGH | Cell cycle regulator |
| Druggability | ✅ HIGH | Approved inhibitors |
| Safety | ⚠️ MEDIUM | On-target effects expected |
| Competitive | 🔴 HIGH | Mature, crowded space |

## Existing Drugs
- Palbociclib (Ibrance)
- Ribociclib (Kisqali)
- Abemaciclib (Verzenio)

## Recommendation
CDK4 is a **validated target** with approved drugs. 
New entrants would need differentiation (selectivity, CNS penetration, etc.)
```

---

## Example 5: Finding Drug Targets for a Disease

**Query**: "What are the best drug targets for Alzheimer's disease?"

### Disease-to-Target Discovery

```python
def find_targets_for_disease(disease_name):
    tu = ToolUniverse(use_cache=True)
    tu.load_tools()
    
    # 1. Get disease ID
    disease_search = tu.tools.OpenTargets_get_disease_ids_by_name(
        diseaseName=disease_name
    )
    efo_id = disease_search.get('id')  # e.g., EFO_0000249 for Alzheimer's
    
    # 2. Get associated targets
    targets = tu.tools.OpenTargets_get_associated_targets_by_disease_efoId(
        efoId=efo_id
    )
    
    # 3. For top targets, assess druggability
    top_targets = targets.get('data', [])[:10]
    
    target_assessments = []
    for target in top_targets:
        ensembl_id = target.get('target_id')
        symbol = target.get('gene_symbol')
        
        # Druggability
        tract = tu.tools.OpenTargets_get_target_tractability_by_ensemblID(
            ensemblID=ensembl_id
        )
        
        # Existing drugs
        drugs = tu.tools.OpenTargets_get_associated_drugs_by_target_ensemblID(
            ensemblID=ensembl_id
        )
        
        # Safety
        safety = tu.tools.OpenTargets_get_target_safety_profile_by_ensemblID(
            ensemblID=ensembl_id
        )
        
        target_assessments.append({
            'symbol': symbol,
            'ensembl_id': ensembl_id,
            'disease_score': target.get('score'),
            'tractability': tract,
            'drug_count': len(drugs.get('data', [])),
            'safety_flags': len(safety.get('data', []))
        })
    
    return target_assessments

alzheimer_targets = find_targets_for_disease("Alzheimer's disease")
```

**Output**:
```markdown
# Top Drug Targets for Alzheimer's Disease

| Rank | Target | Score | Druggability | Drugs | Safety |
|------|--------|-------|--------------|-------|--------|
| 1 | APP | 0.95 | MEDIUM | 0 | ⚠️ |
| 2 | PSEN1 | 0.92 | LOW | 0 | ⚠️ |
| 3 | APOE | 0.88 | LOW | 0 | ✅ |
| 4 | MAPT | 0.85 | MEDIUM | 2 | ⚠️ |
| 5 | BACE1 | 0.82 | HIGH | 0* | ⚠️ |
| 6 | GSK3B | 0.75 | HIGH | 5 | ⚠️ |
| 7 | ACE | 0.70 | HIGH | 10+ | ✅ |
| 8 | TREM2 | 0.68 | MEDIUM | 2 | ✅ |

*BACE1 inhibitors failed in trials

## Recommendations
1. **TREM2** - Emerging target, favorable safety, antibody approaches
2. **GSK3B** - Druggable, existing tool compounds
3. **ACE** - Repurposing opportunity (existing drugs)
```

---

## Quick Reference: Common Multi-Step Patterns

### Pattern: Gene Symbol → Full Profile

```python
# 1. Symbol → UniProt
search = tu.tools.UniProt_search(query=f'gene:{symbol} AND organism_id:9606', limit=1)
uniprot = search['results'][0]['primaryAccession']

# 2. UniProt → Ensembl
mapping = tu.tools.UniProt_id_mapping(ids=[uniprot], from_db='UniProtKB_AC-ID', to_db='Ensembl')
ensembl = mapping['results'][0]['to']

# 3. Get all info
entry = tu.tools.UniProt_get_entry_by_accession(accession=uniprot)
tractability = tu.tools.OpenTargets_get_target_tractability_by_ensemblID(ensemblID=ensembl)
```

### Pattern: PDB → Ligand Analysis

```python
# 1. Get PDB info
pdb_info = tu.tools.get_protein_metadata_by_pdb_id(pdb_id='1M17')

# 2. Get ligands
ligands = pdb_info.get('rcsb_binding_affinity', [])

# 3. For each ligand, get ChEMBL data
for lig in ligands:
    comp_id = lig.get('comp_id')
    smiles = tu.tools.get_ligand_smiles_by_chem_comp_id(chem_comp_id=comp_id)
    # Search ChEMBL for similar molecules
```

### Pattern: Disease → Target → Drug

```python
# 1. Disease → EFO ID
efo = tu.tools.OpenTargets_get_disease_ids_by_name(diseaseName='lung cancer')

# 2. EFO → Targets
targets = tu.tools.OpenTargets_get_associated_targets_by_disease_efoId(efoId=efo['id'])

# 3. Target → Drugs
for target in targets['data'][:5]:
    drugs = tu.tools.OpenTargets_get_associated_drugs_by_target_ensemblID(
        ensemblID=target['target_id']
    )
```
