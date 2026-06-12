# Research Protocol: Step-by-Step Procedures

## Step 1: Initialize Report

```python
from datetime import datetime

def create_report_file(disease_name):
    """Create initial report file with template"""
    filename = f"{disease_name.lower().replace(' ', '_')}_research_report.md"

    template = f"""# Disease Research Report: {disease_name}

**Report Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M')}
**Disease Identifiers**: Pending research...

---

## Executive Summary

*Research in progress...*

---

## 1. Disease Identity & Classification
*Researching...*

## 2. Clinical Presentation
*Pending...*

[... rest of template ...]
"""

    with open(filename, 'w') as f:
        f.write(template)

    return filename
```

## Step 2: Research Each Dimension with Citations

For EACH piece of information, track:
- **Tool name** that provided the data
- **Parameters** used in the query
- **Timestamp** of the query

```python
def research_with_citations(tu, disease_name, report_file):
    """Research and update report with full citations"""

    references = []  # Track all sources

    # === DIMENSION 1: Identity ===

    # Get EFO ID
    efo_result = tu.tools.OSL_get_efo_id_by_disease_name(disease=disease_name)
    efo_id = efo_result.get('efo_id')
    references.append({
        'tool': 'OSL_get_efo_id_by_disease_name',
        'params': {'disease': disease_name},
        'section': 'Identity'
    })

    # Get ICD codes
    icd_result = tu.tools.icd_search_codes(query=disease_name, version="ICD10CM")
    references.append({
        'tool': 'icd_search_codes',
        'params': {'query': disease_name, 'version': 'ICD10CM'},
        'section': 'Identity'
    })

    # Get UMLS
    umls_result = tu.tools.umls_search_concepts(query=disease_name)
    references.append({
        'tool': 'umls_search_concepts',
        'params': {'query': disease_name},
        'section': 'Identity'
    })

    # Get synonyms from EFO
    if efo_id:
        efo_term = tu.tools.ols_get_efo_term(obo_id=efo_id.replace('_', ':'))
        references.append({
            'tool': 'ols_get_efo_term',
            'params': {'obo_id': efo_id},
            'section': 'Identity'
        })

        # Get subtypes
        children = tu.tools.ols_get_efo_term_children(obo_id=efo_id.replace('_', ':'), size=20)
        references.append({
            'tool': 'ols_get_efo_term_children',
            'params': {'obo_id': efo_id, 'size': 20},
            'section': 'Identity'
        })

    # UPDATE REPORT FILE with Identity section
    update_report_section(report_file, 'Identity', {
        'efo_id': efo_id,
        'icd_codes': icd_result,
        'umls': umls_result,
        'synonyms': efo_term.get('synonyms', []) if efo_term else [],
        'subtypes': children
    }, references[-5:])  # Last 5 references for this section

    # === DIMENSION 2: Clinical ===
    # ... continue for all dimensions
```

## Step 3: Update Report File After Each Dimension

```python
# After each dimension's research completes:

# 1. Read current report
with open(report_file, 'r') as f:
    report = f.read()

# 2. Replace placeholder with formatted content
report = report.replace(
    "## 3. Genetic & Molecular Basis\n*Pending...*",
    formatted_genetics_section
)

# 3. Write back immediately
with open(report_file, 'w') as f:
    f.write(report)

# 4. Continue to next dimension
```

## Step 4: Format Section Content

```python
def format_identity_section(data, sources):
    """Format Identity section with proper citations"""

    source_list = ', '.join([s['tool'] for s in sources])

    return f"""## 1. Disease Identity & Classification

### Ontology Identifiers
| System | ID | Source |
|--------|-----|--------|
| EFO | {data['efo_id']} | OSL_get_efo_id_by_disease_name |
| ICD-10 | {data['icd_codes']} | icd_search_codes |
| UMLS CUI | {data['umls']} | umls_search_concepts |

### Synonyms & Alternative Names
{format_list_with_source(data['synonyms'], 'ols_get_efo_term')}

### Disease Subtypes
{format_list_with_source(data['subtypes'], 'ols_get_efo_term_children')}

**Sources**: {source_list}
"""
```

## Final Report Quality Checklist

Before presenting to user, verify:

- [ ] All 10 sections have content (or marked as "No data available")
- [ ] Every data point has a source citation
- [ ] Executive summary reflects key findings
- [ ] References section lists all tools used
- [ ] Tables are properly formatted
- [ ] No placeholder text remains

## Expected Output Scale

For a disease like "Alzheimer's Disease", the final report should be 2000+ lines with:

- **Section 1**: 5+ ontology IDs, 10+ synonyms, disease hierarchy
- **Section 2**: 20+ phenotypes with HPO IDs, symptoms list
- **Section 3**: 50+ genes with scores, 30+ GWAS associations, 100+ ClinVar variants
- **Section 4**: 20+ drugs, 50+ clinical trials with details
- **Section 5**: 10+ pathways, PPI network, expression data
- **Section 6**: 100+ publications, citation analysis, institution list
- **Section 7**: 15+ similar diseases with similarity scores
- **Section 8**: (if cancer) variants, evidence items
- **Section 9**: Pharmacological targets and interactions
- **Section 10**: Drug warnings, adverse events

Total: Detailed report with 500+ individual data points, each with source citation.
