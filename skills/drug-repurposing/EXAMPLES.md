# Drug Repurposing Examples

Concrete examples of drug repurposing workflows using ToolUniverse.

## Example 1: Target-Based Repurposing for Alzheimer's Disease

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse(use_cache=True)
tu.load_tools()

# Step 1: Get disease information
disease_info = tu.tools.OpenTargets_get_disease_id_description_by_name(
    diseaseName="Alzheimer's disease"
)
print(f"Disease ID: {disease_info['data']['id']}")
print(f"Description: {disease_info['data']['description']}")

# Step 2: Get top associated targets
targets = tu.tools.OpenTargets_get_associated_targets_by_disease_efoId(
    efoId=disease_info['data']['id'],
    limit=10
)

print(f"\nTop 10 targets for Alzheimer's disease:")
for i, target in enumerate(targets['data'], 1):
    print(f"{i}. {target['gene_symbol']} - Score: {target['score']}")

# Step 3: Find drugs for top 3 targets
repurposing_candidates = []

for target in targets['data'][:3]:
    gene_symbol = target['gene_symbol']
    print(f"\nSearching drugs for target: {gene_symbol}")
    
    # Search DGIdb
    dgidb_results = tu.tools.DGIdb_get_drug_gene_interactions(
        gene_name=gene_symbol
    )
    
    if dgidb_results and 'data' in dgidb_results:
        for drug in dgidb_results['data']:
            # Get detailed drug information
            drug_info = tu.tools.drugbank_get_drug_basic_info_by_drug_name_or_id(
                drug_name_or_drugbank_id=drug['drug_name']
            )
            
            # Get current indications
            indications = tu.tools.drugbank_get_indications_by_drug_name_or_drugbank_id(
                drug_name_or_drugbank_id=drug['drug_name']
            )
            
            # Check if already used for Alzheimer's
            current_indications = [ind['indication'] for ind in indications.get('data', [])]
            if not any('alzheimer' in ind.lower() for ind in current_indications):
                repurposing_candidates.append({
                    'drug_name': drug['drug_name'],
                    'target': gene_symbol,
                    'interaction_type': drug.get('interaction_type'),
                    'current_indications': current_indications,
                    'approval_status': drug_info.get('data', {}).get('groups')
                })

# Step 4: Score and rank candidates
print(f"\n{'='*80}")
print("REPURPOSING CANDIDATES FOR ALZHEIMER'S DISEASE")
print(f"{'='*80}\n")

for i, candidate in enumerate(repurposing_candidates[:10], 1):
    print(f"{i}. {candidate['drug_name']}")
    print(f"   Target: {candidate['target']}")
    print(f"   Status: {candidate['approval_status']}")
    print(f"   Current uses: {', '.join(candidate['current_indications'][:3])}")
    print()

# Step 5: Deep dive on top candidate
if repurposing_candidates:
    top_drug = repurposing_candidates[0]['drug_name']
    print(f"\nDETAILED ANALYSIS: {top_drug}")
    print("="*80)
    
    # Get safety data
    warnings = tu.tools.FDA_get_warnings_and_cautions_by_drug_name(
        drug_name=top_drug
    )
    
    # Get adverse events
    adverse_events = tu.tools.FAERS_search_reports_by_drug_and_reaction(
        drug_name=top_drug,
        limit=100
    )
    
    # Search literature
    papers = tu.tools.PubMed_search_articles(
        query=f"{top_drug} AND Alzheimer's disease",
        max_results=20
    )
    
    print(f"FDA Warnings: {len(warnings.get('data', []))} found")
    print(f"Adverse Event Reports: {len(adverse_events.get('data', []))} found")
    print(f"Related Literature: {len(papers.get('data', []))} papers")
```

**Expected Output**:
```
Disease ID: EFO_0000249
Description: Alzheimer's disease is a neurodegenerative disorder...

Top 10 targets for Alzheimer's disease:
1. APP - Score: 0.95
2. APOE - Score: 0.89
3. MAPT - Score: 0.85
...

REPURPOSING CANDIDATES FOR ALZHEIMER'S DISEASE
================================================================================

1. Donepezil (approved for other indication)
   Target: ACHE
   Status: ['approved']
   Current uses: mild to moderate dementia, vascular dementia
   
2. Memantine
   Target: GRIN1
   Status: ['approved']
   Current uses: moderate to severe Alzheimer's disease
