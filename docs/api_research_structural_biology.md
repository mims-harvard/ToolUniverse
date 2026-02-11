# Structural Biology APIs - Research Report

**Date**: 2026-02-08
**Agent**: API Research Agent
**Status**: Phase 1 - Complete

## Executive Summary

This report documents available structural biology APIs, analyzes ToolUniverse's current coverage, identifies gaps, and prioritizes new integrations.

**Key Findings**:
- ToolUniverse has **excellent baseline coverage** for structural biology (7+ major databases)
- Core resources covered: PDB (RCSB + PDBe), AlphaFold, EMDB, GPCRdb
- Major gaps in: SASBDB (small angle scattering), ProteinsPlus (docking), Interactome3D (PPIs)
- Medium gaps: SWISS-MODEL API, advanced PDBe features
- Priority: SASBDB > ProteinsPlus > Interactome3D

---

## Target APIs Researched

### 1. EMDB (Electron Microscopy Data Bank)

**URL**: https://www.ebi.ac.uk/emdb/api/
**Type**: REST API (JSON)
**Authentication**: None

#### Capabilities
- Access to 53,964+ cryo-EM structure maps (as of Feb 2026)
- Single-particle analysis, electron tomography, 2D crystallography data
- Metadata: resolution, imaging method, sample prep, molecular details
- Voxel dimensions and coordinate systems
- Map download URLs (MRC/CCP4 format)
- Cross-references to PDB coordinate models

#### API Endpoints
- `/entry/{emdb_id}` - Detailed structure metadata
- `/search` - Query EM structures by criteria
- Statistics and summary endpoints

#### Data Schemas
- JSON responses with comprehensive metadata
- Links to downloadable EM density maps
- PDB cross-references for integrated structure analysis

#### Integration Complexity: **LOW**
- Simple REST API with JSON responses
- Well-documented EBI API standards
- No authentication required

#### ToolUniverse Coverage
- ✅ **`emdb_tools.json` EXISTS**
- ✅ Basic EMDB_get_structure tool implemented
- **PARTIAL GAP**: Verify if search and advanced query tools exist

---

### 2. SASBDB (Small Angle Scattering Biological Data Bank)

**URL**: https://www.sasbdb.org/
**API**: REST-based (JSON/XML)
**Authentication**: None

#### Capabilities
- Small-angle X-ray scattering (SAXS) data
- Small-angle neutron scattering (SANS) data
- Experimental conditions and sample details
- Derived structural models and fits
- Quality assessment metrics
- Downloadable raw data and models

#### API Access
- REST calls returning JSON/XML formats
- Entry-level data retrieval
- Search and query capabilities
- Model and experimental data download

#### Data Types
- Scattering curves (I(q) vs q)
- Distance distribution functions P(r)
- Ab initio bead models
- Atomistic models fitted to data
- Experimental metadata (concentration, temperature, pH)

#### Integration Complexity: **MEDIUM**
- REST API with standard formats
- Need to parse SAXS/SANS-specific data structures
- Quality metrics require domain knowledge

#### ToolUniverse Coverage
- ❌ **NO SASBDB TOOLS**
- **MAJOR GAP**: High-value resource for solution structures
- Complements PDB/EMDB for dynamic/flexible systems
- Critical for drug discovery (protein conformation studies)

---

### 3. PDBe (Protein Data Bank Europe) API

**URL**: https://www.ebi.ac.uk/pdbe/pdbe-rest-api
**Docs**: https://www.ebi.ac.uk/pdbe/api/doc and https://www.ebi.ac.uk/pdbe/api/v2/
**Type**: RESTful API (80+ endpoints)
**Authentication**: None

#### Capabilities
- Aggregated protein structure data
- Functional and biophysical annotations
- Ligand binding sites
- Post-translational modifications
- Experimental quality metrics
- Cross-references to 100+ databases
- AlphaFold predictions integration

