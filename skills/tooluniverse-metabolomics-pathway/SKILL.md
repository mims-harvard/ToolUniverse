---
name: tooluniverse-metabolomics-pathway
description: Metabolomics pathway analysis -- metabolite identification, pathway mapping, disease associations, cross-database enrichment, and enzyme/gene linkage. Connects PubChem, HMDB, MetaCyc, CTD, KEGG, Reactome, MetabolomicsWorkbench, and BridgeDb. Use when users ask about metabolite identification, metabolic pathways, metabolite-disease links, metabolomics data interpretation, or pathway enrichment from metabolite lists.
---

# Metabolomics Pathway Analysis Skill

Systematic metabolomics workflow: identify metabolites, map to metabolic pathways, find disease associations, and connect to enzymes/genes for multi-omics integration.

## When to Use

- "What pathways involve glucose and pyruvate?"
- "Which diseases are associated with elevated homocysteine?"
- "Identify this metabolite from m/z 180.063 and map its pathways"
- "Find metabolic pathways disrupted in phenylketonuria"
- "Get disease associations for a list of metabolites from an MS experiment"
- "What enzymes catalyze the conversion of phenylalanine?"
- "Cross-reference HMDB metabolites with KEGG pathways"

**NOT for** (use other skills instead):
- Drug safety/ADMET profiling -> Use `tooluniverse-chemical-safety`
- Gene enrichment/pathway analysis from gene lists -> Use `tooluniverse-gene-enrichment`
- Drug-target validation -> Use `tooluniverse-drug-target-validation`

---

## Workflow Overview

```
Input (metabolite name, HMDB ID, m/z value, metabolite list)
  |
  v
Phase 0: Metabolite Identification & Resolution
  Resolve names/masses to PubChem CID, HMDB ID, KEGG compound ID
  |
  v
Phase 1: Metabolite Characterization
  Get molecular properties, classification, chemical taxonomy
  |
  v
Phase 2: Pathway Mapping
  MetaCyc pathways, KEGG pathways, Reactome metabolic events
  |
  v
Phase 3: Enzyme & Gene Linkage
  Enzymes catalyzing reactions, genes encoding those enzymes
  |
  v
Phase 4: Disease Associations
  CTD chemical-disease, Metabolite_get_diseases, Reactome disease scores
  |
  v
Phase 5: Cross-Database Enrichment
  MetabolomicsWorkbench studies, BridgeDb cross-references, literature
  |
  v
Phase 6: Report
  Integrated metabolomics pathway report with evidence grading
```

---

## Phase 0: Metabolite Identification & Resolution

Resolve user input to canonical identifiers across databases.

### By Name

**Metabolite_search**: `query` (string REQUIRED), `search_type` (string, "name" or "formula", default "name").
- Returns up to 10 matching compounds from PubChem with CID, name, formula, molecular weight, SMILES.
- Primary entry point for name-based metabolite lookup.

```python
result = tu.tools.Metabolite_search(query="glucose", search_type="name")
# Returns: {status, data: [{cid, name, formula, molecular_weight, smiles}]}
```

**MetabolomicsWorkbench_search_compound_by_name**: `name` (string REQUIRED).
- Cross-reference with Metabolomics Workbench for RefMet classification.

### By Mass/Formula

**MetabolomicsWorkbench_search_by_mz**: `mz` (float REQUIRED), `adduct` (string, e.g., "M+H"), `tolerance` (float).
- Search by mass-to-charge ratio. Uses REFMET database.
- NOTE: Endpoint format is moverz/REFMET/{mz}/{adduct}/{tolerance}.

**MetabolomicsWorkbench_search_by_exact_mass**: `exact_mass` (float REQUIRED), `tolerance` (float).
- Search by exact molecular mass. Uses moverz/REFMET/{mass}/M/{tolerance}.

**Metabolite_search**: with `search_type="formula"` for molecular formula queries (e.g., "C6H12O6").

### By ID

