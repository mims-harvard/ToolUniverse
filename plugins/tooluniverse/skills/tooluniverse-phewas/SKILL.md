---

name: tooluniverse-phewas
description: "Cross-ancestry / cross-biobank phenome-wide association (PheWAS) and replication. Given ONE variant (rsID) or ONE gene, look up every phenotype it associates with across European/UK (UKB-TOPMed), Finnish (FinnGen), Japanese (BioBank Japan), and Taiwanese (TPMI) biobanks, plus exome-wide gene-burden PheWAS (Genebass), then judge whether an association replicates across ancestries or is population-specific. Use whenever the user asks \"what else is this variant/gene associated with\", \"does this association replicate in other ancestries / biobanks\", \"is this effect East-Asian-specific\", \"pleiotropy of rsXXX\", \"phenome scan\", or wants to compare effect sizes/allele frequencies of a variant across populations. NOT for the forward direction (trait → which SNPs: use the gwas-* skills), NOT for fine-mapping a locus (use tooluniverse-gwas-finemapping), and NOT for single-SNP mechanism tracing in one population (use tooluniverse-gwas-snp-interpretation)."
---

# Cross-Biobank PheWAS & Replication

A **PheWAS is the inverse of a GWAS**: a GWAS fixes a phenotype and scans variants; a PheWAS fixes a variant (or gene) and scans the entire phenome. The scientific payoff of running it across *several* biobanks is **replication and ancestry resolution** — an association seen in one population that reappears in another (with the same effect direction) is far more credible, while one that appears only in East-Asian cohorts may reflect ancestry-specific LD, allele frequency, or biology.

This skill orchestrates one variant/gene across four ancestries plus a gene-burden layer. **Look up, don't guess** — never assert a variant's phenotype associations or effect sizes from memory; the whole point is the live cross-biobank numbers.

## The biobank panel

| Tool | Biobank | Ancestry | Build | Evidence type |
|---|---|---|---|---|
| `UKBTOPMed_phewas_by_variant` | UKB-TOPMed | European (UK) | GRCh38 | per-phenotype assoc (phecodes, ~1,400) |
| `FinnGen_get_variant_finemapping` | FinnGen | Finnish | GRCh38 | credible-set membership (fine-mapping) |
| `BioBankJapan_phewas_by_variant` | BioBank Japan | Japanese | **GRCh37** | per-phenotype assoc |
| `TPMI_phewas_by_variant` | TPMI | Taiwanese (Han) | GRCh38 | per-phenotype assoc (ICD-based) |
| `Genebass_gene_burden_phewas` | Genebass (UKB exomes) | European | GRCh38 | gene-level rare-variant burden |

The **four `*_phewas_by_variant` tools** (UKB-TOPMed, BBJ, TPMI) and **`Genebass_gene_burden_phewas`** accept an **rsID** (Genebass also accepts a gene symbol) and resolve coordinates themselves via Ensembl, picking the correct allele for multi-allelic SNPs; the build difference between BBJ-GRCh37 and the others is handled internally — just pass the rsID. You normally do **not** need to hand-convert coordinates for these.

**`FinnGen_get_variant_finemapping` is the exception**: it does NOT accept an rsID. It requires an explicit GRCh38 `variant` string in `chr:pos:ref:alt` format (e.g. `"10:112998590:C:T"`). Resolve the rsID to GRCh38 coordinates first — the simplest way is to read the `variant`/`rsids` field returned by the UKB-TOPMed (GRCh38) call, then pass that coordinate string to FinnGen.

## Workflow

### Step 1 — Decide variant-level vs gene-level
- **Have an rsID / specific variant** → variant-level panel (the four `*_phewas_by_variant` + FinnGen). This is the common case. Pass the rsID directly to the four `*_phewas_by_variant` tools; for `FinnGen_get_variant_finemapping` you must supply an explicit GRCh38 `chr:pos:ref:alt` string (resolve the rsID first — see "The biobank panel" note above).
- **Have a gene and care about rare coding burden** (e.g. "what does loss-of-function of PCSK9 do?") → `Genebass_gene_burden_phewas` with `burden_set: "pLoF"`. Add the variant panel too if a specific common variant is also of interest.

### Step 2 — Query the panel in parallel
Call the relevant tools for the same rsID. Always pass `max_pval: 5e-8` (genome-wide significance) for the variant tools when you want only robust hits, or omit it to see suggestive associations too. Example anchor call:

```
UKBTOPMed_phewas_by_variant(rsid="rs7903146", max_pval=5e-8, limit=25)
BioBankJapan_phewas_by_variant(rsid="rs7903146", max_pval=5e-8, limit=25)
TPMI_phewas_by_variant(rsid="rs7903146", max_pval=5e-8, limit=25)
FinnGen_get_variant_finemapping(variant="10:112998590:C:T")   # FinnGen needs a variant string (GRCh38) or use an rsID-resolved coord
```

For gene-burden:
```
Genebass_gene_burden_phewas(gene="PCSK9", burden_set="pLoF", max_pval=2.5e-6, limit=25)
```

