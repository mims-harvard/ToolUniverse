# Literature Deep Research - Examples

Examples demonstrating target disambiguation, evidence grading, and biological model synthesis.

---

## Example 1: Full Workflow for ATP6V1A (V-ATPase Target)

### User Query
"What does the literature say about ATP6V1A?"

### Phase 0: Clarification

```
Agent: I'll conduct comprehensive research on ATP6V1A. A few questions:

1. **Scope**: Comprehensive overview, or specific focus (druggability, disease, mechanism)?
2. **Known aliases**: Any specific names you use for this target?
3. **Methods appendix**: Do you want search methodology in a separate file?

User: Comprehensive. I know it's part of V-ATPase. No methods file needed.
```

### Phase 1: Target Disambiguation

**1.1 Resolve Identifiers**

```markdown
## Target Identity

| Identifier | Value | Source |
|------------|-------|--------|
| Official Symbol | ATP6V1A | HGNC via UniProt |
| UniProt | P38606 | UniProt_search |
| Ensembl Gene | ENSG00000114573 | UniProt_id_mapping |
| NCBI Gene ID | 523 | MyGene_get_gene_annotation |
| ChEMBL Target | CHEMBL2364682 | OpenTargets |

**Full Name**: V-type proton ATPase catalytic subunit A
**Synonyms**: ATP6A1, VPP2, Vma1, VA68, V-ATPase A subunit
```

**1.2 Collision Check**

Search: `"ATP6V1A"[Title]` - first 20 results reviewed.

```markdown
### Naming Collision Assessment

**Collision risk**: LOW
- Symbol "ATP6V1A" is unambiguous
- Related but distinct: ATP6V0A1-4 (V0 domain vs V1 domain)
- "V-ATPase" is a complex name that may include V0 subunits

**Search strategy**: 
- Use exact symbol for precision: "ATP6V1A"
- For broader V-ATPase context: "V-ATPase" AND (V1 OR catalytic OR "A subunit")
- Exclude pure V0 papers when V1-specific: NOT "V0 domain" NOT "a1 subunit"
```

**1.3 Protein Architecture**

```markdown
### Protein Architecture

| Domain | Position | InterPro ID | Function |
|--------|----------|-------------|----------|
| V-ATPase A, N-terminal | 1-90 | IPR022879 | ATP binding regulatory |
| V-ATPase A, catalytic | 91-490 | IPR005725 | Catalytic activity |
| V-ATPase A, C-terminal | 491-617 | IPR022878 | V1 complex assembly |

**Length**: 617 aa (canonical isoform)
**Isoforms**: 2
- P38606-1 (canonical): 617 aa
- P38606-2: Missing 1-45, 572 aa

**Key Sites**:
- Lys-168: ATP binding (active site)
- Glu-261: Catalytic glutamate

*Sources: InterPro, UniProt*
```

**1.4 Expression Profile**

```markdown
### Baseline Tissue Expression (GTEx v8)

| Tissue | TPM | Rank | Interpretation |
|--------|-----|------|----------------|
| Kidney - Cortex | 145.3 | 1 | Elevated |
| Liver | 98.7 | 2 | Medium-high |
| Brain - Cerebellum | 87.2 | 3 | Medium |
| Lung | 76.4 | 4 | Medium |
| Ubiquitous baseline | ~50 | - | Broad |

**Tissue Specificity**: Low (τ = 0.28) - broadly expressed housekeeping gene
**Implication**: Essential cellular function; targeting may have broad effects

*Source: GTEx_get_median_gene_expression*
```

**1.5 Functional Annotations**

```markdown
### GO Annotations

**Molecular Function**:
- Proton-transporting ATPase activity, rotational mechanism (GO:0046961) [IDA]
- ATP binding (GO:0005524) [IDA]
- ATP hydrolysis activity (GO:0016887) [IDA]

**Biological Process**:
- Lysosomal acidification (GO:0007041) [IMP]
- Autophagy (GO:0006914) [IMP]
- pH regulation (GO:0006885) [IBA]
- Bone resorption (GO:0045453) [IMP]

**Cellular Component**:
- Vacuolar proton-transporting V-type ATPase, V1 domain (GO:0000221) [IDA]
- Lysosomal membrane (GO:0005765) [IDA]

*Source: GO_get_annotations_for_gene, OpenTargets*
```

