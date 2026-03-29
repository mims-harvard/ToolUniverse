# Skill: Population Genetics Analysis

**MC Strategy**: Population genetics MC questions often test whether you know a specific theorem or result. COMPUTE the answer first (use popgen_calculator.py or write Python), then match to options. Don't try to reason about which option "sounds right."

Analyze population-level genetic variation, allele frequencies, GWAS associations, clinical significance, and evolutionary constraints using ToolUniverse tools.

## When to Use

Activate this skill when the user asks about:
- Allele frequencies across populations (gnomAD, 1000 Genomes)
- GWAS associations for diseases/traits
- Clinical variant interpretation (ClinVar, VEP)
- Gene-level constraint metrics (pLI, LOEUF, o/e ratios)
- Selection, drift, linkage disequilibrium, or population structure
- Variant annotation and functional consequences

## LOOK UP, DON'T GUESS

Query gnomAD/1000Genomes/GWAS Catalog FIRST for allele frequencies and associations. Preferred: use the `PopGen_hwe_test`, `PopGen_fst`, `PopGen_inbreeding`, and `PopGen_haplotype_count` tools for HWE, Fst, inbreeding, and haplotype calculations. Fallback: run `popgen_calculator.py` directly. For theoretical problems (delta-q, drift, LD decay), apply the formulas in the Theoretical Reasoning section below.

---

## Tool Quick Reference

| Tool | Key Parameters | Notes |
|------|---------------|-------|
| `gnomad_search_variants` | `query` (REQUIRED) | Resolve rsID to variant_id format "CHR-POS-REF-ALT" |
| `gnomad_get_variant` | `variant_id` (REQUIRED), `dataset` | Population frequencies. Default dataset: gnomad_r3; use gnomad_r4 for latest |
| `gnomad_get_gene_constraints` | `gene_symbol` (REQUIRED) | pLI, o/e ratios. May timeout -- retry once |
| `MyVariant_query_variants` | `query` (REQUIRED) | Aggregated: ClinVar + dbSNP + gnomAD + CADD. Uses hg19 coordinates |
| `EnsemblVEP_annotate_rsid` | `variant_id` (REQUIRED) | Functional consequence, SIFT, PolyPhen. Param is "variant_id" NOT "rsid" |
| `EnsemblVEP_variant_recoder` | `variant_id` (REQUIRED) | Convert between rsID/HGVS/VCF/SPDI |
| `gwas_get_snps_for_gene` | `gene_symbol` (REQUIRED) | All GWAS SNPs for a gene |
| `gwas_search_associations` | `query` (REQUIRED) | GWAS for a disease/trait (NOT gene name -- use gwas_get_snps_for_gene for genes) |
| `gwas_get_variants_for_trait` | `trait` (REQUIRED) | Variants associated with a trait |
| `ClinVar_search_variants` | `gene`, `condition`, `significance` | At least one filter required |
| `RegulomeDB_query_variant` | `rsid` (REQUIRED) | Regulatory scoring (1a=strongest to 7=minimal) |

### Critical Gotchas

1. **gnomAD variant_id**: Format is `"CHR-POS-REF-ALT"` (no "chr" prefix). Always resolve rsIDs via `gnomad_search_variants` first.
2. **gwas_search_associations**: Takes disease/trait names ONLY. Gene names will fail. Use `gwas_get_snps_for_gene` for gene-based lookups.
3. **gwas_search_snps**: BROKEN (HTTP 500). Use `gwas_get_snps_for_gene` instead.
4. **VEP/ClinVar responses**: Format is variable (list, `{data, metadata}`, or `{error}`). Handle all three.

---

## Workflow Patterns

**Variant frequency**: `gnomad_search_variants` -> `gnomad_get_variant(dataset="gnomad_r4")` -> `MyVariant_query_variants` (1000G pop breakdowns) -> `EnsemblVEP_annotate_rsid`

**GWAS for disease**: `gwas_search_associations` -> `gwas_get_variants_for_trait` -> `gnomad_get_variant` for top hits -> `EuropePMC_search_articles`

**Gene characterization**: `gnomad_get_gene_constraints` -> `gwas_get_snps_for_gene` -> `ClinVar_search_variants` -> `PubMed_search_articles`

**Pathogenicity assessment**: `EnsemblVEP_annotate_rsid` -> `MyVariant_query_variants` (CADD, ClinVar) -> `gnomad_get_variant` (frequency) -> `RegulomeDB_query_variant` (if non-coding)

