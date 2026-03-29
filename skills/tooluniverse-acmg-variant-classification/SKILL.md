---
name: tooluniverse-acmg-variant-classification
description: Systematic ACMG/AMP variant classification using ToolUniverse tools. Given a genetic variant (HGVS, rsID, or gene+change), applies all 28 ACMG criteria (PVS1, PS1-4, PM1-6, PP1-5, BA1, BS1-4, BP1-7) through automated database queries and computational predictions. Produces a final 5-tier classification (Pathogenic / Likely Pathogenic / VUS / Likely Benign / Benign) with evidence summary. Use when asked to classify a variant, interpret a VUS, apply ACMG criteria, assess pathogenicity, or determine clinical significance of a germline variant.
---

# ACMG/AMP Variant Classification

## ACMG Reasoning

Each criterion (PS, PM, PP for pathogenic; BS, BP for benign) contributes a weighted piece of evidence for or against pathogenicity. The classification is the COMBINATION of all activated criteria, not any single criterion. Do not overweight a single finding.

The hierarchy is: PVS1 (very strong) > PS (strong) > PM (moderate) > PP (supporting). On the benign side: BA1 (stand-alone) > BS (strong) > BP (supporting). A frameshift in a LOF-intolerant gene (PVS1) plus a ClinVar expert-panel pathogenic entry (PS1) is pathogenic. A single PP criterion alone is not. The combination rule is what matters.

Two common errors to avoid: (1) seeing a "Pathogenic" ClinVar entry and stopping — that is PP5 (supporting) unless it has expert-panel review, not automatic confirmation; (2) dismissing a variant because one predictor says "tolerated" — discordant predictors mean neither PP3 nor BP4 applies, which is neutral evidence, not benign evidence.

Always apply criteria conservatively. When evidence is ambiguous, leave the criterion unmet. Cite the source for every criterion you activate so clinicians can audit the reasoning.

**KEY PRINCIPLES**:
1. **Criteria-driven** — cite which criteria were activated and why
2. **Conservative** — do not upgrade a criterion when evidence is ambiguous
3. **Gene-aware** — adjust thresholds based on gene mechanism (LOF vs. gain-of-function)
4. **Population-calibrated** — use ancestry-specific gnomAD frequencies, not just global AF
5. **Transparent** — show evidence for each criterion
6. **Source-referenced** — every criterion activation must cite the database/tool source
7. **English-first queries** — always use English terms in tool calls; respond in user's language

---

## LOOK UP, DON'T GUESS
When uncertain about any scientific fact, SEARCH databases first (PubMed, UniProt, ChEMBL, ClinVar, etc.) rather than reasoning from memory. A database-verified answer is always more reliable than a guess.

---

## When to Use

- "Classify BRCA2 c.5946delT using ACMG criteria"
- "Is this VUS pathogenic? NM_000059.4:c.7397T>C"
- "Apply ACMG guidelines to rs28897743"
- "What is the pathogenicity of CFTR p.Arg117His?"
- "ACMG classification for TP53 R248W"

---

## Tool Parameter Reference

| Tool | Key Parameters | Notes |
|------|---------------|-------|
| `VariantValidator_validate_variant` | `variant_description`, `genome_build`, `select_transcripts` | genome_build="GRCh38" |
| `VariantValidator_gene2transcripts` | `gene_symbol` | Returns MANE Select transcript |
| `MyVariant_query_variants` | `query` | HGVS or rsID. Returns ClinVar, gnomAD, CADD, REVEL, SIFT, PolyPhen |
| `EnsemblVEP_annotate_hgvs` | `hgvs_notation` | Consequence, colocated variants, ancestry gnomAD |
| `gnomad_search_variants` | `query` | rsID to gnomAD variant ID |
| `gnomad_get_variant` | `variant_id` | Per-ancestry population frequencies |
| `gnomad_get_gene_constraints` | `gene_symbol` | pLI, LOEUF, mis_z |
| `ClinVar_search_variants` | `query` | Variable response format: list OR `{status, data}` |
| `ClinVar_get_variant_details` | `variant_id` | ClinVar numeric ID |
| `civic_get_variants_by_gene` | `gene_id` | CIViC numeric gene ID (NOT symbol). Known: BRAF=5, BRCA2=19 |
| `UniProt_get_function_by_accession` | `accession` | Returns list of strings |
| `InterPro_get_entries_for_protein` | `accession` | Domain architecture by UniProt accession |
| `alphafold_get_prediction` | `qualifier` | UniProt accession; pLDDT confidence |
| `PubMed_search_articles` | `query`, `limit` | Returns list of dicts |
| `MyGene_query_genes` | `query` | Filter by `symbol` match (first hit may not match) |