### Phase 2: Literature Search (Internal - Not Shown)

**Query Strategy Applied**:
1. High-precision: `"ATP6V1A"[Title]` → 23 papers (core set)
2. Citation expansion from top 15 → 89 additional papers
3. Collision-filtered broad: `"V-ATPase" AND (V1 OR "A subunit") AND (mechanism OR acidification)` → 156 papers

**Deduplication**: 268 raw → 187 unique papers

### Phase 3: Report Sections with Evidence Grading

```markdown
## 6. Core Mechanisms

### 6.1 Molecular Function
ATP6V1A is the catalytic A subunit of the vacuolar H+-ATPase (V-ATPase), 
responsible for ATP hydrolysis that drives proton translocation across membranes 
[★★★ Mechanistic: PMID:12345678, crystal structure + biochemistry].

The V1 sector containing ATP6V1A performs ATP hydrolysis, while the V0 
sector mediates proton transport. Rotation of the central stalk couples 
ATP hydrolysis to proton pumping [★★★: PMID:23456789, cryo-EM structure].

**Evidence Quality**: Strong (8 mechanistic studies with direct biochemical evidence)

### 6.2 Biological Role

**Lysosomal Acidification**
V-ATPase acidifies lysosomes to pH 4.5-5.0, required for:
- Acid hydrolase activity [★★★: PMID:34567890]
- Autophagosome-lysosome fusion [★★☆: PMID:45678901, knockdown phenotype]
- Protein degradation [★★☆: PMID:56789012]

**mTORC1 Signaling**
ATP6V1A participates in lysosomal amino acid sensing:
- V-ATPase interacts with Ragulator complex [★★★: PMID:67890123]
- Required for mTORC1 recruitment to lysosome [★★☆: PMID:78901234]
- Bafilomycin A1 inhibits mTORC1 via V-ATPase [★★★: PMID:89012345]

**Bone Resorption**
Osteoclasts use V-ATPase for extracellular acidification:
- ATP6V1A mutation causes osteopetrosis [★★★: PMID:90123456, patient genetics + functional]
- Osteoclast-specific V-ATPase inhibitors in development [★★☆: PMID:01234567]

**Evidence Quality**: Strong (lysosome), Moderate (mTORC1), Strong (bone)
```

### Theme Extraction Example

```markdown
## 12. Research Themes

### 12.1 Lysosomal Function & Autophagy (47 papers)
**Evidence Quality**: Strong (32 mechanistic, 11 functional, 4 association)

ATP6V1A is essential for lysosomal acidification, which is prerequisite for 
autophagy completion. Studies demonstrate that:
- V-ATPase activity required for autophagosome-lysosome fusion [★★★: PMID:xxx]
- Bafilomycin A1 blocks autophagic flux via V-ATPase inhibition [★★★: PMID:xxx]
- ATP6V1A knockdown accumulates LC3-II and p62 [★★☆: PMID:xxx]

**Representative papers** (≥3 required):
1. Forgac M (2007) - V-ATPase structure-function review [★★★: PMID:17428758]
2. Zoncu R et al (2011) - mTORC1 senses amino acids via V-ATPase [★★★: PMID:22153073]
3. Settembre C et al (2013) - TFEB controls lysosomal biogenesis [★★★: PMID:23332759]
4. Abu-Remaileh M et al (2017) - Lysosomal metabolomics [★★★: PMID:28893638]
5. [Additional papers...]

### 12.2 Cancer & Tumor Acidification (28 papers)
**Evidence Quality**: Moderate (8 functional, 15 association, 5 review)

V-ATPase contributes to tumor microenvironment acidification:
- Upregulated in metastatic cancers [★☆☆: PMID:xxx, expression correlation]
- V-ATPase inhibitors show anti-cancer effects [★★☆: PMID:xxx, xenograft study]
- Acidic pH promotes invasion and metastasis [★★☆: PMID:xxx]

**Representative papers**:
1. Neri D & Supuran CT (2011) - Tumor pH and V-ATPase [PMID:21677680]
2. [Additional papers...]

### 12.3 Bone Biology & Osteopetrosis (19 papers)
**Evidence Quality**: Strong (genetic + functional studies)

[Content with evidence grades...]

### 12.4 Viral Infection (12 papers)
**Evidence Quality**: Moderate

Multiple viruses exploit V-ATPase for entry:
- Influenza virus requires acidic endosomes [★★★: PMID:xxx]
- SARS-CoV-2 entry blocked by V-ATPase inhibitors [★★☆: PMID:xxx]
- Flavivirus membrane fusion pH-dependent [★★☆: PMID:xxx]

### 12.5 Neurodegenerative Disease (8 papers)
**Evidence Quality**: Limited (mostly association)

[Content with evidence grades...]

### 12.6 Assays & Tools (15 papers)
**Evidence Quality**: Methodological

[Assay development papers...]
```

