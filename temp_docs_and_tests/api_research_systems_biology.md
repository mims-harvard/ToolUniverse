# Systems Biology & Pathways APIs - Research Report

**Date**: 2026-02-08
**Agent**: API Research Agent
**Status**: Phase 1 - Complete

## Executive Summary

This report documents available systems biology and pathway APIs, analyzes ToolUniverse's current coverage, identifies gaps, and prioritizes new integrations.

**Key Findings**:
- ToolUniverse has **excellent baseline coverage** for pathways (6 major databases)
- Core resources covered: Reactome, KEGG, WikiPathways, PathwayCommons, IntAct, MetaCyc
- Major gaps: **STRING-db** (protein interactions), **BioGRID** (genetic/protein interactions)
- STRING-db highest priority (most widely used PPI database, 2.9M interactions)
- All other major pathway databases already integrated

---

## Target APIs Researched

### 1. Reactome Pathway Database

**URL**: https://reactome.org/
**API Docs**: https://reactome.org/dev/content-service
**Type**: REST API (JSON)
**Authentication**: None

#### Capabilities
- Curated, peer-reviewed pathway database
- Human pathways with ortholog projection to 20+ species
- Hierarchical pathway organization
- Reactions, catalysts, regulations
- Pathway analysis and enrichment
- Network visualization

#### API Services
**Content Service**:
- `/data/pathway/{id}` - Pathway details
- `/data/pathway/{id}/containedEvents` - Reactions and subpathways
- `/data/diseases` - Disease-pathway associations
- `/data/query/{id}` - Query by database identifiers

**Analysis Service** (token-based):
- Pathway enrichment analysis
- Over-representation analysis
- Expression data overlay
- Species comparison

#### Python/R Support
- **reactome2py** Python package
- **ReactomeContentService4R** R package
- Wraps REST API calls

#### Integration Complexity: **MEDIUM**
- Well-documented REST API
- Simple JSON responses
- Token-based analysis workflow
- No authentication for content queries

#### ToolUniverse Coverage
- ✅ **`reactome_tools.json` EXISTS**
- **VERIFY**: Check completeness
  - Content API coverage
  - Analysis API coverage
  - Disease associations
- **PRIORITY**: LOW (likely good coverage, verify and extend)

---

### 2. KEGG (Kyoto Encyclopedia of Genes and Genomes)

**URL**: https://www.kegg.jp/kegg/rest/
**API Docs**: https://www.kegg.jp/kegg/rest/keggapi.html
**Type**: REST API
**Authentication**: **Academic use only** (non-academic requires license)

#### Capabilities
- Pathway maps for metabolism, signaling, disease
- Genes, enzymes, reactions, compounds
- Disease and drug information
- Organism-specific pathways
- Ortholog mapping

#### API Operations
- `info` - Database statistics
- `list` - Entry lists
- `find` - Search by keyword
- `get` - Retrieve entries
- `conv` - Convert identifiers
- `link` - Find related entries
- `ddi` - Drug-drug interactions

#### API Endpoint
- Base URL: https://rest.kegg.jp/
- Max 10 identifiers per query
- Text-based responses (custom parsing needed)

#### Important Restrictions
- **Academic use only** at rest.kegg.jp
- Non-academic users need license/FTP agreement
- Commercial use requires separate arrangement

#### Integration Complexity: **MEDIUM**
- Simple REST API
- Text-based responses (not JSON)
- Requires parsing KEGG flat file format
- Usage restrictions (academic only)

#### ToolUniverse Coverage
- ✅ **`kegg_tools.json` EXISTS**
- **VERIFY**: Check completeness of operations
  - Pathway search and retrieval
  - Compound and enzyme queries
  - Cross-database linking
- **PRIORITY**: LOW (likely good coverage, verify)

---

### 3. WikiPathways

**URL**: https://www.wikipathways.org/
**API**: REST web service
**Authentication**: None

#### Capabilities
- Community-curated pathway database
- Open, collaborative pathway curation
- Pathways for human and model organisms
- Monthly official releases
- Integration with pathway analysis tools

