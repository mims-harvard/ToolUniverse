---
name: tooluniverse-cancer-classification
description: >
  Translate free-text tumor descriptions to OncoTree codes, look up cancer subtypes and tissue
  hierarchies, resolve UMLS/NCI cross-references, and obtain OncoKB-compatible tumor type codes
  for variant annotation. Use when asked to find the OncoTree code for a tumor type, enumerate
  subtypes of a cancer, list cancers by tissue of origin, or standardize tumor nomenclature for
  downstream precision oncology analysis.
---

# Cancer Classification via OncoTree

Standardize cancer type nomenclature using the OncoTree ontology. Resolves free-text tumor
descriptions to structured codes with UMLS/NCI cross-references, enabling downstream use in
OncoKB variant annotation and GDC cohort selection.

## When to Use

Apply when researcher asks about:
- "What is the OncoTree code for [tumor description]?"
- "Find all subtypes of [cancer type]"
- "What cancers originate in [tissue]?"
- "I need the tumor type code for OncoKB annotation"
- "What is the TCGA/COSMIC code for [cancer]?"
- "List all CNS/Brain cancer subtypes"
- "What NCI code corresponds to glioblastoma?"

## Key Tools

| Tool | Purpose | Key Params |
|------|---------|-----------|
| `OncoTree_search` | Free-text search for cancer types | `query` (tumor name or description) |
| `OncoTree_get_type` | Full details for a known OncoTree code | `code` (e.g., "LUAD", "AML") |
| `OncoTree_list_tissues` | List all 32 tissue categories | (no params) |
| `OncoKB_annotate_variant` | Variant annotation using OncoTree code | `gene`, `variant`, `tumor_type` |
| `GDC_get_mutation_frequency` | Pan-cancer mutation frequency (TCGA) | `gene_symbol` |

## Workflow

### Phase 1: Cancer Type Discovery

Start with free-text search to find matching OncoTree codes:

```
OncoTree_search(query="breast cancer")
-> Returns list: code, name, main_type, tissue, parent, level, external_references
```

Key response fields:
- `code`: OncoTree code (e.g., "BRCA", "IBC") — use this in OncoKB calls
- `level`: hierarchy depth (1=tissue, 2=main type, 3-5=subtypes)
- `parent`: parent node code for navigating the hierarchy
- `external_references.UMLS`: UMLS CUI list
- `external_references.NCI`: NCI thesaurus code list

Search tips:
- Broad terms ("lung cancer") return many results; narrow by tissue or level
- Use tissue-specific terms ("invasive breast carcinoma") for precise matching
- Acronyms work: query="GBM" finds glioblastoma, query="AML" finds leukemia types

### Phase 2: Code Validation and Detail Retrieval

Once you have a candidate code, retrieve full details:

```
OncoTree_get_type(code="LUAD")
-> Returns: name, main_type, tissue, color, parent, level, history, external_references
```

Note: Not all codes are valid. "GBM" returns 404 — correct code is "GB" (Glioblastoma, IDH-Wildtype).
Always validate via `OncoTree_get_type` before using in downstream tools.

### Phase 3: Tissue-Level Exploration

When the user wants all cancers in a tissue category:

```
OncoTree_list_tissues()
-> Returns 32 tissue names: "Breast", "CNS/Brain", "Lung", "Myeloid", ...

OncoTree_search(query="CNS/Brain")
-> All cancer types with tissue="CNS/Brain"
```

### Phase 4: Downstream Use in Variant Annotation

Pass validated OncoTree code to OncoKB for cancer-type-specific therapeutic levels:

```
OncoKB_annotate_variant(gene="EGFR", variant="L858R", tumor_type="LUAD")
-> highestSensitiveLevel: "1" (FDA-approved therapy for this tumor+variant)
```

Without `tumor_type`, OncoKB returns pan-cancer levels which may be less specific.

## Tool Parameter Reference

| Tool | Required | Optional | Notes |
|------|---------|---------|-------|
| `OncoTree_search` | `query` | — | Free text; returns list sorted by relevance |
| `OncoTree_get_type` | `code` | — | Case-sensitive; "BRCA" not "brca". Returns 404 for invalid codes |
| `OncoTree_list_tissues` | — | — | No params; returns list of 32 tissue strings |
| `OncoKB_annotate_variant` | `gene`, `variant` | `tumor_type` | `tumor_type` is OncoTree code; omit for pan-cancer |
| `GDC_get_mutation_frequency` | `gene_symbol` | — | Pan-cancer TCGA only; no per-subtype breakdown |

## Common OncoTree Codes (verified working)