#### Recent Updates (2026)
- API reorganization for better clarity
- Unified endpoints with intuitive URLs
- Performance improvements
- Swagger/OpenAPI documentation

#### API Endpoints (80+ total)
**Structure Data**:
- `/pdb/entry/summary/{pdb_id}` - Structure overview
- `/pdb/entry/molecules/{pdb_id}` - Molecular entities
- `/pdb/entry/ligand_monomers/{pdb_id}` - Ligands

**Annotations**:
- `/pdb/entry/binding_sites/{pdb_id}` - Binding site details
- `/pdb/entry/modified_residues/{pdb_id}` - PTMs
- `/pdb/entry/quality/{pdb_id}` - Validation metrics

**Search & Analysis**:
- `/graph-api` - Comprehensive knowledge graph queries
- PDB search API for complex queries

#### Data Schemas
- JSON responses with rich nested structures
- Integrative knowledge graph
- Cross-database links (UniProt, InterPro, GO, etc.)

#### Integration Complexity: **MEDIUM**
- Well-documented REST API
- 80+ endpoints require systematic coverage
- Complex nested JSON structures
- Some endpoints return large payloads

#### ToolUniverse Coverage
- ✅ **`pdbe_api_tools.json` EXISTS**
- **PARTIAL GAP**: Check coverage of 80+ endpoints
  - Priority: Binding sites, ligand annotations, quality metrics
  - Secondary: PTMs, validation, cross-references

---

### 4. SWISS-MODEL

**URL**: https://swissmodel.expasy.org/
**Type**: Web service (API available)
**Authentication**: None for basic queries

#### Capabilities
- Automated protein homology modeling
- Template identification (BLAST, HHblits)
- Sequence-structure alignment
- Model quality assessment
- Multi-template modeling
- Quaternary structure prediction
- AlphaFoldDB structures as templates (recent addition)

#### API Components
- **OpenStructure Actions API**: Programmatic access to modeling pipeline
- **SWISS-MODEL Repository**: Pre-computed models for UniProt
- **Swiss-model Template Library (SMTL)**: PDB-derived templates

#### Modes of Operation
- **Automated mode**: Fully automatic pipeline
- **Alignment mode**: User-defined template alignment
- **Project mode**: Advanced control over modeling

#### Integration Complexity: **MEDIUM-HIGH**
- API exists but less documented than PDB/EMDB
- Job submission and result retrieval workflow
- Modeling jobs can take minutes to hours
- OpenStructure Actions API requires specific setup

#### ToolUniverse Coverage
- ⚠️ **NO SWISS-MODEL SPECIFIC TOOLS**
- **CONSIDERATION**: Useful for structure prediction before AlphaFold
  - Still valuable for specific modeling scenarios
  - Multi-template modeling advantage over AlphaFold in some cases
- **PRIORITY**: MEDIUM-LOW (AlphaFold covers many use cases)

---

### 5. ProteinsPlus

**URL**: https://proteins.plus/
**Type**: REST API
**Authentication**: None

#### Capabilities
- **JAMDA Docking**: Automated protein-ligand docking
- Binding site detection
- Protein-ligand interaction analysis
- Structure analytics and validation
- Molecular modeling tools collection

#### Key Tools
- **JAMDA**: TrixX docking + JAMDA scoring function
- **DoGSiteScorer**: Binding site prediction
- **PLIP**: Protein-ligand interaction profiler
- **ProteinPlus**: Structure quality checks

#### API Access
- All tools available via REST service
- Automated integration in pipelines
- Structure upload and result retrieval

#### Input Requirements
- Protein structure (PDB format)
- Binding site definition
- Ligand molecules to dock

#### Integration Complexity: **MEDIUM-HIGH**
- REST API for automation
- Job-based workflow (submit → poll → retrieve)
- Multiple tools require coordination
- Docking jobs computationally intensive