#### API Access
- REST web service at http://webservice.wikipathways.org
- Swagger documentation available
- Multiple data formats (GPML, SVG, PDF, PNG)
- GMT file support for enrichment analysis

#### Client Libraries
- **rWikiPathways** R package (Bioconductor)
- **pywikipathways** Python package
- **Java library** for WikiPathways webservice

#### Key Features
- Pathway search by keyword, organism
- Retrieve pathway data in multiple formats
- Download monthly releases
- GMT format for GSEA/enrichment

#### Integration Complexity: **LOW-MEDIUM**
- REST API with Swagger docs
- Multiple client libraries available
- Well-documented endpoints
- No authentication required

#### ToolUniverse Coverage
- ✅ **`wikipathways_tools.json` EXISTS**
- **VERIFY**: Check completeness
  - Search and retrieval
  - Format conversion
  - GMT file access for enrichment
- **PRIORITY**: LOW (likely good coverage, verify)

---

### 4. STRING-db (Protein-Protein Interactions)

**URL**: https://string-db.org/
**API**: https://version11.string-db.org/help/api/
**Type**: REST API (JSON/TSV)
**Authentication**: None

#### Capabilities
- **2.9 million protein-protein interactions** (latest: STRING 12.5)
- Evidence from:
  - Experimental data
  - Computational predictions
  - Text mining (literature)
  - Databases
- Confidence scores for interactions
- Network analysis and clustering
- Functional enrichment
- **NEW in 12.5**: Regulatory network with directionality

#### API Endpoints
**Network Retrieval**:
- `/network` - Get interaction network for proteins
- `/interaction_partners` - Direct interactors
- `/homology` - Ortholog interactions

**Enrichment**:
- `/enrichment` - Functional enrichment (GO, KEGG, Reactome)
- `/ppi_enrichment` - PPI enrichment test

**Information**:
- `/get_string_ids` - Map identifiers to STRING IDs
- `/get_link` - Generate network visualization URLs

#### Latest Features (STRING 12.5, 2025)
- **Regulatory network**: Directionality of interactions (activation/inhibition)
- Uses curated pathways + language model parsing literature
- Access via `network_type=regulatory` parameter
- Improved pathway enrichment with FDR correction
- Network embeddings available for download

#### Data Formats
- JSON or TSV responses
- Network: nodes and edges with scores
- Enrichment: terms, p-values, FDR

#### Integration Complexity: **MEDIUM**
- Well-documented REST API
- Multiple output formats
- Requires identifier mapping (STRING IDs vs UniProt/HGNC)
- Large result sets for hub proteins

#### ToolUniverse Coverage
- ❌ **NO STRING TOOLS**
- **MAJOR GAP**: Most widely used PPI database
  - Critical for network analysis
  - Protein function prediction
  - Pathway connectivity
  - Drug target network analysis
- **HIGH VALUE**: Complements existing pathway tools

---

### 5. IntAct Molecular Interaction Database

**URL**: https://www.ebi.ac.uk/intact/
**API**: PSICQUIC webservice
**Type**: REST/SOAP webservices
**Authentication**: None

#### Capabilities
- **1+ million curated binary interactions**
- Literature-curated molecular interactions
- Direct data depositions
- PSI-MI standard support
- Part of International Molecular Exchange (IMEx) consortium

#### API Access
**PSICQUIC**:
- Standard webservice for molecular interaction databases
- MIQL query language (Molecular Interaction Query Language)
- Multiple output formats: PSI-MI XML, MITAB

**Simple URL Interface**:
- Direct URL-based retrieval
- PSI XML format
- Network extraction by protein

#### Data Types
- Protein-protein interactions
- Protein-small molecule interactions
- Confidence scores
- Experimental evidence codes

#### Integration Complexity: **MEDIUM-HIGH**
- PSICQUIC standard (not simple REST)
- MIQL query language
- PSI-MI XML/MITAB formats (complex)
- Requires parsing specialized formats