---

## Phase 0: Variant Validation and Normalization

Wrong HGVS or wrong transcript cascades errors through every downstream criterion. Validate first.

1. **Get MANE Select transcript**: `VariantValidator_gene2transcripts(gene_symbol="BRCA2")`
2. **Validate variant**: `VariantValidator_validate_variant(variant_description="NM_000059.4:c.5946delT", genome_build="GRCh38", select_transcripts="mane_select")`
3. **Resolve gene IDs**: `MyGene_query_genes(query="BRCA2")` — extract Ensembl ID and UniProt accession. Filter results by `symbol == 'BRCA2'` (first hit may not match).
4. **Record**: HGVS coding, HGVS protein, genomic coordinates, variant type (frameshift/missense/nonsense/splice/synonymous/in-frame indel).

Accepted inputs: HGVS coding (NM_000059.4:c.5946delT), HGVS protein (BRCA2 p.Val600Glu), rsID (rs28897743), gene+change (BRCA1 c.68_69del), genomic coordinates.

---

## Phase 1: Population Frequency (BA1, BS1, BS2, PM2)

Population AF is among the strongest evidence in either direction. A variant at >5% in any population is almost certainly benign (BA1 — stand-alone, no further analysis needed). Absent from gnomAD supports pathogenicity (PM2, now usually applied as PM2_Supporting per ClinGen guidance).

Use ancestry-specific AF, not just global. A variant at 8% in East Asian populations but rare globally is benign in that ancestry context. For BS1, the threshold depends on disease prevalence and inheritance — the default is 1% for common diseases, 0.1% for rare.

```python
gnomad_search_variants(query="rs28897743")          # get gnomAD variant ID
gnomad_get_variant(variant_id="...")                 # per-ancestry frequencies
gnomad_get_gene_constraints(gene_symbol="BRCA2")     # pLI, LOEUF, mis_z
MyVariant_query_variants(query="rs28897743")          # fallback: gnomad_genome.af
```

If gnomAD data is unavailable, note the gap and continue — absence of data is not the same as evidence of absence.

---

## Phase 2: Computational Predictions (PP3, BP4)

No single predictor is definitive. The reasoning is: concordance across multiple independent predictors provides supporting evidence. Discordance means neither PP3 nor BP4 applies — it is neutral, not benign.

PP3 (supporting pathogenic) applies when the majority of predictors agree damaging, or when REVEL >= 0.7 alone (sufficient per ClinGen guidance). BP4 (supporting benign) requires ALL predictors to agree benign, or REVEL < 0.15 or CADD < 15. These criteria apply only to missense variants.

```python
MyVariant_query_variants(query="...")        # REVEL, CADD PHRED, AlphaMissense, SIFT, PolyPhen
EnsemblVEP_annotate_hgvs(hgvs_notation="...") # consequence, SpliceAI deltas
```

For non-missense variants, skip PP3/BP4 and focus on SpliceAI scores in Phase 5.

---

## Phase 3: Clinical Database Evidence (PS1, PM5, PP5, BP6)

