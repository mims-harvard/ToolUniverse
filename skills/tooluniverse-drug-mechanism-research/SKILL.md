---
name: tooluniverse-drug-mechanism-research
description: >
  Drug mechanism of action investigation -- systematic strategy to trace a drug from its primary target
  through pathways to clinical outcomes, identify off-target effects, and combine regulatory labels with
  literature evidence for a complete mechanism picture.
triggers:
  - keywords: [mechanism of action, drug target, pharmacology, pathway, pharmacogenomics, drug interaction, DailyMed, CPIC, MOA, off-target]
  - patterns: ["how does .* work", "mechanism of action", "drug target", "pathway context", "clinical pharmacology", "drug-drug interaction", "pharmacogenomic", "off-target effect"]
---

# Drug Mechanism of Action Investigation

## Investigation Philosophy

Drug mechanism research follows one core question chain:

**Target -> Downstream Effect -> Pathway -> Organ Effect -> Clinical Outcome**

Start with the drug's primary target. What receptor, enzyme, or transporter does it bind? Then trace forward: what does inhibiting/activating that target do immediately? What pathway is disrupted? What organ-level change results? What does the patient experience?

The LLM already knows drug pharmacology. This skill teaches HOW TO INVESTIGATE using available tools, not what mechanisms exist.

## When to Use

- "What is the mechanism of action of [drug]?"
- "What are the molecular targets of [drug]?"
- "Which pathways are affected by [drug]?"
- "What pharmacogenomic interactions exist for [drug]?"
- "What are the off-targets of [drug]?"
- "Compare mechanisms of [drug A] vs [drug B]"

## NOT for (use other skills)

- Drug safety/adverse events profiling -> `tooluniverse-adverse-event-detection`
- Drug repurposing/new indications -> `tooluniverse-drug-repurposing`
- Target druggability assessment -> `tooluniverse-drug-target-validation`
- Network pharmacology/polypharmacology -> `tooluniverse-network-pharmacology`
- CPIC dosing guidelines specifically -> `tooluniverse-pharmacogenomics`

---

## Step 1: Resolve the Drug

Before investigating mechanism, resolve the drug name to a canonical identifier. You need a ChEMBL ID for most downstream queries.

```python
# Resolve drug name to ChEMBL ID
result = tu.tools.OpenTargets_get_drug_id_description_by_name(drugName="metformin")
# Alternative: OpenTargets_get_drug_chembId_by_generic_name(drugName="metformin")

# Get PharmGKB ID (needed for PGx queries)
result = tu.tools.PharmGKB_search_drugs(query="metformin")
```

**Fallback**: If OpenTargets returns no hits, try `PharmGKB_search_drugs` or `ChEMBL_get_drug` with a known ChEMBL ID.

---

## Step 2: Identify the Primary Target

The first question: what does this drug bind to, and what does it do to that target?

Two complementary sources give you this:

```python
# OpenTargets: quick summary of MOA with target gene symbols
moa = tu.tools.OpenTargets_get_drug_mechanisms_of_action_by_chemblId(chemblId="CHEMBL1431")
for row in moa["data"]["drug"]["mechanismsOfAction"]["rows"]:
    print(f"{row['mechanismOfAction']} ({row['actionType']}) -> {row['targetName']}")
    for t in row.get("targets", []):
        print(f"  Target gene: {t['approvedSymbol']} ({t['id']})")

# ChEMBL: detailed MOA with literature references and direct_interaction flag
mechs = tu.tools.ChEMBL_get_drug_mechanisms(drug_chembl_id__exact="CHEMBL1431")
for m in mechs["data"]["mechanisms"]:
    print(f"MOA: {m['mechanism_of_action']}, Direct: {m['direct_interaction']}")
    print(f"  Refs: {[r['ref_id'] for r in m.get('mechanism_refs', [])]}")
```

**Key fields to extract**: action_type (INHIBITOR, AGONIST, ANTAGONIST, etc.), target gene symbol, direct_interaction (boolean), and literature references.

**Known issue**: `OpenTargets_get_associated_targets_by_drug_chemblId` may fail (GraphQL schema change). Extract targets from the MOA results instead.

---

## Step 3: Assess Off-Target Effects

Most drugs bind more than one target at clinical concentrations. After identifying the primary target, ask: what other proteins does this drug interact with? Off-target binding explains many side effects and drug interactions.

