# Genomics & Sequencing APIs - Research Report

**Date**: 2026-02-08
**Agent**: API Research Agent
**Status**: Phase 1 - Complete

## Executive Summary

This report documents available genomics and sequencing APIs, analyzes ToolUniverse's current coverage, identifies gaps, and prioritizes new integrations.

**Key Findings**:
- ToolUniverse has strong baseline coverage (10+ genomics databases)
- Major gaps in: SRA data access, advanced ENCODE features, dbGaP phenotype data
- High-priority additions: NCBI SRA Toolkit API, expanded ENCODE functionality
- Medium-priority: GeneBe REST API (alternative gnomAD access), advanced GTEx features

---

## Target APIs Researched

### 1. NCBI Sequence Read Archive (SRA)

**URL**: https://www.ncbi.nlm.nih.gov/sra/docs/
**Type**: REST API + Toolkit API
**Authentication**: None for public data; required for controlled-access dbGaP

#### Capabilities
- Access to high-throughput sequencing data (NGS, RNA-seq, WGS)
- SRA Toolkit provides programmatic data access and format conversion
- Available on AWS and Google Cloud Platform
- Supports FASTQ conversion, compression, and streaming
- Access to dbGaP controlled-access studies

#### API Endpoints
- **E-utilities access**: esearch, esummary, efetch for metadata
- **SRA Toolkit**: Command-line and SDK access to sequence data
- **Cloud access**: Direct S3/GCS bucket access for large-scale analysis

#### Data Schemas
- XML metadata via E-utilities
- FASTQ/FASTA sequence data
- Run metadata: experiment design, platform, sample info

#### Integration Complexity: **MEDIUM-HIGH**
- E-utilities integration straightforward (ToolUniverse has `ncbi_eutils_tool`)
- SRA Toolkit requires binary installation and complex configuration
- Large data volumes require streaming/chunking strategies

#### ToolUniverse Coverage
- ❌ **No SRA-specific tools**
- ✅ Basic NCBI E-utilities support exists
- **GAP**: Need SRA search, metadata retrieval, and run access tools

---

### 2. ENCODE Data Portal

**URL**: https://www.encodeproject.org/help/rest-api/
**API Docs**: https://gtexportal.org/api/v2/redoc
**Type**: RESTful JSON API
**Authentication**: None (rate limited: 10 req/sec)

#### Capabilities
- Functional genomics data (ChIP-seq, ATAC-seq, RNA-seq, Hi-C)
- Chromatin accessibility, transcription factor binding
- Epigenetic marks (histone modifications)
- 3D genome organization data
- Bulk metadata and file downloads

#### API Endpoints
- `/search/` - Query experiments, files, biosamples
- `/experiments/{accession}` - Experiment details
- `/files/{accession}` - File metadata and download links
- `/biosamples/{accession}` - Sample information
- Supports filtering, pagination, and field selection

#### Data Schemas
- JSON objects (Experiment, File, Biosample, Target, etc.)
- Embedded related objects for efficient queries
- Comprehensive metadata following ENCODE standards

#### Integration Complexity: **MEDIUM**
- RESTful API with standard JSON responses
- Well-documented with Swagger/OpenAPI
- Some endpoints return large nested objects

#### ToolUniverse Coverage
- ✅ `encode_tools.json` exists with basic search capabilities
- **PARTIAL GAP**: Need expanded tools for:
  - File download metadata
  - Biosample detailed queries
  - Target protein queries
  - Advanced filtering (cell type, assay, replicate)

---

### 3. GTEx Portal

**URL**: https://gtexportal.org/home/apiPage
**API Docs**: https://gtexportal.org/api/v2/redoc
**Type**: RESTful JSON API (v2 active, v1 deprecated)
**Authentication**: None

#### Capabilities
- Gene expression across 54 human tissues
- eQTL (expression quantitative trait loci) data
- Subject phenotypes and sample annotations
- Transcript-level expression
- Splice QTL data
- Alternative splicing events

#### API Endpoints
**Expression**:
- `/expression/geneExpression` - Gene expression by tissue
- `/expression/medianGeneExpression` - Median across samples
- `/expression/transcriptExpression` - Transcript-level data

**QTL**:
- `/association/dyneqtl` - Dynamic eQTL queries
- `/association/singleTissueEqtl` - Tissue-specific eQTLs