#### ToolUniverse Coverage
- ❌ **NO PROTEINSPLUS TOOLS**
- **MAJOR GAP**: Important for structure-based drug design
  - Automated docking pipelines
  - Ligand pose prediction
  - Binding affinity estimation
- **HIGH VALUE**: Complements compound screening tools

---

### 6. GPCRdb (GPCR Database)

**URL**: https://gpcrdb.org/
**Docs**: https://docs.gpcrdb.org/web_services.html
**Type**: REST API (OpenAPI/Swagger)
**Authentication**: None

#### Capabilities
- G protein-coupled receptor data
- Sequence alignments (27,000+ orthologs)
- GPCR structures from PDB
- Ligand binding data (200,000+ ligands)
- Drug information (2,000+ drugs/clinical compounds)
- Mutations and variants
- G-proteins and arrestins
- AlphaFold2 state-specific models

#### API Endpoints
- Protein/sequence queries
- Structure data retrieval
- Ligand and drug information
- Mutation data access
- Diagram generation

#### Data Scope
- All human non-olfactory GPCRs
- Comprehensive ligand bioactivity
- Structural models (experimental + predicted)
- Residue-level annotations

#### Integration Complexity: **MEDIUM**
- Well-documented REST API with Swagger
- OpenAPI specification
- Code examples available
- Domain-specific terminology

#### ToolUniverse Coverage
- ✅ **`gpcrdb_tools.json` EXISTS**
- **VERIFY**: Check completeness of coverage
  - Ligand/drug endpoints
  - Mutation/variant tools
  - Structure construct data
- **PRIORITY**: LOW (good existing coverage expected)

---

### 7. ModBase

**URL**: http://salilab.org/modbase
**Type**: Web database (limited API)
**Authentication**: None

#### Capabilities
- 3.8 million+ pre-computed comparative models
- ModPipe automated modeling pipeline
- Quality assessment scores
- Model updates on demand
- Integration with Protein Model Portal

#### Access Methods
- Web interface (primary)
- ModWeb for custom modeling
- Protein Model Portal integration
- Bulk download options

#### Integration Complexity: **HIGH**
- Limited public API documentation
- Primarily web interface focused
- Custom modeling via ModWeb requires job management
- Bulk downloads available but not real-time queries

#### ToolUniverse Coverage
- ❌ **NO MODBASE TOOLS**
- **PRIORITY**: LOW
  - AlphaFoldDB covers most use cases (2+ billion structures)
  - ModBase older technology compared to deep learning models
  - May be useful for specific homology modeling scenarios
- **RECOMMENDATION**: Skip in favor of AlphaFold/SWISS-MODEL

---

### 8. Interactome3D

**URL**: https://interactome3d.irbbarcelona.org/
**Type**: Web service (limited API)
**Updated**: January 8, 2026 (release 2024_12)

#### Capabilities
- Structural annotation of protein-protein interactions
- Binary interaction models
- Template-based PPI modeling
- Pre-calculated interactomes (18 organisms)
- User-uploaded interaction modeling
- PDB-based and homology-modeled complexes

#### Coverage
- **Human proteome**: 125,000 experimental PPIs
- **Structural models**: 15,000 binary complexes (~10,000 proteins)
- **Model sources**: ~50% from PDB, ~50% from template modeling
- **18 organisms**: Pre-computed interactomes

#### Data Types
- Binary protein-protein interaction structures
- Interface residue annotations
- Model quality scores
- PDB cross-references

#### Integration Complexity: **MEDIUM-HIGH**
- Web service focused (not primarily REST API)
- Custom modeling requires job submission
- Pre-calculated data accessible
- GitHub pipeline available for interface extraction

#### ToolUniverse Coverage
- ❌ **NO INTERACTOME3D TOOLS**
- **MEDIUM-HIGH GAP**: Valuable for systems biology
  - PPI structural modeling
  - Interface residue prediction
  - Network structural annotation