**Metabolite_get_info**: `compound_name` (string), `hmdb_id` (string, e.g., "HMDB0000122"), `pubchem_cid` (int/string).
- Accepts any one of: compound_name, hmdb_id, or pubchem_cid.
- Returns common name, HMDB ID, PubChem CID, InChIKey, molecular formula, classification.

**KEGG_get_compound**: `compound_id` (string REQUIRED, e.g., "C00031" for glucose).
- Returns KEGG compound info including linked pathways, enzymes, reactions.

### ID Cross-Referencing

**BridgeDb_xrefs**: `identifier` (string REQUIRED), `source` (string REQUIRED), `organism` (string), `target` (string, optional).
- Cross-reference metabolite IDs between databases.
- Source codes: "Ch" (HMDB), "Cs" (ChemSpider), "Ck" (KEGG Compound), "Ce" (ChEBI).
- Example: `BridgeDb_xrefs(identifier="HMDB0000122", source="Ch")` to get KEGG, ChEBI, PubChem IDs.

**BridgeDb_search**: `query` (string REQUIRED), `organism` (string).
- Free-text search for metabolite identifiers.

---

## Phase 1: Metabolite Characterization

**Metabolite_get_info**: (see Phase 0) Returns classification, molecular properties.
- Key fields: `super_class`, `class`, `sub_class` (chemical taxonomy), `biological_roles`, `cellular_locations`.

**MetabolomicsWorkbench_get_refmet_info**: `refmet_name` (string REQUIRED).
- Returns RefMet standardized classification: `super_class`, `main_class`, `sub_class`.
- RefMet provides consistent nomenclature across metabolomics databases.

**KEGG_get_compound**: Returns linked enzyme IDs, reaction IDs, and pathway IDs.

---

## Phase 2: Pathway Mapping

### MetaCyc Pathways

**MetaCyc_search_pathways**: `query` (string REQUIRED, e.g., "glycolysis", "TCA cycle").
- Returns pathway IDs and basic info. Use for keyword-based pathway discovery.

**MetaCyc_get_pathway**: `pathway_id` (string REQUIRED, e.g., "GLYCOLYSIS", "PWY-5177").
- Returns pathway details: reactions, enzymes, compounds, URL.

**MetaCyc_get_compound**: `compound_id` (string REQUIRED, e.g., "PYRUVATE").
- Returns compound details including pathways it participates in.

**MetaCyc_get_reaction**: `reaction_id` (string REQUIRED, e.g., "RXN-14500").
- Returns reaction substrates, products, enzymes, and containing pathways.

### KEGG Pathways

**KEGG_get_gene_pathways**: `gene_id` (string REQUIRED, e.g., "hsa:5230" for PGD).
- Returns KEGG pathways containing the gene/enzyme.

**KEGG_get_pathway_genes**: `pathway_id` (string REQUIRED, e.g., "hsa00010" for glycolysis).
- Returns all genes in a KEGG pathway.

### Reactome Pathways

**ReactomeContent_search**: `query` (string REQUIRED), `types` (string, e.g., "Pathway"), `species` (string).
- Search Reactome for metabolic pathways by keyword.

**Reactome_get_pathway**: `id` (string REQUIRED, Reactome stable ID e.g., "R-HSA-70171").
- Returns pathway details including child events and participants.

**ReactomeAnalysis_pathway_enrichment**: `identifiers` (string REQUIRED -- space-separated, NOT array).
- Perform pathway enrichment from a list of identifiers (gene/protein IDs).
- NOTE: identifiers must be space-separated string, not array.

**Reactome_map_uniprot_to_pathways**: `uniprot_id` (string REQUIRED).
- Find pathways containing a specific enzyme/protein.

---

## Phase 3: Enzyme & Gene Linkage

Connect metabolites to the enzymes that process them, and the genes encoding those enzymes.

