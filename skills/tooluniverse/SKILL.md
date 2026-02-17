---
name: tooluniverse
description: Router skill for ToolUniverse tasks. First checks if specialized tooluniverse skills (54 skills covering disease/drug/target research, clinical decision support, genomics, transcriptomics, single-cell analysis, variant analysis, phylogenetics, statistical modeling, image analysis, epigenomics, chemical safety, systems biology, multi-omics integration, proteomics, metabolomics, spatial omics, immune repertoire analysis, and more) can solve the problem, then falls back to general strategies for using 1400+ scientific tools. Covers tool discovery, multi-hop queries, comprehensive research workflows, disambiguation, evidence grading, and report generation. Use when users need to research any scientific topic, find biological data, or explore drug/target/disease relationships.
---

# ToolUniverse Router & General Strategies

## YOUR TASK: Route User Questions to the Right Solution

When a user asks a question, **DO NOT just show this documentation**. Instead, follow these steps:

### STEP 1: Parse the User's Question

Read the user's question and extract:
1. **Main subject**: What entity? (disease, drug, protein, gene, variant, etc.)
2. **Action**: What do they want? (research, retrieve, find, compare, analyze, etc.)
3. **Scope**: Comprehensive report or specific data?
4. **Keywords**: Key terms that indicate which skill to use

### STEP 2: Check for Routing Match

**IMMEDIATELY** check the routing table below. If the user's keywords match a specialized skill:
- **USE THE Skill TOOL** to invoke that specialized skill right now
- Pass the user's question to the specialized skill
- Let that skill handle the entire workflow
- **DO NOT** continue with general strategies

If multiple skills match:
- **ASK THE USER** which approach they prefer using AskUserQuestion
- **DO NOT** guess which skill to use

If no specialized skill matches:
- **PROCEED TO STEP 3** to use general strategies

### STEP 3: Use General Strategies (Only if No Skill Matches)

If no specialized skill matches, **EXECUTE** the general strategies (not just describe them):
- **Actually run** Tool_Finder queries to discover tools
- **Actually invoke** multiple tools to gather data
- **Actually generate** comprehensive reports
- **DO NOT** just show the strategy documentation

---

## Routing Table (Check This First!)

**ACTION REQUIRED**: Match the user's keywords against this table. When you find a match, **INVOKE THE SKILL** using the Skill tool.

#### 1. Data Retrieval Tasks

**IF** user keywords match → **THEN** invoke skill immediately:

| User Question Keywords | ACTION: Invoke This Skill |
|------------------------|---------------------------|
| "get", "retrieve", "fetch", "**chemical compound**", "PubChem", "ChEMBL", "drug molecule", "compound info", "SMILES", "InChI" | **DO NOW**: `Skill(skill="tooluniverse-chemical-compound-retrieval", args="[user question]")` |
| "get", "retrieve", "**expression data**", "gene expression", "omics dataset", "ArrayExpress", "BioStudies", "RNA-seq", "microarray" | **DO NOW**: `Skill(skill="tooluniverse-expression-data-retrieval", args="[user question]")` |
| "get", "retrieve", "**protein structure**", "PDB", "AlphaFold", "crystal structure", "3D model", "coordinates" | **DO NOW**: `Skill(skill="tooluniverse-protein-structure-retrieval", args="[user question]")` |
| "get", "retrieve", "**sequence**", "DNA sequence", "RNA sequence", "protein sequence", "NCBI", "ENA", "FASTA" | **DO NOW**: `Skill(skill="tooluniverse-sequence-retrieval", args="[user question]")` |

#### 2. Research & Profiling Tasks

**IF** user keywords match → **THEN** invoke skill immediately:

| User Question Keywords | ACTION: Invoke This Skill |
|------------------------|---------------------------|
| "research", "profile", "tell me about", "**disease**", "syndrome", "disorder", "illness", "comprehensive report on [disease]" | **DO NOW**: `Skill(skill="tooluniverse-disease-research", args="[disease name]")` |
| "**multiomic disease characterization**", "molecular profile of disease", "disease omics", "comprehensive disease analysis" | **DO NOW**: `Skill(skill="tooluniverse-multiomic-disease-characterization", args="[disease]")` |
| "research", "profile", "**drug**", "medication", "therapeutic agent", "medicine", "tell me about [drug]" | **DO NOW**: `Skill(skill="tooluniverse-drug-research", args="[drug name]")` |
| "**literature review**", "papers about", "publications on", "research articles", "synthesize literature", "recent studies" | **DO NOW**: `Skill(skill="tooluniverse-literature-deep-research", args="[topic]")` |
| "research", "profile", "**target**", "protein target", "gene target", "target validation", "tell me about [protein/gene]" | **DO NOW**: `Skill(skill="tooluniverse-target-research", args="[target name]")` |

#### 3. Clinical Decision Support Tasks

**IF** user keywords match → **THEN** invoke skill immediately:

| User Question Keywords | ACTION: Invoke This Skill |
|------------------------|---------------------------|
| "**drug safety**", "adverse events", "side effects", "pharmacovigilance", "FAERS", "black box warning", "drug toxicity" | **DO NOW**: `Skill(skill="tooluniverse-pharmacovigilance", args="[drug name]")` |
| "**adverse event detection**", "AE prediction", "safety signal", "drug adverse reaction", "pharmacovigilance analysis" | **DO NOW**: `Skill(skill="tooluniverse-adverse-event-detection", args="[drug name]")` |
| "**chemical safety**", "toxicity prediction", "ADMET", "chemical toxicity", "environmental toxicity", "safety assessment", "toxic effects", "chemical risk" | **DO NOW**: `Skill(skill="tooluniverse-chemical-safety", args="[chemical name or SMILES]")` |
| "**cancer treatment**", "precision oncology", "tumor mutation", "targeted therapy", "EGFR", "KRAS", "BRAF", "therapy for [mutation]" | **DO NOW**: `Skill(skill="tooluniverse-precision-oncology", args="[mutation or cancer type]")` |
| "**cancer variant**", "somatic mutation interpretation", "oncogenic variant", "tumor variant classification" | **DO NOW**: `Skill(skill="tooluniverse-cancer-variant-interpretation", args="[variant]")` |
| "**clinical trial matching**", "trial eligibility", "recruit patients", "trial enrollment", "match patient to trial" | **DO NOW**: `Skill(skill="tooluniverse-clinical-trial-matching", args="[patient criteria]")` |
| "**immunotherapy response**", "checkpoint inhibitor", "PD-1", "PD-L1", "predict response to immunotherapy", "IO biomarkers" | **DO NOW**: `Skill(skill="tooluniverse-immunotherapy-response-prediction", args="[patient data]")` |
| "**rare disease diagnosis**", "differential diagnosis", "phenotype matching", "HPO", "genetic diagnosis", "patient with [symptoms]" | **DO NOW**: `Skill(skill="tooluniverse-rare-disease-diagnosis", args="[symptoms or phenotypes]")` |
| "**variant interpretation**", "VUS", "pathogenicity", "clinical significance", "genetic variant", "is [variant] pathogenic" | **DO NOW**: `Skill(skill="tooluniverse-variant-interpretation", args="[variant ID]")` |
| "**precision medicine stratification**", "patient stratification", "molecular subtyping", "personalized treatment", "biomarker-based stratification" | **DO NOW**: `Skill(skill="tooluniverse-precision-medicine-stratification", args="[patient cohort]")` |

#### 4. Discovery & Design Tasks