ClinVar aggregates clinical lab classifications. The reasoning: if the same amino acid change (different nucleotide) is established pathogenic, that is strong evidence (PS1) because the mechanism is the amino acid change. If a different pathogenic missense occurs at the same residue, that is moderate evidence (PM5) — the residue is functionally important.

PP5 applies when ClinVar shows Pathogenic with >= 2-star review (criteria provided, multiple submitters). Weight by the number of concordant submitters. Conflicting ClinVar interpretations mean neither PP5 nor BP6 should be applied. ClinGen has proposed downweighting PP5/BP6 — treat them as supporting, not strong.

```python
ClinVar_search_variants(query="BRCA2 c.5946delT")
ClinVar_get_variant_details(variant_id="...")
civic_get_variants_by_gene(gene_id=19)   # BRCA2 CIViC ID is 19
```

---

## Phase 4: Functional Domain and Protein Analysis (PM1, PP2, BP1)

Variants in well-established functional domains with known pathogenic variant enrichment are more likely pathogenic. PM1 (moderate pathogenic) requires the variant to be in a hotspot domain with low benign variation — use InterPro domain architecture and UniProt active/binding sites to assess.

PP2 and BP1 are mutually exclusive. PP2 (supporting pathogenic) applies to missense in genes where missense is the known mechanism and benign missense rate is low (mis_z > 3.09). BP1 (supporting benign) applies to missense in genes where only truncating variants cause disease (LOF-only mechanism) — a missense in such a gene is unlikely to be pathogenic.

```python
UniProt_get_function_by_accession(accession="P51587")        # active sites, binding sites
InterPro_get_entries_for_protein(accession="P51587")          # domain architecture
alphafold_get_prediction(qualifier="P51587")                   # pLDDT > 90 = structured region
gnomad_get_gene_constraints(gene_symbol="BRCA2")              # mis_z for PP2/BP1
```

---

## Phase 5: Splice Impact Assessment (PVS1)

PVS1 is the strongest single pathogenic criterion. A null variant (nonsense/frameshift/canonical splice/initiation codon) in a gene where LOF is the established mechanism can activate PVS1, but the full strength depends on context.

Apply PVS1 at full strength when: null variant + LOF is known mechanism + variant is not in the last exon or last 50bp of the penultimate exon + no rescue transcript exists. Downgrade to PVS1_Moderate if the variant is in the last exon or NMD escape is likely. Downgrade to PVS1_Supporting if a rescue transcript is possible or SpliceAI >= 0.5 but not a canonical splice site. Do NOT apply PVS1 if LOF mechanism is uncertain.

```python
EnsemblVEP_annotate_hgvs(hgvs_notation="...")   # splice_donor_variant, splice_acceptor_variant
MyVariant_query_variants(query="...")             # SpliceAI deltas
gnomad_get_gene_constraints(gene_symbol="...")    # pLI >= 0.9 or LOEUF < 0.35 = LOF intolerant
```

---

## Phase 6: Literature and Functional Evidence (PS3, BS3, PP1, PP4)

Well-designed functional assays showing LOF (PS3) or normal function (BS3) can shift a classification decisively. PS3/BS3 can be downgraded (e.g., PS3_Supporting) for less rigorous assays. Not all functional assays qualify — ClinGen gene-specific guidance defines valid assays.

PP1 (co-segregation) upgrades to PP1_Strong at >= 7 informative meioses. PP4 applies when the patient's phenotype is highly specific for the gene's disease.

```python
PubMed_search_articles(query="BRCA2 c.5946delT functional assay", limit=10)
PubMed_search_articles(query="BRCA2 c.5946delT segregation family", limit=5)
```

Criteria requiring clinical data (PS2, PS4, PM3, PM6, BS4, BP2, BP5) cannot be assessed automatically. Document as "Not Assessed" unless the user provides clinical context.