### Biological Model & Hypotheses

```markdown
## 14. Biological Model & Testable Hypotheses

### 14.1 Integrated Biological Model

ATP6V1A is the catalytic engine of the V-ATPase proton pump, essential for 
acidifying lysosomes and other intracellular compartments. Our literature 
synthesis supports the following model:

**Core Function**: ATP6V1A hydrolyzes ATP to power proton translocation, 
maintaining lysosomal pH at 4.5-5.0 [strong evidence from 15+ mechanistic studies].

**Regulatory Hub**: V-ATPase acts as a signaling hub, connecting nutrient 
status to mTORC1 via the Ragulator-Rag pathway. When amino acids are present, 
V-ATPase promotes mTORC1 lysosomal recruitment [moderate evidence, mechanism 
still debated].

**Disease Relevance**:
- Loss-of-function: Osteopetrosis (osteoclast defect), neurodegeneration 
  (impaired autophagy) [strong genetic evidence]
- Gain-of-function/upregulation: Cancer progression, tumor acidification 
  [moderate association evidence]
- Exploitation: Viral entry dependency [strong for influenza, moderate for others]

**Key Uncertainty**: The precise mechanism of V-ATPase-mTORC1 coupling, 
specifically whether V-ATPase ATPase activity vs. scaffolding function 
is required, remains debated [conflicting evidence from 4 studies].

### 14.2 Testable Hypotheses

| # | Hypothesis | Perturbation | Readout | Expected | Priority |
|---|------------|--------------|---------|----------|----------|
| 1 | ATP6V1A is required for autophagy completion | siRNA knockdown in HeLa | LC3-II levels, p62 accumulation, GFP-LC3 puncta | ↑LC3-II, ↑p62, puncta accumulation | HIGH |
| 2 | V-ATPase ATPase activity (not just presence) is required for mTORC1 signaling | Concanamycin A treatment vs knockdown | pS6K levels, mTOR localization | Both reduce pS6K; knockdown more severe if scaffolding matters | HIGH |
| 3 | ATP6V1A inhibition blocks SARS-CoV-2 entry | Bafilomycin A1 pretreatment | Viral RNA, spike protein, infection | ↓ infection in dose-dependent manner | MEDIUM |
| 4 | ATP6V1A expression correlates with cancer metastasis | TCGA pan-cancer analysis | Survival, metastasis-free survival | High ATP6V1A → worse prognosis in epithelial cancers | MEDIUM |
| 5 | V-ATPase inhibitor synergizes with autophagy inducers in cancer | Combination of bafilomycin + rapamycin | Cell death, xenograft growth | Synergistic cytotoxicity | MEDIUM |

### 14.3 Suggested Experiments

**For Hypothesis 1 (Autophagy)**:
- siRNA targeting ATP6V1A in HeLa or MEFs
- Treat ± bafilomycin A1 as positive control
- Western blot for LC3-II, p62
- Confocal microscopy for GFP-LC3 puncta
- Electron microscopy for autophagosome accumulation
- Expected: Knockdown phenocopies bafilomycin

**For Hypothesis 2 (mTORC1 mechanism)**:
- Compare: (a) Concanamycin A (inhibits activity), (b) ATP6V1A siRNA (removes protein)
- Readouts: pS6K, p4E-BP1, mTOR lysosomal localization (IF)
- Include rescue with catalytically-dead ATP6V1A mutant
- Expected: If scaffolding sufficient, siRNA more severe than inhibitor
```

---

## Example 2: Handling Naming Collisions (TRAG)

### Query: "What's known about TRAG?"

### Collision Detection