**IF** user keywords match → **THEN** invoke skill immediately:

| User Question Keywords | ACTION: Invoke This Skill |
|------------------------|---------------------------|
| "**find binders**", "small molecule discovery", "virtual screening", "hit identification", "compounds for [target]" | **DO NOW**: `Skill(skill="tooluniverse-binder-discovery", args="[target name]")` |
| "**drug repurposing**", "new indication", "existing drugs for [disease]", "off-label use", "repurpose [drug]" | **DO NOW**: `Skill(skill="tooluniverse-drug-repurposing", args="[drug or disease]")` |
| "**drug target validation**", "validate target", "target druggability", "target tractability", "is [protein] druggable" | **DO NOW**: `Skill(skill="tooluniverse-drug-target-validation", args="[target]")` |
| "**design protein**", "protein binder", "de novo protein", "RFdiffusion", "ProteinMPNN", "therapeutic protein" | **DO NOW**: `Skill(skill="tooluniverse-protein-therapeutic-design", args="[design specifications]")` |
| "**antibody engineering**", "antibody design", "humanization", "affinity maturation", "design antibody for [target]" | **DO NOW**: `Skill(skill="tooluniverse-antibody-engineering", args="[target]")` |

#### 5. Genomics & Variant Analysis Tasks

**IF** user keywords match → **THEN** invoke skill immediately:

| User Question Keywords | ACTION: Invoke This Skill |
|------------------------|---------------------------|
| "**variant analysis**", "VCF", "mutation analysis", "VAF", "consequence prediction", "VEP", "annotation", "missense", "nonsense", "frameshift" | **DO NOW**: `Skill(skill="tooluniverse-variant-analysis", args="[VCF file or variant]")` |
| "**GWAS study**", "genome-wide association", "GWAS catalog", "genetic associations", "GWAS for [trait]" | **DO NOW**: `Skill(skill="tooluniverse-gwas-study-explorer", args="[trait]")` |
| "**GWAS trait to gene**", "trait-associated genes", "GWAS genes", "causal genes", "genes for [trait]" | **DO NOW**: `Skill(skill="tooluniverse-gwas-trait-to-gene", args="[trait]")` |
| "**fine-mapping**", "finemapping", "credible sets", "causal variants", "statistical refinement" | **DO NOW**: `Skill(skill="tooluniverse-gwas-finemapping", args="[region or study]")` |
| "**SNP interpretation**", "SNP function", "rsID", "rs[number]", "variant annotation" | **DO NOW**: `Skill(skill="tooluniverse-gwas-snp-interpretation", args="[rsID]")` |
| "**polygenic risk**", "PRS", "genetic risk", "risk prediction", "risk score for [disease]" | **DO NOW**: `Skill(skill="tooluniverse-polygenic-risk-score", args="[disease]")` |
| "**structural variant**", "SV", "CNV", "deletion", "duplication", "chromosomal rearrangement" | **DO NOW**: `Skill(skill="tooluniverse-structural-variant-analysis", args="[SV coordinates]")` |

#### 6. Systems & Network Analysis Tasks

**IF** user keywords match → **THEN** invoke skill immediately:

| User Question Keywords | ACTION: Invoke This Skill |
|------------------------|---------------------------|
| "**protein interactions**", "PPI", "interactome", "binding partners", "protein complexes", "interactions of [protein]" | **DO NOW**: `Skill(skill="tooluniverse-protein-interactions", args="[protein name]")` |
| "**systems biology**", "pathway analysis", "network analysis", "gene set enrichment" | **DO NOW**: `Skill(skill="tooluniverse-systems-biology", args="[gene list or pathway]")` |
| "**gene enrichment**", "pathway enrichment", "GO enrichment", "KEGG", "Reactome", "enrichr", "ORA", "GSEA", "overrepresentation" | **DO NOW**: `Skill(skill="tooluniverse-gene-enrichment", args="[gene list]")` |
| "**metabolomics**", "metabolite identification", "metabolic pathway", "small molecule metabolism" | **DO NOW**: `Skill(skill="tooluniverse-metabolomics", args="[metabolite or pathway]")` |
| "**epigenomics**", "gene regulation", "transcription factor", "TF binding", "enhancers", "chromatin", "histone modification", "ATAC-seq", "ChIP-seq", "regulatory elements" | **DO NOW**: `Skill(skill="tooluniverse-epigenomics", args="[gene or region]")` |
| "**network pharmacology**", "drug-target network", "polypharmacology", "multi-target drugs", "systems pharmacology" | **DO NOW**: `Skill(skill="tooluniverse-network-pharmacology", args="[drug or targets]")` |

#### 7. Omics Analysis Tasks

**IF** user keywords match → **THEN** invoke skill immediately:

| User Question Keywords | ACTION: Invoke This Skill |
|------------------------|---------------------------|
| "**RNA-seq**", "differential expression", "DESeq2", "DEG", "gene expression", "count matrix", "padj", "log2FoldChange", "bulk RNA-seq" | **DO NOW**: `Skill(skill="tooluniverse-rnaseq-deseq2", args="[count file or dataset]")` |
| "**single-cell**", "scRNA-seq", "cell clustering", "UMAP", "t-SNE", "cell type", "scanpy", "Seurat", "per-cell-type DE", "marker genes" | **DO NOW**: `Skill(skill="tooluniverse-single-cell", args="[h5ad file or dataset]")` |
| "**proteomics**", "protein quantification", "mass spec", "MS/MS", "peptide identification", "protein abundance" | **DO NOW**: `Skill(skill="tooluniverse-proteomics-analysis", args="[proteomics data]")` |
| "**metabolomics analysis**", "untargeted metabolomics", "metabolite profiling", "peak annotation", "metabolic features" | **DO NOW**: `Skill(skill="tooluniverse-metabolomics-analysis", args="[metabolomics data]")` |
| "**spatial transcriptomics**", "Visium", "spatial gene expression", "tissue architecture", "spatially resolved", "spot-level expression" | **DO NOW**: `Skill(skill="tooluniverse-spatial-transcriptomics", args="[spatial data]")` |
| "**spatial omics**", "spatial proteomics", "imaging mass cytometry", "CODEX", "multiplexed imaging", "spatial multi-omics" | **DO NOW**: `Skill(skill="tooluniverse-spatial-omics-analysis", args="[spatial omics data]")` |
| "**multi-omics integration**", "integrate omics", "multi-level analysis", "cross-omics", "omics fusion", "combine RNA-seq and proteomics" | **DO NOW**: `Skill(skill="tooluniverse-multi-omics-integration", args="[omics datasets]")` |
| "**immune repertoire**", "TCR-seq", "BCR-seq", "V(D)J", "CDR3", "antibody repertoire", "clonotype analysis" | **DO NOW**: `Skill(skill="tooluniverse-immune-repertoire-analysis", args="[repertoire data]")` |

#### 8. Screening & Functional Genomics Tasks

**IF** user keywords match → **THEN** invoke skill immediately:

| User Question Keywords | ACTION: Invoke This Skill |
|------------------------|---------------------------|
| "**CRISPR screen**", "genetic screen", "screen hits", "essential genes", "analyze screen data", "MAGeCK", "RIGER" | **DO NOW**: `Skill(skill="tooluniverse-crispr-screen-analysis", args="[screen data]")` |
| "**drug-drug interaction**", "DDI", "drug combination", "polypharmacy", "interactions between [drug1] and [drug2]" | **DO NOW**: `Skill(skill="tooluniverse-drug-drug-interaction", args="[drug1, drug2]")` |