| Code | Name | Tissue |
|------|------|--------|
| `BRCA` | Invasive Breast Carcinoma | Breast |
| `LUAD` | Lung Adenocarcinoma | Lung |
| `LUSC` | Lung Squamous Cell Carcinoma | Lung |
| `MEL` | Melanoma | Skin |
| `CRC` | Colorectal Cancer | Bowel |
| `PAAD` | Pancreatic Adenocarcinoma | Pancreas |
| `GBM` | (invalid — use `GB`) | CNS/Brain |
| `GB` | Glioblastoma, IDH-Wildtype | CNS/Brain |
| `AML` | Acute Myeloid Leukemia | Myeloid |
| `PRAD` | Prostate Adenocarcinoma | Prostate |

## Common Patterns

```python
# Pattern: Resolve free-text to OncoTree code
results = OncoTree_search(query="pancreatic ductal adenocarcinoma")
# Pick result with lowest level number (most specific match)
code = results["data"][0]["code"]  # e.g., "PAAD"

# Pattern: Get all subtypes within a main type
results = OncoTree_search(query="Glioma")
subtypes = [r for r in results["data"] if r["main_type"] == "Glioma"]

# Pattern: Validate code before OncoKB call
detail = OncoTree_get_type(code="GB")
if detail["status"] == "success":
    OncoKB_annotate_variant(gene="IDH1", variant="R132H", tumor_type="GB")
```

## Reasoning Framework for Result Interpretation

### Evidence Grading

| Grade | Criteria | Example |
|-------|----------|---------|
| **Confirmed** | Exact OncoTree code validated via `OncoTree_get_type`, UMLS + NCI cross-refs present | LUAD: validated, UMLS C0152013, NCI C3512 |
| **Probable** | OncoTree search returns match, but code not yet validated or missing cross-refs | Search for "cholangiocarcinoma" returns CHOL with partial external refs |
| **Ambiguous** | Multiple OncoTree codes match the description at different hierarchy levels | "Breast cancer" matches BRCA (invasive), BREAST (tissue), IBC (inflammatory) |
| **Unresolved** | No OncoTree match; tumor type too rare or novel for the ontology | Ultra-rare sarcoma subtype not in OncoTree |

### Interpretation Guidance

- **OncoTree code confidence**: Always validate candidate codes with `OncoTree_get_type` before downstream use. Some common acronyms (e.g., "GBM") are NOT valid OncoTree codes (correct code is "GB"). A validated code with UMLS and NCI cross-references is highest confidence.
- **UMLS/NCI cross-reference priority**: For standardized reporting, NCI Thesaurus codes are preferred for cancer-specific contexts (used by caDSR, GDC). UMLS CUIs are broader (cross-disease) and useful for literature mining. When both are available, report both; when only one exists, NCI is preferred for oncology workflows.
- **Tissue hierarchy interpretation**: OncoTree levels represent specificity: Level 1 = tissue of origin (e.g., "Lung"), Level 2 = main cancer type (e.g., "Non-Small Cell Lung Cancer"), Level 3+ = histological subtypes (e.g., "Lung Adenocarcinoma"). For OncoKB variant annotation, use the most specific (deepest) level that accurately describes the tumor. For cohort-level analysis (e.g., TCGA), the Level 2-3 code is typically appropriate.
- **OncoKB tumor type impact**: Providing a tumor type code to OncoKB can change the therapeutic level (e.g., EGFR L858R is Level 1 in LUAD but Level 3B pan-cancer). Always use the validated OncoTree code for the patient's specific tumor type.
- **Deprecated or renamed codes**: OncoTree evolves across versions. The `history` field in `OncoTree_get_type` response shows prior names. Always use the current code.

### Synthesis Questions

1. Does the chosen OncoTree code represent the most specific histological subtype, or could a more precise code provide better therapeutic annotation in OncoKB?
2. When the free-text tumor description maps to multiple OncoTree codes, which hierarchy level best balances specificity and coverage for the analysis goal (variant annotation vs cohort selection)?
3. Are the UMLS/NCI cross-references consistent with external classifications (WHO, ICD-O), or are there discrepancies that need resolution?

---

## Fallback Chains

| Primary | Fallback | When |
|---------|---------|------|
| `OncoTree_get_type(code="GBM")` | `OncoTree_search(query="glioblastoma")` | 404 for common aliases |
| `OncoTree_search` (no results) | `OncoTree_list_tissues` + tissue-level search | Very rare/novel tumor types |
| OncoTree code for OncoKB | Omit `tumor_type` param | Code not recognized by OncoKB |
