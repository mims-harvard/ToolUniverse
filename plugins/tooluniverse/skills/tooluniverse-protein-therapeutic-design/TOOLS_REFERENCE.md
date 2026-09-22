# Therapeutic Protein Designer - Tool Reference

## Core NVIDIA NIM Tools

### RFdiffusion - Backbone Generation

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `NvidiaNIM_rfdiffusion` | Backbone design (binders, motif scaffolding, de novo from a template PDB) | `contigs`, `input_pdb` (both required), `hotspot_res`, `diffusion_steps`, `random_seed` |

> The `NvidiaNIM_rfdiffusion` / `NvidiaNIM_proteinmpnn` schemas declare no fixed return keys, and these
> snippets were not live-run (no `NVIDIA_API_KEY` in the environment used to verify this file; the
> arguments below were checked against the tool schemas only). The return keys used in the examples
> (`structure`, `sequences`, `scores`) are placeholders: print `result.keys()` once and adapt.

**Example - Generate backbones**:
```python
# contigs (DSL) and input_pdb (PDB text, ATOM records only) are BOTH required
result = tu.tools.NvidiaNIM_rfdiffusion(
    contigs="A20-60/0 50-100",   # keep residues A20-60 of chain A, add a new 50-100 residue chain
    input_pdb=target_pdb_text,
    hotspot_res=["A50", "A51"],  # optional: binding-site hotspot residues for binder design
    diffusion_steps=50
)
# Returns a dict with the generated PDB coordinates (long-running async operation)
```

**Parameters**:
| Parameter | Description | Default |
|-----------|-------------|---------|
| `contigs` | Contig specification DSL, e.g. `'A20-60/0 50-100'` | Required |
| `input_pdb` | PDB text of the target/scaffold (ATOM records only) | Required |
| `hotspot_res` | Hotspot residues, e.g. `['A50', 'A51']` | None |
| `diffusion_steps` | Number of denoising steps (schema range 15-50) | 15 |
| `random_seed` | Seed for reproducibility | None |

**Notes**:
- More steps = slower; the schema accepts 15-50
- Output is backbone-only (Gly residues)
- Use with ProteinMPNN for sequence design

---

### ProteinMPNN - Sequence Design

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `NvidiaNIM_proteinmpnn` | Design sequences for backbone | `input_pdb`, `num_seq_per_target`, `sampling_temp` |

**Example - Design sequences**:
```python
# Design sequences for backbone
result = tu.tools.NvidiaNIM_proteinmpnn(
    input_pdb=backbone_pdb_content,
    num_seq_per_target=8,
    sampling_temp=[0.1]          # a LIST of temperatures
)
# Returns designed sequences in Multi-FASTA format with log-probabilities (per the tool description)
```

**Parameters**:
| Parameter | Description | Default |
|-----------|-------------|---------|
| `input_pdb` | PDB file content (backbone, ATOM records) | Required |
| `num_seq_per_target` | Number of sequences to generate | 1 |
| `sampling_temp` | List of sampling temperatures (lower = conservative; 0.1-0.3 recommended) | `[0.1]` |
| `ca_only` | Design using only CA atoms | False |
| `use_soluble_model` | Use the model trained on soluble proteins | False |

**Temperature Guide**:
| Temperature | Use Case |
|-------------|----------|
| 0.05-0.1 | Conservative, high-confidence |
| 0.1-0.2 | Balanced exploration |
| 0.2-0.5 | Diverse sampling |
| 0.5-1.0 | Maximum diversity |

---

### ESMFold - Fast Structure Validation

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `NvidiaNIM_esmfold` | Fast structure prediction | `sequence` |

**Example - Validate design**:
```python
# Predict structure for designed sequence
result = tu.tools.NvidiaNIM_esmfold(sequence=designed_sequence)
# Returns: {"structure": "<PDB content>", "plddt": [...], "ptm": 0.85}
```

**Parameters**:
| Parameter | Description | Limit |
|-----------|-------------|-------|
| `sequence` | Amino acid sequence | Max 1024 aa |

**Output Interpretation**:
| Metric | Description | Good Threshold |
|--------|-------------|----------------|
| pLDDT | Per-residue confidence | >70 mean |
| pTM | Global topology confidence | >0.7 |

---

### AlphaFold2 - High-Accuracy Validation

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `NvidiaNIM_alphafold2` | High-accuracy structure | `sequence`, `algorithm` |