```markdown
### Naming Collision Assessment

**HIGH COLLISION RISK DETECTED**

Search `"TRAG"[Title]` reveals multiple meanings:
1. **T-cell regulatory gene (human TRAF1)** - Immune signaling
2. **Bacterial TraG** - Conjugation/plasmid transfer protein
3. **TraG-like domain** - Bioinformatics/structural studies

**Resolution**:
- User clarification needed: "Is this T-cell TRAG or bacterial TraG?"
- If T-cell: Use TRAF1 as primary symbol
- Apply filter: NOT plasmid NOT conjugation NOT "TraG domain"
```

### After User Clarifies (T-cell immune)

```markdown
### Resolved Query Strategy

**Target**: TRAF1 (also known as TRAG, EBI6)
**Collision filter**: NOT plasmid NOT conjugation NOT bacterial NOT "type IV secretion"

**High-precision queries**:
1. "TRAF1"[Title] AND (immune OR T-cell OR NF-kB)
2. "TRAF1" AND lymphoma
3. "TRAG" AND T-cell NOT plasmid NOT conjugation

**Citation expansion**: From TRAF1 signaling papers, expand citations
```

---

## Example 3: Sparse Target with Citation-First Strategy

### Query: "Literature on GPRC5D" (emerging CAR-T target)

### Initial Search Results

```
"GPRC5D"[Title] → Only 8 papers
"GPRC5D" broader → 23 papers total
```

### Citation-First Expansion

```markdown
### Citation Network Strategy Applied

**Seed papers** (8 core papers from title search):
- PMID:31919438 - GPRC5D as multiple myeloma target
- PMID:33020169 - CAR-T targeting GPRC5D
- [6 more]

**Forward citations** from seeds:
- PubMed_get_cited_by → 67 additional papers
- EuropePMC_get_citations → 12 unique (not in PubMed)

**Backward citations** from seeds:
- EuropePMC_get_references → 45 additional (mostly myeloma biology)

**Final corpus**: 132 papers (from 8 initial)

**Note**: For this sparse target, citation expansion (124 papers) vastly 
outperformed keyword search (23 papers).
```

---

## Example 4: Evidence Grading in Practice

### Raw Claim (Before Grading)

"ATP6V1A is involved in autophagy and cancer."

### With Evidence Grading

```markdown
**Autophagy**:
ATP6V1A is essential for lysosomal acidification, which is required for 
autophagy completion [★★★ Mechanistic: PMID:22153073, biochemical + genetic]. 
Knockdown in cell lines causes LC3-II accumulation [★★☆ Functional: PMID:28893638]. 
Multiple reviews discuss V-ATPase-autophagy connection [★☆☆ Mention: PMIDs:xxx,yyy].

**Cancer**:
ATP6V1A is upregulated in several cancers [★☆☆ Association: TCGA data, PMID:xxx]. 
V-ATPase inhibitors show anti-proliferative effects in xenografts [★★☆ Functional: 
PMID:yyy]. The mechanistic role in cancer progression is hypothesized but not 
directly demonstrated [no ★★★ mechanistic studies identified].

**Summary**:
- Autophagy link: STRONG evidence (mechanistic studies)
- Cancer link: MODERATE evidence (functional + association, no mechanistic)
```

---

## Example 5: Bibliography Output Format

### `ATP6V1A_bibliography.json`

```json
{
  "metadata": {
    "generated": "2026-02-04T15:30:00Z",
    "query": "ATP6V1A",
    "identifiers": {
      "symbol": "ATP6V1A",
      "uniprot": "P38606",
      "ensembl": "ENSG00000114573"
    },
    "total_raw": 268,
    "total_unique": 187,
    "collision_filter_applied": false
  },
  "papers": [
    {
      "pmid": "22153073",
      "doi": "10.1126/science.1207056",
      "title": "mTORC1 senses lysosomal amino acids through an inside-out mechanism that requires the vacuolar H+-ATPase",
      "authors": ["Zoncu R", "Bar-Peled L", "Efeyan A", "Wang S", "Sancak Y", "Sabatini DM"],
      "year": 2011,
      "journal": "Science",
      "source_databases": ["PubMed", "OpenAlex", "Crossref"],
      "evidence_tier": "T1",
      "evidence_tier_rationale": "Mechanistic study with biochemistry and genetics",
      "themes": ["mtorc1_signaling", "lysosomal_function"],
      "in_core_set": true,
      "citation_count": 1847,
      "oa_status": "bronze",
      "oa_url": null
    },
    {
      "pmid": "28893638",
      "doi": "10.1126/science.aan6298",
      "title": "Lysosomal metabolomics reveals V-ATPase- and mTOR-dependent regulation of amino acid efflux from lysosomes",
      "authors": ["Abu-Remaileh M", "Wyant GA", "Kim C", "Laqtom NN", "Abbasi M", "Chan SH", "Freinkman E", "Sabatini DM"],
      "year": 2017,
      "journal": "Science",
      "source_databases": ["PubMed", "EuropePMC"],
      "evidence_tier": "T1",
      "themes": ["lysosomal_function", "metabolism"],
      "in_core_set": true,
      "citation_count": 612,
      "oa_status": "gold",
      "oa_url": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5704954/"
    }
  ],
  "theme_summary": {
    "lysosomal_function": {"count": 47, "evidence_quality": "strong"},
    "cancer": {"count": 28, "evidence_quality": "moderate"},
    "bone_biology": {"count": 19, "evidence_quality": "strong"},
    "viral_infection": {"count": 12, "evidence_quality": "moderate"},
    "neurodegenerative": {"count": 8, "evidence_quality": "limited"},
    "methodology": {"count": 15, "evidence_quality": "methodological"}
  }
}
```

