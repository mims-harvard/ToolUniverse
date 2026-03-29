---
name: tooluniverse-gpcr-structural-pharmacology
description: >
  Research GPCR receptors, antibody structures, and protein interface analysis using GPCRdb, SAbDab, and PDBePISA. Retrieves receptor families, known ligands (agonists/antagonists/biased), mutations, crystal/cryo-EM structures, antibody CDR annotations, and protein-protein interface geometry. Use when asked about GPCR drug targets, receptor-ligand interactions, antibody structural data, or protein assembly interfaces.
---

# GPCR and Structural Pharmacology Research

**GPCR pharmacology**: agonist vs antagonist vs inverse agonist vs biased agonist — each has different clinical implications. Biased agonism (preferential G-protein vs β-arrestin signaling) can separate efficacy from side effects; for example, G-protein-biased opioid agonists aim to retain analgesia while reducing β-arrestin-mediated respiratory depression. Always classify retrieved ligands by their pharmacological type, not just their chemical structure. Receptor state (active vs inactive crystal structure) determines which ligands and mutations are interpretable — an inactive-state structure is appropriate for antagonist binding analysis, active-state for agonist-bound complexes. Generic GPCR numbering (Ballesteros-Weinstein) enables cross-receptor mutation comparison; always report positions in this system alongside sequence positions.

**LOOK UP DON'T GUESS**: never assume GPCRdb entry names (e.g., `adrb2_human`) or PDB IDs — always use `GPCRdb_list_proteins` to find the correct entry name and `GPCRdb_get_structures` to confirm available structures.

Research skill integrating GPCRdb (GPCR receptor biology), SAbDab (antibody structures), and PDBePISA (protein interface analysis) to support structural pharmacology, antibody engineering, and GPCR-targeted drug discovery.

**KEY PRINCIPLES**:
1. **Receptor-first** — Identify GPCR entry name before any GPCRdb queries
2. **Ligand classification** — Distinguish agonists, antagonists, partial agonists, biased agonists
3. **Structure-guided** — Pair GPCRdb mutation data with PDB structures via PDBePISA
4. **Antibody context** — Use SAbDab for therapeutic antibody structure retrieval and CDR analysis
5. **English-first queries** — Use standard receptor names (e.g., "beta-2 adrenergic receptor") in searches; convert to GPCRdb entry names for API calls

---

## When to Use

Apply when user asks:
- "What ligands are known for [GPCR receptor]?"
- "What crystal structures exist for [receptor]?"
- "Find antibody structures targeting [antigen]"
- "Analyze the protein-protein interface in PDB [ID]"
- "What mutations affect [GPCR] function or pharmacology?"
- "Which GPCRs are in the [family] family?"
- "What are the CDR loops in antibody PDB [ID]?"
- "What is the biological assembly for [PDB ID]?"

---

## Tool Parameter Reference (CRITICAL)

| Tool | Key Parameters | Notes |
|------|---------------|-------|
| `GPCRdb_get_protein` | `protein` | GPCRdb entry name (e.g., `adrb2_human`), NOT gene symbol or UniProt accession |
| `GPCRdb_list_proteins` | `family` (optional), `protein_class` (optional) | Lists all GPCRs; filter by family slug (e.g., `"adrenoceptors"`) OR by human-readable class name via `protein_class` (e.g., `"chemokine receptors"`, `"opioid receptors"`) |
| `GPCRdb_get_structures` | `protein` (optional), `state` (optional) | `state`: `"active"`, `"inactive"`, `"intermediate"` |
| `GPCRdb_get_ligands` | `protein` | Returns agonists, antagonists, biased ligands with affinities |
| `GPCRdb_get_mutations` | `protein` | Returns mutation effects on receptor function and ligand binding |
| `SAbDab_search_structures` | `query` | Antigen name, species, or keywords; returns browse URL + metadata |
| `SAbDab_get_structure` | `pdb_id` | 4-character PDB code (e.g., `"6W41"`); returns CDR annotations |
| `SAbDab_get_summary` | (no required params) | Database statistics and summary |
| `PDBePISA_get_interfaces` | `pdb_id` | 4-character PDB code; returns all interface pairs with buried area |
| `PDBePISA_get_assemblies` | `pdb_id` | Predicted biological assemblies from crystal packing |
| `PDBePISA_get_monomer_analysis` | `pdb_id` | Per-chain solvent-accessible surface area (SASA) breakdown |

### GPCRdb Entry Name Format

GPCRdb uses its own entry name format: `{receptor_slug}_{species}`. Common examples:
- Beta-2 adrenergic receptor: `adrb2_human`
- Beta-1 adrenergic receptor: `adrb1_human`
- Mu-opioid receptor: `oprm1_human`
- Dopamine D2 receptor: `drd2_human`
- Glucagon-like peptide-1 receptor: `glp1r_human`
- CXCR4 chemokine receptor: `cxcr4_human`

