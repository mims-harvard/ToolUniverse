# Protein Interaction Network Analysis - Domain Analysis

**Date**: 2026-02-12
**Phase**: 1 - Domain Analysis

---

## Skill Overview

**Purpose**: Analyze protein interaction networks to understand biological systems, identify key regulatory proteins, and discover functional relationships.

**Target Users**:
- Systems biologists studying protein networks
- Drug discovery researchers identifying drug targets
- Computational biologists analyzing omics data
- Researchers investigating disease mechanisms

---

## Concrete Use Cases

### Use Case 1: Single Protein Analysis
**Query**: "What proteins interact with TP53?"
**Expected Workflow**:
1. Map "TP53" to protein identifier (STRING ID)
2. Retrieve direct interaction partners (BioGRID + STRING)
3. Get functional enrichment (pathways, GO terms)
4. Generate network report with interaction confidence scores

**Expected Output**:
- List of interacting proteins with confidence scores
- Pathways enriched in the network
- GO terms associated with interactions
- Network visualization data

### Use Case 2: Multi-Protein Network
**Query**: "Analyze the interaction network for TP53, MDM2, ATM"
**Expected Workflow**:
1. Map all protein names to identifiers
2. Retrieve pairwise interactions between proteins
3. Build complete interaction network
4. Identify hubs and key regulators
5. Perform functional enrichment analysis

**Expected Output**:
- Complete interaction network (nodes + edges)
- Network statistics (degree, betweenness, clustering)
- Enriched pathways and biological processes
- Key regulatory proteins identified

### Use Case 3: Disease Pathway Analysis
**Query**: "Find protein interactions involved in DNA damage response"
**Expected Workflow**:
1. Search BioGRID by keyword "DNA damage response"
2. Retrieve interactions from published studies
3. Map proteins to functional categories
4. Analyze pathway enrichment
5. Identify potential drug targets

**Expected Output**:
- Proteins involved in DNA damage response
- Key interaction pairs with evidence
- Pathway maps and GO terms
- PubMed citations for interactions

### Use Case 4: Chemical-Protein Interactions
**Query**: "What proteins interact with Cisplatin?"
**Expected Workflow**:
1. Search BioGRID for chemical interactions
2. Retrieve protein targets of Cisplatin
3. Analyze functional consequences
4. Identify resistance mechanisms

**Expected Output**:
- Direct protein targets
- Interaction types (binding, modification)
- Cellular pathways affected
- Literature evidence

### Use Case 5: Post-Translational Modifications
**Query**: "What phosphorylation sites are found on TP53?"
**Expected Workflow**:
1. Query BioGRID PTM database for TP53
2. Retrieve phosphorylation sites and kinases
3. Analyze functional impact
4. Get literature references

**Expected Output**:
- List of PTM sites with positions
- Kinases that phosphorylate each site
- Functional consequences
- Evidence codes and citations

---

## 4-Phase Analysis Pipeline

### Phase 1: Protein Identification & Mapping
**Goal**: Convert gene names to standardized protein identifiers

**Tools**:
- `STRING_map_identifiers` - Map gene names to STRING IDs
- Validation: Check if proteins exist in databases

**Input**: List of protein names (e.g., ["TP53", "MDM2", "ATM"])
**Output**: Mapped protein IDs with species confirmation

### Phase 2: Interaction Network Retrieval
**Goal**: Get protein-protein interactions from multiple databases

**Tools**:
- `BioGRID_get_interactions` - Get experimentally validated interactions
- `STRING_get_network` - Get functional association network
- `STRING_get_interaction_partners` - Get partners for single protein
- `STRING_get_protein_interactions` - Alternative interaction retrieval

**Input**: Protein IDs from Phase 1
**Output**: Interaction network with confidence scores

### Phase 3: Functional Enrichment Analysis
**Goal**: Identify biological processes and pathways

**Tools**:
- `STRING_functional_enrichment` - Pathway/GO enrichment
- `STRING_ppi_enrichment` - PPI enrichment analysis

**Input**: Network proteins from Phase 2
**Output**: Enriched pathways, GO terms, statistical significance

### Phase 4: Special Analyses (Optional)
**Goal**: Additional analyses based on user needs

**Tools**:
- `BioGRID_search_by_pubmed` - Find interactions from specific studies
- `BioGRID_get_chemical_interactions` - Chemical-protein interactions
- `BioGRID_get_ptms` - Post-translational modifications
- `SASBDB_*` - Structural data (if needed)

**Input**: Specific query parameters
**Output**: Specialized analysis results

---

## Database Specifications

### BioGRID (Biological General Repository for Interaction Datasets)
- **Coverage**: 2.3M+ interactions, 80+ organisms
- **Data Type**: Experimentally validated interactions
- **Evidence**: Curated from literature with methods
- **API**: Requires API key (BIOGRID_API_KEY)