---

## Example 6: Drug-Centric Workflow (Metformin Cancer Repurposing)

### User Query
"What evidence supports metformin for cancer treatment or prevention?"

### Phase 1: Drug Disambiguation

```markdown
## Drug Identity

| Identifier | Value | Source |
|------------|-------|--------|
| Generic Name | Metformin | User query |
| ChEMBL ID | CHEMBL1431 | OpenTargets_get_drug_chembId_by_generic_name |
| DrugBank ID | DB00331 | drugbank_get_drug_basic_info_by_drug_name_or_id |
| PubChem CID | 4091 | PubChem_get_CID_by_compound_name |
| ATC Code | A10BA02 | ChEMBL_get_drug |

**Class**: Biguanide antidiabetic
**Approval Status**: Approved (FDA 1994)
**Primary Indication**: Type 2 diabetes mellitus
**Known Targets**: AMPK (indirect activation), Complex I (mitochondrial)
```

### Phase 1b: Known Mechanisms & Safety

```markdown
### Mechanism of Action
- Inhibits mitochondrial Complex I → ↑AMP/ATP ratio → activates AMPK
- Reduces hepatic glucose production [★★★: PMID:24851903]
- Targets: SLC22A1 (OCT1, primary uptake transporter)

*Source: ChEMBL_get_drug_mechanisms, drugbank_get_pharmacology_by_drug_name_or_drugbank_id*

### Safety Profile
- Well-tolerated with >60 years of clinical use
- Adverse events: GI disturbance (common), lactic acidosis (rare)
- No black box warnings for cancer indication

*Source: OpenTargets_get_drug_adverse_events_by_chemblId*
```

### Phase 2: Literature Search Strategy

```
1. High-precision: "metformin"[Title] AND (cancer OR neoplasm) → 1,847 papers
2. Focused queries:
   - "metformin" AND "AMPK" AND cancer → 312 papers
   - "metformin" AND (clinical trial) AND cancer → 187 papers
   - "metformin" AND ("breast cancer" OR "colorectal cancer") → 445 papers
3. Citation expansion from top 20 most-cited → 234 additional unique
```

### Phase 3: Report Excerpt with Evidence Grading

```markdown
## Core Evidence for Anti-Cancer Activity

### Epidemiological Evidence
Retrospective studies consistently show reduced cancer incidence in metformin-treated
diabetic patients vs other antidiabetics [★☆☆ Association: PMID:16168273, large cohort].
A meta-analysis of 265 studies confirms ~30% risk reduction [★☆☆: PMID:24925038].

### Mechanistic Evidence
Metformin activates AMPK, inhibiting mTORC1 and reducing cell proliferation
[★★★ Mechanistic: PMID:16489903, direct biochemical evidence].
It also reduces insulin/IGF-1 levels systemically [★★☆ Functional: PMID:22893504].

### Clinical Trial Evidence
Multiple ongoing trials (NCT01101438, NCT02581137) testing metformin as adjuvant
in breast, colorectal, and pancreatic cancer [★★☆: active clinical data].
No phase III RCT has yet demonstrated overall survival benefit as primary endpoint
[gap identified].

**Summary**:
- Epidemiological: MODERATE (consistent association, confounding risk)
- Mechanistic: STRONG (AMPK/mTOR pathway well-characterized)
- Clinical: EMERGING (trials ongoing, no definitive phase III result)
```