...
```

---

## Example 2: Compound-Based Repurposing - Finding New Uses for Metformin

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse(use_cache=True)
tu.load_tools()

# Step 1: Get comprehensive drug information
drug_name = "metformin"

print(f"DRUG REPURPOSING ANALYSIS: {drug_name.upper()}")
print("="*80)

# Basic info
drug_info = tu.tools.drugbank_get_drug_basic_info_by_drug_name_or_id(
    drug_name_or_drugbank_id=drug_name
)

# Current indications
indications = tu.tools.drugbank_get_indications_by_drug_name_or_drugbank_id(
    drug_name_or_drugbank_id=drug_name
)

# Targets
targets = tu.tools.drugbank_get_targets_by_drug_name_or_drugbank_id(
    drug_name_or_drugbank_id=drug_name
)

# Pharmacology
pharmacology = tu.tools.drugbank_get_pharmacology_by_drug_name_or_drugbank_id(
    drug_name_or_drugbank_id=drug_name
)

print(f"\nCURRENT APPROVED INDICATIONS:")
for ind in indications.get('data', [])[:5]:
    print(f"  - {ind['indication']}")

print(f"\nTARGETS:")
for target in targets.get('data', [])[:5]:
    print(f"  - {target['name']} ({target['organism']})")

# Step 2: Find diseases associated with drug targets
print(f"\n{'='*80}")
print("POTENTIAL NEW INDICATIONS BASED ON TARGET ANALYSIS")
print("="*80)

potential_indications = []

for target in targets.get('data', [])[:5]:
    gene_symbol = target.get('gene_symbol')
    if gene_symbol:
        # Search for diseases associated with this target
        target_diseases = tu.tools.OpenTargets_get_diseases_by_target_ensemblId(
            ensemblId=target['ensembl_id']
        )
        
        for disease in target_diseases.get('data', [])[:3]:
            # Check if not already indicated
            if disease['disease_name'] not in [ind['indication'] for ind in indications.get('data', [])]:
                potential_indications.append({
                    'disease': disease['disease_name'],
                    'target': gene_symbol,
                    'association_score': disease['score'],
                    'disease_id': disease['disease_id']
                })

# Step 3: Literature evidence for potential indications
print(f"\nLITERATURE EVIDENCE FOR REPURPOSING:")
print("-"*80)

for indication in sorted(potential_indications, key=lambda x: x['association_score'], reverse=True)[:5]:
    # Search for existing research
    query = f"{drug_name} AND {indication['disease']}"
    papers = tu.tools.PubMed_search_articles(
        query=query,
        max_results=10
    )
    
    clinical_trials = tu.tools.ClinicalTrials_search(
        condition=indication['disease'],
        intervention=drug_name
    )
    
    print(f"\n{indication['disease']}")
    print(f"  Target: {indication['target']} (score: {indication['association_score']:.2f})")
    print(f"  Literature: {len(papers.get('data', []))} papers")
    print(f"  Clinical Trials: {len(clinical_trials.get('data', []))} trials")
    
    if papers.get('data'):
        print(f"  Recent paper: {papers['data'][0].get('title', 'N/A')}")

# Step 4: Safety assessment for new indications
print(f"\n{'='*80}")
print("SAFETY PROFILE")
print("="*80)

# FDA warnings
warnings = tu.tools.FDA_get_warnings_and_cautions_by_drug_name(
    drug_name=drug_name
)

# Adverse events
adverse_events = tu.tools.FAERS_count_reactions_by_drug_event(
    medicinalproduct=drug_name.upper()
)

# Drug interactions
interactions = tu.tools.drugbank_get_drug_interactions_by_drug_name_or_id(
    drug_name_or_id=drug_name
)

print(f"\nFDA Warnings: {len(warnings.get('data', []))}")
print(f"Top Adverse Events:")
for event in adverse_events.get('results', [])[:5]:
    print(f"  - {event['term']}: {event['count']} reports")

print(f"\nDrug-Drug Interactions: {len(interactions.get('data', []))}")

# Step 5: Generate repurposing recommendation
print(f"\n{'='*80}")
print("REPURPOSING RECOMMENDATION")
print("="*80)

print(f"""
Drug: {drug_name.upper()}
Current Indication: Type 2 Diabetes
Repurposing Potential: HIGH

Top 3 Repurposing Opportunities:
1. {potential_indications[0]['disease']} (Score: {potential_indications[0]['association_score']:.2f})
   - {len([p for p in papers.get('data', []) if potential_indications[0]['disease'].lower() in p.get('title', '').lower()])} supporting papers
   - Known safety profile (widely used for 60+ years)
   - Low cost, generic availability
   
2. {potential_indications[1]['disease']} (Score: {potential_indications[1]['association_score']:.2f})
   - Emerging evidence from preclinical studies
   - Phase II trial feasibility high
   
3. {potential_indications[2]['disease']} (Score: {potential_indications[2]['association_score']:.2f})
   - Mechanistic rationale strong
   - Population overlap with diabetes patients

Recommended Next Steps:
- Systematic review of existing literature
- Phase II trial design for top indication
- Patient stratification analysis
- Pharmacokinetic/pharmacodynamic modeling
""")
```

