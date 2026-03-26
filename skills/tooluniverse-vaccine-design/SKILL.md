---
name: tooluniverse-vaccine-design
description: Design and evaluate vaccine candidates using computational immunology tools. Covers epitope prediction (MHC-I/II binding via IEDB), population coverage analysis, antigen selection, adjuvant matching, and immunogenicity assessment. Integrates IEDB for epitope prediction, UniProt for antigen sequences, PDB/AlphaFold for structural epitopes, BVBRC for pathogen proteomes, and literature for clinical precedent. Use when asked about vaccine design, epitope prediction, immunogenicity, MHC binding, T-cell epitopes, B-cell epitopes, or population coverage for vaccine candidates.
---

# Vaccine Design

Computational pipeline for designing peptide/subunit vaccine candidates through epitope prediction, population coverage optimization, and immunogenicity assessment.

**Key principles**:
1. **Epitope-driven** — vaccines work by presenting epitopes to T/B cells; start with epitope prediction
2. **Population coverage matters** — HLA diversity means no single epitope covers everyone; design for breadth
3. **Multi-epitope is better** — combine CD8+ (MHC-I) and CD4+ (MHC-II) epitopes for robust immunity
4. **Conservation = broad protection** — conserved epitopes across strains provide cross-protective immunity
5. **Evidence grading** — T1: clinical trial data, T2: in-vivo immunogenicity, T3: in-vitro binding, T4: computational prediction only

---

## When to Use

- "Design a vaccine against [pathogen]"
- "Predict T-cell epitopes for [protein]"
- "What MHC-I epitopes does [protein] have?"
- "Assess population coverage of these epitopes"
- "Find conserved epitopes across [pathogen] strains"

**Not this skill**: For HLA typing or allele frequency only, use `tooluniverse-hla-immunogenomics`. For antibody engineering, use `tooluniverse-antibody-engineering`.

---

## Core Tools

| Tool | Use For |
|------|---------|
| `IEDB_search_epitopes` | Search experimentally validated epitopes |
| `IEDB_get_epitope` | Get detailed epitope data (assay results, MHC restriction) |
| `iedb_search_mhc` | Predict MHC-I/II binding affinity for peptides |
| `iedb_search_mhc` | HLA allele frequencies by population |
| `UniProt_get_entry_by_accession` | Get antigen protein sequence |
| `UniProt_search` | Find pathogen protein sequences |
| `BVBRC_search_genome_features` | Search pathogen proteomes |
| `alphafold_get_prediction` | Get/predict antigen 3D structure |
| `EnsemblVEP_annotate_hgvs` | Check epitope conservation across variants |
| `PubMed_search_articles` | Find published vaccine studies |
| `search_clinical_trials` | Find ongoing vaccine clinical trials |

---

## Workflow

```
Phase 0: Antigen Selection
  Pathogen → essential surface proteins → sequence retrieval
    |
Phase 1: T-Cell Epitope Prediction
  MHC-I (CD8+ CTL) and MHC-II (CD4+ helper) binding prediction
    |
Phase 2: B-Cell Epitope Prediction
  Linear and conformational B-cell epitopes for antibody response
    |
Phase 3: Population Coverage
  HLA allele frequencies → design for target population
    |
Phase 4: Conservation Analysis
  Cross-strain epitope conservation → broad protection
    |
Phase 5: Candidate Assembly & Report
  Multi-epitope construct design → immunogenicity assessment
```

### Phase 0: Antigen Selection

**Best antigens for vaccines**: Surface-exposed, essential for pathogen function, conserved across strains.

```python
# Find pathogen surface proteins
UniProt_search(query="[organism] AND locations:(location:cell surface) AND reviewed:true")
# Or search BVBRC for annotated pathogen proteomes
BVBRC_search_genome_features(keyword="surface protein", genome_id="[taxon_id]")
```

**Antigen prioritization**:

| Criterion | Best (3) | Good (2) | Poor (1) |
|-----------|---------|---------|---------|
| Surface exposure | Outer membrane/secreted | Transmembrane | Cytoplasmic |
| Conservation | >95% identity across strains | 80-95% | <80% (hypervariable) |
| Essentiality | Essential gene (no growth without it) | Important but dispensable | Redundant |
| Immunogenicity precedent | Known immunogen in natural infection | Predicted immunogenic | No data |

### Phase 1: T-Cell Epitope Prediction

**MHC-I epitopes** (CD8+ cytotoxic T cells — kill infected cells):

```python
# Search for known MHC-I epitopes from your pathogen
iedb_search_mhc(
    mhc_class="I",
    qualitative_measure="Positive",
    filters={"source_organism_iri": "eq.NCBITaxon:2697049"},  # SARS-CoV-2
    select=["linear_sequence", "mhc_restriction", "qualitative_measure"],
    limit=50
)
# NOTE: iedb_search_mhc queries EXPERIMENTALLY VALIDATED binding data from IEDB.
# For computational prediction of novel peptides, use external tools (NetMHCpan, MHCflurry)
# or the IEDB Analysis Resource (tools.iedb.org) directly.
```

