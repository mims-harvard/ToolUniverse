---
name: translate-id
description: Resolve an identifier across all relevant namespaces (HGNC symbol, Ensembl, UniProt, NCBI Gene ID, RefSeq, MGI, OMIM, ChEMBL, PubChem, etc.). Detects the input namespace automatically, picks the right resolver tool, and returns a complete cross-reference table. Use when you have an ID in one namespace and need it in others before downstream tool calls.
argument-hint: "[identifier] [optional: target namespace, e.g. 'ensembl', 'uniprot', 'all']"
---

Translate this identifier across namespaces: $ARGUMENTS

Direct ID lookup is brittle: each tool expects its own namespace, and silently
returns nothing if you pass the wrong one. Detect, route, and report.

## Process

### 1. Detect input namespace

Inspect the identifier shape:

| Pattern | Namespace |
|---|---|
| `^ENS[GTPR]\d+(\.\d+)?$` | Ensembl gene/transcript/protein/RefSeq |
| `^[OPQ][0-9][A-Z0-9]{3}[0-9]$` or `^[A-NR-Z][0-9]([A-Z][A-Z0-9]{2}[0-9]){1,2}$` | UniProt accession |
| `^NM_\d+(\.\d+)?$`, `^NP_`, `^XM_` | RefSeq |
| `^\d+$` (numeric only) | likely NCBI Gene ID — confirm via metadata |
| `^OMIM:\d+$` or `^\d{6}$` (6-digit) | OMIM |
| `^MGI:\d+$` | MGI |
| `^CHEMBL\d+$` | ChEMBL |
| `^CID\d+$` or `^\d+$` in chemistry context | PubChem CID |
| `^DB\d{5}$` | DrugBank |
| `^MONDO:\d+$`, `^DOID:\d+$`, `^EFO:\d+$` | ontology disease IDs |
| `^rs\d+$` | dbSNP |
| All-caps, 1-10 chars, no digits | likely HGNC gene symbol |
| Free-form name | drug name / disease name — fuzzy lookup |

If ambiguous (e.g., "BRAF" could be gene OR drug target context), ASK the user
or pick gene by default and note the assumption.

### 2. Pick the resolver

For genes/proteins:
- HGNC symbol → all → `tu run mygene_query_genes '{"q":"<symbol>","species":"human"}'`
  (returns Ensembl, UniProt, RefSeq, NCBI Gene, MGI in one call)
- Ensembl ID → all → `tu run ensembl_lookup_gene '{"gene_id":"<id>"}'`
- UniProt → gene/Ensembl → `tu run UniProt_search '{"query":"<accession>","limit":1}'`
- NCBI Gene ID → all → `tu run NCBIGene_get_summary '{"id":"<id>"}'` then chain

For chemicals:
- Drug name → all → `tu run ChEMBL_search_molecules '{"query":"<name>","limit":1}'`
  then `tu run PubChem_get_CID_by_name` for cross-ref
- ChEMBL ID → all → `get_tool_info` to find the right cross-ref tool

For diseases:
- Disease name → MONDO/DOID/EFO/OMIM → `tu run ols_search_terms '{"query":"<name>","ontologies":["mondo","doid","efo"]}'`
- OMIM → MONDO → `tu run MONDO_search` (if available) or `ols_search_terms`

For variants:
- rsID → ClinVar/dbSNP → `tu run ClinVar_search_variants '{"query":"<rsid>"}'`
- HGVS → ClinVar → same tool

**Broad cross-namespace fallback — TogoID.** When the specific resolvers above don't
cover the exact pair, `TogoID_convert` links 117 ID datasets (genes, proteins,
transcripts, compounds, diseases, pathways, variants, cell lines, organisms) with a
single call. Pass the source ID(s), `source`, and `target` dataset names:
- `tu run TogoID_convert '{"ids":"ENSG00000139618","source":"ensembl_gene","target":"uniprot"}'`
- `tu run TogoID_convert '{"ids":"2244","source":"pubchem_compound","target":"chebi"}'`
- `tu run TogoID_list_datasets '{"category":"Gene"}'` to discover valid dataset names.
TogoID converts only between *directly-related* datasets (it returns "no route" for
unrelated pairs like ncbigene↔chebi); if that happens, hop via an intermediate.

Don't know the right resolver? Run `find_tools("<input namespace> to <target>")`
ONCE, pick the most relevant hit, run it. If 0 hits, mark that conversion as
"no tool" in the output.

### 3. Output: namespace cross-reference table

Always return a table even if some namespaces are missing:

```
| Namespace | ID | Source tool |
|---|---|---|
| HGNC symbol | BRAF | mygene |
| HGNC ID | HGNC:1097 | mygene |
| NCBI Gene | 673 | mygene |
| Ensembl gene | ENSG00000157764 | mygene |
| Ensembl protein | ENSP00000288602 | ensembl_lookup_gene |
| UniProt | P15056 | mygene |
| RefSeq mRNA | NM_004333.6 | mygene |
| RefSeq protein | NP_004324.2 | mygene |
| MGI (mouse ortholog) | MGI:88190 | mygene |
| OMIM | 164757 | mygene |
| (no tool for this conversion) | — | — |
```

Include only namespaces relevant to the entity type. For a drug: ChEMBL,
PubChem, DrugBank, RxNorm, ATC, KEGG-Drug, INN. For a gene: as above. For
a disease: MONDO, DOID, EFO, OMIM, ICD-10/11.

### 4. If `target_namespace` was specified

Output ONLY that conversion (e.g., "BRAF, ensembl" → `ENSG00000157764`).

If the requested target isn't reachable from the input via known tools,
say so explicitly: "no direct conversion HGNC → KEGG-Drug; intermediate
required (HGNC → ChEMBL → KEGG-Drug)" and offer the chained path.

## Stop conditions

- Input namespace can't be detected → ask for clarification, don't guess.
- Primary resolver returns empty → try one alternate (e.g., NCBIGene_search if
  mygene whiffs). Stop after 1 retry.
- For "all" target: return what you got after the primary resolver call.
  Don't burn tools chasing every possible namespace.