#### 9. Phylogenetics & Evolutionary Analysis Tasks

**IF** user keywords match → **THEN** invoke skill immediately:

| User Question Keywords | ACTION: Invoke This Skill |
|------------------------|---------------------------|
| "**phylogenetics**", "phylogenetic tree", "treeness", "RCV", "DVMC", "parsimony informative", "tree length", "evolutionary rate", "PhyKIT", "alignment", "Newick" | **DO NOW**: `Skill(skill="tooluniverse-phylogenetics", args="[alignment or tree file]")` |

#### 10. Statistical Modeling & Regression Tasks

**IF** user keywords match → **THEN** invoke skill immediately:

| User Question Keywords | ACTION: Invoke This Skill |
|------------------------|---------------------------|
| "**statistical modeling**", "regression", "logistic regression", "Cox PH", "survival analysis", "Kaplan-Meier", "odds ratio", "hazard ratio", "mixed effects", "ordinal regression", "multinomial" | **DO NOW**: `Skill(skill="tooluniverse-statistical-modeling", args="[dataset and model type]")` |

#### 11. Image Analysis & Microscopy Tasks

**IF** user keywords match → **THEN** invoke skill immediately:

| User Question Keywords | ACTION: Invoke This Skill |
|------------------------|---------------------------|
| "**image analysis**", "microscopy", "cell counting", "colony morphometry", "fluorescence quantification", "Dunnett's test", "Cohen's d", "natural spline", "image statistics" | **DO NOW**: `Skill(skill="tooluniverse-image-analysis", args="[image file or measurements]")` |

#### 12. Clinical Trial & Study Design Tasks

**IF** user keywords match → **THEN** invoke skill immediately:

| User Question Keywords | ACTION: Invoke This Skill |
|------------------------|---------------------------|
| "**clinical trial design**", "trial protocol", "study design", "endpoint selection", "design trial for [drug/disease]" | **DO NOW**: `Skill(skill="tooluniverse-clinical-trial-design", args="[drug or disease]")` |
| "**GWAS drug discovery**", "genetic target validation", "GWAS to drug", "genetic evidence for drug" | **DO NOW**: `Skill(skill="tooluniverse-gwas-drug-discovery", args="[trait or gene]")` |

#### 13. Outbreak Response Tasks

**IF** user keywords match → **THEN** invoke skill immediately:

| User Question Keywords | ACTION: Invoke This Skill |
|------------------------|---------------------------|
| "**pathogen**", "infectious disease", "outbreak", "emerging infection", "novel virus", "novel bacteria" | **DO NOW**: `Skill(skill="tooluniverse-infectious-disease", args="[pathogen name]")` |

#### 14. Infrastructure & Development Tasks

**IF** user keywords match → **THEN** invoke skill immediately:

| User Question Keywords | ACTION: Invoke This Skill |
|------------------------|---------------------------|
| "**setup**", "install ToolUniverse", "configure MCP", "API keys", "upgrade", "how to install" | **DO NOW**: `Skill(skill="setup-tooluniverse")` |
| "**SDK**", "Python SDK", "build AI scientist", "programmatic access", "use ToolUniverse in Python" | **DO NOW**: `Skill(skill="tooluniverse-sdk", args="[use case]")` |

### Routing Workflow (What You Must Do)

**STEP-BY-STEP ACTIONS**:

1. **Extract keywords** from user's question
2. **Scan routing table** above for keyword matches
3. **Take action based on match**:
   - **If 1 clear match** → **INVOKE THAT SKILL NOW** using the Skill tool
   - **If multiple matches** → **ASK USER** using AskUserQuestion which they prefer
   - **If no match** → **PROCEED to general strategies** (Strategy 1-10 below)
4. **If ambiguous** (e.g., "Tell me about aspirin") → **ASK USER** to clarify intent first

### Tie-Breaking Rules (When Multiple Skills Match)

If multiple skills could handle the query:

1. **Specificity Rule**: Choose more specific over general
   - Example: "cancer treatment" → precision-oncology (specific) NOT disease-research (general)
2. **Data Type Rule**: For "get/retrieve/fetch" queries, choose retrieval skills
   - Example: "get compound structure" → chemical-compound-retrieval NOT drug-research
3. **If still ambiguous**: **ASK USER** using AskUserQuestion with 2-3 options

### When to Use General Strategies

**ONLY** use general strategies when:
- ✅ **No specialized skill** in routing table matches the query
- ✅ User asks "**how do I...**" or "**what's the best way to...**" (meta-questions about ToolUniverse)
- ✅ User wants to **build custom workflow** combining multiple skills
- ✅ User explicitly says "**don't use specialized skills**"

**CRITICAL**: If ANY specialized skill matches, **INVOKE IT**. Don't use general strategies.

---

## Fallback Strategy for Missing Specialized Skills

**Some research areas do not yet have specialized skills.** When a user asks about topics not covered in the routing table:

### Known Coverage Gaps

| Topic Area | Missing Skill | Fallback Approach |
|------------|---------------|-------------------|
| "**methylation analysis**", "CpG islands", "DMR", "differential methylation" | ⚠️ No methylation-specific skill | Use **epigenomics** skill for regulatory context OR use **biostatistics workflows** with methylation tools (search Tool_Finder for "methylation") |
| "**microbiome**", "16S", "metagenomics", "gut microbiome" | ⚠️ No microbiome skill | Use general strategies: Tool_Finder for "microbiome" + "16S" + execute workflows |
| "**lipidomics**", "lipid profiling" | ⚠️ No lipidomics skill | Use **metabolomics-analysis** as closest match OR general strategies with lipid-specific tools |
| "**glycomics**", "glycosylation" | ⚠️ No glycomics skill | Use general strategies: Tool_Finder for "glycan" + execute workflows |
| "**flow cytometry**", "FACS analysis" | ⚠️ No flow cytometry skill | Use **image-analysis** for general cytometry OR general strategies |

### Fallback Workflow (When No Specialized Skill Exists)

When you determine no specialized skill covers the user's request:

1. **Acknowledge the gap**: "There isn't a specialized skill for [topic] yet."
2. **Identify closest skill**: "The closest match is [skill-name], which covers [overlap]."
3. **Offer general approach**: "I can use ToolUniverse's general strategies to:"
   - Search for relevant tools using Tool_Finder
   - Execute multi-hop workflows with discovered tools
   - Generate a comprehensive report
4. **Ask user preference**: "Would you like me to: (A) Use general strategies, or (B) Use [closest-skill] and supplement with additional tools?"

### Example Fallback Response

**User**: "Analyze my methylation data for differentially methylated regions"

**Your Response**:
```
There isn't a specialized methylation analysis skill yet. However, I can help using two approaches:

(A) Use the **epigenomics** skill for regulatory context, then supplement with methylation-specific tools
(B) Use general strategies to discover methylation tools (like RnBeads, DSS, methylKit) and build a custom workflow

Which would you prefer?
```

---

## Routing Examples (Learn From These)

### Example 1: Clear Match → Invoke Skill

**User**: "I need a comprehensive research report on breast cancer"
**Your Action**:
```
1. Keywords: "comprehensive research report", "breast cancer" (disease)
2. Match: Category 2 - "research", "disease" matches disease-research
3. DO: Skill(skill="tooluniverse-disease-research", args="breast cancer")
```

### Example 2: Ambiguous → Ask User