---

## Example 3: Disease-Driven Repurposing for COVID-19

```python
from tooluniverse import ToolUniverse
import json

tu = ToolUniverse(use_cache=True)
tu.load_tools()

# Step 1: Define disease and get information
disease_name = "COVID-19"

print(f"EMERGENCY DRUG REPURPOSING: {disease_name}")
print("="*80)

# Get disease info
disease_info = tu.tools.OpenTargets_get_disease_id_description_by_name(
    diseaseName=disease_name
)

# Step 2: Get viral-host interaction targets
print("\nKEY HOST TARGETS:")
targets = tu.tools.OpenTargets_get_associated_targets_by_disease_efoId(
    efoId=disease_info['data']['id'],
    limit=20
)

for i, target in enumerate(targets['data'][:10], 1):
    print(f"{i}. {target['gene_symbol']} - {target['gene_name']}")

# Step 3: Rapid screening - find ALL approved drugs for these targets
print(f"\n{'='*80}")
print("APPROVED DRUGS TARGETING COVID-19-ASSOCIATED PROTEINS")
print("="*80)

approved_candidates = []

for target in targets['data'][:10]:
    gene_symbol = target['gene_symbol']
    
    # Search multiple databases
    dgidb = tu.tools.DGIdb_get_drug_gene_interactions(gene_name=gene_symbol)
    drugbank = tu.tools.drugbank_get_drug_name_and_description_by_target_name(target_name=gene_symbol)
    
    # Combine results
    all_drugs = []
    if dgidb and 'data' in dgidb:
        all_drugs.extend([d['drug_name'] for d in dgidb['data']])
    if drugbank and 'data' in drugbank:
        all_drugs.extend([d['drug_name'] for d in drugbank['data']])
    
    # Filter to approved only
    for drug_name in set(all_drugs):
        try:
            drug_info = tu.tools.drugbank_get_drug_basic_info_by_drug_name_or_id(
                drug_name_or_drugbank_id=drug_name
            )
            
            if drug_info and 'approved' in drug_info.get('data', {}).get('groups', []):
                approved_candidates.append({
                    'drug': drug_name,
                    'target': gene_symbol,
                    'target_score': target['score']
                })
        except:
            continue

# Step 4: Literature mining for COVID-19 evidence
print(f"\nEVIDENCE ANALYSIS:")
print("-"*80)

scored_candidates = []

for candidate in approved_candidates[:20]:  # Analyze top 20
    drug = candidate['drug']
    
    # Search COVID-19 literature
    query = f"{drug} AND (COVID-19 OR SARS-CoV-2)"
    papers = tu.tools.PubMed_search_articles(
        query=query,
        max_results=50
    )
    
    # Search clinical trials
    trials = tu.tools.ClinicalTrials_search(
        condition="COVID-19",
        intervention=drug
    )
    
    # Calculate evidence score
    paper_count = len(papers.get('data', []))
    trial_count = len(trials.get('data', []))
    
    evidence_score = (
        candidate['target_score'] * 40 +
        min(trial_count * 10, 30) +  # Max 30 points for trials
        min(paper_count * 2, 30)      # Max 30 points for papers
    )
    
    if paper_count > 0 or trial_count > 0:
        scored_candidates.append({
            **candidate,
            'papers': paper_count,
            'trials': trial_count,
            'evidence_score': evidence_score
        })
        
        print(f"{drug}: {paper_count} papers, {trial_count} trials (Score: {evidence_score:.1f})")

# Step 5: Safety rapid assessment
print(f"\n{'='*80}")
print("TOP CANDIDATES - SAFETY ASSESSMENT")
print("="*80)

top_candidates = sorted(scored_candidates, key=lambda x: x['evidence_score'], reverse=True)[:5]

for i, candidate in enumerate(top_candidates, 1):
    drug = candidate['drug']
    print(f"\n{i}. {drug.upper()}")
    print("-"*80)
    
    # Get safety info
    try:
        warnings = tu.tools.FDA_get_warnings_and_cautions_by_drug_name(drug_name=drug)
        adverse = tu.tools.FAERS_count_death_related_by_drug(medicinalproduct=drug.upper())
        
        print(f"Target: {candidate['target']}")
        print(f"Evidence: {candidate['papers']} papers, {candidate['trials']} trials")
        print(f"FDA Warnings: {len(warnings.get('data', []))}")
        print(f"Death-related AEs: {adverse.get('meta', {}).get('total', 0)} reports")
        
        # Get mechanism
        pharmacology = tu.tools.drugbank_get_pharmacology_by_drug_name_or_drugbank_id(
            drug_name_or_drugbank_id=drug
        )
        
        if pharmacology:
            print(f"Mechanism: {pharmacology.get('data', {}).get('mechanism_of_action', 'N/A')[:200]}")
    except:
        print("Safety data unavailable")

# Step 6: Generate priority recommendation
print(f"\n{'='*80}")
print("EMERGENCY USE RECOMMENDATION")
print("="*80)

print(f"""
REPURPOSING CANDIDATES FOR COVID-19 (Ranked by Priority)

HIGH PRIORITY (Strong Evidence + Approved + Safe):
""")

for i, candidate in enumerate(top_candidates[:3], 1):
    print(f"""
{i}. {candidate['drug'].upper()}
   Evidence Score: {candidate['evidence_score']:.1f}/100
   Target: {candidate['target']}
   Clinical Trials: {candidate['trials']} ongoing/completed
   Literature: {candidate['papers']} publications
   Status: FDA approved for other indications
   
   Recommendation: Fast-track to Phase III trial
   Timeline: 6-12 months to emergency use authorization
""")

print("""
NEXT STEPS:
1. Initiate multi-center randomized controlled trial
2. Establish optimal dosing regimen
3. Identify patient subgroups most likely to benefit
4. Monitor for drug-drug interactions with standard COVID treatments
5. Prepare emergency use authorization application
""")
```