**Example - High-accuracy prediction**:
```python
# High-accuracy structure prediction
result = tu.tools.NvidiaNIM_alphafold2(
    sequence=designed_sequence,
    algorithm="mmseqs2",
    relax_prediction=False
)
# Returns: {"structure": "<PDB content>", "plddt": [...]}
```

**When to use instead of ESMFold**:
- Final validation of top candidates
- Sequences >1024 aa
- When highest accuracy needed

---

### ESM2 - Sequence Embeddings

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `NvidiaNIM_esm2_650m` | Sequence embeddings | `sequences`, `format` |

**Example - Get embeddings**:
```python
# Get sequence embeddings for similarity analysis
result = tu.tools.NvidiaNIM_esm2_650m(
    sequences=[seq1, seq2, seq3],
    format="npz"
)
# Returns: Binary NPZ file with embeddings
```

**Use cases**:
- Compare designed sequences to natural proteins
- Cluster designs by similarity
- Quality assessment

---

## Supporting Tools

### Target Structure Retrieval

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `PDBeSIFTS_get_best_structures` | Find PDB structures for a UniProt accession (best first) | `uniprot_accession` |
| `download_text_content` | Download a PDB file (no dedicated PDB-download tool exists) | `url` (`https://files.rcsb.org/download/<PDB_ID>.pdb`) |
| `alphafold_get_prediction` | Get AlphaFold DB structure | `accession` |

**Example - Get target structure**:
```python
# Try PDB first
pdb_hits = tu.tools.PDBeSIFTS_get_best_structures(uniprot_accession="Q9NZQ7")
structures = pdb_hits["data"]["structures"]
if structures:
    pdb_id = structures[0]["pdb_id"].upper()
    structure = tu.tools.download_text_content(
        url=f"https://files.rcsb.org/download/{pdb_id}.pdb"
    )["content"]
else:
    # Fallback to AlphaFold
    structure = tu.tools.alphafold_get_prediction(accession="Q9NZQ7")
```

### EMDB Cryo-EM Structures (NEW)

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `EMDB_search_structures` | Search cryo-EM maps | `query` |
| `EMDB_get_structure` | Get entry details | `emdb_id` (e.g. `EMD-63503`) |

**When to use EMDB**:
- Membrane protein targets (GPCRs, ion channels)
- Large macromolecular complexes
- Targets where conformational states matter
- When X-ray structures unavailable

**Example - Get cryo-EM structure for membrane target**:
```python
# Search EMDB for membrane receptor
emdb_hits = tu.tools.EMDB_search_structures(query="EGFR membrane receptor")["data"]

# Keep entries that have a fitted atomic model (crossreferences.pdb_list);
# many EMDB maps have no deposited PDB model
with_model = [e for e in emdb_hits if "pdb_list" in e.get("crossreferences", {})]

if with_model:
    best_entry = with_model[0]
    pdb_refs = best_entry["crossreferences"]["pdb_list"]["pdb_reference"]
    pdb_id = pdb_refs[0]["pdb_id"].upper()
    
    # Get the atomic model (PDB) for design
    structure = tu.tools.download_text_content(
        url=f"https://files.rcsb.org/download/{pdb_id}.pdb"
    )["content"]
    print(f"Got structure from cryo-EM: {best_entry['emdb_id']} -> {pdb_id}")
```

**Output Quality Assessment**:
| Resolution | Quality | Design Suitability |
|------------|---------|-------------------|
| <3 Å | High | Excellent - use directly |
| 3-4 Å | Good | Good - validate binding site |
| 4-5 Å | Medium | Use with caution |
| >5 Å | Low | Consider AlphaFold instead |

### Sequence Analysis

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `UniProt_get_sequence_by_accession` | Get target sequence | `accession` |
| `InterPro_get_protein_domains` | Get domains | `protein_id` |

---

## Workflow Code Examples

### Example 1: Complete Design Pipeline