**User**: "Tell me about aspirin"
**Your Action**:
```
1. Keywords: "tell me about", "aspirin" (drug)
2. Matches: drug-research, pharmacovigilance, chemical-compound-retrieval, drug-repurposing
3. DO: AskUserQuestion - "Would you like: (A) Comprehensive drug profile, (B) Safety/adverse events, (C) Chemical structure data, or (D) Repurposing opportunities?"
```

### Example 3: No Match → General Strategies

**User**: "How can I find all tools related to proteomics?"
**Your Action**:
```
1. Keywords: "how can I find", "tools", "proteomics"
2. Match: None (this is a meta-question about using ToolUniverse)
3. DO: Proceed to Strategy 1 (Tool Discovery) - Actually run Tool_Finder queries
```

### Example 4: Multiple Entity Query → Invoke Appropriate Skill

**User**: "Find protein interaction data for TP53 from multiple databases"
**Your Action**:
```
1. Keywords: "protein interaction", "TP53", "multiple databases"
2. Match: Category 6 - "protein interactions" matches protein-interactions skill
3. DO: Skill(skill="tooluniverse-protein-interactions", args="TP53")
```

---

## General Usage Strategies (Fallback Mode)

**USE THESE ONLY IF**: No specialized skill matches (see "When to Use General Strategies" above)

**Use the strategies below when no specialized skill matches the user's question.**

Master strategies for using ToolUniverse's 10000+ scientific tools effectively. These principles apply regardless of how you access ToolUniverse (MCP server, SDK, or direct tool calls).

## Core Philosophy (Your Operating Principles)

When using general strategies, follow these principles:

1. **Search widely** - Run multiple tool discovery queries; don't assume you know all tools
2. **Query multiple databases** - Cross-reference data across sources for completeness
3. **Multi-hop persistence** - Chain 5-10 tool calls if needed; one call is rarely enough
4. **Never give up** - If a tool fails, try alternatives; always have a fallback
5. **Comprehensive reports** - Generate detailed reports with sources; detail adds value
6. **English-first queries** - Always translate to English for tool calls, respond in user's language

---

## Strategy 0: Clarify Before Acting

**BEFORE** you start any research, check if clarification is needed:

### When to Ask Clarifying Questions

| Signal | Example | What to Clarify |
|--------|---------|-----------------|
| **Vague entity** | "Research cancer" | Which cancer type? Which aspect (treatment, genetics, epidemiology)? |
| **Ambiguous name** | "Tell me about JAK" | JAK1/2/3? The gene family? A specific inhibitor? |
| **Unclear scope** | "Look into metformin" | Drug profile? Repurposing? Safety? Mechanism? |
| **Missing context** | "What targets this?" | Which compound/disease/pathway? |
| **Multiple interpretations** | "ACE" | ACE the gene? ACE inhibitors? ACE2? |

### When NOT to Ask

Proceed directly when the request is specific enough:
- "What is the structure of EGFR kinase domain?" - Clear entity + clear data type
- "Find all drugs targeting BRAF V600E" - Specific variant + clear task
- "Research Alzheimer's disease comprehensively" - Broad but unambiguous

### Clarification Checklist

Before starting research, confirm you know:
1. **Entity** - Exactly which gene/protein/drug/disease?
2. **Species** - Human unless stated otherwise
3. **Scope** - Comprehensive profile or specific aspect?
4. **Output** - Report, data table, quick answer, or comparison?

If any of these are unclear, ask the user **one concise question** covering all ambiguities rather than asking multiple rounds of questions.

---

## Strategy 1: Exhaustive Tool Discovery

**WHEN TO USE**: User asks "how to find tools" or you need tools for a novel task

### ACTION: Run These Tool Discovery Queries

**STEP 1**: Extract main topic and synonyms from user's question

**STEP 2**: Run multiple tool finder queries IN PARALLEL:

```python
# Example: User asks "find tools for metabolomics and mass spectrometry"

# DO THIS NOW:
Tool_Finder_Keyword(query="metabolomics")
Tool_Finder_Keyword(query="mass spectrometry")
Tool_Finder_Keyword(query="metabolite identification")
Tool_Finder_LLM(query="metabolomics analysis tools")
Tool_Finder(query="metabolomics mass spectrometry")
```

**STEP 3**: Also search by related terms and database names:

```python
# Expand search:
Tool_Finder_Keyword(query="metabolic pathway")
Tool_Finder_Keyword(query="small molecule metabolism")
Tool_Finder_Keyword(query="HMDB")  # Known metabolomics database
Tool_Finder_Keyword(query="MetaboLights")
```

**STEP 4**: Aggregate results, remove duplicates, present organized list to user

### Minimum Discovery Queries Template

For ANY research task, run at least these:

1. **Main topic**: `Tool_Finder_Keyword(query="[main topic]")`
2. **Synonym 1**: `Tool_Finder_Keyword(query="[synonym]")`
3. **Synonym 2**: `Tool_Finder_Keyword(query="[another synonym]")`
4. **Database**: `Tool_Finder_Keyword(query="[known database name]")`
5. **Data type**: `Tool_Finder_Keyword(query="[data type]")`
6. **Use case**: `Tool_Finder_LLM(query="[full use case description]")`

**CRITICAL**: Actually RUN these queries, don't just describe them!

---

## Strategy 2: Multi-Hop Tool Chains

**CRITICAL**: Most scientific questions require multiple tool calls. A single tool rarely gives the complete answer.

### Why Multi-Hop Matters

| Question Type | Single Tool Answer | Multi-Hop Answer |
|---------------|-------------------|------------------|
| "Tell me about EGFR" | Basic protein info | Full profile with structure, expression, drugs, variants, literature |
| "What drugs target TP53?" | List of drug names | Drug details, mechanisms, clinical trials, bioactivity data |
| "Research Alzheimer's" | Disease definition | Genes, pathways, drugs, trials, phenotypes, GWAS, literature |

### Common Multi-Hop Patterns

#### Pattern A: ID Resolution Chain
```
Name → ID → Data → Related Data

Example: Gene name to complete profile
1. gene_name → Ensembl ID
2. Ensembl ID → UniProt accession  
3. UniProt accession → Protein entry
4. UniProt accession → Domains
5. UniProt accession → Structure
```

#### Pattern B: Cross-Database Enrichment
```
Primary Data → Cross-reference → Enriched View

Example: Drug compound enrichment
1. drug_name → PubChem CID
2. drug_name → ChEMBL ID
3. CID → properties
4. ChEMBL ID → bioactivity
5. ChEMBL ID → targets
6. SMILES → ADMET predictions
```

#### Pattern C: Network Expansion
```
Seed Entity → Connected Entities → Entity Details

Example: Target interaction network
1. gene → protein interactions
2. For each interactor → gene info
3. Interactor → disease associations
```

#### Pattern D: Literature + Data Integration
```
Database Annotations → Literature Evidence → Synthesis

Example: Disease mechanism research
1. disease → associated genes
2. disease → phenotypes
3. disease → drugs
4. disease → literature
5. key papers → citations
```

### Multi-Hop Persistence Rules

1. **Don't stop at first result** - One tool gives partial data; keep going
2. **Follow cross-references** - Use IDs from one tool to query others
3. **Chain until complete** - 5-10 tool calls for comprehensive answers is normal
4. **Track all IDs** - Save every identifier for potential future use

---

## Strategy 3: Query Multiple Databases for Same Data

**CRITICAL**: Different databases have different coverage. Query ALL relevant sources.

### Database Redundancy Principle

For any data type, query multiple sources:

| Data Type | Primary | Secondary | Tertiary |
|-----------|---------|-----------|----------|
| **Protein info** | UniProt | Proteins API | NCBI Protein |
| **Gene expression** | GTEx | Human Protein Atlas | ArrayExpress |
| **Drug targets** | ChEMBL | DGIdb | OpenTargets |
| **Variants** | gnomAD | ClinVar | OpenTargets |
| **Literature** | PubMed | Europe PMC | OpenAlex |
| **Pathways** | Reactome | KEGG | WikiPathways |
| **Structures** | RCSB PDB | PDBe | AlphaFold |
| **Disease associations** | OpenTargets | ClinVar | GWAS Catalog |

### Merge Results Strategy

When querying multiple databases:
1. **Collect all results** - Don't stop at first success
2. **Note data source** - Track where each datum came from
3. **Handle conflicts** - Document when sources disagree
4. **Prefer curated** - Weight RefSeq over GenBank, UniProt over predictions

---

## Strategy 3.1: Abstract Search vs Full-Text Search (Literature)

**CRITICAL**: Many biomedical “needle” terms (rsIDs like `rs58542926`, reagent catalog numbers, supplementary-table IDs) never appear in titles/abstracts. If you only search abstracts, you will miss papers even when they are open access.

### Quick rule

- If your keywords look like **body-only terms** (rsIDs, figure/table references, “Supplementary Table”), use **full-text-aware** tools first.

### Tools that can match full text (indexed or retrieved)

| Goal | Tools | Notes |
|------|-------|------|
| **Indexed full-text search (biomed OA)** | `PMC_search_papers` | NCBI “pmc” database indexes full text; good for rsIDs. |
| **Indexed full-text search (Europe PMC subset)** | `EuropePMC_search_articles` with `require_has_ft=true` + `fulltext_terms=[...]` | Uses Europe PMC `HAS_FT:Y` + `BODY:\"...\"` fielded queries; works only when Europe PMC has indexed full text. |
| **Best-effort full-text retrieval + keyword snippets** | `EuropePMC_get_fulltext_snippets` | Fetches full text (XML → HTML fallbacks) and returns bounded snippets with `retrieval_trace`. |
| **OA aggregation + (sometimes) full-text search** | `CORE_search_papers` | Coverage varies; a paper may not exist in CORE even if OA elsewhere. |
| **Download-and-scan fallback** | `CORE_get_fulltext_snippets` | Local PDF scan for body-only terms when index-based search misses; can fail if the “PDF” URL returns HTML/403 (check trace/content-type). |
| **Partial full-text indexing (not guaranteed)** | `openalex_search_works` / `openalex_literature_search` with `require_has_fulltext` / `fulltext_terms` | Only matches works where OpenAlex has indexed full text; can miss PMC-hosted full text. Use as a secondary signal. |

### Recommended flow for body-only keywords

1. Try `PMC_search_papers` and `EuropePMC_search_articles` (with `require_has_ft` + `fulltext_terms`).
2. If you have a PMCID/PMID, use `EuropePMC_get_fulltext_snippets` to **confirm the term is in the paper**.
3. If you only have a PDF URL, use `CORE_get_fulltext_snippets` as a last resort, and treat HTTP `200` as “request succeeded”, not “PDF succeeded” (validate `content_type`).

---

## Strategy 4: Disambiguation First

**CRITICAL**: Before any research, resolve entity identity to avoid wrong data and missed results.

### Why Disambiguation Matters

| Problem | Example | Consequence |
|---------|---------|-------------|
| **Naming collision** | "JAK" = Janus kinase OR "just another kinase" | Wrong papers retrieved |
| **Multiple IDs** | Gene has symbol, Ensembl, Entrez, UniProt IDs | Miss data in some databases |
| **Salt forms** | Metformin vs metformin HCl (different CIDs) | Incomplete compound data |
| **Species ambiguity** | BRCA1 in human vs mouse | Wrong expression/function data |

### Disambiguation Workflow

```
Step 1: Establish Canonical IDs
    gene_name → UniProt, Ensembl, NCBI Gene, ChEMBL target
    compound_name → PubChem CID, ChEMBL ID, SMILES
    disease_name → EFO ID, ICD-10, UMLS CUI

Step 2: Gather Synonyms
    All aliases, alternative names, historical names
    
Step 3: Detect Naming Collisions
    Search "[TERM]"[Title] → check if results are on-topic
    Build negative filters: NOT [collision_term]
    
Step 4: Species Confirmation
    Verify organism is correct (default: Homo sapiens)
```

### ID Types by Entity

**Genes/Proteins:**
- Gene Symbol (EGFR, TP53)
- UniProt accession (P00533)
- Ensembl ID (ENSG00000146648)
- NCBI Gene ID (1956)
- ChEMBL Target ID (CHEMBL203)

**Compounds:**
- PubChem CID (2244)
- ChEMBL ID (CHEMBL25)
- SMILES string
- InChI/InChIKey

**Diseases:**
- EFO ID (EFO_0000249)
- ICD-10 code (G30)
- UMLS CUI (C0002395)
- SNOMED CT

---

## Strategy 5: Never Give Up on Search

**CRITICAL**: When a tool fails or returns empty, don't give up. Try alternatives.

### Failure Handling Protocol

```
Attempt 1: Primary tool
    ↓ fails
Wait briefly, then retry
    ↓ fails
Try fallback tool #1
    ↓ fails
Try fallback tool #2
    ↓ fails
Document as "unavailable" with reason
```

### Common Fallback Chains

| Primary Tool | Fallback Options |
|--------------|------------------|
| PubMed citations | EuropePMC citations → OpenAlex citations |
| GTEx expression | Human Protein Atlas expression |
| PubChem compound lookup | ChEMBL search → SMILES-based lookup |
| ChEMBL bioactivity | PubChem bioactivity summary |
| DailyMed drug labels | PubChem drug label info |
| UniProt protein entry | Proteins API |

### Alternative Search Strategies

**If keyword search fails:**
- Try synonyms and aliases
- Use broader/narrower terms
- Try different databases

**If database is empty:**
- Query related databases
- Use literature to find mentions
- Check if entity exists under different name

**If API rate-limited:**
- Wait and retry
- Try same query on different database
- Use cached results if available

---

## Strategy 6: Generate Comprehensive Reports

**CRITICAL**: With access to many tools, reports should be detailed and thorough.

### Report-First Approach

1. **Create report structure FIRST** - Define all sections before gathering data
2. **Progressively update** - Fill sections as data is gathered
3. **Show findings, not process** - Report results, not search methodology

### Citation Requirements

**Every fact must have a source:**

```
## Protein Function

EGFR is a receptor tyrosine kinase that regulates cell growth.
*Source: UniProt (P00533)*

### Expression Profile
| Tissue | TPM | Source |
|--------|-----|--------|
| Skin | 156.3 | GTEx |
| Lung | 98.4 | GTEx |
```

### Evidence Grading

Grade claims by evidence strength:

| Tier | Symbol | Description | Example |
|------|--------|-------------|---------|
| **T1** | ★★★ | Mechanistic with direct evidence | CRISPR KO study |
| **T2** | ★★☆ | Functional study | siRNA knockdown |
| **T3** | ★☆☆ | Association/screen hit | GWAS, high-throughput screen |
| **T4** | ☆☆☆ | Review mention, text-mined | Review article |

**In report:**
```
ATP6V1A drives lysosomal acidification [★★★: PMID:12345678].
It has been implicated in cancer metabolism [★☆☆: TCGA data].
```