```python
# From KEGG compound -> linked enzymes
compound = tu.tools.KEGG_get_compound(compound_id="C00031")
# Extract enzyme IDs from response

# From MetaCyc reaction -> enzymes
reaction = tu.tools.MetaCyc_get_reaction(reaction_id="RXN-14500")
# Extract enzyme names/IDs

# Map enzyme UniProt to pathways
pathways = tu.tools.Reactome_map_uniprot_to_pathways(uniprot_id="P06744")

# Get gene information for enzyme
gene_info = tu.tools.MyGene_query_genes(
    query="symbol:GPI",
    species="human",
    fields="symbol,ensembl.gene,entrezgene,name"
)
```

### Key Enzyme-Gene Tools

**CTD_get_chemical_gene_interactions**: `input_terms` (string REQUIRED, chemical name).
- Returns genes that interact with the chemical (enzyme targets, transporters, etc.).
- CTD curates from literature; returns large result sets for common chemicals.

**KEGG_get_gene_pathways**: Find which pathways an enzyme gene participates in.

**BridgeDb_attributes**: `identifier` (string REQUIRED), `source` (string REQUIRED), `organism` (string).
- Get attributes (including gene names) for a metabolite or enzyme identifier.

---

## Phase 4: Disease Associations

### CTD (Comparative Toxicogenomics Database)

**CTD_get_chemical_diseases**: `input_terms` (string REQUIRED, chemical/metabolite name).
- Returns curated chemical-disease associations from literature.
- Provides direct and inferred associations with evidence types.
- NOTE: CTD uses common chemical names (e.g., "glucose", "cholesterol"), MeSH IDs, or CAS RN.

**CTD_get_gene_diseases**: `input_terms` (string REQUIRED, gene name).
- Use after Phase 3 to get disease associations for metabolite-processing genes.

### Metabolite-Disease Tool

**Metabolite_get_diseases**: `compound_name` (string), `hmdb_id` (string), `pubchem_cid` (int/string), `limit` (int, default 50).
- Returns curated disease associations via CTD.
- Accepts any of: compound_name, hmdb_id, or pubchem_cid.

```python
diseases = tu.tools.Metabolite_get_diseases(compound_name="homocysteine", limit=50)
# Returns: {status, data: [{disease_name, disease_id, direct_evidence, inference_gene_symbol}]}
```

### Reactome Disease Scores

**reactome_disease_target_score**: For gene/protein targets linked to metabolites, get disease relevance scores from Reactome.

---

## Phase 5: Cross-Database Enrichment

### Metabolomics Workbench Studies

**MetabolomicsWorkbench_get_study**: `study_id` (string REQUIRED, e.g., "ST000001").
- Get details of metabolomics studies for context.

**MetabolomicsWorkbench_get_compound_by_pubchem_cid**: `pubchem_cid` (int/string REQUIRED).
- Cross-reference PubChem CIDs with Metabolomics Workbench.

### Literature Search

**PubMed_search_articles**: `query` (string REQUIRED), `limit` (int).
- Search for metabolomics studies: e.g., "homocysteine metabolic pathway disease".

**EuropePMC_search_articles**: `query` (string REQUIRED), `limit` (int).
- Broader literature coverage including preprints.

### Enrichment Analysis

For metabolite list enrichment (e.g., from an MS experiment):

1. Convert metabolite names to gene/enzyme IDs using CTD_get_chemical_gene_interactions
2. Run pathway enrichment with ReactomeAnalysis_pathway_enrichment (space-separated identifiers)
3. Alternatively, use KEGG_get_gene_pathways per enzyme gene for KEGG pathway coverage

---

## Tool Parameter Quick Reference