If entry name is unknown, use `GPCRdb_list_proteins()` to browse and find the correct slug. You can also filter by receptor class using the `protein_class` parameter with a human-readable name — e.g., `GPCRdb_list_proteins(protein_class="chemokine receptors")` — instead of the numeric family slug. Both `family` and `protein_class` are accepted and serve overlapping purposes; prefer `protein_class` when the user provides a receptor class name.

---

## Workflow Overview

```
Phase 1: Receptor Identification (for GPCR queries)
  -> GPCRdb_list_proteins: find receptor family and entry name
  -> GPCRdb_get_protein: receptor details, family, species

Phase 2: Ligand Landscape
  -> GPCRdb_get_ligands: all known ligands by pharmacology class
  -> Cross-reference with ChEMBL/PubChem for chemical properties

Phase 3: Structural Data
  -> GPCRdb_get_structures: available PDB/EMDB structures with resolution
  -> PDBePISA_get_interfaces: interface analysis on best structure
  -> PDBePISA_get_assemblies: biological assembly determination

Phase 4: Mutation & Pharmacology Data
  -> GPCRdb_get_mutations: pharmacological mutation map
  -> Compare to ligand binding sites from structure

Phase 5: Antibody Structures (for antibody queries)
  -> SAbDab_search_structures: find structures by antigen
  -> SAbDab_get_structure: CDR annotations, chain details
  -> PDBePISA_get_interfaces: antibody-antigen interface analysis
```

---

## Phase 1: GPCR Receptor Identification

```python
# List all GPCRs in a family to find entry name (by slug)
family_list = GPCRdb_list_proteins(family="adrenoceptors")

# Filter by human-readable class name (new -- preferred when user says e.g. "chemokine receptors")
chemokine_list = GPCRdb_list_proteins(protein_class="chemokine receptors")

# Browse all GPCRs (no family filter)
all_gpcrs = GPCRdb_list_proteins()

# Get detailed protein info once you have the entry name
receptor = GPCRdb_get_protein(protein="adrb2_human")
# Returns: family classification, endogenous ligands, tissue expression,
#          GPCRdb-specific annotations, sequence features
```

## Phase 2: Ligand Landscape

```python
# Get all known ligands for a GPCR
ligands = GPCRdb_get_ligands(protein="adrb2_human")
# Returns: ligand names, types (agonist/antagonist/partial/biased/allosteric),
#          binding affinities (Ki, IC50, EC50), references

# Ligand type classification:
# - Agonist: activates receptor
# - Antagonist/Inverse agonist: blocks or suppresses receptor
# - Partial agonist: submaximal activation
# - Biased agonist: selective signaling (Gs vs. beta-arrestin bias)
# - Positive/Negative allosteric modulator (PAM/NAM)
```

After retrieving ligands from GPCRdb, optionally cross-reference with:
- `PubChem_get_CID_by_compound_name(compound_name=ligand_name)` — get CID, SMILES
- `ChEMBL_search_molecules(query=ligand_name)` — get ChEMBL ID, bioactivity data

## Phase 3: Structural Data

```python
# Get available crystal/cryo-EM structures
structures = GPCRdb_get_structures(protein="adrb2_human", state="inactive")
# state options: "active", "inactive", "intermediate" (omit for all)
# Returns: PDB IDs, resolution, ligand in structure, publication info

# Analyze a specific structure's interfaces
interfaces = PDBePISA_get_interfaces(pdb_id="2rh1")  # adrb2 inactive structure
# Returns: interface pairs, buried solvent-accessible area (BSA),
#          interface residues, hydrogen bonds, salt bridges

# Determine biological assembly
assemblies = PDBePISA_get_assemblies(pdb_id="2rh1")
# Returns: predicted oligomeric state, assembly stability score,
#          subunit composition

# Per-chain SASA breakdown
monomers = PDBePISA_get_monomer_analysis(pdb_id="2rh1")
# Returns: accessible/buried surface area per chain
```

**Interface Analysis Interpretation**:
- BSA > 1500 Å²: Strong interface (likely biologically relevant)
- BSA 800-1500 Å²: Moderate interface
- BSA < 800 Å²: Weak or crystal contact

## Phase 4: Mutation Data

```python
# Get all mutations characterized for a GPCR
mutations = GPCRdb_get_mutations(protein="adrb2_human")
# Returns: mutation positions (generic GPCR numbering), effects on:
#   - Expression/folding
#   - Ligand binding (affinity changes)
#   - G-protein coupling
#   - Receptor activation

# Generic GPCR numbering (Ballesteros-Weinstein):
# e.g., 3.32 = position 32 in TM helix 3 — conserved across GPCR classes
```

## Phase 5: Antibody Structure Retrieval