**Metadata**:
- `/dataset/subject` - Subject phenotype data
- `/dataset/tissueSiteDetail` - Tissue information
- `/reference/gene` - Gene reference data

#### Data Schemas
- JSON responses with expression values, statistics, and metadata
- Tissue-specific arrays with TPM values
- QTL associations with p-values and effect sizes

#### Integration Complexity: **MEDIUM**
- Well-structured REST API with comprehensive docs
- Some endpoints require complex query parameters
- Large result sets for genome-wide queries

#### ToolUniverse Coverage
- ✅ `gtex_tools.json` and `gtex_v2_tools.json` exist
- **PARTIAL GAP**: Check if eQTL, splice QTL, and subject phenotype tools exist
  - Need verification of current tool coverage vs API v2 capabilities

---

### 4. gnomAD (Genome Aggregation Database)

**URL**: https://gnomad.broadinstitute.org/
**API Type**: GraphQL (not REST)
**Authentication**: None (rate limited)

#### Capabilities
- Population allele frequencies for variants
- Loss-of-function constraint metrics (pLI, LOEUF)
- Coverage information
- Structural variants
- Copy number variants
- Regional constraint

#### API Access
- **Primary**: GraphQL API at `https://gnomad.broadinstitute.org/api`
- **Alternative**: GeneBe.net REST API (includes gnomAD data)
- **Note**: GraphQL has changed; old queries may be deprecated

#### Query Capabilities
- Variant lookup by position or rsID
- Gene constraint metrics
- Regional variant queries
- Population frequency distributions

#### Integration Complexity: **MEDIUM (GraphQL) / LOW (GeneBe alternative)**
- GraphQL requires different query structure than REST
- Schema changes between gnomAD versions (v2 vs v3 vs v4)
- GeneBe offers REST alternative with gnomAD data

#### ToolUniverse Coverage
- ✅ `gnomad_tools.json` exists with GraphQL tools
- **CONSIDERATION**: Add GeneBe REST API as alternative/supplement
  - GeneBe URL: https://genebe.net/about/api
  - Provides variant annotation with gnomAD frequencies via REST

---

### 5. European Nucleotide Archive (ENA)

**URL**: https://www.ebi.ac.uk/ena/browser/
**Docs**: https://ena-docs.readthedocs.io/en/latest/retrieval/programmatic-access.html
**Type**: REST URLs
**Authentication**: None for public data

#### Capabilities
- Sequence data archive (complement to NCBI)
- Taxonomic information API
- Read data, assemblies, and annotations
- INSDC accession support (GenBank, DDBJ, ENA)
- Multiple format support: XML, HTML, FASTA, FASTQ, flat file

#### API Endpoints
- Browser REST URLs: `/ena/browser/api/{format}/{accession}`
- Portal API: `/ena/portal/api/search`
- Taxonomy API: Lineage and rank information
- Submission API: For data upload

#### Data Formats
- XML for metadata
- FASTA/FASTQ for sequences
- TSV for tabular results
- JSON for portal API

#### Integration Complexity: **LOW-MEDIUM**
- Simple REST URL patterns
- Well-documented formats
- Multiple endpoint types require coordination

#### ToolUniverse Coverage
- ✅ `ena_browser_tools.json` exists
- **VERIFY**: Check coverage of portal API, taxonomy API, and search capabilities

---

### 6. dbGaP (Database of Genotypes and Phenotypes)

**URL**: https://www.ncbi.nlm.nih.gov/gap/
**Type**: Web interface + E-utilities
**Authentication**: **Required for controlled-access data**

#### Capabilities
- Genotype-phenotype association studies
- Individual-level and summary-level data
- Study metadata and variable descriptions
- Links to SRA sequence data

#### Access Levels
- **Open Access**: Study metadata, summaries (no authentication)
- **Controlled Access**: Individual-level data (requires DAC approval + eRA Commons)

#### API Access
- E-utilities for open-access metadata
- Authorized Access System for controlled data
- No direct API for phenotype data download

#### Integration Complexity: **HIGH**
- Controlled access requires institutional authentication
- Limited API capabilities for phenotype data
- Primarily focused on metadata rather than data access