```python
# ChEMBL bioactivity data shows binding affinity across targets
activities = tu.tools.ChEMBL_get_target_activities(target_chembl_id__exact="CHEMBL2364")

# STRING interaction partners reveal the target's protein network
partners = tu.tools.STRING_get_interaction_partners(identifiers="PRKAA1", species=9606)
```

**Reasoning strategy**: If ChEMBL MOA lists multiple targets, compare their action types. Same action type across related targets suggests on-pathway polypharmacology. Different action types suggest true off-target effects. The binding affinity (IC50/Ki from bioactivity data) tells you which targets matter at clinical doses -- nanomolar affinity is primary, micromolar is likely off-target.

---

## Step 4: Map to Pathway Context

A drug target does not work in isolation. Map it to its pathway to understand the breadth of effect.

**Key question**: Is the target upstream (affects many downstream genes, broader effects, more side effects) or downstream (narrow, specific effect)?

```python
# KEGG: find gene ID, then get pathways
genes = tu.tools.kegg_find_genes(keyword="PRKAA1", organism="hsa")
pathways = tu.tools.KEGG_get_gene_pathways(gene_id="hsa:5562")

# Reactome: map protein to pathways (needs UniProt ID)
reactome = tu.tools.Reactome_map_uniprot_to_pathways(uniprot_id="Q13131")

# WikiPathways: search by gene symbol
wp = tu.tools.WikiPathways_find_pathways_by_gene(gene="PRKAA1")

# STRING: functional annotations (GO terms, pathway memberships)
annot = tu.tools.STRING_get_functional_annotations(identifiers="PRKAA1", species=9606)
```

**For multi-target drugs**, run pathway enrichment to find convergent pathways:

```python
# Reactome enrichment (space-separated gene list, NOT array)
enrichment = tu.tools.ReactomeAnalysis_pathway_enrichment(identifiers="PRKAA1 PRKAA2 PRKAB1")

# STRING enrichment
enrichment = tu.tools.STRING_functional_enrichment(identifiers="PRKAA1 PRKAA2", species=9606)
```

**Reasoning strategy**: If multiple drug targets converge on the same pathway, that pathway is the drug's true mechanism. If targets are in different pathways, the drug has genuinely multi-pathway effects -- report each separately.

---

## Step 5: Get the Regulatory View (DailyMed)

Drug labels describe WHAT the drug does. This is the FDA-approved mechanism narrative.

DailyMed requires a two-step process: search for the drug to get a `setid`, then parse specific label sections.

```python
# Step 1: Get setid
spls = tu.tools.DailyMed_search_spls(drug_name="metformin")
setid = spls["data"][0]["setid"]

# Step 2: Parse the clinical pharmacology section (MOA, PK/PD, metabolism)
pharmacology = tu.tools.DailyMed_parse_clinical_pharmacology(
    operation="parse_clinical_pharmacology", setid=setid)

# Drug interactions from the label
interactions = tu.tools.DailyMed_parse_drug_interactions(
    operation="parse_drug_interactions", setid=setid)

# Contraindications
contra = tu.tools.DailyMed_parse_contraindications(
    operation="parse_contraindications", setid=setid)
```

**Other DailyMed parse tools**: `DailyMed_parse_adverse_reactions`, `DailyMed_parse_dosing`.

**Reasoning strategy**: The label's clinical pharmacology section often describes the mechanism differently from database entries. The label emphasizes clinically relevant effects; databases emphasize molecular detail. Both perspectives are needed.

---

## Step 6: Check Pharmacogenomics

Pharmacogenomic variants affect how a patient responds to the drug. This matters for mechanism because PGx genes are often the drug's metabolizing enzymes or targets.

```python
# CPIC gene-drug pairs (gold standard for PGx)
pairs = tu.tools.CPIC_search_gene_drug_pairs(gene_symbol="CYP2C19", cpiclevel="A", limit=20)
# Or search by drug
drug_info = tu.tools.CPIC_get_drug_info(name="clopidogrel")

# FDA PGx biomarkers (what's on the label)
fda_pgx = tu.tools.fda_pharmacogenomic_biomarkers(drug_name="clopidogrel", limit=100)
# Or find all drugs affected by a gene
fda_pgx = tu.tools.fda_pharmacogenomic_biomarkers(biomarker="CYP2D6", limit=100)

# PharmGKB gene details
gene_info = tu.tools.PharmGKB_search_genes(query="CYP2C19")
```