```python
def design_protein_binder(tu, target_uniprot):
    """Complete binder design pipeline."""
    
    # Phase 1: Get target
    target_seq = tu.tools.UniProt_get_sequence_by_accession(
        accession=target_uniprot
    )
    target_structure = tu.tools.NvidiaNIM_alphafold2(
        sequence=target_seq['sequence'],
        algorithm="mmseqs2"
    )
    
    # Phase 2: Generate backbones
    # RFdiffusion needs the target's PDB text (ATOM records) and a contigs string
    target_pdb_text = ...   # e.g. downloaded PDB entry, or the structure from target_structure
    contigs = "A1-150/0 60-100"   # keep target chain A residues 1-150, design a new 60-100 residue binder
    backbones = []
    for i in range(5):
        bb = tu.tools.NvidiaNIM_rfdiffusion(
            contigs=contigs, input_pdb=target_pdb_text,
            diffusion_steps=50, random_seed=i
        )
        backbones.append(bb)
    
    # Phase 3: Design sequences
    all_sequences = []
    for bb in backbones:
        seqs = tu.tools.NvidiaNIM_proteinmpnn(
            input_pdb=bb['structure'],      # placeholder key - see note at top of this file
            num_seq_per_target=8,
            sampling_temp=[0.1]
        )
        all_sequences.extend(zip(seqs['sequences'], seqs['scores']))
    
    # Phase 4: Validate
    validated = []
    for seq, mpnn_score in all_sequences:
        pred = tu.tools.NvidiaNIM_esmfold(sequence=seq)
        plddt = np.mean(pred['plddt'])
        ptm = pred['ptm']
        
        if plddt > 70 and ptm > 0.7:
            validated.append({
                'sequence': seq,
                'mpnn_score': mpnn_score,
                'plddt': plddt,
                'ptm': ptm
            })
    
    # Rank by quality
    return sorted(validated, 
                  key=lambda x: (x['plddt'] + x['ptm']*100 - x['mpnn_score']),
                  reverse=True)
```

### Example 2: Iterative Refinement

```python
def iterative_design(tu, initial_backbone, target_plddt=85):
    """Iteratively improve design quality."""
    
    best_design = None
    best_plddt = 0
    
    contigs = "A1-150/0 60-100"   # required by RFdiffusion; adapt to your target chain/residues
    for iteration in range(3):
        # Increase diffusion steps each iteration (30, 40, 50; the schema accepts 15-50)
        steps = 30 + iteration * 10
        
        # Generate backbone
        bb = tu.tools.NvidiaNIM_rfdiffusion(
            contigs=contigs, input_pdb=initial_backbone, diffusion_steps=steps
        )
        
        # Design sequences with decreasing temperature
        temp = 0.1 / (iteration + 1)
        seqs = tu.tools.NvidiaNIM_proteinmpnn(
            input_pdb=bb['structure'],      # placeholder key - see note at top of this file
            num_seq_per_target=16,
            sampling_temp=[temp]
        )
        
        # Validate all
        for seq, score in zip(seqs['sequences'], seqs['scores']):
            pred = tu.tools.NvidiaNIM_esmfold(sequence=seq)
            plddt = np.mean(pred['plddt'])
            
            if plddt > best_plddt:
                best_plddt = plddt
                best_design = {
                    'sequence': seq,
                    'structure': pred['structure'],
                    'plddt': plddt,
                    'iteration': iteration
                }
        
        # Early exit if target reached
        if best_plddt >= target_plddt:
            break
    
    return best_design
```

### Example 3: Developability Screening

```python
def assess_developability(sequence):
    """Assess developability of designed protein."""
    
    # Calculate properties
    from Bio.SeqUtils.ProtParam import ProteinAnalysis
    analysis = ProteinAnalysis(sequence)
    
    # Basic properties
    mw = analysis.molecular_weight()
    pi = analysis.isoelectric_point()
    gravy = analysis.gravy()
    
    # Count cysteines
    cys_count = sequence.count('C')
    
    # Aggregation propensity (simplified)
    hydrophobic = sum(1 for aa in sequence if aa in 'VILMFYW')
    agg_score = hydrophobic / len(sequence)
    
    # Score
    score = 0
    if 5 <= pi <= 9: score += 1
    if mw < 50000: score += 1
    if agg_score < 0.5: score += 1
    if cys_count == 0 or cys_count % 2 == 0: score += 1
    
    return {
        'molecular_weight': mw,
        'isoelectric_point': pi,
        'gravy': gravy,
        'cysteine_count': cys_count,
        'aggregation_score': agg_score,
        'developability_score': score,
        'tier': '★★★' if score >= 4 else '★★☆' if score >= 3 else '★☆☆'
    }
```

---

## Fallback Chains

### Backbone Generation
| Primary | Fallback 1 | Fallback 2 |
|---------|------------|------------|
| `NvidiaNIM_rfdiffusion` | Manual backbone from PDB | Rosetta de novo |