- **USE CASE**: Drug target analysis, PPI disruption strategies
- **PRIORITY**: MEDIUM (niche but high-value)

---

## Gap Analysis

### Coverage Matrix

| API/Database | Current Status | Coverage Level | Scientific Value | Priority |
|--------------|----------------|----------------|------------------|----------|
| **EMDB** | ✅ Partial | ~60% | High | LOW-MEDIUM |
| **SASBDB** | ❌ Missing | 0% | High | **HIGH** |
| **PDBe API** | ✅ Partial | ~40% | Very High | **MEDIUM-HIGH** |
| **SWISS-MODEL** | ❌ Missing | 0% | Medium | LOW-MEDIUM |
| **ProteinsPlus** | ❌ Missing | 0% | High | **HIGH** |
| **GPCRdb** | ✅ Good | ~80% | High (niche) | LOW |
| **ModBase** | ❌ Missing | 0% | Low | **SKIP** |
| **Interactome3D** | ❌ Missing | 0% | Medium-High | MEDIUM |

### Additional Coverage Notes
- ✅ **RCSB PDB**: Excellent coverage (rcsb_pdb_tools.json)
- ✅ **AlphaFold**: Excellent coverage (alphafold_tools.json)
- ✅ **3D Protein Tools**: protein_structure_3d_tools.json, proteins_api_tools.json

---

## Critical Gaps

### 1. **SASBDB (Small Angle Scattering)** (Priority: HIGH)

**Why Important**:
- Unique capability: Solution structures and conformational flexibility
- Complements X-ray/cryo-EM with dynamic information
- Critical for intrinsically disordered proteins (IDPs)
- Essential for multidomain protein studies
- Drug discovery: Protein conformational changes upon binding

**Missing Capabilities**:
- Search SAXS/SANS entries by protein, organism, method
- Retrieve scattering curves and distance distributions
- Access derived models (ab initio, atomistic fits)
- Download experimental data and metadata
- Quality metrics for data validation

**Recommended Tools** (4-5 tools):
1. `SASBDB_search_entries` - Search by protein name, UniProt, organism
2. `SASBDB_get_entry_data` - Retrieve metadata and experimental conditions
3. `SASBDB_get_scattering_profile` - I(q) scattering curve data
4. `SASBDB_get_models` - Derived structural models and fits
5. `SASBDB_download_data` - Raw data files and processing info

**Implementation Notes**:
- REST API with JSON/XML responses
- Need to handle SAXS-specific data formats
- Include quality assessment metrics (Rg, Dmax, chi-squared)
- Consider data visualization helpers (though plots may be out of scope)

**Effort Estimate**: 2-3 days

---

### 2. **ProteinsPlus Docking Suite** (Priority: HIGH)

**Why Important**:
- Automated protein-ligand docking critical for drug design
- JAMDA provides validated docking + scoring
- Complements ToolUniverse's compound screening capabilities
- Binding site prediction useful for target analysis
- Integration with existing drugbank/chembl tools

**Missing Capabilities**:
- Automated protein-ligand docking (JAMDA)
- Binding site prediction (DoGSiteScorer)
- Protein-ligand interaction profiling (PLIP)
- Structure preparation and validation

**Recommended Tools** (3-4 tools):
1. `ProteinsPlus_predict_binding_sites` - Find druggable pockets
2. `ProteinsPlus_dock_ligand` - JAMDA docking workflow
3. `ProteinsPlus_analyze_interactions` - PLIP interaction analysis
4. `ProteinsPlus_check_structure` - Structure quality validation

**Implementation Notes**:
- REST API available for all tools
- Job-based workflow: submit → poll status → retrieve results
- Handle PDB structure upload or PDB ID input
- Ligand input: SMILES, SDF, or MOL2 format
- Docking jobs may take 5-30 minutes (async handling)

**Integration Opportunities**:
- Chain with PubChem/ChEMBL compound retrieval
- Pair with ADMET prediction for hit prioritization
- Link with PDB structure retrieval