---

## Theoretical Reasoning (CRITICAL for computation problems)

These formulas are needed for quantitative population genetics problems. Work through step by step, showing intermediate values.

### Allele Frequency Change Under Selection (delta-q)

For a recessive deleterious allele (fitness: AA=1, Aa=1, aa=1-s):
```
delta_q = -s * q^2 * p / (1 - s * q^2)
```
where p = freq(A), q = freq(a), s = selection coefficient.

For dominant deleterious (AA=1, Aa=1-s, aa=1-s):
```
delta_q = -s * q * p / (1 - s * q * (2 - q))
```

For heterozygote advantage (AA=1-s1, Aa=1, aa=1-s2):
```
equilibrium: q_hat = s1 / (s1 + s2)
```
Example: plug in s1 and s2 from the question; q_hat = s1/(s1+s2).

**Selection against recessives is slow at low q** because most a alleles hide in heterozygotes. Time to reduce q from q0 to qt: t ~ (1/qt - 1/q0) / s generations.

### Genetic Drift in Small Populations

**Variance in allele frequency per generation**: Var(delta_p) = p*q / (2*Ne)

**Probability of fixation** of a new neutral mutation: 1/(2*Ne)

**Time to fixation** (given it fixes): ~4*Ne generations for neutral alleles

**Heterozygosity decay**: H_t = H_0 * (1 - 1/(2*Ne))^t

After t generations, fraction of heterozygosity lost ~ 1 - e^(-t/(2*Ne))

**Effective population size (Ne)** adjustments:
- Unequal sex ratio: Ne = 4*Nf*Nm / (Nf + Nm)
- Fluctuating size: Ne = harmonic mean of N across generations
- Bottleneck: dominated by the smallest generation size

**Drift vs selection**: Drift dominates when |s| < 1/(2*Ne). A variant with s=0.01 behaves neutrally in a population of Ne < 50.

### Linkage Disequilibrium (LD) Decay

**D** = freq(AB) - freq(A)*freq(B), where A and B are alleles at two loci.

**Decay with recombination**: D_t = D_0 * (1 - r)^t, where r = recombination fraction, t = generations.

**Half-life of LD**: t_half = -ln(2) / ln(1-r) ~ 0.693/r generations (for small r).

**r-squared** (normalized LD): r^2 = D^2 / (pA * pa * pB * pb). Range 0-1.

**Expected r^2 in finite population at equilibrium**: E[r^2] = 1 / (1 + 4*Ne*r) (for drift-recombination balance).

**Practical implications**:
- Tightly linked loci (r < 0.01): LD persists for hundreds of generations
- Loosely linked (r = 0.5, independent assortment): LD halves every generation
- GWAS tag SNPs work because LD extends over blocks; block size depends on Ne and recombination rate
- African populations have shorter LD blocks (larger historical Ne) -> need denser SNP arrays

### Hardy-Weinberg Equilibrium

For alleles A (freq p) and a (freq q=1-p): expected genotypes AA=p^2, Aa=2pq, aa=q^2.

**Chi-square test**: df=1 (2 alleles). Preferred: use `PopGen_hwe_test` tool. Fallback: `popgen_calculator.py --type hwe --AA N1 --Aa N2 --aa N3`.

**Causes of HWE departure**: non-random mating, selection, migration, drift, genotyping error. Excess homozygotes -> inbreeding or population structure (Wahlund effect). Excess heterozygotes -> overdominant selection or negative assortative mating.

### Heritability

- **H^2 (broad-sense)** = V_G / V_P; **h^2 (narrow-sense)** = V_A / V_P
- V_G includes ALL genetic variance: additive + dominance + epistasis. Trap: "broad-sense" is not just additive.
- Under HWE with two alleles (p, q): genotype frequencies are p^2, 2pq, q^2
- Phenotype frequency from genotype: sum(genotype_freq * penetrance) for each genotype class
- For quantitative traits: V_P = V_G + V_E (no covariance assumed)
- With dominance: assign genotypic values (e.g., AA=a, Aa=d, aa=-a), compute mean, then V_G from freq-weighted squared deviations
- **PGS vs SNP-h² trap**: PGS R² is NOT necessarily ≤ h²_SNP. With large GWAS, PGS can exceed SNP-h² by tagging rare causal variants through LD with common SNPs. The word "necessarily" makes this claim False. h²_SNP is estimated from common variants; PGS can capture additional variance.

### Path Analysis (Causal Diagrams)

