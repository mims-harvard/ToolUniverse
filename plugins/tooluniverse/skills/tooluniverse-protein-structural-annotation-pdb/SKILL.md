---

name: tooluniverse-protein-structural-annotation-pdb
description: "Given a PDB structure, produce a per-residue annotation table: which residues sit at a binding interface (vs a partner chain), which line a ligand pocket, which are buried (core) vs solvent-exposed (surface), and optionally secondary structure. This is the structural track drawn under a DMS heatmap and the structural prior SAE feature drops are read against. Use when you need to anchor a variant-interpretation or DMS analysis to the protein's actual physical context."
---

# Protein structural annotation from a PDB

For each residue of a target protein chain, classify whether it sits at a
binding interface, in a ligand pocket, is buried vs solvent-exposed, and
(optionally) which secondary-structure element it belongs to. This is the
annotation track that anchors any DMS heatmap or per-residue interpretation
to the protein's actual physical context.

---

## When to use this skill

- Building a per-residue annotation track for a DMS heatmap
- Deciding whether a variant of interest is **in an interface, in a pocket, or
  in the core** — context that often distinguishes plausible mechanisms
- Reading SAE feature drops at a position against the protein's known biology
  (a feature drop at a ligand-pocket residue means something different from a
  drop at a surface residue)

**Not for**:
- Multi-conformer ensembles or NMR structure comparisons → use
  `tooluniverse-computational-biophysics`
- Whole-structure pocket detection without a known ligand → use a docking
  tool (e.g. SwissDock) or PDBe's pre-computed pockets

---

## Required inputs

| Input | Format | Example |
|---|---|---|
| PDB ID | 4 characters | `6VJJ` (KRAS-RAF1-GTP analogue) |
| Target chain | single character | `A` |
| Partner chain(s) | list of chain IDs | `["B"]` |
| Ligand resnames | 3-letter PDB names | `["GNP", "MG"]` |

Optional:
- `distance_cutoff` (default 5.0 Å)
- `core_rsa_cutoff` (default 0.25)
- `include_secondary_structure` (default false; uses PDBe REST if true)
- `pdb_content` instead of `pdb_id` for local / predicted structures

---

## Workflow

### Step 1 (optional): Find the relevant PDB

If you only have a UniProt accession or gene symbol, pick a structure first:

```python
# PDBe's curated UniProt→PDB mapping (recommended; ranks by coverage + resolution)
PDBeSIFTS_get_best_structures(uniprot_accession="P01116")
# Returns a ranked list of PDB IDs for KRAS with chain mapping

# Or full list (unranked)
PDBeSIFTS_get_all_structures(uniprot_accession="P01116")

# RCSB advanced search (free-text, when you don't have a UniProt yet)
RCSBAdvSearch_search_structures(query="KRAS GTP complex")
```

Pick the structure that contains the **right complex**: include the binding
partner chain you care about, the relevant ligand, and a resolution adequate
for distance-based classification (≤ 3 Å is a safe default).

### Step 2: Run the annotation

```python
Structure_annotate_per_residue(
    pdb_id="6VJJ",
    target_chain="A",
    partner_chains=["B"],
    ligand_resnames=["GNP", "MG"],
    distance_cutoff=5.0,
    core_rsa_cutoff=0.25,
    include_secondary_structure=False,
)
```

Returns `annotations: List[{position, aa, dist_partner, dist_ligand, rsa,
region, is_core, ss_element?}]` for every residue of the target chain. For
KRAS in 6VJJ, this yields 168 rows.

### Step 3: Verify the numbering before joining

PDB residue numbers carry **silent offsets** — crystal constructs add
N-terminal cloning residues, and published figures sometimes shift the track
relative to the panel sequence. Always verify with a landmark:

```python
# Get the canonical reference sequence
UniProt_get_sequence_by_accession(accession="P01116")
# Then spot-check: KRAS canonical position 12 should be glycine
assert annotations[11]["aa"] == "G"  # 1-indexed position 12, 0-indexed index 11
```