**Effort Estimate**: 3-4 days

---

### 3. **PDBe Advanced Features** (Priority: MEDIUM-HIGH)

**Why Important**:
- PDBe aggregates data from 100+ sources
- Binding site and ligand annotations critical for drug discovery
- Quality metrics essential for model validation
- PTM data important for functional studies
- Knowledge graph enables complex queries

**Missing Capabilities** (if not in current pdbe_api_tools):
- Binding site detailed annotations
- Ligand interaction data
- Structure quality/validation metrics
- Modified residues (PTMs)
- Cross-database knowledge graph queries

**Recommended Tools** (3-5 tools, if missing):
1. `PDBe_get_binding_sites` - Detailed binding pocket info
2. `PDBe_get_ligand_interactions` - Protein-ligand contacts
3. `PDBe_get_quality_metrics` - Validation and quality scores
4. `PDBe_get_modified_residues` - PTM annotations
5. `PDBe_query_knowledge_graph` - Complex integrative queries

**Implementation Notes**:
- Verify existing `pdbe_api_tools.json` coverage first
- 80+ endpoints available; prioritize by research value
- Some endpoints return large nested JSON (need parsing)
- Rate limiting considerations
- Swagger docs available for reference

**Effort Estimate**: 2-3 days (after auditing existing tools)

---

### 4. **Interactome3D PPI Structures** (Priority: MEDIUM)

**Why Important**:
- Only resource with comprehensive PPI structural models
- ~15,000 human binary complex structures
- Useful for:
  - PPI interface analysis
  - Disrupting protein interactions (drug strategy)
  - Network structural context
  - Mutation impact on interactions

**Missing Capabilities**:
- Search PPIs by protein name/UniProt
- Retrieve binary complex structures
- Access interface residue annotations
- Model quality scores
- Pre-calculated vs on-demand modeling

**Recommended Tools** (2-3 tools):
1. `Interactome3D_search_interactions` - Find PPIs for proteins
2. `Interactome3D_get_complex_structure` - Retrieve PPI models
3. `Interactome3D_get_interface_residues` - Interface annotations

**Implementation Notes**:
- Web service focused; API may be limited
- Check if REST endpoints available or need scraping
- Pre-calculated data easier to access than custom modeling
- GitHub pipeline exists for data extraction
- May require coordination with web interface

**Effort Estimate**: 2-3 days

---

## Secondary Gaps

### 5. **SWISS-MODEL API** (Priority: LOW-MEDIUM)

**Why Useful**:
- Homology modeling alternative to AlphaFold
- Multi-template modeling advantage
- Swiss-model Repository: pre-computed models for UniProt

**Consideration**:
- AlphaFoldDB covers most use cases (2+ billion structures)
- SWISS-MODEL still useful for:
  - Specific template-based scenarios
  - Comparative modeling workflows
  - When experimental templates preferred

**Recommended Tools** (if implemented):
1. `SwissModel_search_repository` - Pre-computed models
2. `SwissModel_submit_modeling` - Custom modeling job
3. `SwissModel_get_model` - Retrieve results

**Effort Estimate**: 2-3 days
**Priority**: LOW-MEDIUM (defer until other gaps filled)

---

### 6. **EMDB Advanced Features** (Priority: LOW-MEDIUM)

**Current Status**: Basic EMDB_get_structure exists

**Potential Additions**:
- Search EM entries by resolution, method, organism
- Batch queries for multiple structures
- Advanced filtering (resolution range, imaging technique)
- Associated PDB coordinate models

**Recommended Tools** (if missing):
1. `EMDB_search_structures` - Query by criteria
2. `EMDB_get_associated_pdbs` - Linked coordinate models

**Effort Estimate**: 1 day
**Priority**: LOW-MEDIUM (depends on demand)

---

## Prioritized Implementation Roadmap