**Tools (4)**:
1. `BioGRID_get_interactions` - Get PPI for protein
2. `BioGRID_get_chemical_interactions` - Chemical-protein interactions
3. `BioGRID_get_ptms` - Post-translational modifications
4. `BioGRID_search_by_pubmed` - Find interactions by PubMed ID

### STRING (Search Tool for Retrieval of Interacting Genes/Proteins)
- **Coverage**: 14M+ proteins, 5,000+ organisms
- **Data Type**: Functional associations (experimental + predicted)
- **Confidence**: Scores from 0-1000 (combined evidence)
- **API**: Public, no key required (rate limits apply)

**Tools (6 actual STRING tools)**:
1. `STRING_map_identifiers` - Map names to STRING IDs
2. `STRING_get_network` - Get interaction network
3. `STRING_get_interaction_partners` - Get partners for protein
4. `STRING_get_protein_interactions` - Alternative interaction retrieval
5. `STRING_functional_enrichment` - Pathway/GO enrichment
6. `STRING_ppi_enrichment` - PPI enrichment statistics

### SASBDB (Small Angle Scattering Biological Data Bank)
- **Coverage**: 2,000+ entries
- **Data Type**: Structural biology (SAXS/SANS)
- **Use Case**: Protein structure and complex formation
- **API**: Public REST API

**Tools (5)** - Use for structural analysis:
1. `SASBDB_search_entries` - Find structural data
2. `SASBDB_get_entry_data` - Get entry metadata
3. `SASBDB_get_models` - Get structural models
4. `SASBDB_get_scattering_profile` - Get scattering data
5. `SASBDB_download_data` - Download raw data

---

## Example Workflows

### Workflow 1: Cancer Protein Network (TP53)
```
Input: protein = "TP53", organism = "Homo sapiens"

Phase 1: Map identifiers
  STRING_map_identifiers("TP53") → "9606.ENSP00000269305"

Phase 2: Get interactions
  BioGRID_get_interactions("TP53") → 450 interactions
  STRING_get_interaction_partners("9606.ENSP00000269305") → 85 high-confidence partners

Phase 3: Functional enrichment
  STRING_functional_enrichment([TP53 + partners]) → DNA repair, apoptosis, cell cycle

Phase 4: PTM analysis
  BioGRID_get_ptms("TP53") → 20 phosphorylation sites

Output: comprehensive_tp53_network.md
```

### Workflow 2: Multi-Protein Complex (DNA Damage Response)
```
Input: proteins = ["TP53", "ATM", "ATR", "CHEK2"], organism = "Homo sapiens"

Phase 1: Map all identifiers
  STRING_map_identifiers([...]) → 4 STRING IDs

Phase 2: Get complete network
  STRING_get_network([4 proteins], add_neighbors=10) → Network with 50 proteins
  BioGRID_get_interactions for each → 1200 total interactions

Phase 3: Enrichment analysis
  STRING_functional_enrichment([50 proteins]) → DNA damage response pathways

Phase 4: Literature evidence
  BioGRID_search_by_pubmed("DNA damage") → Key papers

Output: dna_damage_network.md
```

### Workflow 3: Drug Target Analysis (Cisplatin)
```
Input: chemical = "Cisplatin", organism = "Homo sapiens"

Phase 1: Skip (chemical query)

Phase 2: Chemical-protein interactions
  BioGRID_get_chemical_interactions("Cisplatin") → 15 target proteins

Phase 3: Analyze target network
  STRING_get_network([15 targets]) → Extended network
  STRING_functional_enrichment([targets]) → DNA repair, apoptosis

Phase 4: Structural data
  SASBDB_search_entries("cisplatin protein") → Structural complexes

Output: cisplatin_targets.md
```

---

## Input Parameters

### Core Parameters
- **protein_list** (list of strings): Gene names or protein IDs
  - Examples: `["TP53"]`, `["TP53", "MDM2", "ATM"]`
  - Optional for chemical/PTM queries

- **organism** (string): Scientific name or taxonomy ID
  - Default: `"Homo sapiens"` (9606)
  - Examples: `"Mus musculus"`, `"10090"`

- **network_type** (string): Type of interactions to retrieve
  - Default: `"physical"` (BioGRID), `"functional"` (STRING)
  - Options: `"physical"`, `"functional"`, `"both"`

### Optional Parameters
- **add_neighbors** (int): Add N interaction partners to expand network
  - Default: `0` (only input proteins)
  - Range: `0-50`

- **confidence_threshold** (float): Minimum interaction confidence (STRING)
  - Default: `0.4` (medium confidence)
  - Range: `0.0-1.0`