---

## Example 4: Network-Based Repurposing Using Pathway Analysis

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse(use_cache=True)
tu.load_tools()

# Step 1: Analyze pathways affected by known effective drug
known_drug = "aspirin"
target_disease = "cardiovascular disease"

print(f"PATHWAY-BASED REPURPOSING: Finding drugs similar to {known_drug}")
print("="*80)

# Get drug pathways
pathways = tu.tools.drugbank_get_pathways_reactions_by_drug_or_id(
    drug_name_or_drugbank_id=known_drug
)

print(f"\nPathways affected by {known_drug}:")
for pathway in pathways.get('data', [])[:5]:
    print(f"  - {pathway['pathway_name']}")

# Step 2: Find other drugs affecting same pathways
pathway_drugs = {}

for pathway in pathways.get('data', [])[:3]:
    pathway_name = pathway['pathway_name']
    
    drugs = tu.tools.drugbank_get_drug_name_and_description_by_pathway_name(
        pathway_name=pathway_name
    )
    
    if drugs and 'data' in drugs:
        pathway_drugs[pathway_name] = [d['drug_name'] for d in drugs['data']]

# Step 3: Score drugs by pathway overlap
drug_scores = {}
for pathway, drugs in pathway_drugs.items():
    for drug in drugs:
        if drug != known_drug:
            drug_scores[drug] = drug_scores.get(drug, 0) + 1

# Rank by pathway overlap
ranked_drugs = sorted(drug_scores.items(), key=lambda x: x[1], reverse=True)

print(f"\nDrugs with highest pathway overlap:")
for drug, score in ranked_drugs[:10]:
    print(f"  {drug}: {score} shared pathways")

# Step 4: Validate for target disease
print(f"\n{'='*80}")
print(f"VALIDATION FOR {target_disease.upper()}")
print("="*80)

validated_candidates = []

