# Clinical Guidelines Tools - Quick Reference

Complete parameter reference for all 41 tools across 4 JSON config files.
All parameters listed are verified by live API testing.

---

## unified_guideline_tools.json (14 tools)

### WHO_Guidelines_Search
- **Parameters**: `query` (str, required), `limit` (int, required)
- **Returns**: list of `{title, url, description, content, source}`
- **Note**: Results not reliably filtered by topic; may return unrelated recent WHO publications

### WHO_Guideline_Full_Text
- **Parameters**: `url` (str, required)
- **Returns**: dict with guideline text (or PDF link)

### GIN_Guidelines_Search
- **Parameters**: `query` (str, required), `limit` (int, required)
- **Returns**: list of `{title, url, description, source, organization}`

### CMA_Guidelines_Search
- **Parameters**: `query` (str, required), `limit` (int, required)
- **Returns**: list of `{title, url, description, content, date}`

### SIGN_search_guidelines
- **Parameters**: `query` (str, required — NOT `q`), `limit` (int, optional)
- **Returns**: list of `{number, title, topic, published, url}`

### SIGN_list_guidelines
- **Parameters**: `limit` (int, optional)
- **Returns**: list of all SIGN guidelines

### CTFPHC_list_guidelines
- **Parameters**: `limit` (int, optional)
- **Returns**: list of `{title, url, year}`

### CTFPHC_search_guidelines
- **Parameters**: `query` (str, required — NOT `q`), `limit` (int, optional)
- **Returns**: list of `{title, url, year}`

### TRIP_Database_Guidelines_Search
- **Parameters**: `query` (str, required), `limit` (int, required), `search_type` (str, required — must be `'guidelines'`)
- **Returns**: list of `{title, url, description, content, publication}`

### OpenAlex_Guidelines_Search
- **Parameters**: `query` (str, required), `limit` (int, required), `year_from` (int, **optional**), `year_to` (int, **optional**)
- **Returns**: list of `{title, authors, institutions, year, doi}`

### EuropePMC_Guidelines_Search
- **Parameters**: `query` (str, required), `limit` (int, required)
- **Returns**: list of `{title, pmid, pmcid, doi, authors}`

### PubMed_Guidelines_Search
- **Parameters**: `query` (str, required), `limit` (int, required), `api_key` (str, **optional** — use `''` or omit)
- **Returns**: list of `{title, pmid, pmcid, doi}`

### NICE_Clinical_Guidelines_Search
- **Parameters**: `query` (str, required), `limit` (int, required)
- **Returns**: list of `{title, url, summary, content, date}`

### NICE_Guideline_Full_Text
- **Parameters**: `url` (str, required)
- **Returns**: dict with guideline text (may be empty; try `.../chapter/Recommendations` URL)

---

## cpic_tools.json (15 tools)

All CPIC tools return **dict-wrapped**: access via `r.get('data', [])` or `r.get('data', {})`.

### CPIC_get_gene_info
- **Parameters**: `genesymbol` (str, required)
- **Returns**: dict `{data: {symbol, name, locus, ...}}`
- **Example**: `CPIC_get_gene_info(genesymbol='CYP2D6')`

### CPIC_get_gene_drug_pairs
- **Parameters**: `genesymbol` (str, required), `limit` (int, optional)
- **Returns**: dict `{data: [{genesymbol, drugid, cpiclevel, pgkbcalevel, usedforrecommendation}, ...]}`
- **Note**: `cpiclevel` A/B/C/D — A = strongest evidence

### CPIC_list_guidelines
- **Parameters**: `limit` (int, optional)
- **Returns**: dict `{data: [{name, guidelineId, url, ...}, ...]}`
- **Use**: Find `guidelineId` for calling `CPIC_get_recommendations`

### CPIC_get_recommendations
- **Parameters**: `guideline_id` (int, required — NOT `genesymbol`), `limit` (int, optional)
- **Returns**: dict `{data: [{phenotype, recommendation, activity_score, ...}, ...]}`
- **⚠️ CRITICAL**: Parameter is `guideline_id` (integer from CPIC_list_guidelines), NOT gene symbol
- **Note**: Returns duplicate records per allele combo — deduplicate by phenotype before presenting
- **Example**: `CPIC_get_recommendations(guideline_id=100416, limit=20)`

### CPIC_get_alleles
- **Parameters**: `genesymbol` (str, required), `limit` (int, optional)
- **Returns**: dict `{data: [{haplotype_name, clinicalfunctionalstatus, ...}, ...]}`
- **⚠️ Use `clinicalfunctionalstatus`** — not `functionalstatus` (always null)

### CPIC_get_drug_info
- **Parameters**: `drugname` (str, required)
- **Returns**: dict `{data: {name, rxNormId, ...}}`
- **Example**: `CPIC_get_drug_info(drugname='codeine')`

### CPIC_search_gene_drug_pairs
- **Parameters**: `genesymbol` (str, required with PostgREST syntax), `limit` (int, optional)
- **⚠️ CRITICAL**: Use PostgREST filter: `genesymbol='eq.CYP2D6'` (not just `'CYP2D6'`)
- **Example**: `CPIC_search_gene_drug_pairs(genesymbol='eq.CYP2D6', limit=5)`

### CPIC_list_drugs
- **Parameters**: `limit` (int, optional)
- **Returns**: dict `{data: [{name, rxNormId, ...}, ...]}`