- **pubmed_id** (string): Filter by specific PubMed ID (BioGRID)
  - Example: `"12345678"`

- **chemical_name** (string): For chemical-protein interaction queries
  - Example: `"Cisplatin"`

- **include_ptms** (bool): Include PTM analysis
  - Default: `False`

- **output_file** (string): Output markdown file path
  - Default: Auto-generated with timestamp

---

## Expected Report Structure

```markdown
# Protein Interaction Network Analysis Report

## 1. Protein Identification
- TP53 → 9606.ENSP00000269305 (Homo sapiens)
- MDM2 → 9606.ENSP00000258149 (Homo sapiens)
- Status: 2/2 proteins mapped successfully

## 2. Interaction Network
### BioGRID Interactions (450 total)
- TP53 - MDM2: Physical interaction (Co-IP, Y2H)
- TP53 - ATM: Physical interaction (Western blot)
- [Full list...]

### STRING Network (85 high-confidence)
- TP53 - TP73: 0.912 (experimental + database)
- TP53 - MDM2: 0.999 (experimental evidence)
- [Full list...]

### Network Statistics
- Total proteins: 87
- Total interactions: 535
- Average degree: 12.3
- Network density: 0.142

## 3. Functional Enrichment
### KEGG Pathways
- p53 signaling pathway (FDR: 1.2e-45)
- Cell cycle (FDR: 3.4e-32)
- Apoptosis (FDR: 5.6e-28)

### GO Biological Process
- DNA damage response (FDR: 2.1e-52)
- Regulation of apoptosis (FDR: 4.3e-40)
- Cell cycle checkpoint (FDR: 8.7e-35)

## 4. Post-Translational Modifications (TP53)
- S15: Phosphorylation by ATM, ATR (DNA damage response)
- S20: Phosphorylation by CHEK2 (p53 stabilization)
- [Full list...]

## 5. Key Hub Proteins
1. TP53 (degree: 450) - Tumor suppressor
2. MDM2 (degree: 234) - p53 regulator
3. ATM (degree: 187) - DNA damage sensor

## 6. Literature Evidence
- BioGRID entries: 450 interactions from 320 publications
- Oldest: 1991, Newest: 2025
- Top journals: Nature, Cell, Science, PNAS
```

---

## Success Criteria

### Phase 1 Complete When:
- ✅ Domain analysis documented with concrete examples
- ✅ All use cases defined with expected inputs/outputs
- ✅ Tool inventory complete (17 tools identified)
- ✅ 4-phase workflow clearly specified
- ✅ Report structure defined

### Next Phase (Phase 2: Tool Testing)
**CRITICAL**: Test ALL tools BEFORE writing documentation
- Create `test_protein_tools.py`
- Test BioGRID tools (4)
- Test STRING tools (6)
- Test SASBDB tools (5)
- Document actual API responses
- Identify SOAP vs REST tools
- Record parameter names and response formats

---

## Notes & Considerations

### API Key Requirements
- **BioGRID**: Requires BIOGRID_API_KEY (may need to request)
- **STRING**: Public API (no key required, rate limits apply)
- **SASBDB**: Public API (no key required)

### Potential Challenges
1. **BioGRID API Key**: Need to check if key is available
2. **Species Mapping**: STRING uses taxonomy IDs, need conversion
3. **Network Size**: Large networks may be slow to retrieve
4. **Confidence Thresholds**: STRING and BioGRID use different scoring

### Fallback Strategies
- **Primary**: BioGRID (experimental) + STRING (functional)
- **Fallback 1**: STRING only (if BioGRID key unavailable)
- **Fallback 2**: Basic network without enrichment (if enrichment fails)
- **Default**: Report what data is available, note limitations

---

## Comparison to Metabolomics Skill

### Similarities
- 4-phase pipeline structure
- Multi-database integration
- Progressive report writing
- Fallback strategies for missing data

### Differences
- **Metabolomics**: Small molecules (metabolites)
- **Protein Interactions**: Macromolecules (proteins)
- **Metabolomics**: 4 databases, 9 tools
- **Protein Interactions**: 3 databases, 17 tools
- **Metabolomics**: SOAP tools (HMDB)
- **Protein Interactions**: Need to verify (likely all REST)

### Lessons to Apply
1. ✅ Test tools BEFORE documentation (caught 3 bugs in Metabolomics)
2. ✅ Validate actual API response structures (don't assume)
3. ✅ Create tests that check data presence, not just keywords
4. ✅ Real-world testing with subagent before release
5. ✅ Document FIX comments for any parsing corrections

---

**Status**: ✅ Phase 1 Complete - Ready for Phase 2 (Tool Testing)
