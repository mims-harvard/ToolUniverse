---
name: tooluniverse-data-integration-analysis
description: Integrate statistical analysis results with biological knowledge from ToolUniverse tools. After computing associations or differential expression, use pathway analysis, literature search, drug-target databases, and variant annotation to interpret findings biologically. Use when statistical results need biological context, when users want to go beyond p-values to understand mechanisms, or when combining data analysis with literature evidence.
---

## COMPUTE, DON'T DESCRIBE
When analysis requires computation (statistics, data processing, scoring, enrichment), write and run Python code via Bash. Don't describe what you would do -- execute it and report actual results. Use ToolUniverse tools to retrieve data, then Python (pandas, scipy, statsmodels, matplotlib) to analyze it.

# Data Integration Analysis

Bridge the gap between statistical results and biological understanding. After any computational analysis produces significant findings, this skill teaches how to interpret them using ToolUniverse's biological knowledge tools -- the key advantage over platforms that only do data analysis.

**IMPORTANT**: Always use English terms in tool calls (gene names, pathway names, organism names), even if the user writes in another language. Respond in the user's language.

---

## When to Use This Skill

Apply when:
- Statistical analysis produced a list of significant genes, variants, metabolites, or exposures
- Users want to go beyond p-values to understand WHY something is significant
- Combining computational results with published evidence
- Interpreting differential expression, GWAS hits, or association study results biologically
- Users ask "what does this result mean?" after running an analysis

**NOT for** (use other skills instead):
- Running the statistical analysis itself --> Use `tooluniverse-statistical-modeling` or `tooluniverse-rnaseq-deseq2`
- Pure gene enrichment without prior analysis --> Use `tooluniverse-gene-enrichment`
- Pure literature review --> Use `tooluniverse-literature-deep-research`
- Single variant interpretation --> Use `tooluniverse-variant-interpretation`

---

## Step 1: Statistical Results to Biological Questions

Map each type of significant finding to the right biological question:

| Finding Type | Biological Question | Tool Discovery Query |
|---|---|---|
| Significant gene list | What pathways are enriched? What functions converge? | `find_tools("gene enrichment pathway analysis")` |
| Significant variant (rsID) | What is the functional impact? Which gene is affected? | `find_tools("variant annotation functional impact")` |
| Significant exposure/chemical | What is the biological mechanism? Which pathways? | `find_tools("chemical gene pathway toxicology")` |
| Significant drug association | What is the molecular target? What is the MOA? | `find_tools("drug target mechanism action")` |
| Significant metabolite | Which metabolic pathway is perturbed? | `find_tools("metabolite pathway identification")` |

**Key principle**: Do not stop at "gene X is significant." Ask: significant in what context? Through what mechanism? With what downstream consequence?

---

## Step 2: Multi-Database Evidence Integration

For each significant finding, query multiple sources and synthesize. The pattern:

1. **Literature evidence**: Search PubMed/EuropePMC for published studies linking your finding to the phenotype. Look for meta-analyses and systematic reviews first.
2. **Genetic association evidence**: Query GWAS Catalog or OpenTargets to check whether genetic evidence independently supports the association.
3. **Pathway context**: Query KEGG, Reactome, or WikiPathways to place the finding in a biological pathway. Identify upstream regulators and downstream effectors.
4. **Interaction networks**: Query STRING or BioGRID for protein-protein interactions. Look for whether your significant genes cluster in the same network neighborhood.
5. **Clinical relevance**: Check ClinVar for variant clinical significance, DGIdb or ChEMBL for druggability, or ClinicalTrials.gov for ongoing interventions.

**Evidence grading** (grade each piece of evidence):

| Grade | Source Type | Example |
|---|---|---|
| T1 (Strong) | Randomized clinical trial, Mendelian randomization | "RCT showed drug X reduces outcome Y" |
| T2 (Moderate) | Large cohort study, GWAS with replication | "GWAS meta-analysis in 500k subjects" |
| T3 (Suggestive) | Case-control study, animal model | "Mouse knockout shows phenotype" |
| T4 (Hypothesis) | In silico prediction, pathway inference | "Network analysis suggests involvement" |

---

## Step 3: Causal Reasoning

Statistical association is not causation. Apply these reasoning frameworks:

**DAG construction**: Before interpreting, sketch the causal directed acyclic graph (DAG).
- Identify potential **confounders** (common causes of exposure and outcome) -- these must be adjusted for.
- Identify potential **mediators** (on the causal path) -- do NOT adjust for these if estimating total effect.
- Identify **colliders** (common effects) -- conditioning on colliders introduces bias.

**Triangulation**: The same finding supported by different methods with different biases strengthens causal inference.
- Observational association + Mendelian randomization + animal experiment = strong triangulated evidence
- If MR contradicts observational data, suspect confounding in the observational study

**Mendelian randomization logic**: Genetic variants (instruments) are assigned at conception, so they are not confounded by lifestyle or reverse causation. If a genetic variant that increases exposure X also increases disease Y, this supports X causing Y. Check instrument strength (F-statistic > 10), exclusion restriction (variant affects Y only through X), and pleiotropy (MR-Egger intercept).

**Mediation analysis**: If gene G is associated with both exposure and outcome, ask: does the exposure effect on outcome go through G? Use the finding's pathway context (Step 2) to propose mediators, then check if adjusting for the mediator attenuates the effect.

---

## Step 4: Cross-Validation

Before reporting a finding as robust, attempt to falsify it:

1. **Replication**: Search literature and datasets (DataCite, GEO, ArrayExpress) for independent datasets where the same finding can be tested. A finding that replicates in an independent cohort is much stronger.
2. **Biological plausibility**: Does the mechanism make biological sense? Check if animal or cell models support it (PubMed search for "[gene] knockout [phenotype]" or "[chemical] exposure [cell type]").
3. **Genetic support**: Check if GWAS evidence supports the direction of effect. If your analysis says gene X is protective but GWAS shows risk alleles increase X expression, there is a contradiction to resolve.
4. **Dose-response**: If available, check whether the effect increases with dose. A dose-response relationship strengthens causal inference.
5. **Negative controls**: If possible, test the same analysis on a finding where you expect no association. If the negative control also shows an association, suspect a methodological artifact.

---

## Step 5: Actionable Reporting

Structure the integrated report as follows:

### Evidence Summary Table
For each significant finding, produce one row:

| Finding | Statistical Evidence | Biological Mechanism | Literature Support | Genetic Support | Evidence Grade |
|---|---|---|---|---|---|
| Gene X upregulated | FDR=0.001, log2FC=2.3 | PI3K/AKT pathway | 12 papers, 2 RCTs | GWAS: rs123 (p=5e-8) | Strong |
| Variant rs456 | OR=1.4, p=2e-6 | Splicing disruption | 3 case reports | eQTL in GTEx | Moderate |

### Strength Assessment
- **Strong**: Statistical significance + biological mechanism + independent replication + genetic support
- **Moderate**: Statistical significance + biological mechanism + partial replication
- **Weak**: Statistical significance + plausible mechanism but no independent support
- **Suggestive**: Statistical trend + computational prediction only

### Knowledge Gaps and Next Steps
- Which findings lack replication? Propose specific datasets to test in.
- Which mechanisms are inferred but not experimentally validated? Propose experiments.
- Which findings have conflicting evidence? State the contradiction explicitly.
- Generate testable hypotheses: "If finding X is causal, then [experimental prediction]."

### Clinical or Public Health Implications
- State whether the finding is actionable now or requires further validation.
- If druggable, identify existing therapeutics and their development stage.
- If a biomarker, assess sensitivity/specificity for clinical utility.