**Reasoning strategy**: CPIC Level A/B pairs have strong evidence and actionable guidelines. If a drug has CPIC Level A interactions, those genes are critical to its mechanism (usually metabolizing enzymes or direct targets). FDA PGx biomarkers tell you what's on the approved label.

---

## Step 7: Gather Literature Evidence

Literature describes WHY the mechanism works. Combine with labels (what) for a complete picture.

```python
# PubMed: returns a plain list of article dicts
articles = tu.tools.PubMed_search_articles(
    query="metformin mechanism of action AMPK mitochondrial", limit=10)

# EuropePMC: returns {status, data, metadata}
articles = tu.tools.EuropePMC_search_articles(
    query="metformin mechanism action mitochondrial", limit=10)

# Follow citation chains for seminal papers
citations = tu.tools.EuropePMC_get_citations(source="MED", identifier="12345678")
```

**Search strategy**: Start with "[drug] mechanism of action [primary target]". If the mechanism is debated, add the competing hypotheses as separate queries. Recent reviews (add "review" to query) give the current consensus.

---

## Step 8: Integrate and Report

### Evidence Hierarchy

- **Tier 1 (Regulatory)**: FDA label (DailyMed), CPIC Level A, FDA PGx biomarker
- **Tier 2 (Experimental)**: ChEMBL mechanisms with literature refs, binding data
- **Tier 3 (Database)**: OpenTargets MOA, pathway databases (KEGG/Reactome/WikiPathways)
- **Tier 4 (Literature)**: PubMed/EuropePMC articles

### Report Structure

```
## Drug Mechanism Report: [Drug Name]

### Drug Identity
- ChEMBL ID, PharmGKB ID, approval status

### Primary Mechanism
- Target: [gene symbol], Action: [INHIBITOR/AGONIST/etc.]
- Mechanism narrative (from DailyMed + databases)
- Direct interaction: yes/no

### Off-Target Effects
- Additional targets with action types and binding affinities
- Which off-targets explain known side effects

### Pathway Context
- Key pathways (from KEGG/Reactome/WikiPathways)
- Upstream vs downstream position of target
- Convergent pathways for multi-target drugs

### Pharmacogenomics
- CPIC gene-drug pairs with levels
- FDA PGx biomarkers

### Drug Interactions
- Mechanism-based interactions (enzyme inhibition/induction)
- Key interactions from DailyMed

### Evidence Summary
| Finding | Source | Tier |
|---------|--------|------|
| Primary MOA | ChEMBL + DailyMed | T1/T2 |
| Off-targets | ChEMBL bioactivity | T2 |
| Pathways | KEGG/Reactome | T3 |
| PGx | CPIC/FDA | T1 |
```

---

## Comparing Two Drugs

When comparing mechanisms, run Steps 2-4 for both drugs, then align:

1. **Same target, different action?** (e.g., agonist vs antagonist at the same receptor)
2. **Different targets, same pathway?** (e.g., both affect insulin signaling but at different nodes)
3. **Different pathways entirely?** (e.g., metformin on AMPK vs pioglitazone on PPAR-gamma)

```python
for drug in [("metformin", "CHEMBL1431"), ("pioglitazone", "CHEMBL595")]:
    moa = tu.tools.OpenTargets_get_drug_mechanisms_of_action_by_chemblId(chemblId=drug[1])
    clin = tu.tools.DailyMed_parse_clinical_pharmacology(drug_name=drug[0])
```

---

## Fallback Strategies

| Step | Primary Tool | Fallback |
|------|-------------|----------|
| Drug ID | OpenTargets_get_drug_id_description_by_name | PharmGKB_search_drugs |
| MOA | OpenTargets_get_drug_mechanisms_of_action_by_chemblId | ChEMBL_get_drug_mechanisms |
| Pathways | KEGG_get_gene_pathways | WikiPathways_find_pathways_by_gene, Reactome_map_uniprot_to_pathways |
| PGx | CPIC_search_gene_drug_pairs | fda_pharmacogenomic_biomarkers |
| Clinical info | DailyMed_parse_clinical_pharmacology | OpenTargets_get_drug_description_by_chemblId |
| DDI | DailyMed_parse_drug_interactions | PubMed_search_articles (DDI query) |
| Literature | PubMed_search_articles | EuropePMC_search_articles |

**MetaCyc note**: MetaCyc requires a paid account and is not available. Use KEGG, Reactome, or WikiPathways instead.
