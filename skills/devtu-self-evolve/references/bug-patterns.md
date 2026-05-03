# Bug Patterns Reference

Detailed code-level fix patterns discovered through role-play debug rounds.

## Table of Contents

**Rounds 52–57 (core patterns)**
- [Regex Overmatch: Mutation vs Fusion](#regex-overmatch)
- [Silent Parameter Alias](#silent-parameter-alias)
- [Always-Fires Conditional](#always-fires-conditional)
- [Silent Normalization](#silent-normalization)
- [Notation / Case Sensitivity](#notation-case)
- [Truncation Not Top-Level](#truncation)
- [Gene Symbol Substring Match](#gene-symbol)
- [try/except Indentation](#try-except)
- [Multi-Word Search Hints](#multi-word-search)
- [Expression Units Inference](#expression-units)
- [Auto-Selected vs Explicit Study](#auto-selected-study)
- [CIViC Therapy + AND Logic](#civic-therapy-and)

**Rounds 68–78 (API-specific patterns)**
- [DGIdb Client-Side Filtering](#dgidb-client-side)
- [CPIC PostgREST Filter Prefix](#cpic-postgrest)
- [CPIC Recommendation Join](#cpic-join)
- [KEGG Organism-Specific Gene Search](#kegg-organism)
- [HPA Deprecated Column](#hpa-deprecated)
- [PDBePISA Operation from Config](#pdbepisa-operation)
- [GTEx Dataset Selection](#gtex-dataset)
- [GxA Silent geneId Ignore](#gxa-geneid)
- [ExpressionAtlas Schema Key Mismatch](#expressionatlas-schema)
- [Proteins API Human Priority](#proteins-api-human)
- [RCSB Null Type in Schema](#rcsb-null)
- [ClinVar Search Field Tags](#clinvar-fields)
- [ENCODE Tissue+Organism Filter](#encode-filter)
- [GEO Double-Adding Search Terms](#geo-double)
- [CPIC Warfarin Algorithm Guideline](#cpic-warfarin)
- [PharmGKB clinpgxid vs pharmgkbid](#pharmgkb-id)
- [ENCODE ChIP-seq Assay Title](#encode-assay)
- [RegulomeDB Parameter Names](#regulomedb)
- [BindingDB API Typo](#bindingdb)
- [ProteomeXchange Title and Instruments](#proteomexchange)
- [MetabolomicsWorkbench moverz URL](#metworkbench)
- [MetaboLights Pagination Ignored](#metalights)
- [ChEBI Search Nulls and HTML](#chebi)
- [HMDB No Open API](#hmdb)
- [PharmGKB relatedGenes Filter](#pharmgkb-related)

---

## Regex Overmatch: Mutation vs Fusion {#regex-overmatch}

**Tools**: civic_search_evidence_items, civic_search_variants
**Bug IDs**: BUG-56A-001

A regex that normalizes `GENE1-GENE2` fusion notation can accidentally match `GENE-MutationCode` (e.g., `EGFR-T790M`, `BRAF-V600E`, `KRAS-G12C`) because mutation codes start with an uppercase letter.

**Fix**: Use a lambda that checks if the second part matches HGVS protein-change format before applying the substitution:
```python
def _maybe_fuse(m):
    second = m.group(2)
    # Protein-change: single letter + digits + letter/asterisk (e.g. T790M, V600E, G12C)
    if re.match(r"^[A-Z]\d+[A-Z*]?$", second):
        return m.group(0)  # leave unchanged
    return m.group(1) + "::" + second

normalized = re.sub(r"\b([A-Z][A-Z0-9]*)-([A-Z][A-Z0-9]+)\b", _maybe_fuse, mol_profile)
```

When the input matches the mutation pattern and returns 0 results, add a hint:
```python
elif re.search(r"\b[A-Z][A-Z0-9]*-[A-Z]\d+[A-Z*]?\b", mol_profile):
    space_form = mol_profile.replace("-", " ", 1)
    mp_warn += f" If '{mol_profile}' is a point mutation, try molecular_profile='{space_form}'..."
```

---

## Silent Parameter Alias

**Tools**: SYNERGxDB_search_combos
**Bug IDs**: BUG-55A-011

Users pass `cancer_type` but tool only accepts `sample`, `tissue_name`, `tissue`. Parameter silently dropped → all-tissue results returned with `status: "success"`.

**Fix**:
```python
sample = (
    arguments.get("sample")
    or arguments.get("tissue_name")
    or arguments.get("tissue")
    or arguments.get("cancer_type")  # ADD aliases here
)
```

---

## Always-Fires Conditional

**Tools**: GtoPdb_get_interactions
**Bug IDs**: BUG-55A-002, BUG-55A-003, BUG-55B-001

`item.get("approved")` on interaction records returns `None` always (field only exists on `/ligands` objects). So `has_approved` was always `False` → conditional note always fired. Also used wrong category language ("kinase/enzyme") for GPCR targets.

**Fix**: Remove the conditional check; always emit the note as factual guidance. Use neutral language; embed the queried gene symbol:
```python
if isinstance(data, list) and len(data) > 0:
    _chembl_target = gene_symbol or result.get("queried_target", {}).get("name", "the target")
    result["coverage_note"] = (
        "GtoPdb interactions list pharmacological research compounds — approved "
        "drugs for this target may not be represented. For approved drugs and "
        "clinical compounds, use ChEMBL_get_drug_mechanisms or "
        f"ChEMBL_search_compounds with target_name='{_chembl_target}'."
    )
```

---

## Silent Normalization

**Tools**: civic_search_evidence_items, civic_search_variants
**Bug IDs**: BUG-55A-008, BUG-55B-005

CIViC normalizes therapy (lowercase → Title Case) and molecular_profile (BCR-ABL1 → BCR::ABL1) without disclosing the transformation. Users debugging empty results can't see what was tried.

**Fix**: Track pre-normalization values, add a `normalization_note` field to the result:
```python
_therapy_normalized_from = None
_mp_normalized_from = None

# When normalizing therapy:
_therapy_normalized_from = therapy
arguments["therapy"] = therapy.title()

# After result is built:
_norm_parts = []
if _therapy_normalized_from:
    _norm_parts.append(f"therapy '{_therapy_normalized_from}' → '{arguments.get('therapy')}' (CIViC uses Title Case)")
if _mp_normalized_from:
    _norm_parts.append(f"molecular_profile '{_mp_normalized_from}' → '{arguments.get('molecular_profile')}' ...")
if _norm_parts:
    result["normalization_note"] = "Input auto-normalized: " + "; ".join(_norm_parts) + "."
```

---

## Notation / Case Sensitivity {#notation-case}

**Tools**: civic_search_evidence_items
**Bug IDs**: BUG-55B-005 (fusion), BUG-53B-002 (therapy case)

CIViC uses `::` for gene fusions (`BCR::ABL1 Fusion`, `EML4::ALK Fusion`). Users write hyphenated forms (`BCR-ABL1`) → 0 results.
CIViC therapy names are Title Case (`"Sotorasib"` not `"sotorasib"`).

**Fix (fusion normalization)**:
```python
import re as _re
mol_profile = arguments.get("molecular_profile")
if mol_profile and isinstance(mol_profile, str):
    normalized_mp = _re.sub(
        r"\b([A-Z][A-Z0-9]*)-([A-Z][A-Z0-9]+)\b",
        r"\1::\2",
        mol_profile,
    )
    if normalized_mp != mol_profile:
        _mp_normalized_from = mol_profile
        arguments = dict(arguments)
        arguments["molecular_profile"] = normalized_mp
```

**Fix (therapy case)**:
```python
if therapy == therapy.lower() or therapy == therapy.upper():
    _therapy_normalized_from = therapy
    arguments["therapy"] = therapy.title()
```

---

## Truncation Not Top-Level {#truncation}

**Tools**: CancerPrognosis_get_gene_expression
**Bug IDs**: BUG-55A-006

Truncation info (e.g., 500 of 1100 samples returned) buried inside `data.note` string. Researchers reading top-level fields miss it.

**Fix**: Add top-level flags:
```python
response = {"status": "success", "data": result_data}
if len(values) > max_samples:
    response["truncated"] = True
    response["truncation_note"] = (
        f"Returning {len(values[:max_samples])} of {len(values)} samples. "
        f"Pass max_samples={len(values)} (up to 2000) to retrieve the full dataset."
    )
return response
```

---

## Gene Symbol Substring Match {#gene-symbol}

**Tools**: GtoPdb_get_interactions
**Bug IDs**: BUG-54B-001

`?name=AR` returns all targets containing "AR" (13+ targets). `?geneSymbol=AR` is the unambiguous HGNC lookup.

**Fix**: Try `?geneSymbol=` first; fall back to `?name=` if nothing returned:
```python
gs_url = f"{base_url}/targets?{urlencode({'geneSymbol': gene_symbol})}"
gs_resp = request_with_retry(...)
if gs_resp.status_code == 200:
    gs_targets = gs_resp.json()
    if gs_targets:
        target_id = gs_targets[0]["targetId"]

# Fall back to ?name= only if geneSymbol returned nothing
if target_id is None:
    lookup_url = f"{base_url}/targets?{urlencode({'name': gene_symbol})}"
    ...
```

---

## try/except Indentation {#try-except}

Every `try:` MUST have an `except` at the **exact same indentation level**. A common error is placing code after `try:` at the same level as the `try:` keyword — Python sees the try block as having no except.

```python
# CORRECT
try:              # 16 spaces
    resp = ...    # 20 spaces (inside try)
    if resp.ok:   # 20 spaces (still inside try)
        ...
except Exception: # 16 spaces — matches try
    pass

# WRONG — SyntaxError
try:              # 16 spaces
    resp = ...    # 20 spaces
if resp.ok:       # 16 spaces — OUTSIDE try, before except!
    ...
except Exception: # 16 spaces — Python: "try without except"
    pass
```

---

## Multi-Word Search Hints {#multi-word-search}

**Tools**: GtoPdb_search_targets, GtoPdb_search_ligands
**Bug IDs**: BUG-54B-002

`name="androgen receptor"` returns empty — GtoPdb text search doesn't reliably match multi-word phrases.

**Fix**: When count=0 and query has a space, add a hint suggesting first word only:
```python
if result["count"] == 0 and name_q and " " in str(name_q):
    first_word = str(name_q).split()[0]
    result["multi_word_hint"] = (
        f"GtoPdb text search may not match multi-word phrases like '{name_q}'. "
        f"Try a single keyword: name='{first_word}'."
    )
```

---

## Expression Units Inference {#expression-units}

**Tools**: CancerPrognosis_get_gene_expression
**Bug IDs**: BUG-54A-002

`_get_expression_units(profile_id)` infers units from the profile ID string. Some studies use misleading suffixes (e.g., `aml_ohsu_2022` uses `_rna_seq_v2_mrna` but stores log2 RPKM).

**Fix**: Return `(profile_id, profile_name)` from `_get_mrna_profile()` and prefer the actual API description over inference:
```python
def _get_expression_units(self, profile_id, profile_name=None):
    if profile_name:
        return profile_name  # Prefer actual API name
    # ... fallback inference from profile_id
```

---

## Auto-Selected vs Explicit Study {#auto-selected-study}

**Tools**: CancerPrognosis_get_gene_expression
**Bug IDs**: BUG-54A-004

`study_note` always said "Auto-selected study_id=..." even when user explicitly passed a full study ID like `brca_tcga`.

**Fix**: Detect explicit specification and use a different message:
```python
study_was_explicit = (
    cancer == study_id_arg
    and study_id_arg
    and "_" in str(study_id_arg)
    and str(study_id_arg).upper() not in TCGA_STUDY_MAP
    and str(study_id_arg).upper() not in _CANCER_NAME_ALIASES
)
"study_note": (
    f"Using explicitly specified study_id='{study_id}'."
    if study_was_explicit
    else f"Auto-selected study_id='{study_id}'. Use CancerPrognosis_search_studies "
         "to find alternative cohorts for this cancer type."
),
```

---

## CIViC Therapy + AND Logic {#civic-therapy-and}

**Tools**: civic_search_evidence_items, civic_search_variants
**Bug IDs**: BUG-54A-001, BUG-54A-005

1. When both `query` and `variant_name` are provided, one silently wins. Fix: apply AND logic.
2. When `molecular_profile + therapy` returns 0, silently fails. Fix: auto-probe without therapy to surface available therapy names.

**Fix (AND logic)**:
```python
raw_query = arguments.get("query")
raw_variant_name = arguments.get("variant_name") or arguments.get("variant")
_both = raw_query and raw_variant_name and raw_query != raw_variant_name
if _both:
    query_term = raw_query
    _secondary_term = raw_variant_name
else:
    query_term = raw_query or raw_variant_name
    _secondary_term = None

# Later, apply AND filter:
if _secondary_term:
    filtered = [v for v in filtered if _secondary_term.lower() in v.get("name","").lower()]
    result["filter_note"] = f"Applied AND logic for query+variant_name."
```

**Fix (therapy auto-probe)**:
```python
if mol_profile and therapy and not disease and len(evidence_nodes) == 0:
    probe_args = {k: v for k, v in arguments.items() if k != "therapy"}
    probe_nodes = civic_query(probe_args)
    available_therapies = sorted({
        t.get("name") for node in probe_nodes
        for t in node.get("therapies", []) if t.get("name")
    })
    result["therapy_warning"] = (
        f"No evidence for '{mol_profile}' + therapy='{therapy}'. "
        f"Available therapies: {available_therapies[:10]}"
    )
```

---

## DGIdb Client-Side Filtering (Feature-68A-001/002)

**Tools**: DGIdb_get_interactions
**Pattern**: API ignores `interaction_types` and `sources` filters server-side → returns everything.

**Fix**: Fetch all, filter client-side:
```python
if interaction_types:
    results = [r for r in results if r.get("interactionTypes") and
               any(it in interaction_types for it in r["interactionTypes"])]
if sources:
    results = [r for r in results if r.get("source") in sources]
# Always wrap with status
return {"status": "success", "count": len(results), "data": results}
```

---

## CPIC PostgREST Filter Prefix (Feature-68A-004)

**Tools**: CPICSearchPairsTool
**Pattern**: PostgREST requires equality filter as `eq.VALUE`, not bare `VALUE`.

**Fix**: Auto-prepend `eq.` if not already present:
```python
def _postgrest_eq(value):
    v = str(value)
    return v if v.startswith("eq.") else f"eq.{v}"
params["genesymbol"] = _postgrest_eq(gene_symbol)
```

---

## CPIC Recommendation Join (Feature-68A-006)

**Tools**: CPIC_get_recommendations
**Pattern**: `/recommendation` endpoint doesn't include drug name — need to join `/drug` table.

**Fix**: Use `?select=*,drug(name)` in the URL query string for PostgREST joins.

---

## KEGG Organism-Specific Gene Search (Feature-68B-001)

**Tools**: KEGG_find_genes
**Pattern**: `/find/genes/{keyword}` ignores organism param → returns all organisms.

**Fix**: Use `/find/{organism}/{keyword}`:
```python
url = f"https://rest.kegg.jp/find/{organism}/{keyword}" if organism else f"https://rest.kegg.jp/find/genes/{keyword}"
```

---

## HPA Deprecated Column (Feature-68B-002)

**Tools**: HPA_get_protein_expression
**Pattern**: `ppi` column was deprecated; API returns error listing alternatives (`enhanced`, `supported`, `approved`, `uncertain`).

**Fix**: Remove `ppi` from select list; return error message with alternatives when API responds with column-not-found error.

---

## PDBePISA Operation from Config (Feature-68B-006)

**Tools**: PDBePISA tools
**Pattern**: `operation` param exposed as public parameter → users pass wrong values.

**Fix**: Read `operation` from the tool's JSON `fields` config, never expose as public argument.

---

## GTEx Dataset Selection (Feature-69A-001/002)

**Tools**: GTEx_get_median_gene_expression
**Pattern**: `gtex_v10` returns empty for `medianGeneExpression` endpoint; only `gtex_v8` works reliably.

**Fix**: Always default to `gtex_v8`. Add note in result:
```python
dataset = arguments.get("dataset", "gtex_v8")
if dataset == "gtex_v10":
    result["dataset_note"] = "gtex_v10 may return empty for this endpoint; gtex_v8 is recommended."
```

---

## GxA Silent geneId Ignore (Feature-69A-003)

**Tools**: ExpressionAtlas_get_experiment
**Pattern**: `/experiments/{accession}` API ignores `geneId` parameter silently.

**Fix**: Apply `geneId` filter client-side on the returned data.

---

## ExpressionAtlas Schema Key Mismatch (Feature-69A-004)

**Tools**: ExpressionAtlas tools
**Pattern**: `return_schema` key `experiments` but code returns `baseline_experiments`.

**Fix**: Make key in `return_schema` match exactly what the code produces. Use `baseline_experiments`.

---

## Proteins API Human Priority (Feature-69A-007)

**Tools**: proteins_api_search
**Pattern**: Gene/name searches return non-human results first.

**Fix**: Add `taxid=9606` default for gene and name searches to prioritize human entries.

---

## RCSB Null Type in Schema (Feature-69B-002/010)

**Tools**: RCSB tools
**Pattern**: `return_schema` has `type: null` which is invalid JSON Schema.

**Fix**: Use `["array", "null"]` or `["string", "null"]` for nullable types. Also avoid using protein-only PDB IDs as test examples — use IDs that represent the tested operation.

---

## ClinVar Search Field Tags (Feature-70B-004/005)

**Tools**: ClinVar tools
**Pattern**: `[variant_id]` is not a valid eSearch field → use `[uid]`. `[disease/phenotype]` not valid → use bare condition text (no brackets).

**Fix**:
```python
# Wrong:
query = f"{variant_id}[variant_id]"
query = f"{condition}[disease/phenotype]"

# Right:
query = f"{variant_id}[uid]"
query = condition  # bare text, NCBI searches all fields
```

---

## ENCODE Tissue+Organism Filter (Feature-70A-003)

**Tools**: ENCODE_search_experiments
**Pattern**: Combining tissue + organism filter → HTTP 404.

**Fix**: Fall back without organism filter when 404 occurs:
```python
try:
    resp = requests.get(url_with_organism)
    if resp.status_code == 404:
        resp = requests.get(url_without_organism)
except Exception:
    ...
```

---

## GEO Double-Adding Search Terms (Feature-70A-008)

**Tools**: GEO_search_datasets
**Pattern**: Code adds "methylation" to query even when it's already present.

**Fix**: Check before appending:
```python
if "methylation" not in query.lower():
    query += " methylation"
```

---

## CPIC Warfarin Algorithm Guideline (Feature-70B-001)

**Tools**: CPIC_get_recommendations
**Pattern**: Warfarin guideline (ID 100425) uses `algorithm` endpoint, not `/recommendation`. Returns 0 rows from recommendation endpoint.

**Fix**: Detect warfarin (or any guideline that uses algorithm-based dosing) and redirect to `/algorithm` endpoint or explain in the response.

---

## PharmGKB clinpgxid vs pharmgkbid (Feature-70B-002/011)

**Tools**: PharmGKB tools
**Pattern**: CPIC `list_guidelines` returns `clinpgxid`, but code uses `pharmgkbid` → 404 from PharmGKB.

**Fix**: Use `clinpgxid` from CPIC response when building PharmGKB URLs.

---

## ENCODE ChIP-seq Assay Title (Feature-73B)

**Tools**: ENCODE_search_experiments
**Pattern**: Querying `assay_title=ChIP-seq` returns 0; correct value is `TF ChIP-seq`.
Also: organism filter uses wrong nested field name.

**Fix**: Map user-friendly aliases to ENCODE-specific values:
```python
ASSAY_ALIASES = {"ChIP-seq": "TF ChIP-seq", "CHIP": "TF ChIP-seq"}
assay_title = ASSAY_ALIASES.get(assay_title, assay_title)
```

---

## RegulomeDB Parameter Names (Feature-73B)

**Tools**: RegulomeDB tools
**Pattern**: `assembly=hg19` is wrong → use `genome=GRCh38`. Test example `rs123456` doesn't exist → use `rs4994`.

**Fix**: Update parameter names and test examples to match actual API.

---

## BindingDB API Typo (Feature-73A)

**Tools**: BindingDB tools
**Pattern**: API endpoint has typo: `getLindsByXxx` (not `getLigandsByXxx`). Also response key is `bdb.affinities` not `affinities`.

**Fix**: Use exact typo as in the real API URL. Access `response["bdb.affinities"]`.

---

## ProteomeXchange Title and Instruments (Feature-73A)

**Tools**: ProteomeXchange tools
**Pattern**: `title` field is plain string not dict. `instruments` use `{name, accession}` not nested `terms`.

**Fix**: Access `dataset.get("title")` directly. For instruments: `inst.get("name")` not `inst["terms"][0]["name"]`.

---

## MetabolomicsWorkbench moverz URL (Feature-73A/74A)

**Tools**: MetabolomicsWorkbench tools
**Pattern**: `moverz` endpoint needs database prefix: `/moverz/{database}/{mz}/{adduct}/{tolerance}`. Also `exactmass` endpoint is broken → use `moverz/REFMET/{mass}/M/{tolerance}`.

**Fix**:
```python
url = f"https://www.metabolomicsworkbench.org/rest/moverz/REFMET/{mz}/M+H/{tolerance}"
```

---

## MetaboLights Pagination Ignored (Feature-74A)

**Tools**: MetaboLights tools
**Pattern**: `/ws/studies` API silently ignores `size` and `page` params → always returns full list.

**Fix**: Apply pagination client-side after fetching all results:
```python
all_studies = resp.json()
start = page * size
return all_studies[start:start + size]
```

---

## ChEBI Search Nulls and HTML (Feature-74A)

**Tools**: ChEBI_search_compounds
**Pattern**: `smiles` and `inchikey` always null from search API. Names contain HTML entities (`&amp;`, `&lt;`).

**Fix**: Strip HTML from names using `re.sub(r"<[^>]+>", "", name)` and `html.unescape(name)`. Don't return null smiles/inchikey — omit them or fetch from detail endpoint.

---

## HMDB No Open API (Feature-74A)

**Tools**: HMDB tools
**Pattern**: HMDB has no open REST API; tools were returning stub success responses.

**Fix**: Return `{"status": "error", "message": "HMDB does not provide a public REST API. Use MetabolomicsWorkbench or ChEBI instead."}`.

---

## PharmGKB relatedGenes Filter (Feature-74B)

**Tools**: PharmGKB tools
**Pattern**: `relatedGenes.id` and `relatedGenes.symbol` filters not supported by API — silently returns all results.

**Fix**: Return informative message: `"relatedGenes filter is not supported by PharmGKB API. Filter results client-side or use gene-specific endpoints instead."`