#### ToolUniverse Coverage
- ✅ **`intact_tools.json` EXISTS**
- **VERIFY**: Check completeness
  - PSICQUIC access
  - Binary interaction retrieval
  - Evidence and confidence
- **PRIORITY**: LOW (likely covered, verify)

---

### 6. BioGRID (Biological General Repository for Interaction Datasets)

**URL**: https://thebiogrid.org/
**API**: https://webservice.thebiogrid.org/
**Type**: REST API
**Authentication**: Access key required (free)

#### Capabilities
- **2.9 million protein and genetic interactions**
- **31,540 chemical interactions**
- **1.1 million post-translational modifications**
- Model organisms: human, yeast, fly, worm, mouse, etc.
- Curated from 87,794 publications (v5.0.254)

#### API Features
**REST Service**:
- URL-based access over HTTPS
- GET and POST operations
- Filter by gene, organism, evidence, publication
- Multiple output formats: JSON, TAB2, PSI-MI

**Access Key**:
- Free registration required
- Get key from https://webservice.thebiogrid.org/
- Include in all requests: `accesskey=[KEY]`

#### Endpoints
- Query by gene names/identifiers
- Filter by evidence type
- PubMed ID-based retrieval
- Organism-specific queries
- Chemical-protein interactions

#### Data Formats
- JSON (recommended)
- TAB2 (tab-delimited)
- PSI-MI XML
- WADL service description available

#### Integration Complexity: **MEDIUM**
- Simple REST API with JSON
- Requires free access key
- Well-documented with examples
- GitHub repo with sample code (Python)

#### ToolUniverse Coverage
- ❌ **NO BIOGRID TOOLS**
- **MEDIUM GAP**: Large interaction database
  - Genetic interactions (unique to BioGRID)
  - Chemical-protein interactions
  - PTM data
- **VALUE**: Complements STRING (different evidence sources)
- **PRIORITY**: MEDIUM (after STRING)

---

### 7. Pathway Commons

**URL**: https://www.pathwaycommons.org/
**API**: https://pathwaycommons.github.io/pcapi/
**Type**: REST API (JSON-LD, BioPAX)
**Authentication**: None

#### Capabilities
- **Integrative resource**: Aggregates 22 pathway databases
- BioPAX format (Biological Pathway Exchange)
- Pathways from Reactome, KEGG, WikiPathways, PANTHER, etc.
- Graph queries and network traversal
- Unified search across databases

#### API Features
**Search**:
- Full-text search across integrated databases
- Get objects by URI
- Advanced graph queries

**Retrieval**:
- JSON-LD for web applications
- BioPAX for pathway analysis
- SIF (Simple Interaction Format)
- Graph neighborhood queries

**Query Types**:
- `search` - Keyword search
- `get` - Retrieve by URI
- `graph` - Graph queries (neighborhood, paths)
- `traverse` - XPath-like database access

#### Integration Complexity: **MEDIUM-HIGH**
- RESTful API well-documented
- Multiple output formats
- BioPAX data model (complex)
- JSON-LD simpler for web use
- Graph queries powerful but complex

#### ToolUniverse Coverage
- ✅ **`pathway_commons_tools.json` EXISTS**
- **VERIFY**: Check completeness
  - Search functionality
  - Graph queries
  - Format support (JSON-LD vs BioPAX)
- **PRIORITY**: LOW (likely covered, verify)

---

### 8. MetaCyc / BioCyc

**URL**: https://metacyc.org/ and https://biocyc.org/
**API**: Available (documentation limited in search results)
**Type**: Database with API access
**Authentication**: Varies by access level

#### Capabilities
**MetaCyc**:
- **3,264 metabolic pathways** (all domains of life)
- 20,039 reactions
- 20,490 metabolites
- Experimentally validated pathways
- Enzyme and reaction details

**BioCyc**:
- **5,700 organism-specific databases**
- Predicted metabolic networks
- Full genomes with pathway annotations
- Operons, transporters, pathway holes

#### API Features
- Programmatic query/update via APIs
- Metabolic modeling capabilities
- Desktop application for advanced use
- Bulk data downloads