#### ToolUniverse Coverage
- ⚠️ **No dbGaP-specific tools**
- **CONSIDERATION**: Add open-access metadata tools
  - Study search and description
  - Variable-level metadata
  - Link to associated SRA/GEO datasets
- **NOT FEASIBLE**: Controlled-access data download (requires auth)

---

### 7. ClinVar

**URL**: https://www.ncbi.nlm.nih.gov/clinvar/
**API Docs**: https://www.ncbi.nlm.nih.gov/clinvar/docs/maintenance_use/
**Type**: E-utilities + Clinical Table Search Service
**Authentication**: Submission API requires service account; retrieval is public

#### Capabilities
- Clinical significance of genetic variants
- Evidence summaries and review status
- Condition associations
- Variant classification (Pathogenic, Benign, VUS, etc.)
- Submission API for data deposition

#### API Endpoints
**E-utilities** (esearch, esummary, efetch):
- Search by gene, condition, variant
- Retrieve XML/JSON summaries
- Batch queries supported

**Clinical Table Search Service**:
- Base URL: `https://clinicaltables.nlm.nih.gov/api/variants/v4/search`
- Restricted to GRCh37 variants
- Simpler REST interface for variant lookup

#### Data Schemas
- XML (E-utilities efetch): Complete ClinVar records
- JSON (E-utilities esummary, Clinical Tables): Simplified summaries
- Monthly archived releases with comprehensive data

#### Integration Complexity: **LOW-MEDIUM**
- E-utilities familiar pattern (already in ToolUniverse)
- Clinical Tables API very simple
- XML parsing can be complex for full records

#### ToolUniverse Coverage
- ✅ `clinvar_tools.json` exists
- **VERIFY**: Check if Clinical Table Search Service is used
  - May be simpler alternative to E-utilities for basic lookups

---

### 8. GEO (Gene Expression Omnibus)

**URL**: https://www.ncbi.nlm.nih.gov/geo/
**Docs**: https://www.ncbi.nlm.nih.gov/geo/info/geo_paccess.html
**Type**: E-utilities (metadata) + FTP (data files)
**Authentication**: None

#### Capabilities
- Gene expression datasets (microarray, RNA-seq)
- Epigenomics data
- Study metadata and experimental design
- Sample annotations
- Platform information

#### API Endpoints
**E-utilities** (db=gds for GEO DataSets):
- esearch: Query datasets
- esummary: Dataset summaries
- efetch: Full records in SOFT format

**FTP Access**:
- Construct URLs: `ftp://ftp.ncbi.nlm.nih.gov/geo/...`
- Download full data tables, raw files, metadata

#### Data Formats
- SOFT (Simple Omnibus Format in Text)
- TXT, CSV for data tables
- XML (via E-utilities)

#### Integration Complexity: **LOW-MEDIUM**
- E-utilities straightforward for metadata
- FTP access requires URL construction
- Large data files may need streaming

#### ToolUniverse Coverage
- ✅ `geo_tools.json` exists
- **VERIFY**: Check if FTP download construction tools exist
  - Useful for automated data retrieval workflows

---

## Gap Analysis

### Coverage Matrix

| API/Database | Current Status | Coverage Level | Priority |
|--------------|----------------|----------------|----------|
| **NCBI SRA** | ❌ Missing | 0% | **HIGH** |
| **ENCODE** | ✅ Partial | ~40% | **MEDIUM-HIGH** |
| **GTEx** | ✅ Partial | ~60% | **MEDIUM** |
| **gnomAD** | ✅ Good | ~80% | **LOW** |
| **ENA** | ✅ Basic | ~50% | **MEDIUM** |
| **dbGaP** | ❌ Missing | 0% | **MEDIUM** |
| **ClinVar** | ✅ Good | ~70% | **LOW-MEDIUM** |
| **GEO** | ✅ Good | ~70% | **LOW-MEDIUM** |

### Critical Gaps

#### 1. **NCBI SRA** (Priority: HIGH)
**Why Important**:
- Essential for NGS/RNA-seq data access
- Massive dataset (petabytes of sequence data)
- Required for reproducible genomics research
- Gateway to dbGaP controlled-access studies

**Missing Capabilities**:
- Search SRA runs by accession, study, organism
- Retrieve SRA metadata (platform, library, samples)
- Get FTP/cloud URLs for FASTQ download
- Link SRA runs to GEO/BioProject/BioSample

