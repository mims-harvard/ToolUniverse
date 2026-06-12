# Network Pharmacology - Use Patterns and Edge Cases

Common analysis patterns and strategies for handling edge cases.

---

## Common Use Patterns

### Pattern 1: Drug Repurposing via Network Proximity
```
Input: compound (metformin) + disease (Alzheimer disease)
Mode: compound-to-disease

Flow:
1. Resolve metformin -> CHEMBL1431, DB00331, CID:4091
2. Get metformin targets (OpenTargets, DrugBank, DGIdb)
3. Get Alzheimer disease genes (OpenTargets, GWAS)
4. Build PPI network (STRING, OpenTargets interactions)
5. Calculate proximity between drug targets and disease genes
6. Score and rank by Network Pharmacology Score
7. Predict mechanism via shared pathways
8. Validate with clinical trials and literature
```

### Pattern 2: Disease-Driven Drug Discovery
```
Input: disease (lupus)
Mode: disease-to-compound

Flow:
1. Resolve lupus -> MONDO/EFO ID
2. Get disease-associated targets (top 50)
3. For each target, find approved drugs (OpenTargets, DGIdb, DrugBank)
4. Build C-T-D network from all drug-target-disease edges
5. Rank drugs by: number of disease targets hit, network proximity, safety
6. Identify polypharmacology advantages (drugs hitting multiple disease targets)
```

### Pattern 3: Target-Centric Network
```
Input: target (EGFR)
Mode: target-centric

Flow:
1. Resolve EGFR -> ENSG00000146648
2. Get all compounds targeting EGFR (with bioactivity)
3. Get all diseases associated with EGFR
4. Build PPI network around EGFR
5. Identify which compounds could bridge to which diseases
6. Rank compound-disease pairs by network metrics
```

### Pattern 4: Polypharmacology Profiling
```
Input: compound (aspirin)
Mode: bidirectional

Flow:
1. Resolve aspirin -> CHEMBL25
2. Get ALL targets (not just primary)
3. Map targets to disease modules
4. Identify multi-target coverage across diseases
5. Analyze synergistic vs antagonistic effects
6. Compare selectivity across target families
```

### Pattern 5: Mechanism Elucidation
```
Input: compound (rapamycin) + disease (aging/longevity)
Mode: compound-to-disease

Flow:
1. Resolve rapamycin -> CHEMBL413 (sirolimus)
2. Get mechanism: mTOR inhibitor
3. Map mTOR pathway to aging-related genes
4. Trace network paths: rapamycin -> mTOR -> autophagy -> aging genes
5. Assess pathway overlap and functional enrichment
6. Provide mechanistic explanation
```

---

## Edge Cases

### Promiscuous Compounds (many targets)
- Limit initial target retrieval to top 50 by confidence
- Classify into primary (mechanism) vs secondary (off-target)
- Focus network analysis on primary targets first
- Note polypharmacology implications

### Orphan Diseases (limited data)
- Expand to parent disease categories in ontology
- Use related diseases from OpenTargets similar entities
- Leverage pathway-level analysis over gene-level
- Note data limitations in report

### Novel Targets (no known drugs)
- Focus on target biology and disease association
- Use DGIdb druggability assessment
- Search for chemical probes (OpenTargets chemical probes)
- Suggest target-based screening approaches

### Large Networks (>100 nodes)
- Prioritize top-scored edges
- Use network modules rather than full network
- Focus on shortest paths between entities
- Summarize statistics rather than listing all nodes

### Disconnected Networks
- Report disconnection explicitly
- Analyze drug module and disease module separately
- Look for pathway-level connections as bridge
- Note that disconnection suggests low repurposing potential
