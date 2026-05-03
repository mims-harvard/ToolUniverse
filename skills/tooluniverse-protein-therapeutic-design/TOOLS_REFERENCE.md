# Therapeutic Protein Designer - Tool Reference

## Core NVIDIA NIM Tools

### RFdiffusion - Backbone Generation

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `NvidiaNIM_rfdiffusion` | De novo backbone design | `diffusion_steps` |

**Example - Generate backbones**:
```python
# Generate de novo backbones
result = tu.tools.NvidiaNIM_rfdiffusion(
    diffusion_steps=50
)
# Returns: {"structure": "<PDB content>", "sequence": "GGG..."}
```

**Parameters**:
| Parameter | Description | Default |
|-----------|-------------|---------|
| `diffusion_steps` | Number of denoising steps | 50 |

**Notes**:
- More steps (75-100) = higher quality but slower
- Output is backbone-only (Gly residues)
- Use with ProteinMPNN for sequence design

---

### ProteinMPNN - Sequence Design

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `NvidiaNIM_proteinmpnn` | Design sequences for backbone | `pdb_string`, `num_sequences` |

**Example - Design sequences**:
```python
# Design sequences for backbone
result = tu.tools.NvidiaNIM_proteinmpnn(
    pdb_string=backbone_pdb_content,
    num_sequences=8,
    temperature=0.1
)
# Returns: {"sequences": ["MVLS...", "MKKT...", ...], "scores": [-1.89, -2.01, ...]}
```

**Parameters**:
| Parameter | Description | Default |
|-----------|-------------|---------|
| `pdb_string` | PDB file content (backbone) | Required |
| `num_sequences` | Number of sequences to generate | 8 |
| `temperature` | Sampling temperature (lower = conservative) | 0.1 |

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
| `PDBe_get_uniprot_mappings` | Find PDB structures | `uniprot_id` |
| `RCSBData_get_entry` | Download PDB file | `pdb_id` |
| `alphafold_get_prediction` | Get AlphaFold DB structure | `accession` |

**Example - Get target structure**:
```python
# Try PDB first
pdb_hits = tu.tools.PDBe_get_uniprot_mappings(uniprot_id="Q9NZQ7")
if pdb_hits:
    structure = tu.tools.PDB_get_structure(pdb_id=pdb_hits[0]['pdb_id'])
else:
    # Fallback to AlphaFold
    structure = tu.tools.alphafold_get_prediction(accession="Q9NZQ7")
```

### EMDB Cryo-EM Structures (NEW)

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `emdb_search` | Search cryo-EM maps | `query` |
| `emdb_get_entry` | Get entry details | `entry_id` |

**When to use EMDB**:
- Membrane protein targets (GPCRs, ion channels)
- Large macromolecular complexes
- Targets where conformational states matter
- When X-ray structures unavailable

**Example - Get cryo-EM structure for membrane target**:
```python
# Search EMDB for membrane receptor
emdb_hits = tu.tools.emdb_search(query="EGFR membrane receptor")

if emdb_hits:
    # Get details including associated PDB models
    best_entry = emdb_hits[0]  # Often sorted by resolution
    details = tu.tools.emdb_get_entry(entry_id=best_entry['emdb_id'])
    
    # Get the atomic model (PDB) for design
    if details.get('pdb_ids'):
        structure = tu.tools.PDB_get_structure(pdb_id=details['pdb_ids'][0])
        print(f"Got structure from cryo-EM: {details['pdb_ids'][0]}")
        print(f"Resolution: {best_entry.get('resolution', 'N/A')} Å")
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
| `UniProt_get_protein_sequence` | Get target sequence | `accession` |
| `InterPro_get_protein_domains` | Get domains | `accession` |

---

## Workflow Code Examples

### Example 1: Complete Design Pipeline

```python
def design_protein_binder(tu, target_uniprot):
    """Complete binder design pipeline."""
    
    # Phase 1: Get target
    target_seq = tu.tools.UniProt_get_protein_sequence(
        accession=target_uniprot
    )
    target_structure = tu.tools.NvidiaNIM_alphafold2(
        sequence=target_seq['sequence'],
        algorithm="mmseqs2"
    )
    
    # Phase 2: Generate backbones
    backbones = []
    for i in range(5):
        bb = tu.tools.NvidiaNIM_rfdiffusion(diffusion_steps=50)
        backbones.append(bb)
    
    # Phase 3: Design sequences
    all_sequences = []
    for bb in backbones:
        seqs = tu.tools.NvidiaNIM_proteinmpnn(
            pdb_string=bb['structure'],
            num_sequences=8,
            temperature=0.1
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
    
    for iteration in range(3):
        # Increase diffusion steps each iteration
        steps = 50 + iteration * 25
        
        # Generate backbone
        bb = tu.tools.NvidiaNIM_rfdiffusion(diffusion_steps=steps)
        
        # Design sequences with decreasing temperature
        temp = 0.1 / (iteration + 1)
        seqs = tu.tools.NvidiaNIM_proteinmpnn(
            pdb_string=bb['structure'],
            num_sequences=16,
            temperature=temp
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
| `emdb_search` + PDB model | PDB_search | `NvidiaNIM_alphafold2` |

---

## Common Parameter Mistakes

| Tool | Wrong | Correct |
|------|-------|---------|
| `NvidiaNIM_rfdiffusion` | `num_steps=50` | `diffusion_steps=50` |
| `NvidiaNIM_proteinmpnn` | `pdb=content` | `pdb_string=content` |
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
    bb = tu.tools.NvidiaNIM_rfdiffusion(diffusion_steps=50)
    backbones.append(bb)
    time.sleep(1.5)  # Rate limit
```