### Mandatory Completeness

All sections must exist, even if "data unavailable":

```
## Pathogen Involvement
No pathogen interactions identified in literature or databases.
*Source: Literature search, UniProt annotations*
```

### Report Quality Metrics

| Quality | Description | Tool Calls | Sections |
|---------|-------------|------------|----------|
| **Excellent** | Multi-database, evidence-graded | 30+ | All mandatory, detailed |
| **Good** | Cross-referenced, sourced | 15-30 | All mandatory, adequate |
| **Adequate** | Single-database focus | 5-15 | Core sections only |
| **Poor** | Single tool, no sources | <5 | Incomplete |

---

## Strategy 7: Defer to Specialized Skills

**CRITICAL**: This general skill should only be used when no specialized skill matches (see routing table in Step 0).

### Quick Reference: When to Stop and Route

If you're using these general strategies and realize the task matches a specialized skill:
1. **STOP** using general strategies
2. **ROUTE** to the appropriate specialized skill (see Step 0 routing table)
3. Let the specialized skill handle the entire workflow

### Why Specialized Skills Are Better

| General Strategies | Specialized Skills |
|--------------------|-------------------|
| Flexible but unstructured | Pre-defined optimal workflows |
| No validated output format | Standardized report structure |
| Manual completeness checking | Automated completeness checklists |
| Ad-hoc tool selection | Curated tool combinations |
| Generic guidance | Domain-specific best practices |

### Complete List of Specialized Skills

See **Step 0: Route to Specialized Skills First** at the top of this document for:
- 41+ specialized tooluniverse skills
- Routing decision tree by task type
- Keyword-based routing table
- When to use vs. when to fallback

---

## Strategy 8: Parallel Execution for Speed

**CRITICAL**: Run independent queries simultaneously for faster research.

### When to Parallelize

| Parallel | Sequential |
|----------|------------|
| Different databases for same entity | Tool B needs output from Tool A |
| Multiple entities, same data type | Building an ID → using the ID |
| Independent research paths | Iterating through a list of results |

### Parallel Research Paths Example

For target research, run these 8 paths simultaneously:
1. **Identity** - Names, IDs, sequence
2. **Structure** - 3D structure, domains
3. **Function** - GO terms, pathways
4. **Interactions** - PPI network
5. **Expression** - Tissue expression
6. **Variants** - Genetic variation
7. **Drugs** - Known drugs, druggability
8. **Literature** - Publications, trends

---

## Strategy 9: Iterative Completeness Check

**CRITICAL**: After gathering data, always ask "What else is missing?" to ensure comprehensive coverage.

### The Completeness Loop

```
Gather initial data
    ↓
Review what you have
    ↓
Ask: "What aspects are still missing?"
    ↓
Identify gaps
    ↓
Search for tools to fill gaps
    ↓
Gather additional data
    ↓
Repeat until comprehensive
```

### Universal Completeness Questions

After each research phase, ask:

1. **Identity**: Do I have all relevant identifiers and names?
2. **Core data**: Do I have the fundamental information for this entity type?
3. **Context**: Do I have surrounding/related information?
4. **Relationships**: Do I know what this connects to?
5. **Variations**: Do I know about variants, forms, or subtypes?
6. **Evidence**: Do I have supporting data from multiple sources?
7. **Literature**: Do I have recent publications on this topic?
8. **Gaps**: Have I documented what's unavailable?

### Gap-Filling Strategies

| Gap Identified | Strategy |
|----------------|----------|
| Missing data type | Search for tools with that data type |
| Single source only | Query additional databases |
| Outdated information | Check literature for recent updates |
| No experimental data | Look for predictions/computational data |
| Conflicting data | Find authoritative/curated sources |
| Shallow coverage | Dive deeper with specialized tools |

### When to Stop

Stop the completeness loop when:
- All relevant aspects have been addressed (even if "not found")
- Multiple sources queried for key data
- Gaps are documented, not ignored
- No obvious missing pieces remain

### Self-Review Questions

Before finalizing any research:

- Have I searched for ALL relevant tools?
- Have I queried multiple databases?
- Have I followed cross-references?
- Have I checked recent literature?
- Have I documented what's unavailable?
- Is there any obvious gap I haven't addressed?
- Would someone reading this ask "but what about X?"

---

## Quick Reference: Tool Categories

### Protein & Gene Tools
UniProt, Proteins API, MyGene, Ensembl tools

### Structure Tools
RCSB PDB, PDBe, AlphaFold, InterPro tools

### Drug & Compound Tools
ChEMBL, PubChem, DGIdb, ADMET-AI, DrugBank tools

### Disease & Phenotype Tools
OpenTargets, ClinVar, GWAS, HPO tools

### Expression Tools
GTEx, Human Protein Atlas, CELLxGENE tools

### Variant Tools
gnomAD, ClinVar, dbSNP tools

### Pathway Tools
Reactome, KEGG, WikiPathways, GO tools

### Literature Tools
PubMed, EuropePMC, OpenAlex, SemanticScholar tools

### Clinical Tools
ClinicalTrials.gov, FAERS, PharmGKB, DailyMed tools

---

## Troubleshooting Common Issues

### "Tool not found"
- Search for similar tools using Tool_Finder
- Check spelling of tool name
- Try alternative tools for same data type

### "Empty results"
- Check spelling of query terms
- Try synonyms/aliases
- Try alternative databases
- Verify IDs are correct type

### "Conflicting data"
- Note all sources
- Prefer curated databases
- Document the conflict in report
- Use evidence grading

### "Incomplete picture"
- Search for more tools
- Query additional databases
- Follow cross-references
- Expand via literature

---

## Strategy 10: English-First Tool Queries

**CRITICAL**: Most ToolUniverse tools only accept English terms. Always translate queries to English before calling tools, regardless of the user's language.

### Language Handling Rules

1. **Default to English** - All tool calls must use English search terms, entity names, and parameters
2. **Translate non-English input** - If the user's question is in Chinese, Japanese, Korean, or any other language, translate the relevant scientific terms to English before making tool calls
3. **Respond in the user's language** - While tools must be queried in English, deliver the final report/answer in the user's original language
4. **Fallback to original language** - Only if an English search returns no results, retry with the original-language terms
5. **Check tool descriptions** - A few tools may explicitly document multi-language support; use the original language only when the tool description says so

### Examples

```
User (Chinese): "研究EGFR靶点"
  → Tool calls: use "EGFR", "epidermal growth factor receptor" (English)
  → Report: deliver in Chinese

User (Japanese): "メトホルミンの安全性プロファイル"
  → Tool calls: use "metformin", "safety profile" (English)
  → Report: deliver in Japanese

User (Korean): "알츠하이머병 관련 유전자"
  → Tool calls: use "Alzheimer's disease", "associated genes" (English)
  → Report: deliver in Korean
```

### Why This Matters

| Scenario | Wrong Approach | Correct Approach |
|----------|---------------|-----------------|
| User asks in Chinese about "二甲双胍" | Pass "二甲双胍" to PubChem search | Translate to "metformin", search in English |
| User asks in Japanese about a disease | Pass Japanese disease name to OpenTargets | Translate to English disease name first |
| User asks in Spanish about a gene | Pass Spanish description to tool | Use standard gene symbol (e.g., TP53) |

---

## Summary: What You Must Do