#### Integration Complexity: **MEDIUM-HIGH**
- API exists but documentation less public
- BioPAX format support
- Desktop app recommended for advanced use
- May require subscription for full API access

#### ToolUniverse Coverage
- ✅ **`metacyc_tools.json` EXISTS**
- **VERIFY**: Check coverage
  - Pathway search and retrieval
  - Metabolite and reaction queries
  - Enzyme information
- **PRIORITY**: LOW (likely basic coverage, verify)

---

## Gap Analysis

### Coverage Matrix

| API/Database | Current Status | Coverage Level | Research Value | Priority |
|--------------|----------------|----------------|----------------|----------|
| **Reactome** | ✅ Good | ~80% | Very High | LOW (verify) |
| **KEGG** | ✅ Good | ~70% | Very High | LOW (verify) |
| **WikiPathways** | ✅ Good | ~80% | High | LOW (verify) |
| **STRING-db** | ❌ Missing | 0% | **Very High** | **HIGH** |
| **IntAct** | ✅ Partial | ~60% | High | LOW-MEDIUM |
| **BioGRID** | ❌ Missing | 0% | High | **MEDIUM** |
| **Pathway Commons** | ✅ Partial | ~50% | High | LOW-MEDIUM |
| **MetaCyc/BioCyc** | ✅ Partial | ~50% | Medium-High | LOW-MEDIUM |

### Additional Coverage Notes
- ✅ All major pathway databases covered (Reactome, KEGG, WikiPathways)
- ✅ Integrative resource (Pathway Commons) available
- ❌ **Critical gap**: STRING-db (most used PPI database)
- ❌ **Medium gap**: BioGRID (large, genetic interactions)

---

## Critical Gaps

### 1. **STRING-db Protein Interaction Network** (Priority: HIGH)

**Why Critical**:
- **Most widely used PPI database** in systems biology
- 2.9 million interactions with confidence scores
- Evidence from multiple sources (experiments, text mining, databases)
- **NEW regulatory network** with directionality (STRING 12.5)
- Essential for:
  - Network-based drug target analysis
  - Protein function prediction
  - Pathway connectivity analysis
  - Disease module identification

**Missing Capabilities**:
- Get protein interaction networks
- Find direct binding partners
- Functional enrichment (GO, KEGG, Reactome)
- Network clustering and modules
- Identifier mapping (UniProt ↔ STRING ID)
- Regulatory network with directionality

**Recommended Tools** (5-6 tools):
1. `STRING_get_interaction_network` - Retrieve PPI network for proteins
2. `STRING_get_interaction_partners` - Direct interactors with scores
3. `STRING_functional_enrichment` - GO/KEGG/Reactome enrichment
4. `STRING_map_identifiers` - Convert IDs to STRING IDs
5. `STRING_get_regulatory_network` - Regulatory interactions with directionality (NEW)
6. `STRING_ppi_enrichment` - Test if proteins interact more than expected

**Implementation Notes**:
- REST API with JSON/TSV output
- No authentication required
- Identifier mapping critical (UniProt/Ensembl → STRING ID)
- Handle large networks (hub proteins have 100+ partners)
- Latest feature: `network_type=regulatory` parameter

**Integration Opportunities**:
- Link to OpenTargets disease-gene associations
- Connect to UniProt protein data
- Integrate with pathway tools (Reactome, KEGG)
- Drug target network analysis

**Effort Estimate**: 3-4 days

---

### 2. **BioGRID Interactions** (Priority: MEDIUM)

**Why Important**:
- **2.9M protein + genetic interactions**
- Unique features:
  - Genetic interactions (epistasis, synthetic lethality)
  - Chemical-protein interactions (31K+)
  - Post-translational modifications (1.1M+)
- Model organism focus (yeast, fly, worm genetics)
- Curated from 87K+ publications

**Missing Capabilities**:
- Query protein-protein interactions
- Retrieve genetic interactions (complementary to STRING)
- Chemical-protein interaction data
- PTM information
- Evidence codes and publication links