- Trace ALL paths from cause to effect through the diagram (direct + indirect)
- Each path's contribution = product of path coefficients along that path
- Total effect (correlation) = sum of contributions from all paths
- Indirect effects can mask (suppression) or inflate (confounding) the direct effect
- Unanalyzed correlations (double-headed arrows) count as valid path segments
- **Never ignore indirect paths** — the total is rarely just the direct arrow

### Genetic Combinatorics (F2 crosses, haplotype counting)

For n SNPs between two inbred (homozygous) strains:
- F1 is heterozygous at all n loci
- F2 distinct haplotypes = 2^n (each SNP contributes parental A or B allele)
- F2 distinct diploid genotypes = 3^n (AA, AB, BB at each locus)
- F2 unique chromosomes (distinct haplotypes) = 2^n (e.g., 5 SNPs → 2^5 = 32; but subtract the 2 parental haplotypes if "novel" is asked → 30)
- **ALWAYS write and run Python code** (`python3 -c "..."`) for these counts. Never enumerate by hand.
- For specimens/counting from field data: parse the data into a structure and compute programmatically.

### Mutation-Selection Balance

Equilibrium frequency of a deleterious allele:
- Recessive lethal: q_hat = sqrt(mu/s) ~ sqrt(mu) when s=1
- Dominant lethal: q_hat = mu/s
- Example: mu=1e-5, s=1 (recessive lethal) -> q_hat = 0.003 (carrier freq ~ 0.006)

### F-statistics and Population Structure

- **Fis**: Inbreeding within subpopulations (heterozygote deficit within demes)
- **Fst**: Differentiation between subpopulations. Fst = Var(p) / (p_bar * q_bar)
- **Fit**: Total inbreeding. (1-Fit) = (1-Fis)(1-Fst)
- Fst interpretation: <0.05 little, 0.05-0.15 moderate, 0.15-0.25 great, >0.25 very great differentiation
- Preferred: use `PopGen_fst` tool. Fallback: `popgen_calculator.py --type fst --p1 X --p2 Y --n1 N1 --n2 N2`

---

## Mendelian Genetics Reasoning Framework

For any genetics cross problem, follow these steps IN ORDER. Do not skip steps.

### Step 1: Identify genes, locations, and allele relationships
- List every gene involved in the cross
- Determine chromosomal location: autosomal vs X-linked (X-linked genes show different inheritance in males vs females)
- Determine allele relationships: dominant/recessive, codominant, incomplete dominance
- Note any epistasis, suppressor, or modifier interactions between genes

### Step 2: Write parental genotypes explicitly
- Use standard notation (e.g., Aa Bb for autosomal; X^w X^+ for X-linked)
- For X-linked genes, males are hemizygous (X^w Y), not homozygous
- If parental genotypes are not given, deduce them from phenotypes and pedigree context

### Step 3: Draw Punnett square(s) for each gene
- For multi-gene crosses, handle each gene independently (if unlinked) then combine
- For linked genes, use recombination frequency to adjust gamete ratios
- For X-linked genes, remember that fathers pass X to all daughters and Y to all sons

### Step 4: Calculate expected phenotypic ratios
- Multiply independent gene ratios (e.g., 3:1 x 3:1 = 9:3:3:1)
- For X-linked: calculate male and female ratios separately, then combine or report separately as required

### Step 5: Verify ratios sum to 1.0
- Convert all ratios to fractions and confirm they sum to 1
- If they don't sum to 1, there is an error in the Punnett square or gamete calculation

### Step 6: Apply phenotype modification rules AFTER computing genotypic ratios
- For epistasis: first compute the full genotypic ratios (e.g., 9:3:3:1), then collapse genotype classes that produce the same phenotype
- For suppressor genes: a suppressor homozygote (su/su) restores wild-type in an otherwise mutant background. Apply suppression AFTER determining which individuals carry the mutant allele
- Example: 9 A_B_ : 3 A_bb : 3 aaB_ : 1 aabb with recessive epistasis (aa masks B) becomes 9:3:4

---

## E. coli Hfr Mapping Framework

For bacterial conjugation and Hfr mapping problems:

### Core Principles
- In Hfr x F- crosses, the Hfr chromosome is transferred linearly starting from the origin of transfer (oriT)
- **Gene transfer order = chromosomal order from the origin**
- Early markers (entering first) are closest to the origin of transfer
- Late markers (entering last) are farthest from the origin