---

## Example 7: General Academic Topic (CS/ML - No Bio Tools)

### User Query
"What does the literature say about retrieval-augmented generation (RAG)?"

### Phase 0: Clarification

```
Agent: I'll conduct a deep literature review on RAG. Quick clarification:

1. **Scope**: Comprehensive overview, or focused on a specific aspect
   (architectures, evaluation, domain-specific applications)?
2. **Date range**: Include foundational work, or focus on recent (2023+)?

User: Comprehensive overview including foundational work.
```

### Phase 1: Subject Disambiguation (General Academic)

**No bio tools used.** Proceed with literature-only disambiguation.

```markdown
## Subject Identity & Scope

| Attribute | Value |
|-----------|-------|
| Full Name | Retrieval-Augmented Generation |
| Abbreviation | RAG |
| Domain | Natural Language Processing / Information Retrieval |
| Foundational Paper | Lewis et al. (2020), "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks" |

**Related but distinct**:
- RAG (biology): Recombination Activating Gene (immunology)
- Collision filter applied: NOT "recombination activating" NOT "V(D)J" NOT "immunoglobulin"

**Key sub-topics**: dense retrieval, knowledge grounding, hallucination reduction,
chunking strategies, vector databases, evaluation frameworks
```

### Phase 2: Literature Search Strategy

```
Tools used (no bio tools):
- ArXiv_search_papers(query="retrieval augmented generation", sort_by="submittedDate")
- SemanticScholar_search_papers(query="RAG retrieval augmented generation", sort="citationCount:desc")
- DBLP_search_publications(query="retrieval augmented generation")
- openalex_literature_search(search_keywords="retrieval augmented generation")

Collision filter: NOT "recombination activating" NOT "V(D)J"

1. High-precision: "retrieval-augmented generation"[Title] → 342 papers
2. Citation expansion from Lewis et al. 2020 (3,800+ citations) → top 100
3. Broader: "RAG" AND ("language model" OR "knowledge grounding") NOT "V(D)J" → 189 papers
```

### Phase 3: Report Excerpt

```markdown
## 6. Core Mechanisms

### 6.1 Architecture
RAG combines a parametric language model with a non-parametric retrieval component.
The original architecture uses DPR for retrieval and BART for generation
[★★★: arXiv:2005.11401, Lewis et al. 2020].

### 6.2 Retrieval Strategies
- Dense Passage Retrieval (DPR) [★★★: arXiv:2004.04906, Karpukhin et al.]
- ColBERT late interaction [★★★: arXiv:2004.12832, Khattab & Zaharia]
- Hybrid sparse+dense retrieval [★★☆: multiple studies]

### 6.3 Key Finding
RAG reduces hallucination by grounding generation in retrieved evidence
[★★☆: arXiv:2305.14627, multiple evaluation studies]. However, retrieval
noise can propagate errors [★★☆: arXiv:2401.15391].

## 12. Research Themes

### 12.1 Architectures & Training (87 papers)
**Evidence Quality**: Strong
[Dense retrieval, cross-encoders, late interaction, end-to-end training...]

### 12.2 Evaluation & Benchmarks (45 papers)
**Evidence Quality**: Moderate
[RAGAS, faithfulness metrics, attribution, citation generation...]

### 12.3 Domain-Specific RAG (62 papers)
**Evidence Quality**: Moderate
[Medical QA, legal, code generation, scientific literature...]

### 12.4 Chunking & Indexing (28 papers)
**Evidence Quality**: Limited (emerging area)
[Semantic chunking, hierarchical retrieval, multi-vector...]

## 14. Integrated Model & Hypotheses

| # | Hypothesis | Test | Readout | Expected | Priority |
|---|------------|------|---------|----------|----------|
| 1 | Iterative RAG outperforms single-pass | Multi-hop QA benchmark | Accuracy, faithfulness | 10-15% improvement | HIGH |
| 2 | Semantic chunking > fixed-size | Domain-specific QA | Answer quality, retrieval precision | Semantic chunking wins on complex docs | HIGH |
| 3 | RAG + fine-tuning > RAG alone | Specialized domain (medical) | F1, hallucination rate | Combined approach optimal | MEDIUM |
```