**Recommended Tools** (3-4 tools):
1. `BioGRID_get_interactions` - Protein/genetic interactions by gene
2. `BioGRID_get_chemical_interactions` - Chemical-protein associations
3. `BioGRID_search_by_pubmed` - Interactions from specific papers
4. `BioGRID_get_ptms` - Post-translational modifications

**Implementation Notes**:
- REST API with JSON output (preferred)
- **Requires free access key** (simple registration)
- Filter by evidence type, organism
- GitHub examples available (Python)

**Integration Opportunities**:
- Complement STRING with genetic interactions
- Chemical-protein data for drug discovery
- PTM data for signaling studies
- Model organism research

**Effort Estimate**: 2-3 days

---

## Secondary Gaps - Verification Needed

### 3. **Reactome Verification** (Priority: LOW)

**Current Status**: `reactome_tools.json` exists

**Verification Checklist**:
- ✅ Content Service: Pathways, reactions, participants
- ? Analysis Service: Enrichment, expression overlay
- ? Disease-pathway associations
- ? Interactor network queries

**Potential Additions** (if missing):
- Analysis API token workflow
- Disease pathway mapping
- Cross-species pathway comparison

**Effort Estimate**: 0.5-1 day (audit + minor additions)

---

### 4. **KEGG Verification** (Priority: LOW)

**Current Status**: `kegg_tools.json` exists

**Verification Checklist**:
- ? All API operations covered (info, list, find, get, conv, link, ddi)
- ? Pathway retrieval and parsing
- ? Compound and drug information
- ? Organism-specific queries

**Potential Additions** (if missing):
- Drug-drug interactions (ddi operation)
- Cross-database linking (link operation)
- Identifier conversion (conv operation)

**Important**: Verify academic use compliance

**Effort Estimate**: 0.5-1 day

---

### 5. **WikiPathways Verification** (Priority: LOW)

**Current Status**: `wikipathways_tools.json` exists

**Verification Checklist**:
- ? Pathway search and retrieval
- ? Multiple format support (GPML, GMT, PNG, SVG)
- ? Monthly release access
- ? Organism filtering

**Potential Additions** (if missing):
- GMT file generation for enrichment
- Pathway image retrieval
- Curation history

**Effort Estimate**: 0.5-1 day

---

### 6. **IntAct Verification** (Priority: LOW-MEDIUM)

**Current Status**: `intact_tools.json` exists

**Verification Checklist**:
- ? PSICQUIC service access
- ? MIQL query support
- ? Output formats (PSI-MI, MITAB)
- ? Confidence scores

**Potential Additions** (if missing):
- Enhanced PSICQUIC queries
- Experimental evidence filtering
- IMEx database queries

**Effort Estimate**: 1 day

---

### 7. **Pathway Commons Verification** (Priority: LOW-MEDIUM)

**Current Status**: `pathway_commons_tools.json` exists

**Verification Checklist**:
- ? Search functionality
- ? Graph queries (neighborhood, paths)
- ? Output formats (JSON-LD, BioPAX, SIF)
- ? Integrated database coverage

**Potential Additions** (if missing):
- Advanced graph queries
- BioPAX parsing helpers
- Cross-database network queries

**Effort Estimate**: 1 day

---

### 8. **MetaCyc Verification** (Priority: LOW-MEDIUM)

**Current Status**: `metacyc_tools.json` exists

**Verification Checklist**:
- ? Pathway search and retrieval
- ? Metabolite and compound queries
- ? Enzyme and reaction information
- ? Organism coverage (BioCyc PGDBs)

**Potential Additions** (if missing):
- Metabolic network queries
- Pathway comparison
- Enzyme classification

**Effort Estimate**: 1 day

---

## Prioritized Implementation Roadmap

### Phase 1: High Priority - Protein Interaction Networks (Week 1)
**Goal**: Add critical STRING-db PPI database

**1. STRING-db Tools** (Est: 3-4 days)
- 5-6 tools for protein interaction networks
- Highest research value for network biology
- New regulatory network with directionality
- Essential for drug target and pathway analysis

