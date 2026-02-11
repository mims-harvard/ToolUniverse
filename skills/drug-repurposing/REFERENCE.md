# Drug Repurposing Reference

Detailed tool documentation and API reference for drug repurposing workflows.

## ToolUniverse Tools by Category

### Disease & Target Discovery Tools

#### OpenTargets_get_disease_id_description_by_name
```python
disease_info = tu.tools.OpenTargets_get_disease_id_description_by_name(
    diseaseName="Alzheimer's disease"
)
# Returns: {'data': {'id': 'EFO_0000249', 'name': '...', 'description': '...'}}
```
**Use**: Initial disease lookup, get EFO ID for further queries

#### OpenTargets_get_associated_targets_by_disease_efoId
```python
targets = tu.tools.OpenTargets_get_associated_targets_by_disease_efoId(
    efoId="EFO_0000249",
    limit=20
)
# Returns: List of targets with association scores
```
**Use**: Find proteins/genes associated with disease (repurposing targets)

#### OpenTargets_get_diseases_by_target_ensemblId
```python
diseases = tu.tools.OpenTargets_get_diseases_by_target_ensemblId(
    ensemblId="ENSG00000012048"
)
# Returns: Diseases associated with gene/protein
```
**Use**: Reverse lookup - find diseases for drug targets (compound-based repurposing)

---

### Drug Discovery Tools

#### drugbank_get_drug_name_and_description_by_target_name
```python
drugs = tu.tools.drugbank_get_drug_name_and_description_by_target_name(
    target_name="BACE1"
)
# Returns: List of drugs targeting specified protein
```
**Use**: Primary tool for finding drugs by target (target-based repurposing)

#### drugbank_get_drug_name_and_description_by_indication
```python
drugs = tu.tools.drugbank_get_drug_name_and_description_by_indication(
    indication="hypertension"
)
# Returns: Drugs approved for specified indication
```
**Use**: Find drugs for related indications (indication-based repurposing)

#### DGIdb_get_drug_gene_interactions
```python
interactions = tu.tools.DGIdb_get_drug_gene_interactions(
    gene_name="APP"
)
# Returns: Drug-gene interactions with interaction types
```
**Use**: Alternative source for drug-target pairs, includes interaction types

#### DGIdb_get_gene_druggability
```python
druggability = tu.tools.DGIdb_get_gene_druggability(
    gene_name="APOE"
)
# Returns: Druggability assessment and tier
```
**Use**: Assess if target is druggable before extensive search

#### ChEMBL_search_drugs
```python
drugs = tu.tools.ChEMBL_search_drugs(
    query="kinase inhibitor",
    limit=10
)
# Returns: ChEMBL drug molecules matching query
```
**Use**: Broad drug search, alternative to DrugBank

#### ChEMBL_get_drug_mechanisms
```python
mechanisms = tu.tools.ChEMBL_get_drug_mechanisms(
    chembl_id="CHEMBL941"
)
# Returns: Mechanism of action details
```
**Use**: Understand drug mechanism for repurposing rationale

---

### Drug Information Tools

#### drugbank_get_drug_basic_info_by_drug_name_or_id
```python
info = tu.tools.drugbank_get_drug_basic_info_by_drug_name_or_id(
    drug_name_or_drugbank_id="metformin"
)
# Returns: Basic drug info including approval status, groups, description
```
**Use**: Initial drug lookup, verify approval status

#### drugbank_get_indications_by_drug_name_or_drugbank_id
```python
indications = tu.tools.drugbank_get_indications_by_drug_name_or_drugbank_id(
    drug_name_or_drugbank_id="aspirin"
)
# Returns: List of approved indications
```
**Use**: Check current uses, identify repurposing opportunities (new indications)

#### drugbank_get_targets_by_drug_name_or_drugbank_id
```python
targets = tu.tools.drugbank_get_targets_by_drug_name_or_drugbank_id(
    drug_name_or_drugbank_id="imatinib"
)
# Returns: Drug targets with accessions
```
**Use**: Compound-based repurposing - find all targets for known drug