**Recommended Tools**:
1. `NCBI_SRA_search_runs` - Search by study, organism, strategy
2. `NCBI_SRA_get_run_info` - Metadata for SRA run accessions
3. `NCBI_SRA_get_download_urls` - FTP and cloud URLs for data access
4. `NCBI_SRA_link_to_biosample` - Link runs to BioSample records

**Implementation Notes**:
- Use E-utilities (db=sra) for metadata
- Construct FTP URLs: `ftp://ftp-trace.ncbi.nlm.nih.gov/sra/sra-instant/reads/...`
- Cloud URLs available via SRA Toolkit API or direct S3 access

---

#### 2. **ENCODE Advanced Features** (Priority: MEDIUM-HIGH)
**Why Important**:
- ENCODE is gold standard for functional genomics
- Current tools lack file-level and biosample queries
- Need better filtering for complex experimental designs

**Missing Capabilities**:
- Query files with download links by experiment
- Biosample detailed metadata (donor, treatment)
- Target protein/factor search
- Cell type and tissue filtering
- Replicate-level data access

**Recommended Tools**:
1. `ENCODE_get_files_by_experiment` - List files for download
2. `ENCODE_search_biosamples` - Query samples by cell type, donor
3. `ENCODE_search_targets` - Find experiments by TF/histone mark
4. `ENCODE_get_replicate_data` - Replicate-level metadata

**Implementation Notes**:
- Extend existing `encode_tool.py`
- Use REST API with `?frame=object` for embedded data
- Rate limiting: 10 req/sec (add throttling)

---

#### 3. **dbGaP Open-Access Metadata** (Priority: MEDIUM)
**Why Important**:
- Links genotype-phenotype studies
- Study-level metadata useful for discovery
- Connects to SRA and GEO datasets

**Missing Capabilities**:
- Search studies by disease, phenotype, or population
- Retrieve study descriptions and variable metadata
- Link to associated SRA/GEO datasets

**Recommended Tools**:
1. `dbGaP_search_studies` - Search by disease or keyword
2. `dbGaP_get_study_info` - Study descriptions and design
3. `dbGaP_get_study_variables` - Variable-level metadata
4. `dbGaP_get_linked_datasets` - Find SRA/GEO links

**Implementation Notes**:
- Use E-utilities (db=gap)
- Focus on open-access metadata only
- Note limitations: no controlled-access data

---

### Secondary Gaps

#### 4. **GeneBe REST API** (Priority: MEDIUM)
**Why Useful**:
- Alternative to gnomAD GraphQL
- REST interface simpler than GraphQL
- Includes gnomAD, ClinVar, dbSNP in one API

**API**: https://genebe.net/about/api
**Capabilities**: Variant annotation, population frequencies, clinical significance

**Recommended Tools**:
1. `GeneBe_annotate_variant` - Comprehensive variant annotation
2. `GeneBe_batch_annotate` - Batch variant queries

---

#### 5. **GTEx eQTL Tools** (Priority: LOW-MEDIUM)
**Why Useful**:
- eQTL data critical for functional interpretation
- Current coverage unknown - needs verification

**Recommended Tools** (if missing):
1. `GTEx_get_eqtls_by_gene` - Gene-level eQTL associations
2. `GTEx_get_eqtls_by_variant` - Variant-level eQTL effects
3. `GTEx_get_splice_qtls` - Splice QTL data

---

## Prioritized Implementation Roadmap

### Phase 1: High Priority (Week 1-2)
**Goal**: Add critical missing SRA functionality

1. **NCBI SRA Tools** (Est: 2-3 days)
   - 4 new tools for SRA metadata and download URLs
   - Leverage existing `ncbi_eutils_tool` patterns
   - Test with common use cases (RNA-seq, WGS studies)

### Phase 2: Medium Priority (Week 2-3)
**Goal**: Expand ENCODE and add dbGaP metadata

2. **ENCODE Advanced Tools** (Est: 2 days)
   - 4 new tools extending `encode_tool.py`
   - File-level, biosample, and replicate queries
   - Comprehensive testing with real experiments

3. **dbGaP Metadata Tools** (Est: 1-2 days)
   - 4 new tools for study discovery
   - Open-access focus only
   - Link to SRA/GEO integration

