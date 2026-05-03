# API-Specific Fix Reference

Patterns discovered through rounds 52–78 of role-play debugging.

## Quick Lookup Table

| Tool/API | Issue | Fix |
|---|---|---|
| GtoPdb | `?name=AR` returns 13+ targets | Use `?geneSymbol=AR` first, fall back to `?name=` |
| GtoPdb | Multi-word names return 0 | Add `multi_word_hint` suggesting first word only |
| CIViC | Fusion notation `BCR-ABL1` → 0 results | Normalize `-` → `::` (but not for mutations like T790M) |
| CIViC | Therapy lowercase → 0 results | Auto `.title()` and disclose in `normalization_note` |
| CIViC | `query + variant_name` — one silently wins | Apply AND logic client-side |
| CancerPrognosis | expression_units wrong | Prefer `profile_name` from API over inference from `profile_id` |
| CancerPrognosis | study_note wrong when explicit | Detect explicit specification, use different message |
| SYNERGxDB | `cancer_type` param silently ignored | Add alias handling for `cancer_type`, `tissue_name`, `tissue` |
| GTEx | `gtex_v10` returns empty | Default to `gtex_v8`; note limitation when v10 requested |
| ENCODE | `ChIP-seq` → 0 results | Map to `TF ChIP-seq` |
| ClinVar | `[variant_id]` field → error | Use `[uid]` |
| KEGG find_genes | organism param ignored | Use `/find/{organism}/{keyword}` not `/find/genes/{keyword}` |
| MetabolomicsWorkbench | exactmass broken | Use `moverz/REFMET/{mass}/M/{tolerance}` |
| BindingDB | `getLigands` typo | Use `getLinds` (actual API typo in URL) |
| PharmGKB | `pharmgkbid` → 404 | Use `clinpgxid` from CPIC response |
| CPIC | Warfarin 0 recommendations | Route to `/algorithm` endpoint |
| CPIC | Bare value in PostgREST | Prepend `eq.` prefix |
| HPA | `ppi` column → error | Remove; use `enhanced`/`supported`/`approved` |
| HMDB | No public API | Return `status: error` explaining alternatives |
| RegulomeDB | `assembly=hg19` wrong | Use `genome=GRCh38` |
| DGIdb | `interaction_types`/`sources` ignored | Filter client-side |
| GxA | `geneId` param ignored | Filter client-side |
| MetaboLights | `size`/`page` ignored | Paginate client-side |
| RCSB | `type: null` in schema | Use `["array", "null"]` |
| ProteomeXchange | `title` accessed as dict | Access as plain string |

## Detailed Patterns

### GtoPdb Gene Symbol Disambiguation (Feature-54B-001)

```python
# Try precise geneSymbol first
gs_resp = request_with_retry(f"{base_url}/targets?geneSymbol={gene_symbol}")
if gs_resp.status_code == 200 and gs_resp.json():
    target_id = gs_resp.json()[0]["targetId"]
else:
    # Fall back to name (may return multiple)
    name_resp = request_with_retry(f"{base_url}/targets?name={gene_symbol}")
    ...
```

### CIViC Fusion vs Mutation Regex (Feature-56A-001)

```python
def _maybe_fuse(m):
    second = m.group(2)
    # Protein-change: single letter + digits + letter/asterisk (e.g. T790M, V600E)
    if re.match(r"^[A-Z]\d+[A-Z*]?$", second):
        return m.group(0)  # leave unchanged — it's a mutation
    return m.group(1) + "::" + second

normalized = re.sub(r"\b([A-Z][A-Z0-9]*)-([A-Z][A-Z0-9]+)\b", _maybe_fuse, mol_profile)
```

### CPIC PostgREST Equality Filter (Feature-68A-004)

```python
def _postgrest_eq(value):
    v = str(value)
    return v if v.startswith("eq.") else f"eq.{v}"

params["genesymbol"] = _postgrest_eq(gene_symbol)
```

### ENCODE Assay Title Alias (Feature-73B)

```python
ASSAY_ALIASES = {"ChIP-seq": "TF ChIP-seq", "CHIP": "TF ChIP-seq"}
assay_title = ASSAY_ALIASES.get(assay_title, assay_title)
```

### GTEx Dataset Safety (Feature-69A-001)

```python
dataset = arguments.get("dataset", "gtex_v8")
if dataset == "gtex_v10":
    result["dataset_note"] = "gtex_v10 may return empty; gtex_v8 is recommended."
```

### Broken API Response

```python
# Wrong: return stub success data
# Right:
return {
    "status": "error",
    "message": "HMDB has no public REST API. Use MetabolomicsWorkbench or ChEBI instead."
}
```