#### drugbank_get_pharmacology_by_drug_name_or_drugbank_id
```python
pharmacology = tu.tools.drugbank_get_pharmacology_by_drug_name_or_drugbank_id(
    drug_name_or_drugbank_id="warfarin"
)
# Returns: Mechanism of action, pharmacodynamics, pharmacokinetics
```
**Use**: Understand drug mechanism for repurposing rationale

#### drugbank_get_pathways_reactions_by_drug_or_id
```python
pathways = tu.tools.drugbank_get_pathways_reactions_by_drug_or_id(
    drug_name_or_drugbank_id="statins"
)
# Returns: Affected pathways and reactions
```
**Use**: Pathway-based repurposing - find drugs affecting similar pathways

#### drugbank_get_drug_name_and_description_by_pathway_name
```python
drugs = tu.tools.drugbank_get_drug_name_and_description_by_pathway_name(
    pathway_name="cholesterol biosynthesis"
)
# Returns: Drugs affecting specified pathway
```
**Use**: Find drugs with pathway overlap (network-based repurposing)

#### drugbank_get_drug_desc_pharmacology_by_moa
```python
drugs = tu.tools.drugbank_get_drug_desc_pharmacology_by_moa(
    mechanism_of_action="receptor antagonist"
)
# Returns: Drugs with specified mechanism
```
**Use**: Mechanism-based repurposing

---

### Safety Assessment Tools

#### FDA_get_warnings_and_cautions_by_drug_name
```python
warnings = tu.tools.FDA_get_warnings_and_cautions_by_drug_name(
    drug_name="aspirin"
)
# Returns: FDA warnings, precautions, contraindications
```
**Use**: Critical safety assessment before repurposing recommendation

#### FDA_get_precautions_by_drug_name
```python
precautions = tu.tools.FDA_get_precautions_by_drug_name(
    drug_name="metformin"
)
# Returns: Precautions and special populations
```
**Use**: Identify patient populations to exclude

#### drugbank_get_drug_interactions_by_drug_name_or_id
```python
interactions = tu.tools.drugbank_get_drug_interactions_by_drug_name_or_id(
    drug_name_or_id="warfarin"
)
# Returns: Drug-drug interactions
```
**Use**: Assess interaction risk for new indication (different patient population)

#### FAERS_search_reports_by_drug_and_reaction
```python
reports = tu.tools.FAERS_search_reports_by_drug_and_reaction(
    drug_name="LIPITOR",
    reaction="myalgia",
    limit=100
)
# Returns: Adverse event reports
```
**Use**: Real-world safety data, specific adverse events

#### FAERS_count_reactions_by_drug_event
```python
reactions = tu.tools.FAERS_count_reactions_by_drug_event(
    medicinalproduct="ASPIRIN"
)
# Returns: Counts of all reported reactions
```
**Use**: Overview of adverse event profile

#### FAERS_count_death_related_by_drug
```python
deaths = tu.tools.FAERS_count_death_related_by_drug(
    medicinalproduct="FENTANYL"
)
# Returns: Death-related adverse event counts
```
**Use**: Most serious safety assessment

#### FAERS_count_seriousness_by_drug_event
```python
seriousness = tu.tools.FAERS_count_seriousness_by_drug_event(
    medicinalproduct="METFORMIN"
)
# Returns: Classification of events by seriousness
```
**Use**: Stratify adverse events by severity

---

### Chemical Property Tools

#### PubChem_get_CID_by_compound_name
```python
cid = tu.tools.PubChem_get_CID_by_compound_name(
    compound_name="aspirin"
)
# Returns: PubChem Compound ID
```
**Use**: First step for PubChem queries

#### PubChem_get_compound_properties_by_CID
```python
properties = tu.tools.PubChem_get_compound_properties_by_CID(
    cid=2244
)
# Returns: MW, formula, SMILES, LogP, H-bond donors/acceptors
```
**Use**: Assess drug-likeness, compare analogs