### Interrupted Mating Experiments
- Genes that appear in recombinants at earlier time points are closer to oriT
- The time of entry gives the order and approximate distance between genes
- Recombinants require integration by homologous recombination (double crossover)

### Recombination Frequency Between Markers
- **KEY TRAP**: Highest recombination frequency occurs between markers that are FARTHEST APART on the transferred segment
- This is because more time elapses between entry of distant markers, providing more opportunity for recombination events between them
- Conversely, markers that enter close together in time show LOW recombination between them
- Do NOT confuse "highest recombination frequency" with "first markers to enter" -- these are opposite concepts

### Ordering Markers from Hfr Data
1. Use time-of-entry data to establish gene order relative to oriT
2. Use recombination frequency data between pairs of selected markers to confirm/refine order
3. Multiple Hfr strains with different origins can be used to build a circular map

---

## MCQ Elimination Strategy for Genetics

### General MCQ Protocol
1. **ALWAYS evaluate ALL options** before choosing an answer
2. Never select the first option that seems correct -- there may be a better or more precise answer
3. Read the question stem carefully for qualifiers: "MOST likely", "LEAST likely", "NOT true", "ALWAYS", "NEVER"

### "Which is NOT true" Questions
- Evaluate EACH statement independently as True or False
- Mark each option with T or F before selecting
- The answer is the statement marked F
- Double-check: verify the "false" statement is genuinely false, not just misleadingly worded

### "Which mechanism" Questions
- Test each proposed mechanism against ALL observations given in the question
- A correct mechanism must explain every observation, not just some
- Eliminate mechanisms that contradict even one observation

### Specific Traps to Watch For
- **Subfunctionalization vs neofunctionalization**: Subfunctionalization = partitioning of EXISTING ancestral functions between duplicates (both copies needed to perform original function). Neofunctionalization = one copy acquires a genuinely NEW function not present in the ancestor
- **Copy-neutral LOH**: Caused by mitotic recombination (segmental, affects part of a chromosome), NOT uniparental disomy (UPD, which is whole-chromosome). The question may try to conflate these
- **Penetrance vs expressivity**: Penetrance = fraction of individuals with genotype who show ANY phenotype. Expressivity = degree/severity of phenotype among those who show it. These are distinct concepts
- **Complementation vs recombination**: Complementation = two mutations in DIFFERENT genes restore wild-type in trans. Recombination = exchange between two mutations in the SAME or different genes. Complementation is tested in F1 (heterozygote); recombination is tested in progeny

---

## Common Genetics Reasoning Traps

These are specific patterns that have caused reasoning failures in hard genetics questions. Review before answering genetics MCQs.

### Suppressor Genetics
- A suppressor mutation, when homozygous, restores wild-type phenotype in an otherwise mutant background
- In F2 crosses involving both the original mutation and an autosomal recessive suppressor:
  - Treat as a dihybrid cross — the primary mutation and the suppressor segregate independently
  - Only 1/4 of F2 are homozygous for the suppressor
  - The suppressor only acts in individuals that are also homozygous for the primary mutation
  - Use a Punnett square to enumerate all genotypic classes, then apply the suppression rule to determine phenotypes

### Non-disjunction (Bridges' Experiments)
- Bridges used non-disjunction to prove the chromosome theory of inheritance
- X0 males arise from female meiosis non-disjunction events
- **Meiosis I non-disjunction**: both X chromosomes go to one pole -> XX egg + O egg (nullo-X)
- **Meiosis II non-disjunction**: sister chromatids fail to separate -> XX egg from one secondary oocyte
- The classic Bridges result: exceptional white-eyed females (X^w X^w) and red-eyed males (from nullo-X eggs + Y sperm = X0, but these are typically sterile)
- Key distinction: know which type of non-disjunction (MI vs MII) produces which specific gamete types

### GWAS LD Blocks
- SNPs WITHIN the same LD block are correlated and can inflate false positive associations (one causal SNP drags along non-causal tag SNPs)
- SNPs ACROSS different LD blocks are largely independent and do NOT create misleading cross-locus associations
- LD block structure varies by population (shorter in African populations due to larger historical Ne)
- Fine-mapping within an LD block is needed to distinguish the causal variant from hitchhiking tag SNPs