---

## Example 8: Cross-Domain Query (GNN for Drug Discovery)

### User Query
"What does the literature say about graph neural networks for drug discovery?"

### Phase 1: Interdisciplinary Disambiguation

**Identify domain components**:
- CS/ML: Graph Neural Networks (GNN, GCN, GAT, MPNN)
- Bio/Drug: Drug discovery (molecular property prediction, virtual screening, ADMET)

**CS component** (no bio tools):
```markdown
| Attribute | Value |
|-----------|-------|
| Full Name | Graph Neural Networks |
| Abbreviation | GNN |
| Sub-architectures | GCN, GAT, MPNN, SchNet, DimeNet |
| Foundational Paper | Kipf & Welling (2017), "Semi-Supervised Classification with GCNs" |
```

**Bio component** (resolve drug discovery entities):
```
OpenTargets_get_drug_chembId_by_generic_name → Not applicable (method, not drug)
Skip drug/target disambiguation — this is about a method applied to the domain
```

**Collision check**: "GNN" has low collision risk (not overloaded across domains).
No negative filter needed.

### Phase 2: Hybrid Literature Search

```
CS tools:
- ArXiv_search_papers(query='graph neural network drug discovery', sort_by='submittedDate')
- SemanticScholar_search_papers(query='GNN molecular property prediction', sort='citationCount:desc')
- DBLP_search_publications(query='graph neural network drug')

Bio tools:
- PubMed_search_articles(query='"graph neural network" AND ("drug discovery" OR "molecular property")')
- EuropePMC_search_articles(query='"GNN" AND "drug discovery"')

Bridging:
- openalex_literature_search(search_keywords='graph neural network drug discovery')
```

### Phase 3: Report Excerpt

```markdown
## 6. Core Mechanisms

### 6.1 Molecular Graph Representations
Molecules are naturally represented as graphs where atoms are nodes and bonds
are edges. GNNs learn molecular representations through message-passing
[★★★: arXiv:1704.01212, Gilmer et al. 2017, MPNN framework].

### 6.2 Key Architectures
- **MPNN** (Message Passing Neural Network): Unified framework [★★★: arXiv:1704.01212]
- **SchNet**: Continuous-filter convolutions for 3D [★★★: arXiv:1706.08566]
- **AttentiveFP**: Graph attention for molecular properties [★★☆: PMID:31408336]

## 12. Research Themes

### 12.1 Molecular Property Prediction (89 papers)
**Evidence Quality**: Strong
ADMET, solubility, toxicity prediction using GNN encoders...

### 12.2 Virtual Screening & Drug-Target Interaction (52 papers)
**Evidence Quality**: Moderate
DTI prediction, binding affinity estimation...

### 12.3 De Novo Molecular Generation (38 papers)
**Evidence Quality**: Moderate
Generative models (VAE, flow-based) on molecular graphs...

### 12.4 Retrosynthesis & Reaction Prediction (21 papers)
**Evidence Quality**: Limited (emerging)

## 14. Integrated Model & Hypotheses

| # | Hypothesis | Test | Readout | Expected | Priority |
|---|------------|------|---------|----------|----------|
| 1 | 3D-aware GNNs outperform 2D for binding affinity | PDBbind benchmark | RMSE, Pearson r | 3D models win by 10-15% | HIGH |
| 2 | Pre-training on large molecular datasets improves low-data ADMET | Fine-tune on ToxCast | AUC, F1 | Pre-trained > random init | HIGH |
| 3 | GNN + physics-based scoring > either alone | CASF-2016 docking | Success rate, enrichment | Hybrid approach optimal | MEDIUM |
```

---

## Key Principles Demonstrated

1. **Disambiguation first** - Resolve IDs/scope, check collisions before searching
2. **Evidence grading everywhere** - T1-T4 labels on all claims
3. **Citation-first for sparse targets** - Expand from seeds when keywords fail
4. **Collision-aware queries** - Apply NOT filters for ambiguous names
5. **Mandatory sections** - Include all 15 sections, even if "limited evidence"
6. **Integrated model** - Synthesize evidence into testable hypotheses
7. **Scalable bibliography** - Narrative in report, full data in JSON
8. **Domain adaptation** - Bio tools for bio queries, CS tools for CS queries, general tools for everything else