#### PubChem_search_compounds_by_similarity
```python
similar = tu.tools.PubChem_search_compounds_by_similarity(
    smiles="CC(=O)Oc1ccccc1C(=O)O",
    threshold=85,
    limit=50
)
# Returns: Structurally similar compounds
```
**Use**: Structure-based repurposing - find approved drug analogs

#### PubChem_get_bioactivity_summary_by_CID
```python
bioactivity = tu.tools.PubChem_get_bioactivity_summary_by_CID(
    cid=2244
)
# Returns: Active/inactive assay counts
```
**Use**: Evidence of biological activity

#### ChEMBL_get_bioactivity_by_chemblid
```python
bioactivity = tu.tools.ChEMBL_get_bioactivity_by_chemblid(
    chembl_id="CHEMBL25"
)
# Returns: Detailed bioactivity data (IC50, EC50, etc.)
```
**Use**: Quantitative activity data for target validation

---

### ADMET Prediction Tools

#### ADMETAI_predict_admet
```python
admet = tu.tools.ADMETAI_predict_admet(
    smiles="CC(C)Cc1ccc(cc1)C(C)C(O)=O"
)
# Returns: Absorption, distribution, metabolism, excretion, toxicity predictions
```
**Use**: Predict drug-like properties for candidates, filter early

**Important**: Use `use_cache=True` for expensive ML predictions

#### ADMETAI_predict_toxicity
```python
toxicity = tu.tools.ADMETAI_predict_toxicity(
    smiles=["SMILES1", "SMILES2"]
)
# Returns: Toxicity predictions (hERG, hepatotoxicity, etc.)
```
**Use**: Safety screening before clinical consideration

---

### Literature Search Tools

#### PubMed_search_articles
```python
papers = tu.tools.PubMed_search_articles(
    query="metformin AND Alzheimer's disease",
    max_results=50
)
# Returns: PubMed articles with PMIDs, titles, abstracts
```
**Use**: Primary literature evidence for repurposing hypothesis

#### EuropePMC_search_articles
```python
papers = tu.tools.EuropePMC_search_articles(
    query="aspirin AND cancer",
    limit=50
)
# Returns: Europe PMC articles (includes preprints)
```
**Use**: Alternative/additional literature source

#### ClinicalTrials_search
```python
trials = tu.tools.ClinicalTrials_search(
    condition="COVID-19",
    intervention="hydroxychloroquine"
)
# Returns: Clinical trial records
```
**Use**: Check existing clinical evidence, identify completed/ongoing trials

---

### Protein/Target Information Tools

#### UniProt_get_entry_by_accession
```python
protein = tu.tools.UniProt_get_entry_by_accession(
    accession="P05067"
)
# Returns: Detailed protein information
```
**Use**: Understand target biology, confirm druggability

---

## Parameter Guidelines

### Query Construction

**Drug names**:
- Use generic names: "aspirin" not "Bayer Aspirin"
- Lowercase for DrugBank: `drug_name="metformin"`
- UPPERCASE for FAERS: `medicinalproduct="METFORMIN"`

**Disease names**:
- Use standard terminology: "Alzheimer's disease" not "dementia"
- Try variations if not found: "breast cancer", "breast carcinoma", "mammary carcinoma"

**Gene/Target names**:
- HUGO nomenclature: "APP" not "Amyloid Precursor Protein"
- Protein names: "Amyloid beta A4 protein" for UniProt
- Ensembl IDs: "ENSG00000" format for OpenTargets

### Result Limits

Recommended limits by tool:
- `OpenTargets_get_associated_targets`: 20-50 (prioritize by score)
- `DGIdb_get_drug_gene_interactions`: No limit (returns all)
- `ChEMBL_search_drugs`: 10-20
- `PubMed_search_articles`: 50-100 for thorough analysis
- `FAERS` tools: 100-1000 (statistical analysis)
- `PubChem_search_compounds_by_similarity`: 50-100

### Caching Strategy

**Always cache**:
- ADMET predictions (expensive ML)
- Literature searches (large results)
- Drug/protein detail queries (static data)

**Don't cache**:
- FAERS data (updated quarterly)
- Clinical trials (frequently updated)
- Real-time safety alerts