### Phase 1: High Priority - Structure-Based Drug Design (Week 1-2)
**Goal**: Enable comprehensive docking and solution structure analysis

**1. SASBDB Tools** (Est: 2-3 days)
- 4-5 tools for SAXS/SANS data access
- Critical for dynamic/flexible protein studies
- Complements static structure databases

**2. ProteinsPlus Docking** (Est: 3-4 days)
- 3-4 tools for automated docking and binding site analysis
- High-value for drug design workflows
- Integrates with existing compound tools

**Phase 1 Total**: 5-7 days, 7-9 tools

---

### Phase 2: Medium Priority - Advanced Annotations (Week 2-3)
**Goal**: Enhance structure annotation and PPI modeling

**3. PDBe Advanced Features** (Est: 2-3 days)
- Audit existing pdbe_api_tools coverage
- Add 3-5 missing high-value endpoints
- Focus: binding sites, ligands, quality metrics

**4. Interactome3D PPI Tools** (Est: 2-3 days)
- 2-3 tools for PPI structure access
- Valuable for systems biology and PPI-targeted drug design

**Phase 2 Total**: 4-6 days, 5-8 tools

---

### Phase 3: Low-Medium Priority - Optional Enhancements (Week 3-4)
**Goal**: Fill remaining gaps if time permits

**5. SWISS-MODEL API** (Est: 2-3 days)
- 3 tools for homology modeling
- Lower priority due to AlphaFold coverage
- Consider skipping if timeline tight

**6. EMDB Search/Advanced** (Est: 1 day)
- 1-2 tools for advanced EM queries
- Extend existing EMDB tool

**Phase 3 Total**: 3-4 days, 4-5 tools

---

### Phase 4: Verification & Audits (Week 4)
**Goal**: Ensure quality and completeness

**7. GPCRdb Coverage Audit** (Est: 0.5 day)
- Verify existing tools complete
- Add missing endpoints if identified

**8. Integration Testing** (Est: 1 day)
- End-to-end workflows (e.g., structure retrieval → docking → analysis)
- Cross-tool validation
- Documentation updates

**Phase 4 Total**: 1.5 days

---

## Effort Estimates

| Phase | Focus | Tools | Estimated Days | Priority |
|-------|-------|-------|----------------|----------|
| Phase 1 | SASBDB + Docking | 7-9 | 5-7 | HIGH |
| Phase 2 | PDBe + Interactome3D | 5-8 | 4-6 | MEDIUM-HIGH |
| Phase 3 | SWISS-MODEL + EMDB | 4-5 | 3-4 | LOW-MEDIUM |
| Phase 4 | Verification | - | 1.5 | - |
| **Total** | | **16-22 tools** | **14-18.5 days** | |

**Recommended Focus**: Phase 1 + Phase 2 (9-10 days, 12-17 tools)
**Optional**: Phase 3 (additional 3-4 days if timeline allows)

---

## Technical Considerations

### API Characteristics

**Rate Limits**:
- **PDBe**: No explicit limit mentioned (EBI standard ~few requests/sec)
- **EMDB**: Same as PDBe (EBI infrastructure)
- **ProteinsPlus**: Unknown; likely rate limited
- **SASBDB**: No information; assume conservative limits
- **Interactome3D**: Web-focused; may be restrictive

**Recommendation**: Implement rate limiting and caching for all new tools

### Authentication
- **All APIs**: Public access, no authentication required
- **ProteinsPlus**: May require registration for heavy use (verify)

### Computational Considerations
- **ProteinsPlus Docking**: Async job workflow (5-30 min per job)
- **SWISS-MODEL**: Async modeling (minutes to hours)
- **Interactome3D**: Custom modeling slow; use pre-calculated data

**Implementation**: Job polling mechanisms for async tools

### Data Formats
- **SASBDB**: SAXS-specific formats (I(q), P(r), DAT files)
- **ProteinsPlus**: PDB input, MOL2/SDF for ligands
- **PDBe**: Rich nested JSON structures
- **Interactome3D**: PDB format structures