| Situation | Your Action (DO THIS) |
|-----------|------------------------|
| **User question arrives** | Immediately check routing table for keyword matches |
| **1 clear skill match** | **INVOKE THE SKILL** using Skill tool - do NOT describe it |
| **Multiple skill matches** | **ASK USER** which they prefer using AskUserQuestion |
| **No skill matches** | **EXECUTE** general strategies (run actual tool queries) |
| **Ambiguous query** | **ASK FOR CLARIFICATION** before proceeding |
| **Tool call needed** | **ACTUALLY RUN IT** - don't just explain what it does |
| **Report needed** | **GENERATE AND FILL IT** - don't just describe the structure |
| **Tool fails** | **TRY ALTERNATIVES** - have fallback options |
| **Multiple databases** | **QUERY ALL** - run queries in parallel |
| **Complex workflow** | **CHAIN TOOL CALLS** - 5-10 calls is normal |
| **Non-English query** | **TRANSLATE TO ENGLISH** for tools, respond in user's language |

**CRITICAL REMINDER**: Your job is to **ACT**, not to **DESCRIBE**. When you see a match in the routing table, **USE THE Skill TOOL IMMEDIATELY**.

---

## Anti-Patterns (What NOT to Do)

❌ **Don't**: Show the routing table to the user and ask them to choose
✅ **Do**: Match keywords yourself and invoke the appropriate skill

❌ **Don't**: Explain what Strategy 1 is and how it works
✅ **Do**: Execute Strategy 1 by running Tool_Finder queries

❌ **Don't**: Say "You should use /tooluniverse-disease-research for this"
✅ **Do**: Actually invoke the skill: `Skill(skill="tooluniverse-disease-research", args="[disease]")`

❌ **Don't**: Describe the report structure you would generate
✅ **Do**: Create the report file and fill it with actual data

❌ **Don't**: Tell user they need to clarify something without asking a specific question
✅ **Do**: Use AskUserQuestion with specific options

---

## Quick Decision Tree

```
User asks question
      ↓
Extract keywords
      ↓
Check routing table
      ↓
    Match?
   /      \
 YES       NO
  ↓         ↓
1 match?   Meta-question
  ↓  \     about usage?
YES  NO     ↓  \
 ↓    ↓   YES  NO
INVOKE ASK  USE  EXECUTE
SKILL USER STRAT1 WORKFLOW
NOW!  WHICH?  NOW!  NOW!
```

**THE KEY**: Whatever the outcome, **TAKE ACTION**. Don't just show documentation.

---

## Strategy 11: Cross-Skill Workflow Orchestration (NEW)

**CRITICAL**: For complex multi-step analyses, automatically chain multiple specialized skills together to create end-to-end pipelines.

### When to Use Workflow Orchestration

Detect workflow requests by identifying multi-step language:
- "from X to Y" (e.g., "from GWAS to drugs")
- "comprehensive analysis" spanning multiple domains
- "integrate X and Y" requiring multiple skills
- Questions that naturally span 3+ skill domains

### Pre-Defined Workflow Templates

#### Workflow 1: GWAS to Function to Therapeutics

**Trigger words**: "GWAS", "trait", "from variants to drugs", "genetic risk to therapy"

**Pipeline**:
```
User provides: GWAS trait or significant SNPs

Step 1: Genetic Discovery (variant-analysis)
→ Input: GWAS summary stats or SNP list
→ Output: Associated genes with evidence scores

Step 2: Target Validation (target-research)
→ Input: Gene list from Step 1
→ Output: Protein function, pathways, druggability

Step 3: Expression Context (rnaseq-deseq2 or expression-data-retrieval)
→ Input: Gene list
→ Output: Tissue-specific expression, disease relevance

Step 4: Pathway Analysis (gene-enrichment)
→ Input: Gene list
→ Output: Enriched pathways, biological processes

Step 5: Drug Discovery (drug-repurposing or binder-discovery)
→ Input: Targets + pathways from previous steps
→ Output: Candidate therapeutics, mechanism of action

Final Output: Unified report connecting genetic variants → genes →
function → pathways → druggable targets → therapeutic candidates
```

**Example execution**:
```python
# User: "What drugs could treat genetic risk for Type 2 Diabetes?"

# Step 1: Get GWAS genes
genes = Skill("tooluniverse-gwas-trait-to-gene", "Type 2 Diabetes")
# Returns: TCF7L2, PPARG, KCNJ11, etc.

# Step 2: Research each target
target_profiles = []
for gene in genes[:5]:  # Top 5
    profile = Skill("tooluniverse-target-research", gene)
    target_profiles.append(profile)

# Step 3: Get expression patterns
expression = Skill("tooluniverse-expression-data-retrieval",
                   f"pancreas {', '.join(genes[:5])}")

# Step 4: Pathway enrichment
pathways = Skill("tooluniverse-gene-enrichment",
                 f"genes={','.join(genes)}")

# Step 5: Find drugs
drugs = Skill("tooluniverse-drug-repurposing",
              f"targets={','.join(genes[:5])} disease=Type 2 Diabetes")

# Generate unified report with all findings
```

#### Workflow 2: Variant to Clinical Action

**Trigger words**: "VCF", "mutations", "clinical interpretation", "treatment options", "variant to therapy"

**Pipeline**:
```
User provides: VCF file or variant list

Step 1: Variant Annotation (variant-analysis)
→ Input: VCF file
→ Output: Annotated variants with consequences, frequencies

Step 2: Pathogenicity Assessment (variant-interpretation)
→ Input: Variants from Step 1
→ Output: Clinical significance, ACMG criteria

Step 3: Treatment Matching (precision-oncology)
→ Input: Actionable mutations
→ Output: FDA-approved therapies, clinical trials

Step 4: Drug Safety (pharmacovigilance)
→ Input: Recommended drugs from Step 3
→ Output: Adverse events, contraindications

Step 5: Pharmacogenomics
→ Input: Variants + drugs
→ Output: Drug metabolism predictions, dosing recommendations

Final Output: Clinical report with variant interpretations, treatment
options, safety profiles, and actionable recommendations
```

#### Workflow 3: Multi-Omics Disease Characterization

**Trigger words**: "multi-omics", "integrate omics", "comprehensive molecular profile", "transcriptome and proteome"

**Pipeline**:
```
User provides: Disease name or patient omics data

Step 1: Disease Background (disease-research)
→ Input: Disease name
→ Output: Pathophysiology, known genes, biomarkers

Step 2: Expression Analysis (rnaseq-deseq2)
→ Input: RNA-seq data or public datasets
→ Output: Differentially expressed genes

Step 3: Epigenetic Analysis (epigenomics)
→ Input: Methylation data
→ Output: Differentially methylated regions

Step 4: Variant Analysis (variant-analysis)
→ Input: VCF with SNVs/CNVs
→ Output: Disease-associated variants

Step 5: Multi-Omics Integration (multi-omics-integration)
→ Input: Results from Steps 2-4
→ Output: Cross-omics correlations, patient subtypes

Step 6: Pathway Integration (gene-enrichment)
→ Input: Multi-omics gene lists
→ Output: Dysregulated pathways across omics

Step 7: Therapeutic Discovery (drug-repurposing)
→ Input: Target pathways + disease
→ Output: Drug candidates

Final Output: Comprehensive disease characterization with molecular
mechanisms across omics layers and therapeutic opportunities
```

#### Workflow 4: Protein Function to Drug Design

**Trigger words**: "design inhibitor", "therapeutic protein", "target to drug", "structure-based design"