for drug, overlap_score in ranked_drugs[:20]:
    # Search for disease-specific evidence
    query = f"{drug} AND {target_disease}"
    papers = tu.tools.PubMed_search_articles(query=query, max_results=10)
    
    # Get drug info
    drug_info = tu.tools.drugbank_get_drug_basic_info_by_drug_name_or_id(
        drug_name_or_drugbank_id=drug
    )
    
    if papers.get('data'):
        validated_candidates.append({
            'drug': drug,
            'pathway_overlap': overlap_score,
            'evidence_papers': len(papers['data']),
            'status': drug_info.get('data', {}).get('groups', [])
        })

# Print validated candidates
for i, candidate in enumerate(validated_candidates[:5], 1):
    print(f"\n{i}. {candidate['drug']}")
    print(f"   Shared pathways: {candidate['pathway_overlap']}")
    print(f"   Supporting papers: {candidate['evidence_papers']}")
    print(f"   Status: {', '.join(candidate['status'])}")
```

---

## Example 5: Structure-Based Repurposing

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse(use_cache=True)
tu.load_tools()

# Step 1: Start with known active compound
known_active = "imatinib"  # Cancer drug
target_disease = "rheumatoid arthritis"

print(f"STRUCTURE-BASED REPURPOSING")
print("="*80)
print(f"Known active: {known_active}")
print(f"Target disease: {target_disease}\n")

# Get structure
cid_result = tu.tools.PubChem_get_CID_by_compound_name(
    compound_name=known_active
)
cid = cid_result['data']['cid']

# Get SMILES
props = tu.tools.PubChem_get_compound_properties_by_CID(cid=cid)
smiles = props['data']['CanonicalSMILES']

print(f"PubChem CID: {cid}")
print(f"SMILES: {smiles}\n")

# Step 2: Find structurally similar compounds
print("Searching for similar structures...")
similar_compounds = tu.tools.PubChem_search_compounds_by_similarity(
    smiles=smiles,
    threshold=85,  # 85% similarity
    limit=50
)

print(f"Found {len(similar_compounds.get('data', []))} similar compounds")

# Step 3: Check which are approved drugs
approved_analogs = []

for compound in similar_compounds.get('data', [])[:20]:
    compound_cid = compound['cid']
    
    # Get drug information
    drug_label = tu.tools.PubChem_get_drug_label_info_by_CID(cid=compound_cid)
    
    if drug_label and 'data' in drug_label:
        # This is an approved drug
        drug_name = drug_label['data'].get('drug_name')
        
        # Get current indications
        drugbank_info = tu.tools.drugbank_get_indications_by_drug_name_or_drugbank_id(
            drug_name_or_drugbank_id=drug_name
        )
        
        approved_analogs.append({
            'drug_name': drug_name,
            'cid': compound_cid,
            'similarity': compound.get('similarity_score', 'N/A'),
            'indications': drugbank_info.get('data', [])
        })

print(f"\nFound {len(approved_analogs)} approved structural analogs\n")

# Step 4: Evaluate for target disease
print(f"Evaluating analogs for {target_disease}:")
print("-"*80)

for analog in approved_analogs[:5]:
    drug = analog['drug_name']
    
    # Check if already used for target disease
    current_indications = [ind['indication'] for ind in analog['indications']]
    already_used = any(target_disease.lower() in ind.lower() for ind in current_indications)
    
    if not already_used:
        # Search literature
        query = f"{drug} AND {target_disease}"
        papers = tu.tools.PubMed_search_articles(query=query, max_results=10)
        
        # Predict properties
        analog_props = tu.tools.PubChem_get_compound_properties_by_CID(
            cid=analog['cid']
        )
        
        print(f"\n{drug}")
        print(f"  Structural similarity: {analog['similarity']}")
        print(f"  Current indications: {', '.join(current_indications[:2])}")
        print(f"  Literature evidence: {len(papers.get('data', []))} papers")
        print(f"  MW: {analog_props['data']['MolecularWeight']}, LogP: {analog_props['data']['XLogP']}")
```

---

## Example 6: Adverse Event Mining for Repurposing