```python
# Enable caching globally
tu = ToolUniverse(use_cache=True)

# Or per-call
result = tu.tools.ADMETAI_predict_admet(smiles="...", use_cache=True)
```

---

## Data Structure Patterns

### Standard Result Format
```python
{
    'data': [...],           # Main results (list or dict)
    'meta': {...},           # Metadata (counts, pagination)
    'status': 'success',     # Status indicator
    'message': 'Optional message'
}
```

### OpenTargets Target Object
```python
{
    'gene_symbol': 'APP',
    'gene_name': 'Amyloid Precursor Protein',
    'ensembl_id': 'ENSG00000142192',
    'uniprot_id': 'P05067',
    'score': 0.95,           # Association score (0-1)
    'data_sources': [...]    # Evidence sources
}
```

### DrugBank Drug Object
```python
{
    'drugbank_id': 'DB00945',
    'name': 'Aspirin',
    'description': '...',
    'groups': ['approved', 'vet_approved'],
    'indication': '...',
    'pharmacodynamics': '...',
    'mechanism_of_action': '...',
    'targets': [...]
}
```

### FAERS Result Format
```python
{
    'results': [
        {
            'term': 'NAUSEA',
            'count': 12345
        },
        ...
    ],
    'meta': {
        'total': 50000,
        'disclaimer': '...'
    }
}
```

---

## Common Patterns & Recipes

### Pattern 1: Batch Target Screening
```python
# Screen multiple targets efficiently
targets = ['APP', 'APOE', 'MAPT', 'PSEN1', 'PSEN2']

all_drugs = []
for target in targets:
    drugs = tu.tools.DGIdb_get_drug_gene_interactions(gene_name=target)
    if drugs and 'data' in drugs:
        all_drugs.extend([{**d, 'target': target} for d in drugs['data']])

# Deduplicate by drug name
unique_drugs = {d['drug_name']: d for d in all_drugs}.values()
```

### Pattern 2: Cross-Database Validation
```python
# Validate drug-target interaction across databases
drug = "imatinib"
target = "ABL1"

# Check DrugBank
db_targets = tu.tools.drugbank_get_targets_by_drug_name_or_drugbank_id(
    drug_name_or_drugbank_id=drug
)
db_confirms = any(t['gene_symbol'] == target for t in db_targets.get('data', []))

# Check DGIdb
dgidb = tu.tools.DGIdb_get_drug_gene_interactions(gene_name=target)
dgidb_confirms = any(d['drug_name'].lower() == drug.lower() 
                     for d in dgidb.get('data', []))

# Check ChEMBL
chembl_drugs = tu.tools.ChEMBL_search_drugs(query=drug, limit=1)
if chembl_drugs and 'data' in chembl_drugs:
    chembl_id = chembl_drugs['data'][0]['molecule_chembl_id']
    mechanisms = tu.tools.ChEMBL_get_drug_mechanisms(chembl_id=chembl_id)
    chembl_confirms = any(target in str(m) for m in mechanisms.get('data', []))

validation_score = sum([db_confirms, dgidb_confirms, chembl_confirms])
print(f"Validation: {validation_score}/3 databases confirm {drug}-{target} interaction")
```

### Pattern 3: Safety Signal Detection
```python
# Detect safety signals for repurposing
drug = "THALIDOMIDE"

# Get all adverse events
all_reactions = tu.tools.FAERS_count_reactions_by_drug_event(
    medicinalproduct=drug
)

# Classify by seriousness
seriousness = tu.tools.FAERS_count_seriousness_by_drug_event(
    medicinalproduct=drug
)

# Get death reports
deaths = tu.tools.FAERS_count_death_related_by_drug(
    medicinalproduct=drug
)

# Calculate safety score
total_reports = sum(r['count'] for r in all_reactions.get('results', []))
death_count = deaths.get('meta', {}).get('total', 0)
death_ratio = death_count / max(total_reports, 1)

if death_ratio > 0.01:  # >1% death reports
    print(f"⚠️ HIGH RISK: {death_ratio*100:.2f}% death ratio")
elif death_ratio > 0.001:
    print(f"⚠️ MODERATE RISK: {death_ratio*100:.2f}% death ratio")
else:
    print(f"✓ ACCEPTABLE RISK: {death_ratio*100:.2f}% death ratio")
```

