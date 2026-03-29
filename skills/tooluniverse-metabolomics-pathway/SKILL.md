---
name: tooluniverse-metabolomics-pathway
description: Metabolomics pathway analysis -- metabolite identification, pathway mapping, disease associations, cross-database enrichment, and enzyme/gene linkage. Connects PubChem, HMDB, MetaCyc, CTD, KEGG, Reactome, MetabolomicsWorkbench, and BridgeDb. Use when users ask about metabolite identification, metabolic pathways, metabolite-disease links, metabolomics data interpretation, or pathway enrichment from metabolite lists.
---

# Metabolomics Pathway Analysis

Identify metabolites, map to metabolic pathways, find disease associations, and connect to enzymes/genes.

## Domain Reasoning

Metabolite-to-pathway mapping requires correct, database-specific identifiers. HMDB IDs link to KEGG/Reactome but must be converted via BridgeDb; PubChem CIDs need explicit cross-referencing. Always verify metabolite identity first: the same common name can refer to structurally distinct isomers, and PubChem names frequently differ from CTD/KEGG names.

## LOOK UP DON'T GUESS

- Pathway membership: call `MetaCyc_get_compound`, `KEGG_get_compound`, or `ReactomeContent_search`
- Cross-database IDs: use `BridgeDb_xrefs`
- Enzyme-metabolite relationships: use `CTD_get_chemical_gene_interactions` or `KEGG_get_compound`
- Disease associations: query `Metabolite_get_diseases` or `CTD_get_chemical_diseases`

---

## COMPUTE, DON'T DESCRIBE
When analysis requires computation (statistics, data processing, scoring, enrichment), write and run Python code via Bash. Don't describe what you would do — execute it and report actual results. Use ToolUniverse tools to retrieve data, then Python (pandas, scipy, statsmodels, matplotlib) to analyze it.

## Workflow

```
Phase 0: Identify & Resolve → Phase 1: Characterize → Phase 2: Pathway Map →
Phase 3: Enzyme/Gene Linkage → Phase 4: Disease Associations → Phase 5: Cross-DB Enrichment → Report
```

---

## Phase 0: Metabolite Identification & Resolution

### By Name
**Metabolite_search**: `query` (REQUIRED), `search_type` ("name"/"formula"). Returns PubChem matches with CID, name, formula, MW, SMILES.
**MetabolomicsWorkbench_search_compound_by_name**: `name` (REQUIRED). Cross-reference with RefMet.

### By Mass/Formula
**MetabolomicsWorkbench_search_by_mz**: `mz` (REQUIRED), `adduct` (e.g., "M+H"), `tolerance`. Uses moverz/REFMET/{mz}/{adduct}/{tolerance}.
**MetabolomicsWorkbench_search_by_exact_mass**: `exact_mass` (REQUIRED), `tolerance`. Uses moverz/REFMET/{mass}/M/{tolerance}.

### By ID
**Metabolite_get_info**: `compound_name`, `hmdb_id` (e.g., "HMDB0000122"), or `pubchem_cid`. Returns HMDB ID, CID, InChIKey, classification.
**KEGG_get_compound**: `compound_id` (e.g., "C00031"). Returns linked pathways, enzymes, reactions.

### ID Cross-Referencing
**BridgeDb_xrefs**: `identifier` (REQUIRED), `source` (REQUIRED: "Ch"=HMDB, "Cs"=ChemSpider, "Ck"=KEGG, "Ce"=ChEBI), `target` (optional).
**BridgeDb_search**: `query` (REQUIRED), `organism`. Free-text metabolite search.

---

## Phase 1: Metabolite Characterization

**Metabolite_get_info**: classification (super_class/class/sub_class), biological_roles, cellular_locations.
**MetabolomicsWorkbench_get_refmet_info**: `refmet_name` (REQUIRED). Standardized RefMet classification.
**KEGG_get_compound**: linked enzyme/reaction/pathway IDs.

---

## Phase 2: Pathway Mapping

### MetaCyc
- `MetaCyc_search_pathways`: `query` (keyword search, e.g., "glycolysis")
- `MetaCyc_get_pathway`: `pathway_id` (e.g., "GLYCOLYSIS") -- reactions, enzymes, compounds
- `MetaCyc_get_compound`: `compound_id` (e.g., "PYRUVATE") -- pathways it participates in
- `MetaCyc_get_reaction`: `reaction_id` -- substrates, products, enzymes

