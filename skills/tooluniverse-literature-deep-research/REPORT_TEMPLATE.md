# Report Templates & Output Formats

Templates for deep research reports, bibliography files, and completeness checklists.

---

## Table of Contents

1. [Full Deep-Research Report Template](#full-deep-research-report-template)
2. [Domain-Specific Adaptations](#domain-specific-adaptations)
3. [Bibliography Format](#bibliography-format)
4. [Theme Extraction Protocol](#theme-extraction-protocol)
5. [Completeness Checklist](#completeness-checklist)

---

## Full Deep-Research Report Template

Use for **Full Deep-Research Mode** only. For factoid mode, use the short fact-check template in SKILL.md.

```markdown
# [TARGET/TOPIC]: Comprehensive Research Report

*Generated: [Date]*
*Evidence cutoff: [Date]*
*Total unique papers: [N]*

---

## Executive Summary

[2-3 paragraphs synthesizing key findings across all sections]

**Bottom Line**: [One-sentence actionable conclusion]

---

## 1. Subject Identity & Scope
*[MANDATORY - clarify what is being researched]*

### 1.1 Official Identifiers
[Table of IDs, database entries, or scope definition]

### 1.2 Synonyms and Aliases
[All known names - critical for complete literature coverage]

### 1.3 Known Naming Collisions
[Document collisions and how they were handled]

---

## 2. Background & Context
*[MANDATORY - domain-specific background]*

For biological targets: protein architecture, domains, isoforms, key sites
For drugs: chemical structure, properties, drug class, formulation
For diseases: epidemiology, classification, current understanding
For general topics: historical context, scope, key definitions

---

## 3. Key Entities & Relationships
*[MANDATORY]*

For biological targets: complexes, interaction partners, scores
For drugs: known targets, mechanisms of action, binding sites
For diseases: associated genes, pathways, risk factors
For general topics: key actors, institutions, competing frameworks

---

## 4. Spatial/Temporal Context
*[MANDATORY]*

For biological targets: subcellular localization with confidence
For drugs: pharmacokinetics (ADME), tissue distribution
For diseases: affected tissues/organs, disease progression timeline
For general topics: geographic/temporal scope, key periods

---

## 5. Quantitative Profile
*[MANDATORY]*

For biological targets: expression profile (top tissues, specificity)
For drugs: clinical pharmacology (dosing, bioavailability, DDIs)
For diseases: prevalence, incidence, demographic patterns
For general topics: key metrics, benchmarks, trends over time

---

## 6. Core Mechanisms / Central Arguments
*[MANDATORY - heart of the report]*

### 6.1 Primary Function / Main Thesis
[Central finding with evidence grades]
**Evidence Quality**: [Strong/Moderate/Limited]

### 6.2 Supporting Evidence
[Role in broader context, pathways, causal chains]

### 6.3 Key Processes / Pathways
[Involvement in larger systems with evidence grades]

### 6.4 Regulation / Modulation
[How the subject is regulated, controlled, or influenced]

---

## 7. Experimental / Empirical Evidence
*[MANDATORY]*

### 7.1 Direct Evidence
[Controlled experiments, clinical trials, primary studies]

### 7.2 Model Systems
[Animal models, simulations, analogues]

### 7.3 Cross-Validation
[Conservation, replication, meta-analyses]

---

## 8. Variation & Heterogeneity
*[MANDATORY]*

For biological targets: human genetic variants, constraint scores, ClinVar, GWAS
For drugs: pharmacogenomics, responder vs non-responder profiles
For diseases: subtypes, genetic basis, population differences
For general topics: competing schools of thought, regional variation

---

## 9. Applied / Translational Relevance
*[MANDATORY - include evidence strength]*

### 9.1 Strong Evidence
[Claims with causal/mechanistic support]

### 9.2 Moderate Evidence
[Claims with functional/associative support]

### 9.3 Weak Evidence
[Claims with correlation/mention only]

### 9.4 Evidence Summary Table

| Claim/Link | Evidence Type | Key Papers | Grade |
|------------|---------------|------------|-------|
| [Claim 1] | Mechanistic | PMID:xxx | ★★★ |
| [Claim 2] | Association | PMID:yyy | ★★☆ |

---

## 10. External Factors
*[MANDATORY - state "None identified" if N/A]*

For biological targets: pathogen interactions, environmental factors
For drugs: drug-drug interactions, food effects, contraindications
For diseases: environmental triggers, comorbidities
For general topics: external influences, confounders, policy implications

---

## 11. Methods & Assays / Methodological Landscape
*[MANDATORY]*

### 11.1 Standard Approaches
[Established methods for studying this subject]

### 11.2 Emerging Methods
[New techniques, tools, technologies]

### 11.3 Key Resources
[Datasets, repositories, reference standards]

---

## 12. Research Themes
*[MANDATORY - structured theme extraction]*

### 12.1 [Theme 1 Name] (N papers)
**Evidence Quality**: [Strong/Moderate/Limited]
**Representative Papers**: [≥3 papers or state "insufficient"]

[Theme description with evidence-graded citations]

### 12.2 [Theme 2 Name] (N papers)
[Same structure]

[Continue for all themes - require ≥3 papers per theme, or state "limited evidence"]

---

## 13. Open Questions & Research Gaps
*[MANDATORY]*

### 13.1 Fundamental Unknowns
[What we don't understand]

### 13.2 Practical/Translational Unknowns
[What we don't know for applications]

### 13.3 Suggested Priority Questions
[Ranked list of important unanswered questions]

---

## 14. Integrated Model & Testable Hypotheses
*[MANDATORY - synthesis section]*

### 14.1 Integrated Model
[3-5 paragraph synthesis integrating all evidence into coherent model]

### 14.2 Testable Hypotheses

| # | Hypothesis | Test/Perturbation | Readout | Expected Result | Priority |
|---|------------|-------------------|---------|-----------------|----------|
| 1 | [Hypothesis] | [Experiment] | [Measure] | [Prediction] | HIGH |
| 2 | [Hypothesis] | [Experiment] | [Measure] | [Prediction] | HIGH |
| 3 | [Hypothesis] | [Experiment] | [Measure] | [Prediction] | MEDIUM |

### 14.3 Suggested Next Studies
[Brief description of key experiments/studies to test hypotheses]

---

## 15. Conclusions & Recommendations
*[MANDATORY]*

### 15.1 Key Takeaways
[Bullet points of most important findings]

### 15.2 Confidence Assessment
[Overall confidence: High/Medium/Low with justification]

### 15.3 Recommended Next Steps
[Prioritized action items]

---

## References

*[Summary reference list - full bibliography in separate file]*

### Key Papers (Must-Read)
1. [Citation with PMID/DOI] - [Why important] [Grade: ★★★]
2. ...

### By Theme
[Organized reference lists]

---

## Data Limitations

- [Any databases that failed or returned no data]
- [Any known gaps in coverage]
- [OA status method used]

*Full methodology available in methods_appendix.md upon request.*
```

---

## Domain-Specific Adaptations

### Biological Target Reports

Map generic sections to biology-specific content:

| Generic Section | Biological Target Content |
|----------------|--------------------------|
| 2. Background & Context | Protein architecture: domains, isoforms, PTMs, active sites |
| 3. Key Entities | Complexes, interaction partners (STRING, IntAct scores) |
| 4. Spatial/Temporal | Subcellular localization (HPA, UniProt) |
| 5. Quantitative Profile | Tissue expression (GTEx TPM, HPA), tissue specificity |
| 6. Core Mechanisms | Molecular function, biological role, pathway involvement |
| 7. Experimental Evidence | Mouse KO phenotypes, model organism data |
| 8. Variation | Constraint scores (pLI, LOEUF), ClinVar variants, GWAS |
| 9. Applied Relevance | Disease links with evidence strength |
| 10. External Factors | Pathogen involvement, viral exploitation |

### Drug Reports

| Generic Section | Drug Content |
|----------------|-------------|
| 2. Background & Context | Chemical structure, molecular formula, weight, SMILES, drug class |
| 3. Key Entities | Known targets, MOA, binding sites |
| 4. Spatial/Temporal | Pharmacokinetics: ADME, half-life |
| 5. Quantitative Profile | Clinical pharmacology: dosing, bioavailability, DDIs |
| 6. Core Mechanisms | Drug's mechanism of action |
| 7. Experimental Evidence | Preclinical: animal models, in vitro activity |
| 8. Variation | Pharmacogenomics: genetic variants affecting response |
| 9. Applied Relevance | Indications (approved + investigational), repurposing |
| 10. External Factors | Antimicrobial activity (if applicable), contraindications |

### Disease Reports

| Generic Section | Disease Content |
|----------------|----------------|
| 2. Background & Context | Classification, epidemiology, diagnostic criteria |
| 3. Key Entities | Associated genes, pathways, risk factors |
| 4. Spatial/Temporal | Affected tissues/organs, disease stages/progression |
| 5. Quantitative Profile | Prevalence, incidence, survival rates |
| 6. Core Mechanisms | Pathophysiology, molecular basis |
| 7. Experimental Evidence | Animal models, clinical trials |
| 8. Variation | Subtypes, genetic basis, population differences |
| 9. Applied Relevance | Treatment options, drug pipeline |
| 10. External Factors | Environmental triggers, comorbidities |

### General Academic Topics (CS, Social Science, Humanities, etc.)

| Generic Section | General Topic Content |
|----------------|----------------------|
| 2. Background & Context | Historical development, key definitions, scope |
| 3. Key Entities | Key researchers, institutions, competing frameworks |
| 4. Spatial/Temporal | Geographic/temporal scope, key periods |
| 5. Quantitative Profile | Benchmarks, metrics, trends over time |
| 6. Core Mechanisms | Central theories/arguments, causal models |
| 7. Experimental Evidence | Key studies, replications, meta-analyses |
| 8. Variation | Competing views, cultural/regional differences |
| 9. Applied Relevance | Practical applications, industry adoption |
| 10. External Factors | Policy, ethics, societal impact |

---

## Bibliography Format

### JSON (`[topic]_bibliography.json`)

```json
{
  "metadata": {
    "generated": "2026-03-07",
    "query": "[TOPIC]",
    "identifiers": {},
    "total_raw": 268,
    "total_unique": 187
  },
  "papers": [
    {
      "pmid": "12345678",
      "doi": "10.1038/xxx",
      "arxiv_id": null,
      "dblp_key": null,
      "title": "Paper Title",
      "authors": ["Smith A", "Jones B"],
      "year": 2024,
      "journal": "Nature",
      "source_databases": ["PubMed", "OpenAlex"],
      "evidence_tier": "T1",
      "themes": ["theme_a", "theme_b"],
      "oa_status": "gold",
      "oa_url": "https://...",
      "citation_count": 45,
      "in_core_set": true
    }
  ]
}
```

Also generate `[topic]_bibliography.csv` with same data in tabular format.

---

## Theme Extraction Protocol

### Clustering Process

1. Extract keywords from titles and abstracts
2. Cluster into themes using semantic similarity
3. Require minimum N papers per theme (default N=3)
4. Label themes with standardized descriptive names

### Theme Quality Requirements

| Papers | Theme Status |
|--------|--------------|
| ≥10 | Major theme (full section) |
| 3-9 | Minor theme (subsection) |
| <3 | Insufficient (note as "limited evidence" or merge) |

### Standard Theme Categories (adapt to domain)

**Biological**: Core function, Disease relevance, Signaling/Pathways, Trafficking/Localization, Genetics/Variants, Infection/Immunity, Methodology/Tools

**Drug**: Mechanism, Efficacy, Safety/Toxicity, Pharmacokinetics, Resistance, Repurposing, Clinical trials, Biomarkers

**General academic**: Theoretical foundations, Empirical studies, Methodology, Applications, Ethics/Policy, Historical development

---

## Completeness Checklist

Verify ALL boxes before delivery. Mark "N/A" or "Limited evidence" where appropriate.

### Identity & Context
- [ ] Official identifiers or scope definition resolved
- [ ] All synonyms/aliases documented
- [ ] Naming collisions identified and handled
- [ ] Background/context described (or N/A stated)

### Core Content
- [ ] Core mechanisms/arguments with evidence grades
- [ ] Supporting evidence documented
- [ ] Experimental/empirical evidence (or "none found")
- [ ] Key entities and relationships listed
- [ ] Methods/assays described

### Variation & Application
- [ ] Variation/heterogeneity documented
- [ ] Applied relevance with evidence strength grades
- [ ] External factors (or "none identified")

### Synthesis
- [ ] Research themes clustered with ≥3 papers each (or noted as limited)
- [ ] Open questions/gaps articulated
- [ ] Integrated model synthesized
- [ ] ≥3 testable hypotheses with experiments
- [ ] Conclusions with confidence assessment

### Technical
- [ ] All claims have source attribution
- [ ] Evidence grades applied throughout
- [ ] Bibliography file generated (JSON + CSV)
- [ ] Data limitations documented
- [ ] Code/data availability noted (for CS/ML topics with reproducibility expectations)
