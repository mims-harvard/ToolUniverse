# Clinical & EHR APIs - Research Report

**Date**: 2026-02-08
**Agent**: API Research Agent
**Status**: Phase 1 - Complete

## Executive Summary

This report documents available clinical and electronic health record (EHR) APIs, analyzes ToolUniverse's current coverage, identifies gaps, and prioritizes new integrations.

**Key Findings**:
- ToolUniverse has **limited clinical/EHR coverage** (2 major tools: UMLS, RxNorm)
- Major gaps in: FHIR, ICD codes, LOINC, SNOMED CT, CDS Hooks
- Clinical terminology standards are critical for healthcare interoperability
- Priority: ICD API > LOINC > CDS Hooks > FHIR (complex, lower priority)
- **Important**: Many clinical APIs require authentication/licenses

---

## Target APIs Researched

### 1. FHIR (Fast Healthcare Interoperability Resources)

**URL**: https://www.hl7.org/fhir/
**Type**: RESTful API standard (not a single API)
**Authentication**: Implementation-dependent

#### Capabilities
- Industry-wide standard for health data exchange
- RESTful APIs using HTTP operations (GET, POST, PUT, DELETE)
- Standardized resource types (Patient, Observation, Medication, etc.)
- JSON and XML support
- OAuth2 authentication
- Real-time interoperable data exchange

#### Current Status
- **FHIR Release 5** (Trial Use) released March 2023
- **FHIR R4** (1st Normative Content) from 2018 widely adopted
- CMS mandate: FHIR APIs for Patient Access, Provider Directory (2021+)
- Major cloud providers offer FHIR services (Azure, GCP, AWS)

#### Implementation Considerations
- FHIR is a **standard, not a single API**
- Each EHR vendor/provider implements their own FHIR server
- Public FHIR test servers available for development
- SMART on FHIR for app integration

#### Integration Complexity: **VERY HIGH**
- Not a single API but a framework/standard
- Multiple implementations across vendors
- Requires OAuth2, patient consent workflows
- PHI/HIPAA compliance considerations
- Each implementation varies in coverage

#### ToolUniverse Coverage
- ❌ **NO FHIR TOOLS**
- **CONSIDERATION**: Low priority for ToolUniverse
  - FHIR is vendor-specific (Epic, Cerner, etc.)
  - Requires institutional access and authentication
  - Not suitable for general research queries
  - Better suited for clinical application integration
- **RECOMMENDATION**: **SKIP** (not research-focused)

---

### 2. ICD-10/ICD-11 (International Classification of Diseases)

**URL**: https://icd.who.int/icdapi
**Docs**: https://icd.who.int/docs/icd-api/APIDoc-Version2/
**Type**: REST API (JSON)
**Authentication**: API key required (free registration)

#### Capabilities
- **ICD-10**: Diagnosis and procedure codes (current US standard)
- **ICD-11**: Next-generation classification (WHO adopted 2019, effective 2022)
- Disease classification and coding
- Mortality and morbidity statistics
- Multilingual support
- Search by disease name, code, or symptoms
- Hierarchical browsing
- Cross-walks between ICD versions

#### API Features
**ICD-11 API**:
- REST and FHIR-compliant
- Multilingual (50+ languages)
- Search by text or code
- Linearization (different use cases: mortality, morbidity, primary care)
- Post-coordination (detailed coding)

**ICD-10 Data**:
- 2026 ICD-10-CM codes available (effective Oct 2025)
- Free access to code lists and descriptions
- Various online resources (icd10data.com, etc.)

#### Data Schemas
- JSON responses with disease entities
- Hierarchical structure (chapters → categories → subcategories)
- Code, title, definition, inclusions, exclusions
- Cross-references and indexing terms

#### Integration Complexity: **MEDIUM**
- Well-documented REST API
- Free API key required
- ICD-11 API comprehensive
- ICD-10 may require third-party sources (WHO focuses on ICD-11)

#### ToolUniverse Coverage
- ❌ **NO ICD TOOLS**
- **MAJOR GAP**: Critical for disease coding and classification
  - Essential for clinical research
  - Disease prevalence and epidemiology
  - Drug indication mapping
  - Comorbidity analysis
- **HIGH VALUE**: Links to existing disease tools (OpenTargets, Orphanet)

---

### 3. SNOMED CT (Systematized Nomenclature of Medicine -- Clinical Terms)