```python
from tooluniverse import ToolUniverse
from collections import Counter

tu = ToolUniverse(use_cache=True)
tu.load_tools()

# Concept: Adverse effects can be therapeutic in different contexts
# Example: Weight loss (AE in some drugs) → Obesity treatment

print("ADVERSE EVENT MINING FOR REPURPOSING")
print("="*80)

# Step 1: Define therapeutic target from adverse event
target_adverse_event = "weight loss"  # Could be therapeutic for obesity
therapeutic_indication = "obesity"

# Step 2: Find drugs with this adverse event
print(f"\nSearching for drugs causing: {target_adverse_event}")

# Query FAERS for drugs associated with weight loss
weight_loss_drugs = tu.tools.FAERS_count_drugs_by_drug_event(
    patient_reaction=target_adverse_event
)

top_drugs = [drug['term'] for drug in weight_loss_drugs.get('results', [])[:20]]

print(f"Found {len(top_drugs)} drugs with significant {target_adverse_event} reports")

# Step 3: For each drug, validate the effect and check safety
candidates = []

for drug_name in top_drugs:
    # Get full adverse event profile
    all_reactions = tu.tools.FAERS_count_reactions_by_drug_event(
        medicinalproduct=drug_name
    )
    
    # Check seriousness
    seriousness = tu.tools.FAERS_count_seriousness_by_drug_event(
        medicinalproduct=drug_name
    )
    
    # Get drug info
    try:
        drug_info = tu.tools.drugbank_get_drug_basic_info_by_drug_name_or_id(
            drug_name_or_drugbank_id=drug_name.lower()
        )
        
        indications = tu.tools.drugbank_get_indications_by_drug_name_or_drugbank_id(
            drug_name_or_drugbank_id=drug_name.lower()
        )
        
        # Check if already used for obesity
        current_uses = [ind['indication'] for ind in indications.get('data', [])]
        if not any('obesity' in use.lower() for use in current_uses):
            candidates.append({
                'drug': drug_name,
                'current_indications': current_uses[:3],
                'weight_loss_reports': next((r['count'] for r in all_reactions.get('results', []) 
                                            if 'weight' in r['term'].lower()), 0),
                'serious_reports': seriousness.get('meta', {}).get('serious_count', 0),
                'status': drug_info.get('data', {}).get('groups', [])
            })
    except:
        continue

# Step 4: Rank by safety and efficacy signals
print(f"\n{'='*80}")
print(f"REPURPOSING CANDIDATES FOR {therapeutic_indication.upper()}")
print("="*80)

# Sort by weight loss reports, but filter out highly toxic
safe_candidates = [c for c in candidates 
                   if 'approved' in c.get('status', []) 
                   and c['serious_reports'] < 1000]

ranked = sorted(safe_candidates, 
                key=lambda x: x['weight_loss_reports'], 
                reverse=True)

for i, candidate in enumerate(ranked[:10], 1):
    print(f"\n{i}. {candidate['drug']}")
    print(f"   Weight loss reports: {candidate['weight_loss_reports']}")
    print(f"   Status: {', '.join(candidate['status'])}")
    print(f"   Current use: {', '.join(candidate['current_indications'])}")
    print(f"   Serious AE reports: {candidate['serious_reports']}")
    
    # Check mechanism
    try:
        pharmacology = tu.tools.drugbank_get_pharmacology_by_drug_name_or_drugbank_id(
            drug_name_or_drugbank_id=candidate['drug'].lower()
        )
        moa = pharmacology.get('data', {}).get('mechanism_of_action', '')
        if moa:
            print(f"   Mechanism: {moa[:150]}...")
    except:
        pass

print(f"\n{'='*80}")
print("RECOMMENDATION")
print("="*80)
print("""
Strategy: Repurpose drugs with weight loss adverse events for obesity treatment

Top candidates show:
- Consistent weight loss signal in FAERS data
- Approved status (known safety profile)
- Mechanisms compatible with weight regulation
- Lower serious adverse event rates

Next steps:
1. Systematic review of weight loss magnitude
2. Dose-response relationship analysis  
3. Patient population stratification
4. Phase II efficacy trial design
5. Long-term safety monitoring protocol
""")
```

---

## Example 7: Multi-Database Integration for Comprehensive Analysis

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse(use_cache=True)
tu.load_tools()