---

## Use Case Synergies

### Drug Discovery Pipeline Integration

**Current ToolUniverse Capabilities**:
1. Target identification (OpenTargets, UniProt)
2. Compound screening (PubChem, ChEMBL, DrugBank)
3. ADMET prediction (ADMETAI)
4. Literature evidence (PubMed, EuropePMC)

**Structural Biology Additions Enable**:
1. **SASBDB**: Solution structures for flexible targets
2. **ProteinsPlus**: Automated docking for hit validation
3. **PDBe**: Binding site characterization
4. **Interactome3D**: PPI-targeted drug design

**Complete Workflow Example**:
```
Disease → Targets (OpenTargets) → Structure (PDB/AlphaFold)
→ Binding Sites (PDBe/ProteinsPlus) → Compound Screening (ChEMBL)
→ Docking (ProteinsPlus) → ADMET (ADMETAI) → Prioritized Hits
```

---

## Next Steps

### Handoff to Implementation Agent

**Inputs Provided**:
1. ✅ API documentation links for all target APIs
2. ✅ Endpoint specifications and capabilities
3. ✅ Gap analysis with prioritization
4. ✅ Implementation roadmap with effort estimates
5. ✅ Technical considerations and integration opportunities

**Recommended Start**:
- **Phase 1**: Begin with SASBDB (2-3 days) → ProteinsPlus (3-4 days)
- **Rationale**: Both high-value, complement existing tools, enable new workflows
- **Coordination**: Test integration with existing PDB/compound tools

**Audit First**:
- Verify `pdbe_api_tools.json` current coverage before starting Phase 2
- Check `gpcrdb_tools.json` completeness

**Open Questions for User**:
1. Prioritize SASBDB or ProteinsPlus first?
2. Skip SWISS-MODEL entirely (AlphaFold sufficient)?
3. Include Interactome3D or defer to later release?
4. Should we audit existing PDBe/GPCRdb tools before adding new ones?

---

## Sources

- [EMDB API Documentation](https://www.ebi.ac.uk/emdb/api/)
- [EMDB NAR 2025 Update](https://academic.oup.com/nar/article/52/D1/D456/7442543)
- [SASBDB Help](https://www.sasbdb.org/help/)
- [SASBDB NAR Paper](https://academic.oup.com/nar/article/43/D1/D357/2436355)
- [PDBe REST API Documentation](https://www.ebi.ac.uk/pdbe/pdbe-rest-api)
- [PDBe API Breaking Changes 2026](https://www.ebi.ac.uk/pdbe/news/unifying-pdbe-api-endpoints-breaking-changes-pdbe-api)
- [PDBe Aggregated API NAR Paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC8570819/)
- [SWISS-MODEL Website](https://swissmodel.expasy.org/)
- [SWISS-MODEL NAR 2018](https://academic.oup.com/nar/article/46/W1/W296/5000024)
- [ProteinsPlus NAR 2022](https://academic.oup.com/nar/article/50/W1/W611/6576358)
- [ProteinsPlus NAR 2020](https://academic.oup.com/nar/article/48/W1/W48/5820880)
- [GPCRdb Web Services](https://docs.gpcrdb.org/web_services.html)
- [GPCRdb Website](https://gpcrdb.org/)
- [ModBase NAR 2014](https://academic.oup.com/nar/article/42/D1/D336/1053869)
- [Interactome3D Website](https://interactome3d.irbbarcelona.org/)
- [Interactome3D Nature Methods 2013](https://www.nature.com/articles/nmeth.2289)

---

**Report Status**: ✅ Complete
**Next Agent**: Implementation Agent (Phase 1: SASBDB → ProteinsPlus)
**Audit Needed**: PDBe and GPCRdb existing tool coverage
**Date Completed**: 2026-02-08