### Phase 3: Low-Medium Priority (Week 3-4)
**Goal**: Alternative APIs and enhancement

4. **GeneBe REST API** (Est: 1 day)
   - 2 new tools for variant annotation
   - Complement existing gnomAD/ClinVar tools

5. **GTEx eQTL Verification** (Est: 0.5-1 day)
   - Audit existing `gtex_v2_tools`
   - Add missing eQTL/sQTL tools if needed

### Phase 4: Verification & Polish (Week 4)
**Goal**: Comprehensive testing and documentation

6. **ENA & ClinVar Verification** (Est: 1 day)
   - Verify existing tool coverage
   - Add missing features if identified

7. **Integration Testing** (Est: 1 day)
   - End-to-end workflows (e.g., GEO → SRA → analysis)
   - Cross-tool validation

---

## Effort Estimates

| Phase | Tools | Estimated Days | Priority |
|-------|-------|----------------|----------|
| Phase 1: SRA | 4 | 2-3 | HIGH |
| Phase 2: ENCODE + dbGaP | 8 | 3-4 | MEDIUM-HIGH |
| Phase 3: GeneBe + GTEx | 2-3 | 1.5-2 | MEDIUM |
| Phase 4: Verification | - | 2 | - |
| **Total** | **14-15 tools** | **8.5-11 days** | - |

---

## Technical Considerations

### API Rate Limits
- **ENCODE**: 10 requests/sec per user
- **gnomAD**: Unspecified but rate limited
- **GTEx**: No explicit limit mentioned
- **NCBI E-utilities**: 3 req/sec without API key, 10 req/sec with key

**Recommendation**: Implement rate limiting and caching in all tools

### Authentication Requirements
- **Public APIs**: No auth required (SRA, ENCODE, GTEx, gnomAD, ClinVar, GEO, ENA)
- **dbGaP Controlled Access**: Requires eRA Commons account (NOT FEASIBLE for ToolUniverse)
- **ClinVar Submission API**: Requires service account (not needed for retrieval)

### Data Volume Considerations
- **SRA**: Petabyte-scale data; return download URLs, not data itself
- **ENCODE**: File metadata can be large; implement pagination
- **GTEx**: Expression matrices can be large; consider limits
- **GEO**: FTP access for large datasets

---

## Next Steps

### Handoff to Implementation Agent

**Inputs Provided**:
1. ✅ API documentation links for all target APIs
2. ✅ Endpoint specifications and data schemas
3. ✅ Gap analysis with prioritization
4. ✅ Implementation roadmap with effort estimates
5. ✅ Technical considerations (rate limits, auth, data volumes)

**Recommended Start**:
- Begin with Phase 1: NCBI SRA tools (4 tools, ~3 days)
- Use existing `ncbi_eutils_tool.py` as template
- Coordinate with Testing Agent for real-world use case validation

**Open Questions for User**:
1. Should we prioritize SRA → ENCODE → dbGaP order, or adjust?
2. Do you want GeneBe API (alternative to gnomAD) or skip it?
3. Any specific genomics workflows to support (e.g., variant calling, expression analysis)?

---

## Sources

- [NCBI SRA Documentation](https://www.ncbi.nlm.nih.gov/sra/docs/)
- [ENCODE REST API Documentation](https://www.encodeproject.org/help/rest-api/)
- [GTEx Portal API](https://gtexportal.org/home/apiPage)
- [GTEx API v2 ReDoc](https://gtexportal.org/api/v2/redoc)
- [gnomAD Website](https://gnomad.broadinstitute.org/)
- [ENA Programmatic Access](https://ena-docs.readthedocs.io/en/latest/retrieval/programmatic-access.html)
- [dbGaP Home](https://www.ncbi.nlm.nih.gov/gap/)
- [ClinVar Accessing Data](https://www.ncbi.nlm.nih.gov/clinvar/docs/maintenance_use/)
- [ClinVar API Documentation](https://www.ncbi.nlm.nih.gov/clinvar/docs/api_http/)
- [GEO Programmatic Access](https://www.ncbi.nlm.nih.gov/geo/info/geo_paccess.html)
- [GeneBe API Documentation](https://genebe.net/about/api)

---

**Report Status**: ✅ Complete
**Next Agent**: Implementation Agent (Phase 1: NCBI SRA tools)
**Date Completed**: 2026-02-08