**MHC-II epitopes** (CD4+ helper T cells — activate B cells and CD8+ T cells):

```python
iedb_search_mhc(
    mhc_class="II",
    qualitative_measure="Positive",
    filters={"source_organism_iri": "eq.NCBITaxon:2697049"},
    limit=50
)
```

**Binding affinity interpretation**:

| IC50 (nM) | Classification | Vaccine Relevance |
|-----------|---------------|-------------------|
| < 50 | Strong binder | Include — high presentation probability |
| 50-500 | Moderate binder | Consider — may contribute to response |
| 500-5000 | Weak binder | Exclude — unlikely to be presented |
| > 5000 | Non-binder | Exclude |

**HLA supertype strategy**: For broad coverage, predict against HLA supertypes:
- **A2 supertype** (A*02:01, A*02:06, A*68:02) — covers ~40% globally
- **A3 supertype** (A*03:01, A*11:01, A*31:01) — covers ~25%
- **B7 supertype** (B*07:02, B*35:01, B*51:01) — covers ~25%
- **A2 + A3 + B7 + B44** combined — covers >90% of most populations

### Phase 2: B-Cell Epitope Prediction

B-cell epitopes trigger antibody production. Look for:
- **Linear epitopes**: Continuous peptide sequences (easier to synthesize)
- **Conformational epitopes**: 3D surface patches (requires structural data)

```python
# Check for known B-cell epitopes
IEDB_search_epitopes(query="[protein_name]", epitope_type="B cell")
# Get structure for conformational epitope prediction
alphafold_get_prediction(uniprot_id="[accession]")
```

**B-cell epitope criteria**: Surface-exposed loops, hydrophilic regions, flexible regions (high B-factor). Combine computational prediction with structural analysis.

### Phase 3: Population Coverage

```python
# Search for epitopes restricted to common HLA alleles in target population
# NOTE: No HLA frequency tool exists in ToolUniverse. For population coverage:
# 1. Use IEDB Analysis Resource (tools.iedb.org/population) for population coverage calculation
# 2. Use the HLA supertype strategy (see above) to ensure broad coverage
# 3. Search PubMed for published HLA frequency data: PubMed_search_articles(query="HLA allele frequency [population]")
```

**Population coverage targets**:

| Coverage Level | Interpretation | Action |
|---------------|---------------|--------|
| >90% | Excellent — vaccine will work in most individuals | Proceed to development |
| 70-90% | Good — most people covered; some populations underserved | Add more epitopes for uncovered HLA types |
| 50-70% | Moderate — significant gaps | Redesign with broader HLA coverage |
| <50% | Poor — vaccine will miss too many people | Fundamental redesign needed |

### Phase 4: Conservation Analysis

Check if epitopes are conserved across pathogen strains/variants:

```python
# Search for protein variants across strains
PubMed_search_articles(query="[pathogen] [protein] sequence variation strains")
# Check specific mutations in epitope regions
EnsemblVEP_annotate_hgvs(hgvs_notation="[variant_in_epitope]")
```

**Conservation interpretation**:
- **100% conserved** across all known strains → ideal vaccine target
- **>95% conserved** → good target; monitor emerging variants
- **80-95% conserved** → may need strain-specific variants in construct
- **<80% conserved** → avoid; pathogen evolves to escape this epitope

### Phase 5: Candidate Assembly & Report

**Multi-epitope construct design principles**:
1. Include 3-5 MHC-I epitopes (CD8+ response)
2. Include 2-3 MHC-II epitopes (CD4+ helper response)
3. Include 1-2 B-cell epitopes (antibody response)
4. Connect with appropriate linkers (AAY for MHC-I, GPGPG for MHC-II)
5. Add adjuvant sequence if needed (e.g., flagellin domain for TLR5)

**Report structure**:
1. **Antigen Selection** — rationale, conservation, essentiality
2. **Epitope Map** — all predicted epitopes with binding affinities and HLA restrictions
3. **Top Epitopes** — ranked by binding strength × conservation × population coverage
4. **Population Coverage** — % coverage per major world population
5. **Conservation Analysis** — strain coverage, escape risk assessment
6. **Construct Design** — multi-epitope sequence with linkers
7. **Clinical Precedent** — existing vaccines/trials for related antigens
8. **Limitations** — predicted only (T4 evidence); needs experimental validation

---

## Limitations

- **All predictions are computational** (T4 evidence) — experimental validation (binding assays, immunogenicity studies) is required before any clinical development
- **No immunogenicity guarantee** — MHC binding ≠ immunogenicity; many good binders are not immunogenic in vivo
- **B-cell epitope prediction is less reliable** than T-cell; conformational epitopes require accurate structures
- **No adjuvant optimization** — adjuvant selection requires empirical testing
- **Pathogen evasion** — rapidly evolving pathogens (HIV, influenza) may escape epitope-based vaccines