**URL**: https://www.nlm.nih.gov/healthit/snomedct/
**API**: Multiple implementations (Snowstorm, NHS FHIR, etc.)
**Authentication**: Varies by implementation

#### Capabilities
- Comprehensive clinical terminology (400,000+ active concepts)
- Hierarchical concept relationships
- Clinical findings, procedures, body structures, organisms
- Supports clinical documentation and decision support
- Used worldwide (UK NHS, US VA, many countries)

#### API Implementations
**Snowstorm** (SNOMED International):
- REST API built on Elasticsearch
- High performance and scalability
- FHIR terminology service endpoints
- Concept search, relationships, hierarchies

**NHS FHIR Terminology Server**:
- **Note**: NHS developer servers decommissioned March 2, 2026
- Alternative implementations needed

**NLM UMLS Integration**:
- SNOMED CT accessible via UMLS API
- Source abbreviation: 'SNOMEDCT_US'

#### Integration Complexity: **MEDIUM-HIGH**
- Multiple API implementations with different capabilities
- SNOMED license required for use (free in many countries via national agreements)
- Complex concept model (hierarchies, relationships)
- Best accessed via UMLS API (already in ToolUniverse)

#### ToolUniverse Coverage
- ✅ **PARTIAL via UMLS** (`umls_tools.json`)
- **PARTIAL GAP**: SNOMED accessible through UMLS API
  - Current UMLS tools can filter by 'SNOMEDCT_US'
  - May lack SNOMED-specific features (relationships, hierarchies)
- **RECOMMENDATION**: Enhance UMLS tools for SNOMED queries
  - Add SNOMED-specific helper tools if needed
  - Consider standalone Snowstorm integration (MEDIUM priority)

---

### 4. LOINC (Logical Observation Identifiers Names and Codes)

**URL**: https://loinc.org/fhir/
**Type**: FHIR Terminology Server
**Authentication**: Free LOINC account required

#### Capabilities
- Laboratory and clinical observation codes (100,000+ terms)
- Test names, clinical measurements, survey instruments
- Lab results standardization (e.g., "hemoglobin", "blood glucose")
- Radiology codes, clinical notes, survey questions
- Answer lists and forms