### KEGG
- `KEGG_get_gene_pathways`: `gene_id` (e.g., "hsa:5230") -- pathways for enzyme gene
- `KEGG_get_pathway_genes`: `pathway_id` (e.g., "hsa00010") -- all genes in pathway

### Reactome
- `ReactomeContent_search`: `query`, `types` (e.g., "Pathway"), `species`
- `Reactome_get_pathway`: `id` (e.g., "R-HSA-70171")
- `ReactomeAnalysis_pathway_enrichment`: `identifiers` (space-separated string, NOT array)
- `Reactome_map_uniprot_to_pathways`: `uniprot_id`

---

## Phase 3: Enzyme & Gene Linkage

**CTD_get_chemical_gene_interactions**: `input_terms` (chemical name). Returns interacting genes.
**KEGG_get_gene_pathways**: which pathways an enzyme gene participates in.
**BridgeDb_attributes**: `identifier`, `source`, `organism`. Get attributes for identifier.

Workflow: KEGG compound -> enzyme IDs -> MetaCyc reaction -> enzyme names -> Reactome uniprot -> pathways -> MyGene for gene info.

---

## Phase 4: Disease Associations

**CTD_get_chemical_diseases**: `input_terms` (chemical name, MeSH, CAS RN). Curated associations with direct/inferred evidence.
**CTD_get_gene_diseases**: `input_terms` (gene name). For metabolite-processing genes from Phase 3.
**Metabolite_get_diseases**: `compound_name`/`hmdb_id`/`pubchem_cid`, `limit` (default 50). CTD-backed.

---

## Phase 5: Cross-Database Enrichment

**MetabolomicsWorkbench_get_study**: `study_id` (e.g., "ST000001").
**MetabolomicsWorkbench_get_compound_by_pubchem_cid**: `pubchem_cid`.
**PubMed_search_articles** / **EuropePMC_search_articles**: literature context.

For metabolite list enrichment: (1) convert names to gene/enzyme IDs via CTD, (2) run `ReactomeAnalysis_pathway_enrichment` with space-separated identifiers, (3) use `KEGG_get_gene_pathways` per enzyme.

---

## Common Mistakes to Avoid

| Mistake | Correction |
|---------|-----------|
| Array to ReactomeAnalysis_pathway_enrichment | Must be space-separated string |
| HMDB IDs in CTD_get_chemical_diseases | CTD uses common names or MeSH IDs |
| Not resolving names first | Always start with Metabolite_search |
| gene_id without organism prefix for KEGG | Need "hsa:5230" not "5230" |
| Expecting HMDB API | No open API; use Metabolite_get_info (PubChem-backed) |
| PubChem title to CTD when names differ | Try both PubChem name and common synonyms |
| MetabolomicsWorkbench exactmass | Use moverz/REFMET/{mass}/M/{tolerance} (exactmass broken) |

---

## Fallback Strategies

- **Metabolite_search empty** -> MetabolomicsWorkbench_search_compound_by_name or KEGG_get_compound
- **MetaCyc not found** -> KEGG or Reactome pathways
- **CTD empty for disease** -> Metabolite_get_diseases with HMDB/CID
- **No KEGG compound ID** -> BridgeDb_xrefs from HMDB/ChEBI
- **exactmass fails** -> search_by_mz with M+H adduct
- **Need enzyme genes** -> CTD_get_chemical_gene_interactions

---

## Evidence Grading

| Tier | Criteria | Sources |
|------|----------|---------|
| **T1** | Curated disease association, direct evidence | CTD curated, OMIM |
| **T2** | Multiple database pathway concordance | MetaCyc + KEGG + Reactome agreement |
| **T3** | Inferred or single-database | CTD inferred, single pathway DB |
| **T4** | Computational prediction or text-mining | Literature, RefMet classification |

---

## Limitations

- HMDB has no open API; use Metabolite_get_info (PubChem-backed).
- MetaCyc pathways are reference (not organism-specific like KEGG).
- CTD can return very large sets for common metabolites (22K+ for acetaminophen).
- ReactomeAnalysis expects gene/protein IDs, not metabolite IDs directly.
- BridgeDb coverage depends on the metabolite being in mapping databases.