| Tool | Key Params | Notes |
|------|-----------|-------|
| `Metabolite_search` | `query`, `search_type` | search_type: "name" or "formula" |
| `Metabolite_get_info` | `compound_name` or `hmdb_id` or `pubchem_cid` | One identifier required |
| `Metabolite_get_diseases` | `compound_name` or `hmdb_id` or `pubchem_cid`, `limit` | CTD-backed disease lookup |
| `MetaCyc_search_pathways` | `query` | Keyword search for pathways |
| `MetaCyc_get_pathway` | `pathway_id` | e.g., "GLYCOLYSIS", "PWY-5177" |
| `MetaCyc_get_compound` | `compound_id` | e.g., "PYRUVATE", "CPD-1" |
| `MetaCyc_get_reaction` | `reaction_id` | e.g., "RXN-14500" |
| `KEGG_get_compound` | `compound_id` | e.g., "C00031" for glucose |
| `KEGG_get_gene_pathways` | `gene_id` | e.g., "hsa:5230" (organism-prefixed) |
| `KEGG_get_pathway_genes` | `pathway_id` | e.g., "hsa00010" for glycolysis |
| `CTD_get_chemical_diseases` | `input_terms` | Chemical name, MeSH, CAS RN |
| `CTD_get_chemical_gene_interactions` | `input_terms` | Chemical name -> interacting genes |
| `CTD_get_gene_diseases` | `input_terms` | Gene name -> associated diseases |
| `BridgeDb_xrefs` | `identifier`, `source` | Cross-reference IDs. Source: "Ch"=HMDB, "Ck"=KEGG |
| `BridgeDb_search` | `query`, `organism` | Free-text metabolite search |
| `BridgeDb_attributes` | `identifier`, `source`, `organism` | Get attributes for identifier |
| `MetabolomicsWorkbench_search_compound_by_name` | `name` | Search MW by compound name |
| `MetabolomicsWorkbench_get_refmet_info` | `refmet_name` | RefMet classification |
| `MetabolomicsWorkbench_search_by_mz` | `mz`, `adduct`, `tolerance` | m/z-based search |
| `MetabolomicsWorkbench_search_by_exact_mass` | `exact_mass`, `tolerance` | Mass-based search |
| `MetabolomicsWorkbench_get_study` | `study_id` | e.g., "ST000001" |
| `ReactomeContent_search` | `query`, `types`, `species` | Search Reactome content |
| `ReactomeAnalysis_pathway_enrichment` | `identifiers` | Space-separated string, NOT array |
| `Reactome_map_uniprot_to_pathways` | `uniprot_id` | UniProt -> Reactome pathways |

---

## Common Mistakes to Avoid

| Mistake | Correction |
|---------|-----------|
| Passing array to ReactomeAnalysis_pathway_enrichment | `identifiers` must be space-separated string |
| Using HMDB IDs in CTD_get_chemical_diseases | CTD uses common chemical names or MeSH IDs, not HMDB IDs |
| Not resolving metabolite names first | Always start with Metabolite_search to get canonical name and CID |
| Using gene_id without organism prefix for KEGG | KEGG gene IDs need organism prefix: "hsa:5230" not "5230" |
| Expecting HMDB API to work directly | HMDB has no open API; use Metabolite_get_info (PubChem-backed) instead |
| Passing PubChem title to CTD when names differ | CTD may use different names; try both PubChem name and common synonyms |
| MetabolomicsWorkbench exactmass endpoint | Use moverz/REFMET/{mass}/M/{tolerance} format (exactmass endpoint broken) |

---

## Fallback Strategies

- **Metabolite_search returns no results** -> Try MetabolomicsWorkbench_search_compound_by_name or KEGG_get_compound with KEGG ID
- **MetaCyc pathway not found** -> Search KEGG pathways or Reactome pathways instead
- **CTD returns empty for disease** -> Try Metabolite_get_diseases with HMDB ID or PubChem CID
- **No KEGG compound ID** -> Use BridgeDb_xrefs to cross-reference from HMDB or ChEBI
- **MetabolomicsWorkbench exactmass fails** -> Use search_by_mz with M+H adduct and appropriate tolerance
- **Need enzyme genes** -> CTD_get_chemical_gene_interactions returns gene symbols for any chemical

---

## Example Workflows

### Workflow 1: Single Metabolite Deep Analysis (Homocysteine)