**Phase 1 Total**: 3-4 days, 5-6 tools

---

### Phase 2: Medium Priority - Expand Interactions (Week 2)
**Goal**: Add BioGRID genetic and chemical interactions

**2. BioGRID Tools** (Est: 2-3 days)
- 3-4 tools for genetic/protein interactions
- Unique genetic interaction data
- Chemical-protein associations
- PTM information

**Phase 2 Total**: 2-3 days, 3-4 tools

---

### Phase 3: Verification & Enhancements (Week 2-3)
**Goal**: Audit existing tools and fill gaps

**3. Pathway Tool Audits** (Est: 3-5 days total)
- Reactome: 0.5-1 day (check analysis API)
- KEGG: 0.5-1 day (verify all operations)
- WikiPathways: 0.5-1 day (check formats)
- IntAct: 1 day (PSICQUIC completeness)
- Pathway Commons: 1 day (graph queries)
- MetaCyc: 1 day (metabolic networks)

**Phase 3 Total**: 3-5 days (distributed audits)

---

## Effort Estimates

| Phase | Focus | New Tools | Estimated Days | Priority |
|-------|-------|-----------|----------------|----------|
| Phase 1 | STRING-db | 5-6 | 3-4 | HIGH |
| Phase 2 | BioGRID | 3-4 | 2-3 | MEDIUM |
| Phase 3 | Audits (6 DBs) | Varies | 3-5 | MEDIUM |
| **Total** | | **8-10 new tools** | **8-12 days** | |

**Recommended Focus**:
- **Minimum**: Phase 1 only (3-4 days, STRING-db critical)
- **Recommended**: Phase 1 + Phase 2 (5-7 days, both gaps filled)
- **Comprehensive**: All 3 phases (8-12 days, complete coverage)

---

## Technical Considerations

### API Characteristics

| API | Auth Required | Rate Limits | Data Format | License |
|-----|--------------|-------------|-------------|---------|
| **Reactome** | No | Not specified | JSON | Open |
| **KEGG** | No | Academic only | TEXT | Academic only |
| **WikiPathways** | No | Not specified | Multiple | Open |
| **STRING** | No | Not specified | JSON/TSV | Open (cite) |
| **IntAct** | No | Not specified | PSI-MI/MITAB | Open |
| **BioGRID** | **Free key** | Not specified | JSON/TAB2 | Open (cite) |
| **Pathway Commons** | No | Not specified | JSON-LD/BioPAX | Open |
| **MetaCyc** | Varies | Not specified | BioPAX | Free/Subscription |

### Important Notes

**KEGG Academic Use**:
- REST API at rest.kegg.jp **for academic use only**
- Non-academic users require license
- Commercial use needs separate arrangement
- Verify compliance for ToolUniverse users

**BioGRID Access Key**:
- Free registration required
- Simple form at webservice.thebiogrid.org
- Key required in all API requests
- No cost, just for tracking

**Citation Requirements**:
- STRING, BioGRID require citation in publications
- Standard for academic databases
- Not a legal restriction, community norm

---

## Use Case Synergies

### Network-Based Drug Discovery

**Current ToolUniverse Capabilities**:
- Targets (OpenTargets, UniProt)
- Compounds (PubChem, ChEMBL, DrugBank)
- Pathways (Reactome, KEGG, WikiPathways)

**STRING-db Addition Enables**:
1. **Target network analysis**: Identify drug targets in disease networks
2. **Polypharmacology**: Multi-target drugs and network effects
3. **Side effect prediction**: Off-target interactions
4. **Combination therapy**: Targets in complementary pathways
5. **Drug repositioning**: Network proximity of drugs to diseases

**Example Workflow**:
```
Disease (OpenTargets) → Disease genes → STRING network
→ Network modules → Drug targets → Compounds (ChEMBL)
→ Target interactions (STRING) → Polypharmacology analysis
→ Side effects prediction → Candidate ranking
```