### Gene Retention After Whole-Genome Duplication
- **Neofunctionalization**: One copy acquires a NEW function -> most commonly cited reason for gene RETENTION after duplication (preserves both copies because each is now essential)
- **Subfunctionalization**: Ancestral functions are PARTITIONED between copies -> explains DIVERGENCE of duplicate copies, but both copies must be retained to maintain the full ancestral function
- **Dosage balance**: Some genes are retained in duplicate to maintain stoichiometric balance in protein complexes
- Trap: Questions may ask "what explains retention" vs "what explains divergence" -- these have different best answers
- For retention: neofunctionalization (new function makes both copies essential)
- For divergence of expression/function: subfunctionalization (partitioning of ancestral roles)

---

## Advanced Genetics Traps v2

### PGS vs Heritability: "Necessarily True" Logic
For "necessarily true" questions about PGS and heritability: a statement is necessarily true only if it holds when V_D=0 AND when V_D=V_G. Test the extremes.

### Path Diagram Sign Assignment Protocol
Do NOT guess path signs from general knowledge. Signs may differ from well-known systems. Follow this protocol:
1. **Establish reference direction**: What varies? What is increasing?
2. **For each path X→Y**: Ask ONLY "when X increases, does Y increase (+) or decrease (-)?"
3. **Use the question's experimental context** (knockout/control comparisons, provided data) to determine signs — not intuition
4. **Expect negative paths**: Path diagrams test your ability to identify negative relationships. All-positive is almost always wrong. Direct residual paths (e) often have opposite sign from expectation.

### Chi-Square: "Most Likely to Reject" Protocol
Compute chi-square from the expected ratio given in the question. Compare to chi-square-critical at df = (number of phenotype classes - 1). Pick the answer choice with the highest chi-square, but also check which pattern is biologically diagnostic of the alternative hypothesis.

### LD and Misleading GWAS Associations
LD block boundaries at recombination hotspots are a source of GWAS false localization — strong signal in the block does not guarantee the causal variant is in the block.

### Low-Frequency Allele Detection
Duplex sequencing (unique molecular identifiers + double-strand consensus) detects alleles at 0.01% frequency — far below standard NGS even at 80X depth. Simply increasing read depth does NOT help for ultra-rare variants because the Illumina error rate (~0.1%) masks variants rarer than ~1% regardless of depth. Error correction methods (UMIs, duplex consensus) are needed to distinguish true rare variants from sequencing errors.

---

## Bundled Computation Script

**Script**: `skills/tooluniverse-population-genetics/scripts/popgen_calculator.py`

**Preferred**: Use ToolUniverse tools (via MCP/SDK) instead of the script when possible:
- `PopGen_hwe_test` tool -- HWE chi-square test. Fallback: `popgen_calculator.py --type hwe`
- `PopGen_fst` tool -- Weir-Cockerham Fst. Fallback: `popgen_calculator.py --type fst`
- `PopGen_inbreeding` tool -- Inbreeding coefficient from pedigree. Fallback: `popgen_calculator.py --type inbreeding`
- `PopGen_haplotype_count` tool -- Expected haplotype diversity. Fallback: `popgen_calculator.py --type haplotypes`

**Fallback script** modes (all require `--type`):
- `hwe`: `--AA N --Aa N --aa N` -- chi-square HWE test with p-value
- `fst`: `--p1 F --p2 F --n1 N --n2 N` -- Weir-Cockerham Fst
- `inbreeding`: `--pedigree TYPE --generations G` -- F from pedigree (self, full-sib, half-sib, first-cousin, etc.)
- `haplotypes`: `--snps N --generations G --recomb_rate R` -- expected haplotype diversity

---

## Key Concepts

- **MAF**: Minor allele frequency. Common: >5%. Rare: <1%. Ultra-rare: <0.01%.
- **pLI**: P(LoF intolerant). >0.9 = haploinsufficient gene.
- **LOEUF**: LoF o/e upper fraction. <0.35 = highly constrained.
- **CADD PHRED**: >=10 top 10%, >=20 top 1%, >=30 top 0.1% most deleterious.
- **Genome-wide significance**: GWAS p < 5e-8 (Bonferroni for ~1M independent tests).
- **Effect size**: OR > 1 = risk allele, < 1 = protective. Beta > 0 = increases trait.

## Evidence Grading

- **T1**: ClinVar pathogenic/likely pathogenic, FDA pharmacogenomics
- **T2**: gnomAD frequencies, GTEx eQTLs, GWAS genome-wide significant
- **T3**: CADD/SIFT/PolyPhen predictions, RegulomeDB, constraint metrics
- **T4**: VEP consequence terms, dbSNP annotations, literature mentions