**Pipeline**:
```
User provides: Target protein name

Step 1: Target Research (target-research)
→ Input: Protein name
→ Output: Function, pathways, disease relevance

Step 2: Structure Retrieval (protein-structure-retrieval)
→ Input: Protein name/UniProt ID
→ Output: PDB structures, AlphaFold model

Step 3: Binding Site Analysis (protein-interactions)
→ Input: Structure + known interactors
→ Output: Binding sites, functional residues

Step 4: Virtual Screening (binder-discovery)
→ Input: Target structure + binding site
→ Output: Hit compounds from screening

Step 5: ADMET Prediction (chemical-safety)
→ Input: Hit compounds
→ Output: Toxicity, bioavailability predictions

Step 6: Literature Validation (literature-deep-research)
→ Input: Target + hit compounds
→ Output: Published evidence, similar approaches

Final Output: Drug design report with validated target, binding sites,
screened compounds, ADMET profiles, and literature support
```

#### Workflow 5: Single-Cell to Cell Communication to Therapeutics

**Trigger words**: "single-cell", "cell-cell communication", "tumor microenvironment", "ligand-receptor"

**Pipeline**:
```
User provides: Single-cell RNA-seq data

Step 1: Cell Type Identification (single-cell)
→ Input: scRNA-seq AnnData
→ Output: Clusters, cell type annotations, marker genes

Step 2: Cell Communication Analysis (single-cell Phase 10)
→ Input: Annotated AnnData + cell types
→ Output: Ligand-receptor interactions, cell-type pairs

Step 3: Target Validation (target-research)
→ Input: Key ligands/receptors from Step 2
→ Output: Druggability, clinical relevance

Step 4: Drug Repurposing (drug-repurposing)
→ Input: Communication targets
→ Output: Drugs targeting L-R pairs

Step 5: Clinical Trials (clinical trials search via ToolUniverse)
→ Input: Drug candidates + indication
→ Output: Ongoing trials, evidence

Final Output: Cell communication map with therapeutic opportunities
targeting specific cell-cell interactions
```

#### Workflow 6: Structural Variant to Clinical Report

**Trigger words**: "CNV", "deletion", "duplication", "structural variant", "SV interpretation"

**Pipeline**:
```
User provides: SV/CNV VCF or coordinates

Step 1: SV Annotation (variant-analysis Phase 7)
→ Input: SV VCF or coordinates
→ Output: Population frequencies, affected genes

Step 2: Dosage Sensitivity (via ClinGen tools in variant-analysis)
→ Input: Affected genes
→ Output: Haploinsufficiency/triplosensitivity scores

Step 3: Gene Function (target-research)
→ Input: Dosage-sensitive genes
→ Output: Gene function, disease associations

Step 4: Clinical Interpretation
→ Input: All evidence from Steps 1-3
→ Output: ACMG/ClinGen classification

Step 5: Literature Evidence (literature-deep-research)
→ Input: Genes + phenotype
→ Output: Case reports, published CNVs

Final Output: Clinical SV report with pathogenicity assessment,
gene dosage effects, and evidence-based recommendations
```

### Workflow Execution Pattern

When you detect a workflow request:

1. **Identify the workflow** - Match keywords to pre-defined templates
2. **Confirm with user** (if ambiguous) - Ask which workflow they want
3. **Execute sequentially** - Run each skill in order, passing data forward
4. **Track intermediate results** - Store outputs from each step
5. **Generate unified report** - Synthesize all findings into coherent narrative

### Data Passing Between Skills

**Pattern**: Extract relevant data from each skill's output and pass to next skill.

```python
# Example: GWAS to Drug workflow

# Step 1: Get genes from GWAS
gwas_result = Skill("tooluniverse-gwas-trait-to-gene", "hypertension")
genes = extract_gene_list(gwas_result)  # ['AGT', 'ACE', 'NOS3', ...]

# Step 2: Research top genes (pass gene list)
target_info = {}
for gene in genes[:5]:
    result = Skill("tooluniverse-target-research", gene)
    target_info[gene] = result

# Step 3: Pathway enrichment (pass gene list)
pathways = Skill("tooluniverse-gene-enrichment",
                 f"genes={','.join(genes)}")
top_pathways = extract_top_pathways(pathways)

# Step 4: Drug repurposing (pass genes + pathways)
drugs = Skill("tooluniverse-drug-repurposing",
              f"targets={','.join(genes[:5])} pathways={','.join(top_pathways)}")

# Final: Synthesize report
report = generate_unified_report(genes, target_info, pathways, drugs)
```

### Parallel Execution in Workflows

When steps are independent, execute in parallel:

```python
# Steps that can run in parallel:

# After getting gene list from GWAS, these are independent:
parallel_results = run_in_parallel([
    Skill("tooluniverse-target-research", genes[0]),  # Gene 1
    Skill("tooluniverse-target-research", genes[1]),  # Gene 2
    Skill("tooluniverse-target-research", genes[2]),  # Gene 3
    Skill("tooluniverse-expression-data-retrieval", "tissue expression"),
    Skill("tooluniverse-literature-deep-research", "gene function")
])

# Then continue with steps that depend on these results
```

### Error Handling in Workflows

If a step fails, implement graceful degradation:

1. **Log the failure** - Document which step failed
2. **Try alternative** - Use backup skill or tool if available
3. **Continue if possible** - Skip failed step if not critical
4. **Inform user** - Note limitations in final report

```python
# Example error handling
try:
    expression_data = Skill("tooluniverse-expression-data-retrieval", genes)
except SkillError:
    # Fallback: Use GTEx tools directly
    expression_data = fallback_gtex_query(genes)
    # Note in report: "Expression data from GTEx API (skill unavailable)"
```

### Workflow Customization

Allow users to customize workflows:

```python
# User: "Run GWAS to drug workflow, but skip pathway enrichment"

# Modified workflow execution:
execute_workflow("gwas_to_drug", exclude_steps=["pathway_enrichment"])
```

### When NOT to Use Workflows

Single-skill tasks should use direct routing:
- ❌ "Research BRCA1" → Don't use workflow, just call target-research
- ❌ "Analyze this VCF" → Don't use workflow, just call variant-analysis
- ✅ "From GWAS to drugs" → Use workflow (multi-step)
- ✅ "Comprehensive multi-omics analysis" → Use workflow (complex)

### Workflow Success Criteria

A successful workflow execution includes:
- ✅ All critical steps completed
- ✅ Data passed correctly between steps
- ✅ Intermediate results documented
- ✅ Unified final report generated
- ✅ Clear narrative connecting all steps
- ✅ Actionable conclusions provided

---

## Workflow Orchestration Summary

| Workflow | Skills Used | Output |
|----------|-------------|--------|
| **GWAS to Therapeutics** | variant-analysis, target-research, gene-enrichment, drug-repurposing | Gene-to-drug report |
| **Variant to Clinical** | variant-analysis, variant-interpretation, precision-oncology, pharmacovigilance | Clinical action report |
| **Multi-Omics Disease** | disease-research, rnaseq-deseq2, epigenomics, variant-analysis, multi-omics-integration, gene-enrichment, drug-repurposing | Comprehensive molecular profile |
| **Protein to Drug** | target-research, protein-structure-retrieval, binder-discovery, chemical-safety, literature-deep-research | Drug design report |
| **Single-Cell Communication** | single-cell, target-research, drug-repurposing | Cell communication + therapeutics |
| **SV Clinical Report** | variant-analysis (Phase 7), target-research, literature-deep-research | SV pathogenicity report |

**THE KEY**: Recognize multi-step requests and execute workflows automatically, passing data between skills to create comprehensive end-to-end analyses.
