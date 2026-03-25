---
name: tooluniverse-protein-therapeutic-design
description: Design novel protein therapeutics (binders, enzymes, scaffolds) using AI-guided de novo design. Uses RFdiffusion for backbone generation, ProteinMPNN for sequence design, ESMFold/AlphaFold2 for validation. Use when asked to design protein binders, therapeutic proteins, or engineer protein function.
---

# Therapeutic Protein Designer

AI-guided de novo protein design using RFdiffusion backbone generation, ProteinMPNN sequence optimization, and structure validation for therapeutic protein development.

**KEY PRINCIPLES**:
1. **Structure-first** - Generate backbone geometry before sequence
2. **Target-guided** - Design binders with target structure in mind
3. **Iterative validation** - Predict structure to validate designs
4. **Developability-aware** - Consider aggregation, immunogenicity, expression
5. **Evidence-graded** - Grade designs by confidence metrics
6. **Actionable output** - Provide sequences ready for experimental testing
7. **English-first queries** - Always use English terms in tool calls

---

## When to Use

Apply when user asks to:
- Design a protein binder, therapeutic protein, or scaffold
- Optimize a protein sequence for function
- Design a de novo enzyme
- Generate protein variants for target binding

---

## Workflow Overview

```
Phase 1: Target Characterization
  Get structure (PDB, EMDB cryo-EM, AlphaFold), identify binding epitope

Phase 2: Backbone Generation (RFdiffusion)
  Define constraints, generate >= 5 backbones, filter by geometry

Phase 3: Sequence Design (ProteinMPNN)
  Design >= 8 sequences per backbone, sample with temperature control

Phase 4: Structure Validation (ESMFold/AlphaFold2)
  Predict structure, compare to backbone, assess pLDDT/pTM

Phase 5: Developability Assessment
  Aggregation, pI, expression prediction

Phase 6: Report Synthesis
  Ranked candidates, FASTA, experimental recommendations
```

---

## Critical Requirements

### Report-First Approach (MANDATORY)
1. Create `[TARGET]_protein_design_report.md` first with section headers
2. Progressively update as designs are generated
3. Output `[TARGET]_designed_sequences.fasta` and `[TARGET]_top_candidates.csv`

### Design Documentation (MANDATORY)
Every design MUST include: Sequence, Length, Target, Method, and Quality Metrics (pLDDT, pTM, MPNN score, binding prediction).

---

## NVIDIA NIM Tools

| Tool | Purpose | Key Parameter |
|------|---------|---------------|
| `NvidiaNIM_rfdiffusion` | Backbone generation | `diffusion_steps` (NOT `num_steps`) |
| `NvidiaNIM_proteinmpnn` | Sequence design | `pdb_string` (NOT `pdb`) |
| `NvidiaNIM_esmfold` | Fast validation | `sequence` (NOT `seq`) |
| `NvidiaNIM_alphafold2` | High-accuracy validation | `sequence`, `algorithm` |
| `NvidiaNIM_esm2_650m` | Sequence embeddings | `sequences`, `format` |

### Common Parameter Mistakes

| Tool | Wrong | Correct |
|------|-------|---------|
| `NvidiaNIM_rfdiffusion` | `num_steps=50` | `diffusion_steps=50` |
| `NvidiaNIM_proteinmpnn` | `pdb=content` | `pdb_string=content` |
| `NvidiaNIM_esmfold` | `seq="MVLS..."` | `sequence="MVLS..."` |
| `NvidiaNIM_alphafold2` | `seq="MVLS..."` | `sequence="MVLS..."` |

### NVIDIA NIM Requirements
- **API Key**: `NVIDIA_API_KEY` environment variable required
- **Rate limits**: 40 RPM (1.5 second minimum between calls)
- AlphaFold2 may return 202 (polling required); RFdiffusion and ESMFold are synchronous

---

## Supporting Tools

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `PDBe_get_uniprot_mappings` | Find PDB structures | `uniprot_id` |
| `RCSBData_get_entry` | Download PDB file | `pdb_id` |
| `alphafold_get_prediction` | Get AlphaFold DB structure | `accession` |
| `emdb_search` | Search cryo-EM maps | `query` |
| `emdb_get_entry` | Get entry details | `entry_id` |
| `UniProt_get_protein_sequence` | Get target sequence | `accession` |
| `InterPro_get_protein_domains` | Get domains | `accession` |

---

## Evidence Grading

| Tier | Criteria |
|------|----------|
| T1 (best) | pLDDT >85, pTM >0.8, low aggregation, neutral pI |
| T2 | pLDDT >75, pTM >0.7, acceptable developability |
| T3 | pLDDT >70, pTM >0.65, developability concerns |
| T4 | Failed validation or major developability issues |

---

## Completeness Checklist

- [ ] Target structure obtained (PDB or predicted)
- [ ] Binding epitope identified
- [ ] >= 5 backbones generated, top 3-5 selected
- [ ] >= 8 sequences per backbone, MPNN scores reported
- [ ] All sequences validated (ESMFold), pLDDT/pTM reported, >= 3 passing
- [ ] Developability assessed (aggregation, pI, expression)
- [ ] Ranked candidate list, FASTA file, experimental recommendations

---

## Reference Files

- **DESIGN_PROCEDURES.md** - Phase-by-phase code examples, sampling parameters, fallback chains
- **TOOLS_REFERENCE.md** - Complete tool documentation with code examples
- **EXAMPLES.md** - Sample design workflows and outputs
- **CHECKLIST.md** - Detailed phase checklists and quality metrics
- **design_templates.md** - Report templates and output format examples