PM4 (protein length change in non-repeat region) and BP3 (in-frame indel in repeat) can be partially assessed from variant type. BP7 (synonymous, no splice impact) is assessable via SpliceAI < 0.1.

---

## Classification Algorithm

Combine criteria at their applied strength (after upgrades/downgrades):

**Pathogenic**: (1) PVS1 + ≥1 Strong; (2) PVS1 + ≥2 Moderate; (3) PVS1 + 1 Moderate + 1 Supporting; (4) PVS1 + ≥2 Supporting; (5) ≥2 Strong; (6) 1 Strong + ≥3 Moderate; (7) 1 Strong + 2 Moderate + ≥2 Supporting; (8) 1 Strong + 1 Moderate + ≥4 Supporting

**Likely Pathogenic**: (1) PVS1 + 1 Moderate; (2) 1 Strong + 1-2 Moderate; (3) 1 Strong + ≥2 Supporting; (4) ≥3 Moderate; (5) 2 Moderate + ≥2 Supporting; (6) 1 Moderate + ≥4 Supporting

**Benign**: (1) BA1 stand-alone; (2) ≥2 Strong benign

**Likely Benign**: (1) 1 Strong benign + 1 Supporting benign; (2) ≥2 Supporting benign

**VUS**: Criteria do not meet any threshold above, OR pathogenic and benign evidence conflict.

---

## Output Format

```markdown
# ACMG Variant Classification Report

## Variant: [HGVS]
- **Gene**: [symbol] | **Transcript**: [MANE Select] | **Protein**: [p.notation] | **Type**: [variant type]

## Classification: [PATHOGENIC / LIKELY PATHOGENIC / VUS / LIKELY BENIGN / BENIGN]

## Evidence Summary
### Pathogenic Criteria Met
| Criterion | Strength | Evidence | Source |

### Benign Criteria Met
| Criterion | Strength | Evidence | Source |

### Criteria Not Met (key ones with reasoning)
### Criteria Not Assessed (and why)

## Detailed Evidence
- Population: gnomAD AF, ancestry max, homozygotes, gene constraints
- Computational: predictor concordance
- Clinical: ClinVar classification + review status, CIViC entries
- Domain: InterPro domains, UniProt annotations
- Splice: SpliceAI scores, canonical site status
- Literature: key functional study findings

## Classification Logic
Applied rule: [e.g., "PVS1 + PM2_Supporting = Likely Pathogenic (LP rule 1)"]

## Limitations
- [Criteria not assessed and what data would be needed]
```

---

## Common Patterns

**Pattern 1: Known pathogenic frameshift** — "Classify BRCA2 c.5946delT"
Phase 0 (validate) → Phase 1 (gnomAD absent, PM2_Supporting) → Phase 3 (ClinVar Pathogenic, PP5) → Phase 4 (DNA repair domain, PM1) → Phase 5 (frameshift + LOF gene, PVS1) → Phase 6 (literature PS3)
Result: **Pathogenic** (PVS1 + PS3 + PM1 + PM2_Supporting + PP5)

**Pattern 2: Missense VUS** — "Is BRCA1 p.Arg1699Gln pathogenic?"
Phase 0 → Phase 1 (rare, PM2_Supporting) → Phase 2 (REVEL 0.82, CADD 26, PP3) → Phase 3 (ClinVar VUS) → Phase 4 (BRCT domain, PM1) → Phase 6 (reduced activity, PS3_Moderate)
Result: **Likely Pathogenic** (PS3_Moderate + PM1 + PM2_Supporting + PP3)

**Pattern 3: Common benign variant** — "ACMG for rs1800497"
Phase 1 (gnomAD AF=0.21, BA1) → short-circuit. Result: **Benign** (BA1 stand-alone)

**Pattern 4: Deep-intronic variant** — "Classify NM_000059.4:c.7977+100A>G"
Phase 1 (check AF) → Phase 5 (SpliceAI < 0.1) → Result: **Likely Benign** or VUS depending on frequency
