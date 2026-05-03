---
name: tooluniverse-lipidomics
description: Analyze lipids, lipid metabolism, and lipid-disease associations using LIPID MAPS, HMDB, PubChem, KEGG, and CTD. Covers lipid identification, classification, pathway mapping, biomarker discovery, and disease links. Distinct from general metabolomics — focuses on lipid-specific biology (membrane composition, signaling lipids, lipoproteins, sphingolipids, eicosanoids). Use when asked about lipid profiling, lipidomics data interpretation, lipid biomarkers, lipid metabolism disorders, or lipid-disease connections.
---

# Lipidomics Analysis

Integrated pipeline for lipid identification, classification, pathway mapping, and disease association analysis. Distinct from general metabolomics because lipids have unique classification systems (LIPID MAPS), specialized pathways (sphingolipid, eicosanoid, steroid), and disease associations (cardiovascular, neurodegeneration, metabolic syndrome).

## Reasoning Strategy

Lipid identification starts with mass spectrometry: the lipid class is determined by the head group fragment mass (e.g., m/z 184 for phosphocholine in positive mode), total chain length and saturation from the precursor exact mass, and individual fatty acid chains from neutral loss or product ion scans. LIPID MAPS classification organizes lipids by chemical structure into 8 categories — knowing the category immediately tells you the likely biological context (sphingolipids → apoptosis/neurodegeneration; glycerophospholipids → membrane remodeling; eicosanoids → inflammation). Structural specificity matters biologically: Cer(d18:1/16:0) and Cer(d18:1/24:1) have different membrane properties and disease associations despite being the same lipid class. Always map changed lipids back to metabolic pathways because lipids are intermediates — an elevated ceramide could mean increased synthesis (CERS activity up), decreased degradation (ASAH1 down), or shunting from sphingomyelin (SMPD1 up).

**LOOK UP DON'T GUESS**: Do not assume a lipid's LIPID MAPS ID, exact mass, or pathway membership — query `LipidMaps_search_by_name` first. Do not guess which diseases are associated with a lipid class; retrieve them from HMDB or CTD.

**Key principles**:
1. **LIPID MAPS classification first** — use the 8-category system (fatty acyls, glycerolipids, glycerophospholipids, sphingolipids, sterol lipids, prenol lipids, saccharolipids, polyketides)
2. **Structural specificity matters** — chain length, unsaturation, and sn-position affect biological function
3. **Connect to pathways** — lipids are metabolic intermediates; always map to biosynthesis/degradation pathways
4. **Disease context** — many lipids are disease biomarkers (sphingolipids in neurodegeneration, oxidized lipids in CVD)
5. **Evidence grading** — T1: clinical biomarker studies, T2: mechanistic studies, T3: association data, T4: computational prediction

---

## When to Use

- "Identify this lipid species from m/z and retention time"
- "What pathways involve ceramide/sphingomyelin?"
- "Lipid biomarkers for Alzheimer's disease"
- "What diseases are associated with altered sphingolipid metabolism?"
- "Map my lipidomics results to KEGG pathways"
- "Compare lipid profiles between conditions"

**Not this skill**: For general metabolomics (amino acids, sugars, organic acids), use `tooluniverse-metabolomics`. For drug ADMET properties, use `tooluniverse-admet-prediction`.

---

## Core Tools

| Tool | Use For |
|------|---------|
| `LipidMaps_search_by_name` | Lipid identification by name, abbreviation, or mass |
| `LipidMaps_get_compound_by_id` | Detailed lipid info (structure, classification, pathways) |
| `HMDB_search` / `HMDB_get_metabolite` | Lipid metabolite details, disease associations |
| `kegg_search_pathway` | Lipid metabolism pathways (keyword=`sphingolipid`, `glycerolipid`, etc.) |
| `KEGG_get_pathway_genes` | Enzymes in lipid pathways |
| `PubChem_get_compound_properties_by_CID` | Chemical properties (mass, formula, SMILES) |
| `CTD_get_gene_diseases` | Gene-disease links for lipid metabolism enzymes |
| `DisGeNET_search_gene` | Disease associations for lipid genes |
| `PubMed_search_articles` | Published lipidomics studies |
| `OpenTargets_get_associated_drugs_by_target_ensemblID` | Drugs targeting lipid metabolism enzymes |

---

## Workflow

```
Phase 0: Lipid Identity Resolution
  Name/mass/abbreviation → LIPID MAPS ID → classification
    |
Phase 1: Structural Classification
  LIPID MAPS 8-category system → subclass → molecular species
    |
Phase 2: Pathway Mapping
  KEGG lipid metabolism → biosynthesis/degradation enzymes
    |
Phase 3: Disease Associations
  CTD/DisGeNET/HMDB → lipid-disease links with evidence
    |
Phase 4: Interpretation & Report
  Biological significance → biomarker potential → recommendations
```

### Phase 0: Lipid Identity Resolution

```
LipidMaps_search_by_name(query="ceramide")  → LMSP ID, exact mass, classification
HMDB_search(compound_name="ceramide")       → HMDB ID, disease links
PubChem_get_CID_by_compound_name(name="ceramide") → CID, SMILES
```