```python
# Search SAbDab for antibody structures by antigen
results = SAbDab_search_structures(query="EGFR", limit=20)
# Returns: browse URL + metadata table of matching structures

# Get detailed annotations for a specific antibody structure
structure = SAbDab_get_structure(pdb_id="1IQD")
# Returns: VH/VL chain IDs, CDR1-3 (Kabat/IMGT), antigen info,
#          heavy/light chain types, resolution

# Get database overview
summary = SAbDab_get_summary()
# Returns: total structures, species breakdown, antigen coverage stats
```

**CDR Analysis**:
- CDR-H3 is most variable and typically dominates antigen contact
- CDR length distribution: SAbDab provides Kabat, Chothia, and IMGT numbering
- After retrieving SAbDab structure, use `PDBePISA_get_interfaces(pdb_id=...)` to compute antibody-antigen buried surface area

---

## Common Research Patterns

### Pattern 1: GPCR Drug Target Profiling
```
Input: GPCR name (e.g., "GLP-1 receptor")
Flow: GPCRdb_list_proteins -> find "glp1r_human" ->
      GPCRdb_get_protein (receptor details) ->
      GPCRdb_get_ligands (approved + investigational drugs) ->
      GPCRdb_get_structures (available PDB structures) ->
      PDBePISA_get_interfaces on best structure ->
      GPCRdb_get_mutations (pharmacological mutants)
Output: Complete GPCR pharmacology profile with structural context
```

### Pattern 2: Antibody-Antigen Interface Analysis
```
Input: Target antigen (e.g., "PD-L1") or specific PDB code
Flow: SAbDab_search_structures(query="PD-L1") ->
      SAbDab_get_structure(pdb_id="best hit") (CDR annotations) ->
      PDBePISA_get_interfaces(pdb_id=...) (buried area, key contacts) ->
      PDBePISA_get_assemblies (assembly context)
Output: CDR sequences, epitope contact residues, interface energetics
```

### Pattern 3: GPCR Family Survey
```
Input: Drug class question (e.g., "beta-adrenergic receptors")
Flow: GPCRdb_list_proteins(family="adrenoceptors") ->
      GPCRdb_get_protein per receptor (adrb1/2/3) ->
      GPCRdb_get_ligands per receptor (selectivity landscape) ->
      GPCRdb_get_structures per receptor (structural coverage)
Output: Family-wide selectivity map, structural availability, ligand classes
```

### Pattern 4: Structure Interface Characterization
```
Input: PDB code
Flow: PDBePISA_get_assemblies (oligomeric state) ->
      PDBePISA_get_interfaces (all interface pairs ranked by BSA) ->
      PDBePISA_get_monomer_analysis (per-chain surface burial)
Output: Biologically relevant assembly, key interface residues, buried areas
```

---

## Tool Combinations with Other Skills

This skill complements other ToolUniverse skills:

| Goal | This skill provides | Complement with |
|------|--------------------|--------------------|
| GPCR drug discovery | Receptor/ligand/structure data | `tooluniverse-binder-discovery` for virtual screening |
| Antibody engineering | SAbDab structure + CDR data | `tooluniverse-antibody-engineering` for optimization |
| Variant impact on GPCR | GPCRdb mutation effects | `tooluniverse-variant-functional-annotation` for ACMG |
| Target validation | GPCR expression, ligand data | `tooluniverse-drug-target-validation` |
| PDB structure analysis | PDBePISA interfaces | `tooluniverse-protein-structure-retrieval` for RCSB/PDBe |

---

## Fallback Chains

| Primary Tool | Fallback | Use When |
|-------------|----------|----------|
| `GPCRdb_get_protein` | UniProt search + PubMed | Entry name unknown or non-GPCR target |
| `GPCRdb_get_ligands` | ChEMBL bioactivity search | Receptor not in GPCRdb |
| `GPCRdb_get_structures` | RCSB PDB text search | Structures not yet in GPCRdb |
| `SAbDab_search_structures` | RCSB PDB antibody search | Antigen not indexed in SAbDab |
| `PDBePISA_get_interfaces` | PDBe graph API | PDBePISA returns no interfaces |

---

## Completeness Checklist

For GPCR profiling:
- [ ] Entry name resolved via `GPCRdb_list_proteins` or `GPCRdb_get_protein`
- [ ] Receptor family and class documented
- [ ] Ligand landscape retrieved with pharmacology types
- [ ] Available structures listed with resolution and state
- [ ] Best structure analyzed with PDBePISA (interfaces + assembly)
- [ ] Mutation data retrieved for pharmacological context

For antibody structure:
- [ ] SAbDab search run with antigen name
- [ ] Best structure retrieved with `SAbDab_get_structure`
- [ ] CDR1-3 sequences extracted for VH and VL chains
- [ ] Antibody-antigen interface analyzed with PDBePISA
- [ ] Buried surface area and key contact residues documented

---

## Key References

- GPCRdb: https://gpcrdb.org — standardized GPCR data with generic numbering
- SAbDab: https://opig.stats.ox.ac.uk/webapps/newsabdab/sabdab — structural antibody database
- PDBePISA: https://www.ebi.ac.uk/pdbe/pisa — protein interface analysis