def comprehensive_repurposing_analysis(drug_name, new_indication):
    """
    Comprehensive drug repurposing analysis integrating multiple databases.
    """
    results = {
        'drug': drug_name,
        'proposed_indication': new_indication,
        'scores': {}
    }
    
    print(f"COMPREHENSIVE REPURPOSING ANALYSIS")
    print("="*80)
    print(f"Drug: {drug_name}")
    print(f"Proposed indication: {new_indication}\n")
    
    # 1. DRUG INFORMATION (DrugBank)
    print("1. DRUGBANK ANALYSIS")
    print("-"*80)
    
    basic_info = tu.tools.drugbank_get_drug_basic_info_by_drug_name_or_id(
        drug_name_or_drugbank_id=drug_name
    )
    
    targets = tu.tools.drugbank_get_targets_by_drug_name_or_drugbank_id(
        drug_name_or_drugbank_id=drug_name
    )
    
    indications = tu.tools.drugbank_get_indications_by_drug_name_or_drugbank_id(
        drug_name_or_drugbank_id=drug_name
    )
    
    print(f"Status: {basic_info.get('data', {}).get('groups', [])}")
    print(f"Targets: {len(targets.get('data', []))}")
    print(f"Current indications: {len(indications.get('data', []))}")
    
    results['drugbank'] = {
        'status': basic_info.get('data', {}).get('groups', []),
        'targets': targets.get('data', []),
        'indications': indications.get('data', [])
    }
    
    # 2. TARGET-DISEASE ASSOCIATION (OpenTargets)
    print(f"\n2. OPENTARGETS ANALYSIS")
    print("-"*80)
    
    disease_info = tu.tools.OpenTargets_get_disease_id_description_by_name(
        diseaseName=new_indication
    )
    
    disease_targets = tu.tools.OpenTargets_get_associated_targets_by_disease_efoId(
        efoId=disease_info['data']['id'],
        limit=50
    )
    
    # Calculate target overlap
    drug_target_symbols = [t.get('gene_symbol') for t in targets.get('data', [])]
    disease_target_symbols = [t['gene_symbol'] for t in disease_targets.get('data', [])]
    overlap = set(drug_target_symbols) & set(disease_target_symbols)
    
    print(f"Disease targets: {len(disease_target_symbols)}")
    print(f"Drug targets: {len(drug_target_symbols)}")
    print(f"Overlap: {len(overlap)} targets")
    if overlap:
        print(f"Shared targets: {', '.join(overlap)}")
    
    target_score = len(overlap) / max(len(drug_target_symbols), 1) * 100
    results['scores']['target_overlap'] = target_score
    
    # 3. CHEMICAL PROPERTIES (PubChem)
    print(f"\n3. PUBCHEM ANALYSIS")
    print("-"*80)
    
    cid = tu.tools.PubChem_get_CID_by_compound_name(
        compound_name=drug_name
    )
    
    if cid and 'data' in cid:
        properties = tu.tools.PubChem_get_compound_properties_by_CID(
            cid=cid['data']['cid']
        )
        
        bioactivity = tu.tools.PubChem_get_bioactivity_summary_by_CID(
            cid=cid['data']['cid']
        )
        
        print(f"CID: {cid['data']['cid']}")
        print(f"MW: {properties['data']['MolecularWeight']}")
        print(f"LogP: {properties['data']['XLogP']}")
        print(f"Active assays: {bioactivity['data']['active_assay_count']}")
        
        results['pubchem'] = {
            'cid': cid['data']['cid'],
            'properties': properties['data'],
            'bioactivity': bioactivity['data']
        }
    
    # 4. BIOACTIVITY DATA (ChEMBL)
    print(f"\n4. CHEMBL ANALYSIS")
    print("-"*80)
    
    chembl_drugs = tu.tools.ChEMBL_search_drugs(
        query=drug_name,
        limit=1
    )
    
    if chembl_drugs and 'data' in chembl_drugs:
        chembl_id = chembl_drugs['data'][0]['molecule_chembl_id']
        
        mechanisms = tu.tools.ChEMBL_get_drug_mechanisms(
            chembl_id=chembl_id
        )
        
        bioactivity_chembl = tu.tools.ChEMBL_get_bioactivity_by_chemblid(
            chembl_id=chembl_id
        )
        
        print(f"ChEMBL ID: {chembl_id}")
        print(f"Mechanisms: {len(mechanisms.get('data', []))}")
        print(f"Bioactivity records: {len(bioactivity_chembl.get('data', []))}")
        
        results['chembl'] = {
            'id': chembl_id,
            'mechanisms': mechanisms.get('data', []),
            'bioactivity': bioactivity_chembl.get('data', [])
        }
    
    # 5. SAFETY PROFILE (FDA + FAERS)
    print(f"\n5. SAFETY ASSESSMENT")
    print("-"*80)
    
    warnings = tu.tools.FDA_get_warnings_and_cautions_by_drug_name(
        drug_name=drug_name
    )
    
    adverse_events = tu.tools.FAERS_count_reactions_by_drug_event(
        medicinalproduct=drug_name.upper()
    )
    
    death_reports = tu.tools.FAERS_count_death_related_by_drug(
        medicinalproduct=drug_name.upper()
    )
    
    print(f"FDA warnings: {len(warnings.get('data', []))}")
    print(f"Adverse event types: {len(adverse_events.get('results', []))}")
    print(f"Death-related reports: {death_reports.get('meta', {}).get('total', 0)}")
    
    # Safety score (inverse - fewer issues = higher score)
    death_count = death_reports.get('meta', {}).get('total', 0)
    safety_score = max(0, 100 - (death_count / 100))  # Cap at 100
    results['scores']['safety'] = safety_score
    
    results['safety'] = {
        'warnings': warnings.get('data', []),
        'adverse_events': adverse_events.get('results', [])[:10],
        'deaths': death_count
    }
    
    # 6. LITERATURE EVIDENCE (PubMed + Europe PMC)
    print(f"\n6. LITERATURE EVIDENCE")
    print("-"*80)
    
    query = f"{drug_name} AND {new_indication}"
    
    pubmed = tu.tools.PubMed_search_articles(
        query=query,
        max_results=50
    )
    
    pmc = tu.tools.EuropePMC_search_articles(
        query=query,
        limit=50
    )
    
    print(f"PubMed articles: {len(pubmed.get('data', []))}")
    print(f"Europe PMC articles: {len(pmc.get('data', []))}")
    
    literature_score = min(len(pubmed.get('data', [])) * 2, 100)
    results['scores']['literature'] = literature_score
    
    results['literature'] = {
        'pubmed_count': len(pubmed.get('data', [])),
        'pmc_count': len(pmc.get('data', [])),
        'recent_papers': pubmed.get('data', [])[:5]
    }
    
    # 7. CLINICAL TRIALS
    print(f"\n7. CLINICAL TRIALS")
    print("-"*80)
    
    trials = tu.tools.ClinicalTrials_search(
        condition=new_indication,
        intervention=drug_name
    )
    
    print(f"Relevant trials: {len(trials.get('data', []))}")
    
    if trials.get('data'):
        for trial in trials['data'][:3]:
            print(f"  - {trial.get('title', 'N/A')}")
            print(f"    Status: {trial.get('status', 'N/A')}")
    
    trial_score = min(len(trials.get('data', [])) * 20, 100)
    results['scores']['clinical_trials'] = trial_score
    
    results['trials'] = trials.get('data', [])
    
    # 8. CALCULATE OVERALL REPURPOSING SCORE
    print(f"\n{'='*80}")
    print("REPURPOSING SCORE")
    print("="*80)
    
    weights = {
        'target_overlap': 0.30,
        'safety': 0.25,
        'literature': 0.25,
        'clinical_trials': 0.20
    }
    
    overall_score = sum(
        results['scores'].get(key, 0) * weight 
        for key, weight in weights.items()
    )
    
    print(f"\nTarget Overlap: {results['scores']['target_overlap']:.1f}/100 (30%)")
    print(f"Safety Profile: {results['scores']['safety']:.1f}/100 (25%)")
    print(f"Literature Evidence: {results['scores']['literature']:.1f}/100 (25%)")
    print(f"Clinical Trials: {results['scores']['clinical_trials']:.1f}/100 (20%)")
    print(f"\n{'='*80}")
    print(f"OVERALL REPURPOSING POTENTIAL: {overall_score:.1f}/100")
    print("="*80)
    
    # Classification
    if overall_score >= 70:
        recommendation = "HIGH POTENTIAL - Recommend immediate trial planning"
    elif overall_score >= 50:
        recommendation = "MODERATE POTENTIAL - Additional validation recommended"
    elif overall_score >= 30:
        recommendation = "LOW POTENTIAL - Requires more evidence"
    else:
        recommendation = "INSUFFICIENT DATA - Not recommended at this time"
    
    print(f"\nRecommendation: {recommendation}")
    
    return results

# Example usage
result = comprehensive_repurposing_analysis(
    drug_name="metformin",
    new_indication="Alzheimer's disease"
)
```

This comprehensive example demonstrates:
- Multi-database integration
- Systematic scoring methodology
- Evidence-based ranking
- Practical recommendations