If the landmark mismatches, record the offset explicitly (e.g. `pdb_pos =
uniprot_pos + offset`) before any downstream join. **Do not silently rebase
positions.**

### Step 4: Combine with secondary structure (optional)

If you set `include_secondary_structure=True`, the tool fetches per-residue
helix/strand/coil from PDBe REST. Alternatively, use the dedicated PDBe
secondary-structure tool separately:

```python
pdbe_get_entry_secondary_structure(pdb_id="6VJJ")
# Returns per-chain helix + strand ranges
```

### Step 5: Use the annotation

The returned table is keyed by 1-based canonical residue number. Typical
downstream uses:

| Use case | Field to read |
|---|---|
| Is variant X in a pocket? | `by_pos = {a["position"]: a for a in annotations}; by_pos[X]["region"] in ("ligand", "both")` — index by position field, NOT list index (PDB residue numbers may not start at 1 or be contiguous) |
| Build a DMS heatmap annotation track | `[(r["position"], r["region"], r["is_core"], r.get("ss_element"))]` |
| Filter SAE hotspot features to ligand-binding residues | filter clusters by `region == "ligand"` |
| Compare buried vs surface signal | group statistics by `is_core` |

---

## Interpretation table

| Region label | Biological meaning | Common functional role |
|---|---|---|
| `interface` | Within `distance_cutoff` of a partner chain | Protein-protein binding residue; variants often disrupt complex formation |
| `ligand` | Within `distance_cutoff` of a ligand heavy atom | Pocket residue; variants often disrupt substrate / cofactor / drug binding |
| `both` | Both | Allosteric or shared-surface residue |
| `other` | Neither | Surface (if not `is_core`) or core (if `is_core`) — variants impact through stability or distal effects |
| `is_core=true` | RSA < `core_rsa_cutoff` (0.25 by default) | Buried residue; variants often destabilize the fold |

---

## Honest limitations

1. **One conformer only**. A static crystal structure does not capture
   alternative conformations or induced-fit binding. A residue may be at the
   pocket in one conformer and away in another. Pick the structure whose
   bound state matches your question.
2. **Numbering is fragile**. Crystal constructs add N-terminal tags or skip
   disordered N/C termini. **Always verify** with a landmark before joining
   to a sequence or to another annotation source. The skill cannot detect
   silent offsets for you.
3. **Distance cutoff is a convention, not a truth**. 5.0 Å is the literature
   default. Tighten to 4.0 Å for stricter pocket
   calls; loosen to 6.0 Å to include 2nd-shell residues.
4. **freesasa RSA can exceed 1.0** for small / unusual structures because the
   max-ASA reference is calibrated for a typical protein context. For real
   well-folded proteins values cluster in [0, 1.2]; reading them as a
   fraction is fine, but treat extreme values as a flag to inspect.
5. **`partner_chains=[]` is permitted** but then all `dist_partner` values
   are `null` — interface analysis is skipped entirely.
6. **HETATM ligands only**. Modified residues (e.g. phosphoresidues already
   in the chain) are not detected as ligands — they are part of the chain.

---

## Cross-references

| Tool | Role | Use it for |
|---|---|---|
| `Structure_annotate_per_residue` | This skill's atomic tool | The annotation itself |
| `PDBeSIFTS_get_best_structures` | UniProt → ranked PDB list | Step 1 |
| `PDBeSIFTS_get_all_structures` | UniProt → full PDB list | Step 1 |
| `RCSBAdvSearch_search_structures` | Free-text RCSB search | Step 1 |
| `UniProt_get_sequence_by_accession` | Canonical sequence | Step 3 (numbering verification) |
| `pdbe_get_entry_secondary_structure` | SS alone | Step 4 alternative |
| `tooluniverse-residue-functional-mechanism-interpretation` | Downstream consumer | Use this annotation as the structural evidence layer when interpreting DMS hotspots; the skill also plots an annotated DMS heatmap in its Step 7 |