**LIPID MAPS search tips**:
- Generic names work well: "ceramide", "sphingomyelin", "phosphatidylcholine"
- Species-level abbreviations like "Cer(d18:1/16:0)" may return 0 results — use the generic class name first, then filter by chain length from results
- For exact mass search: use `LipidMaps_search_by_formula` with molecular formula (e.g., "C34H67NO3")
- If name search fails, try PubChem: `PubChem_get_CID_by_compound_name(name="C16 Ceramide")` then cross-reference

### Phase 1: Structural Classification

Use `LipidMaps_get_compound_by_id` to retrieve the LIPID MAPS 8-category classification (FA, GL, GP, SP, ST, PR, SL, PK) for any lipid. The category immediately signals biological context: SP (sphingolipids) → apoptosis/neurodegeneration; GP (glycerophospholipids) → membrane remodeling; FA-derived eicosanoids → inflammation.

### Phase 2: Pathway Mapping

Key lipid metabolism pathways in KEGG:

| Pathway | KEGG ID | Key Enzymes | Disease Relevance |
|---------|---------|-------------|-------------------|
| Sphingolipid metabolism | hsa00600 | SMPD1, CERS1-6, ASAH1 | Niemann-Pick, Fabry, Gaucher |
| Glycerophospholipid metabolism | hsa00564 | PLA2, LPCAT, LPIN | Barth syndrome, atherosclerosis |
| Arachidonic acid metabolism | hsa00590 | COX1/2, LOX, CYP450 | Inflammation, asthma, CVD |
| Steroid biosynthesis | hsa00100 | HMGCR, CYP51A1, DHCR7 | Hypercholesterolemia, Smith-Lemli-Opitz |
| Fatty acid biosynthesis | hsa00061 | FASN, ACC, SCD | Obesity, NAFLD, cancer |
| Fatty acid degradation | hsa00071 | CPT1, ACADM, HADHA | MCAD deficiency, VLCAD deficiency |
| Bile acid biosynthesis | hsa00120 | CYP7A1, CYP27A1 | Cholestasis, gallstones |
| Ether lipid metabolism | hsa00565 | AGPS, GNPAT | Rhizomelic chondrodysplasia |

```python
# Map lipids to pathways
kegg_search_pathway(keyword="sphingolipid")  # → hsa00600
KEGG_get_pathway_genes(pathway_id="hsa00600")  # → SMPD1, CERS1, ...
```

### Phase 3: Disease Associations

For each lipid or lipid enzyme, check disease links:

```python
CTD_get_gene_diseases(input_terms="SMPD1")  # sphingomyelinase → Niemann-Pick
DisGeNET_search_gene(gene="SMPD1")  # broader disease associations
HMDB_get_metabolite(compound_name="ceramide")  # metabolite-disease links
PubMed_search_articles(query="ceramide biomarker Alzheimer")  # clinical evidence
```

**Disease context**: Ceramide elevation → apoptosis, Alzheimer's, insulin resistance. Sphingomyelin depletion → Niemann-Pick. Oxidized phospholipids → CVD. Altered bile acid ratios → NAFLD, cholestasis. Eicosanoid elevation → inflammation. Always verify via HMDB or CTD rather than relying on memory.

### Phase 4: Interpretation & Report

**Computational procedure: Lipid class enrichment analysis**

```python
# When user provides a list of significantly changed lipids
import pandas as pd
from scipy.stats import fisher_exact

# Input: list of changed lipids with LIPID MAPS categories
changed = pd.DataFrame({
    'lipid': ['Cer(d18:1/16:0)', 'SM(d18:1/16:0)', 'PC(16:0/18:1)', 'LPC(18:0)'],
    'category': ['SP', 'SP', 'GP', 'GP'],
    'direction': ['up', 'down', 'unchanged', 'up'],
    'fold_change': [2.1, 0.5, 1.1, 1.8]
})

# Count changed vs unchanged per category
from collections import Counter
changed_cats = Counter(changed[changed['direction'] != 'unchanged']['category'])
total_cats = Counter(changed['category'])

# Report
print("Lipid class enrichment:")
for cat in total_cats:
    n_changed = changed_cats.get(cat, 0)
    n_total = total_cats[cat]
    print(f"  {cat}: {n_changed}/{n_total} changed")

# Interpretation
if changed_cats.get('SP', 0) / max(total_cats.get('SP', 1), 1) > 0.5:
    print("→ Sphingolipid metabolism is significantly altered")
    print("  Consider: apoptosis, neurodegeneration, insulin resistance")
```

**Report structure**:
1. **Lipid Identity** — LIPID MAPS classification, structural features
2. **Pathway Context** — which metabolic pathways are affected
3. **Disease Associations** — evidence-graded disease links
4. **Biomarker Assessment** — clinical utility of identified lipid changes
5. **Mechanistic Model** — how lipid changes connect to disease biology
6. **Recommendations** — validation experiments, clinical follow-up

---

## Limitations

- **No raw MS data processing** — this skill interprets identified lipids, not raw spectra. Use LipidSearch, MS-DIAL, or LipiDex for identification first.
- **LIPID MAPS coverage** — some rare or novel lipid species may not be in the database
- **Quantitative thresholds** — fold-change cutoffs are context-dependent; the skill provides frameworks, not universal thresholds
- **Species-specific** — most disease data is human; rat/mouse lipid metabolism can differ significantly