#### API Features
**LOINC FHIR API** (https://fhir.loinc.org):
- FHIR terminology service endpoints
- Current version: LOINC 2.81 (versions 2.69-2.80 available)
- Operations: $lookup, $expand, $validate-code
- Concept search and value set expansion
- Translations and alternate names

**Alternative APIs**:
- **NIH Clinical Table Search Service**: Simpler REST API for LOINC questions/forms
- API Base URL: https://clinicaltables.nlm.nih.gov/api/loinc/

#### Current Status
- LOINC FHIR API has **BETA maturity** (not production-ready as of recent docs)
- Monthly updates with LOINC releases
- Requires authentication (free account)

#### Data Schemas
- FHIR CodeSystem and ValueSet resources
- JSON/XML formats
- LOINC codes with long/short names, component, system, scale, method

#### Integration Complexity: **MEDIUM**
- FHIR-based API (more complex than simple REST)
- Beta status may have limitations
- Authentication required
- Alternative NIH Clinical Tables API simpler

#### ToolUniverse Coverage
- ❌ **NO LOINC TOOLS**
- **MEDIUM-HIGH GAP**: Important for lab data and observations
  - Essential for interpreting clinical lab results
  - Standardizing test names across studies
  - Mapping phenotype data to observations
- **USE CASES**: Clinical data analysis, lab result interpretation, GWAS phenotypes

---

### 5. RxNorm (Medication Terminology)

**URL**: https://lhncbc.nlm.nih.gov/RxNav/APIs/index.html
**Type**: REST API
**Authentication**: None (free, open access)

#### Capabilities
- Normalized drug naming system (generic and branded drugs)
- RxCUI (unique drug identifiers)
- Drug relationships and hierarchies
- Ingredient mapping
- Dose form and strength information
- NDC (National Drug Code) mapping
- Drug interactions (via RxClass API)

#### API Suite
**RxNorm API**:
- Drug name lookup and spelling suggestions
- RxCUI retrieval by name or code
- Drug relationships and attributes
- Ingredient and strength queries

**RxTerms API**:
- Prescribable drug data
- Simpler than full RxNorm (clinical use)

**RxClass API**:
- Drug classes (ATC, MeSH, etc.)
- Class members and hierarchies
- Drug-class relationships

#### Data Formats
- JSON and XML responses
- No authentication required
- Monthly updates following RxNorm releases

#### Integration Complexity: **LOW**
- Simple REST API
- Well-documented
- No authentication
- Multiple specialized APIs

#### ToolUniverse Coverage
- ✅ **`rxnorm_tools.json` EXISTS**
- **VERIFY**: Check completeness of coverage
  - RxNorm API: drug lookup, relationships
  - RxClass API: drug classes
  - RxTerms API: prescribable content
- **PRIORITY**: LOW (likely good coverage, verify and extend if needed)

---

### 6. UMLS (Unified Medical Language System)

**URL**: https://documentation.uts.nlm.nih.gov/
**Type**: REST API
**Authentication**: API key required (free license)

#### Capabilities
- **160+ vocabularies** integrated (SNOMED CT, ICD-10, ICD-11, LOINC, RxNorm, MeSH, etc.)
- Concept search across all terminologies
- Cross-vocabulary mapping
- Semantic network (concept types and relationships)
- Multilingual support
- CUI (Concept Unique Identifiers)

#### API Endpoints
**Search**:
- `/search/current` - Search terms across vocabularies
- Filter by source (SNOMEDCT_US, ICD10CM, LOINC, RXNORM, etc.)

**Concepts**:
- `/content/current/CUI/{cui}` - Get concept details
- Atoms, attributes, definitions, relations

**Vocabularies**:
- `/metadata` - Source vocabulary information

#### Current Status
- **2025AB release** available (November 2025)
- API and Metathesaurus Browser updated
- Free license required (individual, no charge)

#### Data Schemas
- JSON responses
- Rich nested structures for concepts, atoms, relations
- Semantic types and groups

#### Integration Complexity: **MEDIUM**
- Well-documented REST API
- Requires free license and API key
- Complex data model (Metathesaurus structure)
- Powerful for cross-terminology mapping

#### ToolUniverse Coverage
- ✅ **`umls_tools.json` EXISTS**
- **VERIFY**: Check completeness
  - Search functionality
  - CUI lookup
  - Source-specific queries (ICD, SNOMED, LOINC via UMLS)
  - Cross-vocabulary mapping
- **PRIORITY**: LOW-MEDIUM (verify existing, extend if needed)

---

### 7. CDS Hooks (Clinical Decision Support Hooks)

**URL**: https://cds-hooks.org/
**Specs**: https://cds-hooks.hl7.org/
**Type**: RESTful API specification
**Authentication**: Implementation-dependent

#### Capabilities
- Real-time clinical decision support integration
- Hook-based pattern for EHR workflow integration
- Embed CDS into clinician workflow (e.g., prescribing, ordering)
- Return "cards" with recommendations, alerts, suggestions
- Launch SMART on FHIR apps from EHR context

#### Hooks Examples
- `patient-view`: Patient record opened
- `order-select`: Medication/order selected
- `order-sign`: Order about to be signed
- `encounter-start`: Encounter begins

#### CDS Service Components
**Discovery API**: Publish available CDS services
**Service API**: Request decision support
**Feedback API**: Learn outcomes of recommendations

#### Current Status
- **CDS Hooks 2.0.1** published early 2025
- **CDS Hooks Library 1.0.1** published early 2025
- HL7 published specification
- Open-source and free

#### Integration Complexity: **HIGH**
- Requires EHR integration
- Need CDS service infrastructure
- Authentication and security considerations
- Not standalone API but integration framework

#### ToolUniverse Coverage
- ❌ **NO CDS HOOKS TOOLS**
- **CONSIDERATION**: Lower priority for research use
  - Designed for EHR integration, not standalone queries
  - Requires clinical workflow context
  - More relevant for clinical applications than research
- **RECOMMENDATION**: MEDIUM-LOW priority (research-focused alternative CDS tools preferred)

---

### 8. MIMIC (Medical Information Mart for Intensive Care)

**URL**: https://physionet.org/content/mimiciv/
**Type**: Database download (not real-time API)
**Authentication**: PhysioNet credentialed account required

#### Capabilities
- **MIMIC-III**: 40,000+ ICU patients, 26 tables
- **MIMIC-IV**: 65,000+ ICU patients, 200,000+ ED patients
- De-identified EHR data:
  - Vital signs, lab results, medications, procedures
  - Clinical notes, imaging reports
  - Diagnoses (ICD codes), survival data
  - Fluid balance, charted observations

#### Access Methods
- **PhysioNet**: Download full dataset (credentialed access)
- **AWS**: Cloud-hosted for analysis (requires AWS account + PhysioNet approval)
- **PyHealth**: Python library for programmatic access
- **BigQuery**: Google BigQuery public dataset

#### Data Format
- Relational database (PostgreSQL schema)
- CSV files for download
- BigQuery tables for cloud analysis

#### Integration Complexity: **VERY HIGH**
- Not a real-time API (bulk data download)
- Requires credentialed access (training, approval)
- Large datasets (GBs of data)
- PHI concerns (de-identified but still regulated)
- Best suited for local analysis, not API queries

#### ToolUniverse Coverage
- ❌ **NO MIMIC TOOLS**
- **CONSIDERATION**: Not suitable for ToolUniverse API model
  - Bulk download, not query API
  - Requires credentialed access
  - Designed for local analysis, not real-time queries
- **RECOMMENDATION**: **SKIP** (not API-based)

---

## Gap Analysis

### Coverage Matrix

| API/Database | Current Status | Coverage Level | Research Value | Priority |
|--------------|----------------|----------------|----------------|----------|
| **FHIR** | ❌ Missing | 0% | Medium (EHR) | **SKIP** |
| **ICD-10/11** | ❌ Missing | 0% | Very High | **HIGH** |
| **SNOMED CT** | ✅ Partial (UMLS) | ~40% | High | MEDIUM |
| **LOINC** | ❌ Missing | 0% | High | **MEDIUM-HIGH** |
| **RxNorm** | ✅ Good | ~80% | High | LOW |
| **UMLS** | ✅ Good | ~70% | Very High | LOW-MEDIUM |
| **CDS Hooks** | ❌ Missing | 0% | Medium (clinical) | MEDIUM-LOW |
| **MIMIC** | ❌ Missing | 0% | High (research) | **SKIP** |

---

## Critical Gaps

### 1. **ICD-10/ICD-11 API** (Priority: HIGH)

**Why Important**:
- **Universal disease classification standard**
- Essential for epidemiology and public health
- Drug indication mapping (ICD codes used for approvals)
- Comorbidity analysis
- Clinical research inclusion/exclusion criteria
- Links disease names to standardized codes

**Missing Capabilities**:
- Search diseases by name or symptoms
- Get ICD codes for conditions
- Browse hierarchical disease classification
- Cross-reference ICD-10 ↔ ICD-11
- Multilingual disease names

**Recommended Tools** (4-5 tools):
1. `ICD11_search_diseases` - Search by disease name or symptoms
2. `ICD11_get_entity` - Get detailed disease entity by code
3. `ICD11_browse_hierarchy` - Navigate disease classification tree
4. `ICD10_get_code_info` - ICD-10-CM code details (2026 codes)
5. `ICD_crosswalk_codes` - Map between ICD-10 and ICD-11

**Implementation Notes**:
- ICD-11 API requires free registration for API key
- ICD-10 data available from icd10data.com and WHO
- Focus on ICD-11 (newer, WHO official API)
- Include ICD-10 for current US standard compatibility

**Integration Opportunities**:
- Link to OpenTargets disease IDs
- Connect to DrugBank indications
- Enhance disease-intelligence-gatherer skill

**Effort Estimate**: 2-3 days

---

### 2. **LOINC API** (Priority: MEDIUM-HIGH)

**Why Important**:
- Standard for lab tests and clinical observations
- Critical for clinical data interpretation
- Phenotype-lab result mapping
- GWAS phenotype standardization
- Clinical trial eligibility (lab criteria)

**Missing Capabilities**:
- Search lab tests by name
- Get LOINC codes for observations
- Access answer lists (e.g., blood type values)
- Forms and surveys (e.g., PHQ-9 depression)
- Unit conversion and reference ranges

**Recommended Tools** (3-4 tools):
1. `LOINC_search_tests` - Search lab tests and observations
2. `LOINC_get_code_details` - Detailed LOINC code information
3. `LOINC_get_answer_list` - Answer choices for coded values
4. `LOINC_search_forms` - Survey instruments and forms

**Implementation Notes**:
- LOINC FHIR API (beta status, requires free account)
- Alternative: NIH Clinical Table Search Service (simpler REST)
- Recommend starting with NIH Clinical Tables (easier)
- Consider FHIR API for advanced features later

**Integration Opportunities**:
- Link to phenotype databases (HPO, PhenomeNET)
- Clinical trial eligibility criteria
- GWAS study phenotype mapping

**Effort Estimate**: 2-3 days

---

### 3. **SNOMED CT Enhancements via UMLS** (Priority: MEDIUM)

**Current Status**: SNOMED accessible via existing UMLS tools

**Why Important**:
- Most comprehensive clinical terminology (400,000+ concepts)
- Used in UK NHS, US VA, many EHRs
- Clinical findings, procedures, organisms, body structures

**Potential Enhancements**:
- SNOMED-specific search helpers
- Concept hierarchy navigation
- Relationship queries (is-a, part-of, etc.)
- Preferred terms and synonyms

**Recommended Approach**:
1. **Audit existing UMLS tools** first
2. Test SNOMED queries via UMLS (source='SNOMEDCT_US')
3. If sufficient, document SNOMED usage patterns
4. If gaps, add SNOMED-specific wrapper tools

**Recommended Tools** (if needed, 2-3 tools):
1. `SNOMED_search_concepts` - Wrapper for UMLS SNOMED queries
2. `SNOMED_get_concept_hierarchy` - Navigate is-a relationships
3. `SNOMED_find_related_concepts` - Relationship exploration

**Effort Estimate**: 1-2 days (including audit)

---

### 4. **CDS Hooks Integration** (Priority: MEDIUM-LOW)

**Why Useful (but not critical)**:
- Standardized clinical decision support framework
- Could enable rule-based recommendations
- Workflow integration for clinical tools

**Challenges**:
- Designed for EHR integration, not research queries
- Requires clinical workflow context
- Need to build CDS services (not just consume API)

**Recommended Approach**:
- Lower priority for research-focused ToolUniverse
- Consider if building clinical applications
- Alternative: Build custom decision support tools using existing data

**Recommended Tools** (if implemented, 2-3 tools):
1. `CDSHooks_discover_services` - Find available CDS services
2. `CDSHooks_invoke_hook` - Trigger decision support
3. `CDSHooks_parse_cards` - Process recommendations

**Effort Estimate**: 3-4 days (complex, requires infrastructure)
**Recommendation**: **DEFER** to later phase or skip

---

## Secondary Gaps and Considerations

### 5. **RxNorm Verification** (Priority: LOW)

**Current Status**: `rxnorm_tools.json` exists

**Verification Needed**:
- Audit existing tools for completeness
- Check coverage of RxNorm, RxClass, RxTerms APIs
- Ensure drug relationships, classes, and prescribable content accessible

**Potential Additions** (if missing):
- RxClass drug-class queries
- Ingredient-based searches
- NDC code mapping

**Effort Estimate**: 0.5-1 day

---

### 6. **UMLS Enhancements** (Priority: LOW-MEDIUM)

**Current Status**: `umls_tools.json` exists

**Verification Needed**:
- Audit for concept lookup, search, cross-vocabulary mapping
- Test filtering by specific sources (ICD, SNOMED, LOINC)

**Potential Additions**:
- Semantic network queries
- Relation browsing
- Atom-level access

**Effort Estimate**: 1 day

---

## Prioritized Implementation Roadmap

### Phase 1: High Priority - Disease Classification (Week 1)
**Goal**: Add critical ICD disease coding capability

**1. ICD-10/ICD-11 API Tools** (Est: 2-3 days)
- 4-5 tools for disease search, entity lookup, crosswalks
- Highest research value for disease-related queries
- Integrates with existing disease tools

**Phase 1 Total**: 2-3 days, 4-5 tools

---

### Phase 2: Medium Priority - Clinical Observations (Week 2)
**Goal**: Add lab test and clinical observation standardization

**2. LOINC API Tools** (Est: 2-3 days)
- 3-4 tools for lab test lookup and observation coding
- Important for clinical data interpretation
- Use NIH Clinical Tables API (simpler than FHIR)

**Phase 2 Total**: 2-3 days, 3-4 tools

---

### Phase 3: Audits & Enhancements (Week 2-3)
**Goal**: Verify and extend existing tools

**3. SNOMED CT Enhancement** (Est: 1-2 days)
- Audit existing UMLS tools for SNOMED access
- Add SNOMED-specific wrappers if needed
- Document SNOMED usage patterns

**4. RxNorm Verification** (Est: 0.5-1 day)
- Audit existing rxnorm_tools
- Add missing RxClass or RxTerms features

**5. UMLS Verification** (Est: 1 day)
- Audit umls_tools completeness
- Add missing features (semantic network, relations)

**Phase 3 Total**: 2.5-4 days

---

### Phase 4: Optional - CDS Integration (Week 3-4)
**Goal**: Clinical decision support (lower priority)

**6. CDS Hooks** (Est: 3-4 days)
- Build CDS service infrastructure
- API integration for hook invocation
- Card parsing and recommendation display

**Phase 4 Total**: 3-4 days, 2-3 tools
**Recommendation**: **DEFER** or **SKIP** (research focus)

---

## Effort Estimates

| Phase | Focus | Tools | Estimated Days | Priority |
|-------|-------|-------|----------------|----------|
| Phase 1 | ICD API | 4-5 | 2-3 | HIGH |
| Phase 2 | LOINC API | 3-4 | 2-3 | MEDIUM-HIGH |
| Phase 3 | Audits & Enhance | Varies | 2.5-4 | MEDIUM |
| Phase 4 | CDS Hooks (optional) | 2-3 | 3-4 | LOW (DEFER) |
| **Total (no CDS)** | | **7-9 tools** | **6.5-10 days** | |
| **Total (with CDS)** | | **9-12 tools** | **9.5-14 days** | |

**Recommended Focus**: Phase 1 + Phase 2 + Phase 3 (audit only) = ~6-8 days

---

## Technical Considerations

### API Authentication Requirements

| API | Auth Required | License | Cost |
|-----|--------------|---------|------|
| **ICD-11** | API key | Free registration | Free |
| **LOINC** | Free account | Free | Free |
| **RxNorm** | None | None | Free |
| **UMLS** | API key | Free individual license | Free |
| **SNOMED CT** | Via UMLS or license | Country-dependent | Free (US via NLM) |
| **CDS Hooks** | Implementation-dependent | N/A | Free (spec) |
| **FHIR** | Vendor-dependent | EHR access | Varies |

**All priority APIs are free with registration**

### Rate Limits and Throttling
- **ICD-11**: Not specified, assume conservative limits
- **LOINC FHIR**: Beta status, limits unclear
- **LOINC Clinical Tables**: NLM infrastructure, likely lenient
- **RxNorm**: Monthly updates, no explicit limits mentioned
- **UMLS**: Not specified, assume moderate limits

**Recommendation**: Implement caching and rate limiting for all tools

### PHI and Compliance
- All APIs provide **de-identified reference data**
- No patient-specific data transmitted
- HIPAA not applicable for terminology/classification APIs
- FHIR and EHR APIs **would** require HIPAA compliance (not in scope)

---

## Use Case Synergies

### Enhanced Drug Discovery Workflows

**Current ToolUniverse Capabilities**:
- Targets, compounds, ADMET, literature

**Clinical/EHR Additions Enable**:
1. **ICD Codes**: Map disease indications to standardized codes
2. **LOINC**: Interpret lab results for inclusion/exclusion criteria
3. **RxNorm**: Standardize drug names across data sources

**Example Workflow**:
```
Disease (ICD-11) → Targets (OpenTargets) → Drugs (DrugBank/RxNorm)
→ Clinical Trials (ClinicalTrials.gov with ICD/LOINC criteria)
→ Literature (PubMed with standardized terms)
```

### Clinical Research and Phenotyping

**Current**: Disease, genomics, literature
**Enhanced with Clinical APIs**:
- ICD codes for epidemiology
- LOINC for lab phenotypes
- SNOMED for clinical findings
- UMLS for cross-terminology mapping

---

## Important Notes

### FHIR Decision Rationale

**Why SKIP FHIR**:
1. **Not a single API** - FHIR is a standard, not a centralized service
2. **Vendor-specific** - Each EHR has its own FHIR implementation
3. **Authentication complex** - Requires institutional access, OAuth2, patient consent
4. **PHI/HIPAA** - Dealing with protected health information
5. **Not research-focused** - Designed for clinical care data exchange
6. **ToolUniverse scope** - Primarily scientific research, not EHR integration

**When FHIR makes sense**:
- Building clinical applications
- Integrating with specific EHR systems
- Patient-facing health apps
- Provider-facing clinical tools

**For ToolUniverse**: Terminology and classification APIs (ICD, LOINC, RxNorm, UMLS) provide research value without EHR complexity

### MIMIC Database Decision Rationale

**Why SKIP MIMIC**:
1. **Not an API** - Bulk data download, not real-time queries
2. **Credentialed access** - Requires PhysioNet approval, training
3. **Large datasets** - GBs of data, designed for local analysis
4. **Not query-oriented** - Load into database, analyze locally
5. **PHI considerations** - De-identified but still regulated

**When MIMIC makes sense**:
- Clinical ML model training
- ICU outcome prediction research
- Retrospective cohort studies
- Academic research projects

**For ToolUniverse**: Focus on APIs for real-time queries, not bulk datasets

---

## Next Steps

### Handoff to Implementation Agent

**Inputs Provided**:
1. ✅ API documentation links for all target APIs
2. ✅ Authentication requirements and licensing
3. ✅ Gap analysis with prioritization
4. ✅ Implementation roadmap with effort estimates
5. ✅ Technical considerations and integration opportunities
6. ✅ Clear recommendations on which APIs to skip and why

**Recommended Start**:
- **Phase 1**: ICD-10/ICD-11 API tools (2-3 days, 4-5 tools)
- **Rationale**: Highest research value, fills critical gap, integrates well
- **Then Phase 2**: LOINC API tools (2-3 days, 3-4 tools)

**Audits First** (Phase 3):
- Verify `umls_tools.json` coverage of SNOMED queries
- Verify `rxnorm_tools.json` completeness
- Determine if enhancements needed before implementation

**Open Questions for User**:
1. Start with ICD-11 (WHO official, newer) or ICD-10 (current US standard)?
   - Recommendation: ICD-11 first, then ICD-10 crosswalk
2. LOINC FHIR API (comprehensive, beta) or NIH Clinical Tables (simpler, stable)?
   - Recommendation: NIH Clinical Tables for MVP, FHIR later if needed
3. Build CDS Hooks tools (Phase 4) or skip entirely?
   - Recommendation: Skip (defer to clinical application focus)
4. Should we enhance SNOMED via standalone API or keep via UMLS?
   - Recommendation: Audit UMLS first, decide after

---

## Sources

- [FHIR Overview](https://www.hl7.org/fhir/overview.html)
- [HL7 FHIR Foundation](https://www.fhir.org/)
- [ICD API Homepage](https://icd.who.int/icdapi)
- [ICD-11 Documentation](https://icd.who.int/en/)
- [ICD API Version 2 Docs](https://icd.who.int/docs/icd-api/APIDoc-Version2/)
- [2026 ICD-10-CM Codes](https://www.icd10data.com/)
- [SNOMED CT - NLM](https://www.nlm.nih.gov/healthit/snomedct/index.html)
- [SNOMED International Terminology Services](https://www.implementation.snomed.org/terminology-services)
- [LOINC FHIR API](https://loinc.org/fhir/)
- [LOINC Clinical Tables API](https://clinicaltables.nlm.nih.gov/apidoc/loinc/v3/doc.html)
- [RxNav APIs](https://lhncbc.nlm.nih.gov/RxNav/APIs/index.html)
- [RxNorm Overview](https://www.nlm.nih.gov/research/umls/rxnorm/overview.html)
- [UMLS REST API Documentation](https://documentation.uts.nlm.nih.gov/)
- [UMLS Homepage](https://www.nlm.nih.gov/research/umls/index.html)
- [CDS Hooks](https://cds-hooks.org/)
- [CDS Hooks 2.0](https://cds-hooks.hl7.org/2.0/)
- [MIMIC-IV Database](https://physionet.org/content/mimiciv/)
- [MIMIC-III on AWS](https://registry.opendata.aws/mimiciii/)

---

**Report Status**: ✅ Complete
**Next Agent**: Implementation Agent (Phase 1: ICD-10/11 API tools)
**Audit Needed**: UMLS and RxNorm existing tool coverage
**Date Completed**: 2026-02-08