### Systems Biology Analysis

**Enhanced Capabilities with STRING + BioGRID**:
- Protein interaction networks (STRING)
- Genetic interactions (BioGRID)
- Pathway connectivity (Reactome + STRING)
- Network clustering and modules
- Functional enrichment with network context
- Cross-species ortholog networks

---

## Next Steps

### Handoff to Implementation Agent

**Inputs Provided**:
1. ✅ API documentation links for all target APIs
2. ✅ Authentication requirements and access keys
3. ✅ Gap analysis with clear prioritization
4. ✅ Implementation roadmap with effort estimates
5. ✅ Technical considerations and license restrictions
6. ✅ Integration opportunities and use cases

**Recommended Start**:
- **Phase 1**: STRING-db tools (3-4 days, 5-6 tools)
- **Rationale**:
  - Highest priority gap
  - Most widely used PPI database
  - Critical for network-based research
  - Latest features (regulatory network) available
- **Then Phase 2**: BioGRID tools (2-3 days, 3-4 tools)

**Audit After Implementation**:
- Phase 3: Systematic verification of existing 6 pathway tools
- Identify and fill specific gaps
- Document existing coverage
- Create usage examples

**Open Questions for User**:
1. Prioritize STRING alone (3-4 days) or include BioGRID (5-7 days)?
   - Recommendation: Both (STRING critical, BioGRID complements)
2. Start audits immediately or after STRING/BioGRID implementation?
   - Recommendation: Implement new tools first, audit in parallel or after
3. KEGG academic use compliance - how to handle/enforce?
   - Recommendation: Document in tool descriptions, user responsibility
4. BioGRID access key - built into tools or user-provided?
   - Recommendation: User-provided via env variable (like UMLS API key)

---

## Summary Statistics

### Current ToolUniverse Systems Biology Coverage

**Pathway Databases** (6):
- ✅ Reactome
- ✅ KEGG
- ✅ WikiPathways
- ✅ Pathway Commons (integrative)
- ✅ MetaCyc
- ✅ IntAct

**Missing Protein Interaction Databases** (2):
- ❌ STRING-db (CRITICAL)
- ❌ BioGRID (MEDIUM)

**Overall Assessment**:
- Pathway coverage: **Excellent**
- PPI coverage: **Major gap (STRING)**
- Genetic interactions: **Missing (BioGRID)**

---

## Sources

- [Reactome Content Service](https://reactome.org/dev/content-service)
- [Reactome Analysis Service](https://reactome.org/dev/analysis)
- [Reactome Home](https://reactome.org/)
- [KEGG REST API](https://www.kegg.jp/kegg/rest/)
- [KEGG API Manual](https://www.kegg.jp/kegg/rest/keggapi.html)
- [WikiPathways Home](https://www.wikipathways.org/)
- [WikiPathways Webservice Help](https://classic.wikipathways.org/index.php/Help:WikiPathways_Webservice)
- [STRING-db Home](https://string-db.org/)
- [STRING API Documentation](https://version11.string-db.org/help/api/)
- [STRING Database 2025 Update (NAR)](https://academic.oup.com/nar/article/53/D1/D730/7903368)
- [IntAct Portal](https://www.ebi.ac.uk/intact/)
- [IntAct NAR 2022](https://academic.oup.com/nar/article/50/D1/D648/6425548)
- [BioGRID Home](https://thebiogrid.org/)
- [BioGRID REST Service](https://wiki.thebiogrid.org/doku.php/biogridrest)
- [Pathway Commons Home](https://www.pathwaycommons.org/)
- [Pathway Commons API Console](https://pathwaycommons.github.io/pcapi/)
- [MetaCyc Home](https://metacyc.org/)
- [BioCyc Home](https://biocyc.org/)

---

**Report Status**: ✅ Complete
**Next Agent**: Implementation Agent (Phase 1: STRING-db tools)
**Audit Needed**: Reactome, KEGG, WikiPathways, IntAct, Pathway Commons, MetaCyc (6 tools)
**Date Completed**: 2026-02-08