### Step 3 — Align phenotypes across biobanks
Phenotype coding differs per biobank (UKB/TPMI use phecodes, BBJ uses curated endpoints, FinnGen uses its own endpoint codes, Genebass uses UKB field codes). Match on the **human-readable name / disease concept**, not the code. Group associations into shared concepts (e.g. "Type 2 diabetes" across all of them) before comparing.

### Step 4 — Judge replication (see interpretation table)
For each shared phenotype concept, compare significance, **effect-size direction (sign of beta)**, and allele frequency across biobanks.

### Step 5 — Report
Use the report template below. Lead with what replicates, then ancestry-specific signals, then caveats.

## Interpretation

| Pattern across biobanks | Meaning |
|---|---|
| Significant + **same beta sign** in ≥2 ancestries | **Replicated, robust** association — highest confidence |
| Significant in European but not East-Asian | May be European-specific, OR underpowered / lower allele frequency in East-Asian cohort — check `af` and `num_cases` before concluding biology |
| Significant only in BBJ/TPMI | Candidate **East-Asian-specific** effect (ancestry-specific LD or biology) — flag for follow-up |
| **Opposite beta signs** between biobanks | Caution: possible strand/allele-coding mismatch, or genuine flip — verify the ref/alt allele each biobank reported before interpreting |
| Variant-level null but Genebass burden significant | Phenotype driven by **rare coding** variation in the gene, not the common variant |
| FinnGen credible-set hit but weak elsewhere | Variant is a fine-mapped candidate in Finns; credible-set membership ≠ p-value, so treat as corroborating, not quantitative |

**Allele-frequency caveat is central.** A "missing" association in one population is only interesting after you confirm the variant is actually common enough there to be powered. Each `*_phewas_by_variant` result carries `af`, `num_cases`, `num_controls` — use them. A variant at AF 0.30 in Europeans but 0.02 in Japanese will look "European-specific" purely from power, not biology.

## Report structure

```
# PheWAS: <rsID / gene> (<nearest gene>)

## Replicated associations (≥2 ancestries, concordant direction)
- <phenotype> — UKB-TOPMed p=<>, β=<>; BBJ p=<>, β=<>; TPMI p=<>, β=<>  → concordant

## Ancestry-specific / unreplicated signals
- <phenotype> — significant in <biobank> only; AF=<> elsewhere (powered? yes/no)

## Gene-burden layer (if run)
- <phenotype> — Genebass <burden_set> p=<>

## Caveats
- allele-frequency / power notes, build notes, coding-direction checks
```

## Worked example (rs7903146, TCF7L2)

Running the panel on `rs7903146` returns **Type 2 diabetes** as the top hit with the T (risk) allele increasing risk (β>0) in every ancestry — UKB-TOPMed (p~1e-134), BioBank Japan (native Japanese T2D endpoint p~2e-47; its external Suzuki-2024 meta entries underflow to `pval: 0.0`), and TPMI (p~6e-11) — concordant positive effect across European, Japanese, and Taiwanese ancestries → textbook replicated association. (Exact p-values drift as biobanks update; treat these as illustrative.) The weaker TPMI p-value tracks the **lower T-allele frequency in East Asians** (AF~0.29 in Europeans vs ~0.02–0.05 in East Asians) and smaller case count, not a weaker biological effect — exactly the power caveat above. A nice secondary signal: in BBJ the T2D-risk allele associates with *lower* BMI/body weight, the known TCF7L2 feature that it acts through insulin secretion rather than adiposity. This is the canonical robustly-replicated common-variant association and a good sanity check that the panel is working.

**Reading `pval: 0.0`:** a returned p-value of exactly `0.0` is floating-point underflow on an astronomically significant association (the true value is below ~1e-308), **not** "no association." Treat it as the strongest possible hit, not a null.

**BioBank Japan catalogue note:** the BBJ PheWeb surfaces both native BBJ endpoints *and* external multi-ancestry GWAS meta-analyses (e.g. Suzuki 2024, with separate EUR/EAS/AFA/SAS/HIS rows). This is a bonus — you get per-ancestry betas from one call — but do not double-count the meta-analysis rows as independent "Japanese" evidence; the native BBJ endpoint is the Japanese-specific one.

## Limitations
- **Variant-level only reports what each biobank pre-computed.** PheWeb instances return summary associations, not raw genotypes; you cannot run a custom phenotype not in their catalogue.
- **TPMI / BBJ phenotype catalogues are ICD/endpoint-based** and less granular than UKB phecodes; absence of a phenotype may mean "not catalogued", not "no association".
- **Genebass is European (UKB exomes) only** — it adds a rare-variant burden layer but not an ancestry dimension.
- **No automatic meta-analysis.** This skill compares biobanks qualitatively (replication, direction, power). For a formal cross-ancestry meta-analysis or fine-mapping, hand off to dedicated tooling (`tooluniverse-mendelian-randomization`, `tooluniverse-gwas-finemapping`).
- **FinnGen evidence is credible-set membership**, a different currency than the PheWeb p-values; do not put its "hits" on the same numeric axis.