### Pattern 4: Literature Evidence Scoring
```python
# Score repurposing candidate by literature evidence
drug = "metformin"
disease = "cancer"

query = f"{drug} AND {disease}"

# Search multiple sources
pubmed = tu.tools.PubMed_search_articles(query=query, max_results=100)
pmc = tu.tools.EuropePMC_search_articles(query=query, limit=100)
trials = tu.tools.ClinicalTrials_search(condition=disease, intervention=drug)

# Count evidence types
review_count = sum(1 for p in pubmed.get('data', []) 
                   if 'review' in p.get('title', '').lower())
rct_count = sum(1 for p in pubmed.get('data', []) 
                if 'randomized' in p.get('title', '').lower())
trial_count = len(trials.get('data', []))

# Calculate evidence score
evidence_score = (
    len(pubmed.get('data', [])) * 1 +      # 1 point per paper
    review_count * 3 +                      # 3 points per review
    rct_count * 5 +                         # 5 points per RCT
    trial_count * 10                        # 10 points per trial
)

print(f"Evidence Score: {evidence_score}")
print(f"  Papers: {len(pubmed.get('data', []))}")
print(f"  Reviews: {review_count}")
print(f"  RCTs: {rct_count}")
print(f"  Trials: {trial_count}")
```

---

## Troubleshooting

### Issue: "Disease not found"
**Solutions**:
1. Try disease synonyms
2. Use broader disease categories
3. Search OMIM or other disease databases
4. Use EFO ID directly if known

### Issue: "No drugs found for target"
**Causes**:
- Target not druggable
- Target name incorrect
- Limited database coverage

**Solutions**:
1. Check gene symbol (HUGO nomenclature)
2. Try protein name instead
3. Expand to pathway-level drugs
4. Check target druggability first

### Issue: "Drug name not recognized"
**Solutions**:
1. Try generic name (not brand)
2. Try different capitalization
3. Use DrugBank ID if known
4. Search PubChem first

### Issue: "API rate limits"
**Solutions**:
1. Enable caching: `use_cache=True`
2. Add delays between calls
3. Use batch operations
4. Register for API keys (NCBI, etc.)

### Issue: "Empty results for FAERS"
**Causes**:
- Drug name spelling
- Insufficient reports
- Wrong capitalization

**Solutions**:
1. Use UPPERCASE: "ASPIRIN" not "aspirin"
2. Try brand names
3. Check OpenFDA directly

### Issue: "Slow performance"
**Solutions**:
1. Enable caching globally
2. Limit result counts
3. Load specific tool categories
4. Use batch operations
5. Disable validation after testing

---

## Best Practices Summary

1. **Start with approved drugs** - Known safety profiles
2. **Validate across databases** - Cross-reference DrugBank, DGIdb, ChEMBL
3. **Check safety first** - FDA warnings before detailed analysis
4. **Use caching** - Save API calls and time
5. **Limit initial searches** - Expand only promising candidates
6. **Document evidence** - Keep track of supporting papers
7. **Consider mechanism** - Biological plausibility critical
8. **Assess patient populations** - Different from original indication
9. **Check IP landscape** - Patent status for new indications
10. **Think commercially** - Market size and unmet need

---

## Additional Resources

- **ToolUniverse Documentation**: https://zitniklab.hms.harvard.edu/ToolUniverse/
- **Tool Catalog**: https://zitniklab.hms.harvard.edu/ToolUniverse/tools/
- **DrugBank**: https://go.drugbank.com/
- **OpenTargets**: https://platform.opentargets.org/
- **ChEMBL**: https://www.ebi.ac.uk/chembl/
- **OpenFDA**: https://open.fda.gov/
- **PubMed**: https://pubmed.ncbi.nlm.nih.gov/
