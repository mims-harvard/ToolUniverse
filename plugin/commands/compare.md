---
name: compare
description: Side-by-side comparison of N items (drugs, targets, diseases, variants, trials, etc.) with a domain-appropriate column set, structured tabular output, and per-cell source citation. Use when the user wants to evaluate alternatives, not when they want a profile of a single item. Enforces the comparison structure that ad-hoc research doesn't.
argument-hint: "[items separated by commas, e.g. 'alpelisib, ipatasertib, capivasertib' or 'BRCA1, BRCA2, PALB2 in ovarian cancer']"
---

Compare these items side-by-side: $ARGUMENTS

Comparison ≠ profile-each-then-merge. The structure has to be decided up
front (what columns? what dimensions?), the data has to be aligned (same
units, same date range, same reference), and the output has to be a TABLE
the user can act on, not a stack of paragraphs.

## Process

### 1. Detect domain

Inspect the items to figure out what KIND of things they are:

| Items look like | Domain | Column set |
|---|---|---|
| Generic drug names, kinase inhibitors, mAbs | drug | mechanism, target(s), approved indications, key trials, AE profile, FDA status, dosing |
| Gene symbols (BRCA1, TP53, KRAS) | gene/target | function, disease associations, druggability, # approved drugs targeting, mutation frequency in cancer |
| Disease names, syndromes | disease | prevalence, key genes, treatments, ICD codes, clinical trials count |
| Variants (V600E, R175H) | variant | gene, amino acid change, pathogenicity, frequency (gnomAD), drug sensitivity, evidence tier |
| Clinical trial NCT IDs | trial | phase, indication, intervention, enrollment, status, primary endpoint, sponsor |
| Cell lines | cell line | tissue, mutations, drug sensitivity, source |

If items mix domains (e.g., "BRCA1, alpelisib"), ask the user what comparison
axis they want — drug-vs-target makes no sense as a row-aligned table.

If domain isn't obvious, look up the first item: `find_tools` with the item
name, see what kind of tool matches. Drug-tools → drug; gene-tools → gene; etc.

State the detected domain in one line before continuing.

### 2. Decide the column set

Use the table above as the default. Ask yourself: what's the user actually
trying to PICK BETWEEN? Drop columns that don't help discriminate (e.g., if
all items have the same FDA status, drop that column). Keep 5-8 columns max
— more becomes unreadable.

If the user's prompt gave a hint ("compare on safety"), bias the column set
toward that axis (more safety columns, fewer mechanism columns).

### 3. Gather data per item, per column

Make a fetch plan:

```
| Column | Tool to call | Once per item or batch |
|---|---|---|
| Mechanism | ChEMBL_search_molecules | per-item |
| Target | DGIdb_get_drug_gene_interactions | batch (all drugs at once) |
| Approved indications | OpenFDA_search_drug_approvals | per-item |
| AE profile | FAERS_get_drug_safety | per-item |
```

Prefer batch tools when available (`DGIdb_get_drug_gene_interactions` accepts a
list). When per-item, call sequentially — track results in a working
scratchpad so you can fill the table cell-by-cell.

If a tool fails for one item, leave that cell as `—` with a note in the
caveats section. Don't guess and don't drop the row.

### 4. Output: aligned comparison table

```
## Comparing: <items>
## Domain: <detected>

| | <item 1> | <item 2> | <item 3> |
|---|---|---|---|
| Mechanism | … | … | … |
| Target(s) | PIK3CA (α) | AKT (1/2/3) | AKT1/2/3 |
| Approved indications | HR+/HER2- breast w/ PIK3CA mut | none (Phase 3) | none (Phase 3) |
| Key trial | SOLAR-1 | IPATunity130 | CAPItello-291 |
| AE profile (top 3) | hyperglycemia, rash, diarrhea | … | … |
| FDA status | Approved 2019 | Investigational | Investigational |
| Sources | OpenFDA, ChEMBL | ClinicalTrials, ChEMBL | ClinicalTrials, ChEMBL |
```

Critical formatting rules:
- ITEMS as columns (one column per item), DIMENSIONS as rows. Easier to scan
  for differences across items.
- Keep cell content to ~10 words; if a fact needs more, footnote it.
- Last row = sources used per column (or last column = sources per row).
- Use `—` for missing cells, never omit the row.

### 5. Synthesis paragraph

After the table, 3-5 sentences:
- Where the items DIFFER most (the columns with the most variation)
- Where they're EQUIVALENT (columns the user can treat as a wash)
- An explicit "best for X" call IF the comparison was a decision question
  (e.g., "for tumor with PIK3CA H1047R, alpelisib is the only approved
  option as of 2026-Q1")

Don't say "they each have strengths and weaknesses" — that's content-free.
Make the contrast specific.

### 6. Caveats

End with:
- Date the data was retrieved (since approvals/trials change)
- Whether any cells came from K (knowledge) tier — flag those rows
- Whether the comparison axis chosen was a heuristic (vs. user-specified)
- Items where data was incomplete

## Stop conditions

- Per-item data fetch fails after 2 attempts → fill cell with `—`, move on.
- More than 30% of cells are `—` → wrap with a "data sparse" warning;
  user should narrow the column set or pick different items.
- Items don't share a domain (drug vs gene) → stop, ask for axis.
- More than 6 items → suggest the user split into rounds; >6 columns is
  unreadable.