```
Step 1: Metabolite_search(query="homocysteine")
  -> Get PubChem CID, molecular formula, SMILES

Step 2: Metabolite_get_info(compound_name="homocysteine")
  -> Get HMDB ID, classification, biological roles

Step 3: MetaCyc_search_pathways(query="homocysteine")
  -> Find pathways: methionine cycle, transsulfuration

Step 4: CTD_get_chemical_gene_interactions(input_terms="homocysteine")
  -> Get enzymes: CBS, MTR, MTHFR, BHMT

Step 5: Metabolite_get_diseases(compound_name="homocysteine")
  -> Get disease associations: hyperhomocysteinemia, cardiovascular disease, neural tube defects

Step 6: KEGG_get_compound(compound_id="C00155")
  -> Get KEGG pathways, linked reactions

Step 7: Report with pathway map, enzyme list, disease associations
```

### Workflow 2: m/z-Based Metabolite Identification

```
Step 1: MetabolomicsWorkbench_search_by_mz(mz=180.063, adduct="M+H", tolerance=0.01)
  -> Candidate metabolites from RefMet

Step 2: For each candidate:
  Metabolite_get_info(compound_name=candidate_name)
  -> Confirm identity, get cross-database IDs

Step 3: MetaCyc_search_pathways(query=confirmed_metabolite)
  -> Map to metabolic pathways

Step 4: CTD_get_chemical_diseases(input_terms=confirmed_metabolite)
  -> Disease relevance
```

### Workflow 3: Metabolite List Pathway Enrichment

```
Step 1: For each metabolite in list:
  Metabolite_search(query=name) -> get canonical name
  CTD_get_chemical_gene_interactions(input_terms=name) -> get enzyme genes

Step 2: Collect unique gene list from all metabolites

Step 3: ReactomeAnalysis_pathway_enrichment(identifiers="GENE1 GENE2 GENE3")
  -> Enriched metabolic pathways

Step 4: For top enriched pathways:
  Reactome_get_pathway(id=pathway_id) -> pathway details

Step 5: Report: enriched pathways, participating metabolites, disease links
```

### Workflow 4: Disease-Focused Metabolite Discovery

```
Step 1: CTD_get_chemical_diseases(input_terms="phenylketonuria")
  -> ERROR: CTD expects chemical input. Instead:

Step 1 (corrected): PubMed_search_articles(query="phenylketonuria metabolomics biomarkers")
  -> Find key metabolites from literature

Step 2: For identified metabolites (phenylalanine, tyrosine):
  Metabolite_get_diseases(compound_name="phenylalanine")
  -> Confirm disease association

Step 3: MetaCyc_search_pathways(query="phenylalanine")
  -> Map disrupted pathways

Step 4: CTD_get_chemical_gene_interactions(input_terms="phenylalanine")
  -> Identify PAH (phenylalanine hydroxylase) and related enzymes

Step 5: CTD_get_gene_diseases(input_terms="PAH")
  -> Confirm gene-disease link
```

---

## Evidence Grading

| Tier | Criteria | Sources |
|------|----------|---------|
| **T1** | Curated disease association with direct evidence | CTD curated, OMIM |
| **T2** | Multiple database pathway concordance | MetaCyc + KEGG + Reactome agreement |
| **T3** | Inferred associations or single-database | CTD inferred, single pathway DB |
| **T4** | Computational prediction or text-mining only | Literature search, RefMet classification |

---

## Limitations

- HMDB has no open API; metabolite info comes from PubChem via Metabolite_get_info.
- MetaCyc pathways are reference pathways (not organism-specific like KEGG).
- CTD chemical-disease associations can be very large for common metabolites (22K+ for acetaminophen).
- MetabolomicsWorkbench exactmass endpoint is broken; use moverz/REFMET instead.
- ReactomeAnalysis_pathway_enrichment expects gene/protein IDs, not metabolite IDs directly.
- Metabolite name discrepancies between PubChem and CTD may require trying synonyms.
- BridgeDb metabolite coverage depends on the metabolite being in the mapping databases.