### Sequence Design
| Primary | Fallback 1 | Fallback 2 |
|---------|------------|------------|
| `NvidiaNIM_proteinmpnn` | Rosetta ProteinMPNN | Manual design |

### Structure Validation
| Primary | Fallback 1 | Fallback 2 |
|---------|------------|------------|
| `NvidiaNIM_esmfold` | `NvidiaNIM_alphafold2` | AlphaFold DB homolog |
| `NvidiaNIM_alphafold2` | `alphafold_get_prediction` | `NvidiaNIM_openfold2` |

### Target Structure
| Primary | Fallback 1 | Fallback 2 | Fallback 3 |
|---------|------------|------------|------------|
| PDB experimental | EMDB cryo-EM + PDB | `NvidiaNIM_alphafold2` | AlphaFold DB |

### Cryo-EM (Membrane Targets) (NEW)
| Primary | Fallback 1 | Fallback 2 |
|---------|------------|------------|
| `EMDB_search_structures` + PDB model | PDB_search_similar_structures | `NvidiaNIM_alphafold2` |

---

## Common Parameter Mistakes

| Tool | Wrong | Correct |
|------|-------|---------|
| `NvidiaNIM_rfdiffusion` | `num_steps=50` | `diffusion_steps=50` (plus required `contigs` and `input_pdb`) |
| `NvidiaNIM_proteinmpnn` | `pdb=content`, `pdb_string=content`, `num_sequences=8`, `temperature=0.1` | `input_pdb=content`, `num_seq_per_target=8`, `sampling_temp=[0.1]` |
| `NvidiaNIM_esmfold` | `seq="MVLS..."` | `sequence="MVLS..."` |
| `NvidiaNIM_alphafold2` | `seq="MVLS..."` | `sequence="MVLS..."` |

---

## NVIDIA NIM Requirements

**API Key**: `NVIDIA_API_KEY` environment variable required

**Rate limits**: 40 RPM (1.5 second minimum between calls)

### Check Availability
```python
import os

nvidia_available = bool(os.environ.get("NVIDIA_API_KEY"))
if not nvidia_available:
    raise ValueError("NVIDIA_API_KEY required for protein design")
```

### Async Operations
- AlphaFold2 may return 202 (polling required)
- RFdiffusion is typically synchronous
- ESMFold is synchronous

---

## Quality Thresholds

### Structure Prediction
| Metric | Fail | Marginal | Good | Excellent |
|--------|------|----------|------|-----------|
| pLDDT | <50 | 50-70 | 70-85 | >85 |
| pTM | <0.5 | 0.5-0.7 | 0.7-0.85 | >0.85 |

### ProteinMPNN Score
| Score Range | Interpretation |
|-------------|----------------|
| < -2.5 | Exceptional (rare) |
| -2.5 to -2.0 | Very good |
| -2.0 to -1.5 | Good |
| -1.5 to -1.0 | Acceptable |
| > -1.0 | Consider redesign |

### Design Tiers
| Tier | pLDDT | pTM | MPNN | Aggregation |
|------|-------|-----|------|-------------|
| ★★★ | >85 | >0.8 | <-1.8 | <0.5 |
| ★★☆ | >75 | >0.7 | <-1.5 | <0.6 |
| ★☆☆ | >70 | >0.65 | <-1.2 | <0.7 |
| ☆☆☆ | <70 | <0.65 | >-1.2 | >0.7 |

---

## Batch Processing Tips

### Efficient Pipeline
```python
def batch_validate(tu, sequences, batch_size=5):
    """Validate sequences in batches to manage rate limits."""
    import time
    
    results = []
    for i in range(0, len(sequences), batch_size):
        batch = sequences[i:i+batch_size]
        
        for seq in batch:
            result = tu.tools.NvidiaNIM_esmfold(sequence=seq)
            results.append(result)
            time.sleep(1.5)  # Rate limit
        
        # Longer pause between batches
        time.sleep(5)
    
    return results
```

### Parallel Backbone Generation
```python
# Generate diverse backbones
backbones = []
for _ in range(10):
    bb = tu.tools.NvidiaNIM_rfdiffusion(
        contigs=contigs, input_pdb=target_pdb_text, diffusion_steps=50
    )
    backbones.append(bb)
    time.sleep(1.5)  # Rate limit
```