### CPIC_list_genes
- **Parameters**: `limit` (int, optional)
- **Returns**: dict `{data: [{symbol, name, ...}, ...]}`

### CPIC_search_drugs
- **Parameters**: `name` (str, required)
- **Returns**: dict `{data: [...]}`

### CPIC_get_guideline
- **Parameters**: `guideline_id` (int, required)
- **Returns**: dict `{data: {name, url, ...}}`

### CPIC_get_gene_phenotypes
- **Parameters**: `genesymbol` (str, required)
- **Returns**: dict `{data: [...]}`

### CPIC_get_publication
- **Parameters**: `pmid` (str, required)
- **Returns**: dict `{data: {...}}`

### CPIC_list_publications
- **Parameters**: `limit` (int, optional)
- **Returns**: dict `{data: [...]}`

### CPIC_get_frequency_data
- **Parameters**: `genesymbol` (str, required)
- **Returns**: dict `{data: [...]}`

---

## ada_aha_nccn_tools.json (18 tools)

### ADA_list_standards_sections
- **Parameters**: none
- **Returns**: list of ADA Standards of Care sections with PMIDs

### ADA_search_standards
- **Parameters**: `query` (str, required), `limit` (int, required)
- **Returns**: list of `{title, ...}`
- **Note**: Use broad medical terms. Filter: `'[corp] American Diabetes Association'[Author]`

### ADA_get_standards_section
- **Parameters**: `section_number` (int, required)
- **Returns**: dict with abstract (not full PMC text)

### ADA_get_full_standard
- **Parameters**: `pmid` (str, required)
- **Returns**: dict with full text content

### AHA_ACC_search_guidelines
- **Parameters**: `query` (str, required), `limit` (int, required)
- **Returns**: list directly — `[{title, ...}]`
- **Example**: `AHA_ACC_search_guidelines(query='heart failure management', limit=5)`

### AHA_list_guidelines
- **Parameters**: `limit` (int, required)
- **Returns**: list of recent AHA guidelines

### ACC_list_guidelines
- **Parameters**: `limit` (int, required)
- **Returns**: list of recent ACC guidelines

### AHA_ACC_get_guideline
- **Parameters**: `pmid` (str, required)
- **Returns**: dict with full guideline text from PMC

### AHA_search_statements
- **Parameters**: `query` (str, required), `limit` (int, required)
- **Returns**: list

### ACC_search_guidelines
- **Parameters**: `query` (str, required), `limit` (int, required)
- **Returns**: list

### NCCN_list_patient_guidelines
- **Parameters**: `limit` (int, required)
- **Returns**: list of `{cancer_type, url, category}`
- **⚠️ Field is `cancer_type`**, NOT `title`

### NCCN_search_guidelines
- **Parameters**: `query` (str, required), `limit` (int, required)
- **Returns**: list of JNCCN PubMed abstracts
- **Note**: Returns PubMed articles about NCCN guidelines, not proprietary guideline text

### NCCN_get_patient_guideline
- **Parameters**: `url` (str, required — full URL string)
- **Returns**: dict with patient guideline text
- **⚠️ CRITICAL**: Pass full URL, NOT integer ID
- **Example**: `NCCN_get_patient_guideline(url='https://www.nccn.org/patientresources/patient-resources/guidelines-for-patients/guidelines-for-patients-details?patientGuidelineId=61')`

### NCI_search_cancer_resources
- **Parameters**: `q` (str, required — NOT `query`), `size` (int, required — NOT `limit`)
- **Returns**: dict → `r.get('data', {}).get('results', [])` gives list
- **⚠️ NOTE**: This is a catalog of bioinformatics tools/datasets, NOT clinical guidelines

### NCI_list_cancer_types
- **Parameters**: `limit` (int, optional)
- **Returns**: list

### NCI_get_cancer_resource
- **Parameters**: `resource_id` (str, required)
- **Returns**: dict

### MAGICapp_list_guidelines
- **Parameters**: `limit` (int, required)
- **Returns**: dict → `r.get('data', [])` gives list of `{name, guidelineId, ...}`
- **⚠️ Field is `name`**, NOT `title`

### MAGICapp_get_guideline
- **Parameters**: `guideline_id` (str, required)
- **Returns**: dict → `r.get('data', {})` gives guideline details

---

## sign_ctfphc_tools.json (15 tools)

*(SIGN and CTFPHC tools listed above in unified_guideline_tools.json section also appear here — same interface)*

### MAGICapp_get_recommendations
- **Parameters**: `guideline_id` (str, required)
- **Returns**: dict → `r.get('data', [])` gives list of recommendations

### MAGICapp_get_sections
- **Parameters**: `guideline_id` (str, required)
- **Returns**: dict → `r.get('data', [])` gives list of sections

---

## Quick Decision Guide

| Clinical question type | Start with |
|------------------------|------------|
| General disease guideline | NICE + GIN + TRIP |
| UK-specific | NICE + SIGN |
| Canadian | CMA + CTFPHC |
| International | GIN + OpenAlex |
| Cardiology | AHA_ACC_search_guidelines + AHA_list_guidelines |
| Oncology | NCCN_search_guidelines + NCCN_list_patient_guidelines |
| Diabetes | ADA_list_standards_sections + ADA_search_standards |
| Pharmacogenomics | CPIC workflow (gene_info → drug_pairs → list_guidelines → recommendations) |
| Living/current | MAGICapp_list_guidelines |
| Research tools/datasets | NCI_search_cancer_resources (not clinical guidelines!) |
