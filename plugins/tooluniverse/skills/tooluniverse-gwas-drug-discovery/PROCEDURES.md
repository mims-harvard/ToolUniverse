# GWAS-to-Drug Discovery: Detailed Procedures

## Workflow Step Details

### Step 1: GWAS Gene Discovery

**Input**: Disease/trait name (e.g., "type 2 diabetes", "Alzheimer disease")

**Process**:
- Query GWAS Catalog for associations
- Filter by significance threshold (p < 5x10^-8)
- Map variants to genes (nearest, eQTL, fine-mapping)
- Aggregate evidence across studies

**Output**: List of genes with genetic support

### Step 2: Druggability Assessment

**Input**: Gene list from Step 1

**Process**:
- Check target class (GPCR, kinase, ion channel, etc.)
- Assess tractability (antibody, small molecule)
- Evaluate safety (expression profile, essentiality)
- Check for tool compounds or crystal structures

**Output**: Druggability score (0-1) + modality recommendations

**Scoring Formula**:
```
Target Score = (GWAS Score x 0.4) + (Druggability x 0.3) + (Clinical Evidence x 0.2) + (Novelty x 0.1)
```

### Step 3: Target Prioritization

**Input**: Genes with GWAS + druggability data

**Process**:
- Calculate composite score: genetic evidence x druggability
- Rank targets by score
- Add qualitative factors (novelty, competitive landscape)
- Generate target dossiers

### Step 4: Existing Drug Search

**Input**: Prioritized target list

**Process**:
- Search drug-target associations (ChEMBL, DGIdb)
- Find approved drugs, clinical candidates, tool compounds
- Get mechanism of action, indication, phase
- Check for off-label use or failed trials

### Step 5: Clinical Evidence

**Input**: Drug candidates

**Process**:
- Check clinical trial history (ClinicalTrials.gov)
- Review safety profile (FDA labels, adverse events)
- Assess pharmacology (PK/PD, formulation)
- Evaluate regulatory path

### Step 6: Repurposing Opportunities

**Input**: Approved drugs + new disease associations

**Process**:
- Match drug targets to new disease genes
- Assess mechanistic fit (agonist vs antagonist)
- Check contraindications
- Estimate repurposing probability

**Repurposing Score**:
- Genetic overlap: Gene targeted by drug = gene implicated in new disease
- Clinical feasibility: Dosing, route, safety profile compatible
- Regulatory path: Faster approval (Phase II vs Phase I)

## Use Cases

### Use Case 1: Novel Target Discovery for Rare Disease

**Scenario**: Identify druggable targets for Huntington's disease

**Steps**:
1. Get GWAS hits for Huntington's -> HTT, PDE10A, MSH3
2. Assess druggability -> PDE10A (phosphodiesterase) = high
3. Find existing PDE10A inhibitors -> Multiple tool compounds
4. Recommendation: Develop selective PDE10A inhibitor

**Clinical Context**:
- HTT (huntingtin) = difficult to drug (large, scaffold protein)
- PDE10A = modifier gene, GPCR-coupled, small molecule tractable
- Precedent: PDE5 inhibitors (sildenafil) already approved

### Use Case 2: Drug Repurposing for Common Disease

**Scenario**: Find repurposing opportunities for Alzheimer's disease

**Steps**:
1. Get GWAS targets -> APOE, CLU, CR1, PICALM, BIN1, TREM2
2. Find drugs targeting these -> Anti-inflammatory drugs (CR1, TREM2)
3. Match approved drugs -> Anakinra (IL-1R antagonist)
4. Rationale: TREM2 links inflammation to neurodegeneration

**Example Output**:
```
Repurposing Candidate: Anakinra
- Target: IL-1R -> affects TREM2 pathway
- Current use: Rheumatoid arthritis (approved)
- AD rationale: 3 GWAS genes in immune pathway
- Clinical phase: Phase II trial in progress
- Safety: Known profile, subcutaneous injection
```

### Use Case 3: Target Validation for Existing Drug Class

**Scenario**: Validate new diabetes targets related to GLP-1 pathway

**Steps**:
1. Get T2D GWAS genes -> TCF7L2, PPARG, KCNJ11, GLP1R
2. GLP1R validated -> Existing drug class (semaglutide, liraglutide)
3. Check related genes -> GIP, GIPR (glucose-dependent insulinotropic polypeptide)
4. Outcome: Dual GLP-1/GIP agonists (tirzepatide, approved 2022)

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

**Small Molecules**: Intracellular proteins, enzymes; oral bioavailability, CNS penetration
**Antibodies**: Extracellular proteins, receptors; high specificity, long half-life; no CNS
**Antisense/RNAi**: mRNA (any gene); sequence-specific; delivery challenges, liver-centric
**Gene Therapy**: Genetic defects; one-time treatment; immunogenicity concerns
