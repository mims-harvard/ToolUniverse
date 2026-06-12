# GWAS-to-Drug Discovery Reference

## Core Concepts

### 1. GWAS Evidence Strength

Not all genetic associations are equal. Consider:

- **P-value** - Statistical significance (genome-wide: p < 5x10^-8)
- **Effect size (beta/OR)** - Magnitude of genetic effect
- **Replication** - Confirmed in multiple studies
- **Sample size** - Larger studies = more reliable
- **Population diversity** - Validated across ancestries

### 2. Druggability Criteria

A good drug target must be:

- **Accessible** - Protein location allows drug binding (extracellular > intracellular)
- **Modality match** - Target class fits drug type (GPCR -> small molecule, receptor -> antibody)
- **Tractable** - Binding pocket suitable for drug design
- **Safe** - Minimal off-target effects, not essential in all tissues

### 3. Target Prioritization Framework

**GWAS Evidence (40%)**:
- Multiple independent SNPs = stronger signal
- Functional variants (missense > intronic)
- Tissue-specific expression matches disease

**Druggability (30%)**:
- Known druggable protein family
- Structural data available
- Existing chemical matter

**Clinical Evidence (20%)**:
- Prior safety data
- Validated disease models
- Biomarker availability

**Commercial Factors (10%)**:
- Patent landscape
- Market size
- Competitive positioning

### 4. Drug Repurposing Logic

Repurposing works when:

1. **Shared genetic architecture** - Same gene implicated in multiple diseases
2. **Pathway overlap** - Related biological mechanisms
3. **Opposite effects** - Drug's mechanism counteracts disease pathology
4. **Proven safety** - Approved drug = de-risked

**Example**: Metformin (T2D drug) being tested for cancer (AMPK activation), aging (mitochondrial effects), PCOS (insulin sensitization).

## Druggability Assessment Deep Dive

### Target Classes (by Druggability)

**Tier 1: High Druggability**
- **GPCRs** (33% of approved drugs) - Extracellular binding, established chemistry
- **Kinases** (18% of approved drugs) - ATP-competitive inhibitors, allosteric sites
- **Ion channels** (15% of approved drugs) - Blocking/opening channels
- **Nuclear receptors** - Ligand-binding domains

**Tier 2: Moderate Druggability**
- **Proteases** - Active site inhibitors
- **Phosphatases** - Challenging selectivity
- **Epigenetic targets** - Readers, writers, erasers

**Tier 3: Difficult to Drug**
- **Transcription factors** - No obvious binding pocket
- **Scaffold proteins** - Large, flat surfaces
- **RNA targets** - Emerging modality

### Modality Selection

**Small Molecules**: Intracellular proteins, enzymes. Oral bioavailability, CNS penetration. Off-target effects possible.

**Antibodies**: Extracellular proteins, receptors. High specificity, long half-life. Injection-only, no CNS.

**Antisense/RNAi**: mRNA (any gene). Sequence-specific, undruggable targets. Delivery challenges, liver-centric.

**Gene Therapy**: Genetic defects. One-time treatment, curative potential. Immunogenicity, manufacturing complexity.

## Clinical Translation Considerations

### Regulatory Requirements

**IND Application**: Pharmacology/toxicology, manufacturing info, clinical protocols.

**Clinical Trial Phases**:
- Phase I: Safety, dosing (20-100 healthy volunteers)
- Phase II: Efficacy, side effects (100-300 patients)
- Phase III: Confirmatory trials (1,000-3,000 patients)
- Phase IV: Post-market surveillance

**Repurposing Advantages**: Skip Phase I if dosing similar, shorter timelines (2-4 years vs 10-15), lower costs ($50M vs $2B).

### Success Rate Benchmarks

**Traditional**: Overall 12% (Phase I to approval).
**With Genetic Evidence**: 24% (2x improvement). Phase II -> Approval: 38% vs 18%.

### Cost and Timeline

**Traditional**: 10-15 years, $2-2.5B.
**Repurposing**: 3-5 years, $150-250M.

## Best Practices

### 1. Multi-Ancestry GWAS
Include trans-ethnic meta-analyses. Check replication in multiple ancestries. Consider population-specific variants.

### 2. Functional Validation
eQTL analysis, pQTL analysis, colocalization, fine-mapping. Tools: GTEx, ENCODE, gnomAD.

### 3. Network and Pathway Analysis
Group GWAS hits by pathway (KEGG, Reactome). Identify druggable nodes. Consider combination therapies.

### 4. Safety Liability Assessment
Red flags: essential gene, broad expression, off-target kinase panel, hERG inhibition, CYP450 interactions.
Tools: gnomAD pLI, GTEx expression, PharmaGKB.

### 5. Intellectual Property
Target patents (composition of matter), method of use patents, formulation patents. Check freedom to operate.

## Limitations and Caveats

### GWAS Limitations
1. Association does not equal causation (LD, pleiotropy, confounding). Solution: fine-mapping, functional studies, MR.
2. Missing heritability (common variants explain 10-50%). Solution: WGS, family studies.
3. Druggable does not equal effective. Solution: experimental validation, disease models.

### Target Validation Challenges
1. Mouse models do not equal humans (95% of drugs work in mice, 5% in humans).
2. Genetic perturbation does not equal pharmacology (knockout vs partial inhibition).
3. Efficacy does not equal safety (on-target toxicity, off-target effects).

## Ethical and Regulatory Considerations

### Human Genetics Research
- Informed consent for secondary use, return of results, privacy protections
- Equity: Most GWAS = European ancestry (78%). Diversify cohorts.

### Clinical Trials
- Stratification by genetics, adaptive trials, real-world evidence
- FDA Breakthrough Therapy, Accelerated Approval pathways

## Resources and References

### Databases
- GWAS: GWAS Catalog, Open Targets Genetics, PhenoScanner
- Drugs: ChEMBL, DrugBank, DGIdb
- Targets: Open Targets Platform, PHAROS
- Clinical: ClinicalTrials.gov, FDA Labels

### Key Literature
- Nelson et al. (2015) Nature Genetics - Genetic support doubles clinical success
- King et al. (2019) PLOS Genetics - Systematic analysis of target success
- Visscher et al. (2017) AJHG - 10 years of GWAS
- Pushpakom et al. (2019) Nature Reviews Drug Discovery - Repurposing opportunities

## Disclaimer

For research purposes only. Not for clinical decision-making, patient treatment, or regulatory submissions. All targets require experimental validation. GWAS evidence is correlational, not causal. Consult domain experts.
