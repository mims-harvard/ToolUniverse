---
name: tu-audit-data
description: Pre-analysis sanity check on a local data file or folder. Reports file format, encoding, missing values, duplicates, suspicious distributions, schema mismatches, and ID-column collisions BEFORE invoking an analysis skill. Use when you're about to run a downstream analysis and want to catch garbage-in problems first.
argument-hint: "[path to file or folder]"
---

Audit this data before any analysis: $ARGUMENTS

Skills assume clean, well-formatted data. When data is dirty, skills produce
wrong answers without raising errors. Run a pre-flight audit so the user
sees problems before the analysis runs.

This is a NON-DESTRUCTIVE read-only check. Do not modify anything.

## Process

### 1. Resolve the input

If `$ARGUMENTS` is a directory, list the contents and pick the data files
(skip READMEs, scripts, notebooks). Audit each separately, then summarize.

If `$ARGUMENTS` is a single file, audit just that file.

If a corresponding `*_executed.ipynb` is present in the folder, mention it
prominently in the audit report — that's an authoritative analysis already
run, and the user may not need to re-run anything (RULE ZERO from the
router skill).

### 2. Format and structure check

For each file:

```bash
file <path>           # detect actual type (don't trust the extension alone)
head -3 <path>        # first lines — header? delimiters? encoding hints?
wc -l <path>          # row count
```

Specifically check:
- **File type vs extension** — `.csv` files that are actually TSV or Excel
  are common and break naive readers
- **Encoding** — `latin1` / `cp1252` masquerading as UTF-8 (clinical-trial
  CSV exports do this constantly)
- **BOM** — leading `\xef\xbb\xbf` will turn the first column name into garbage
- **Line endings** — `\r\n` vs `\n` vs `\r` — usually not a problem but worth noting
- **Delimiter** — `,` vs `\t` vs `;` vs `|`; sniff if not obvious
- **Quoting** — fields containing the delimiter; check for unbalanced quotes

### 3. Schema check

Load with `pandas.read_csv(..., nrows=100)` (or appropriate reader) to peek:

```python
import pandas as pd
df = pd.read_csv(path, nrows=100, encoding='latin1' if utf8_failed else 'utf-8')
print(df.shape)           # (rows_sampled, n_columns)
print(df.dtypes)          # type per column
print(df.columns.tolist())
print(df.isna().sum())    # missing per column
```

Report:
- Column count + names + types
- Whether columns match a recognized schema (RNA-seq counts: gene-id col + sample columns of integers; SDTM clinical: USUBJID/STUDYID/etc.; VCF: standard 8 columns; FASTA/FASTQ: header pattern)
- Any column where >30% of rows are NA (suspicious — wrong join? wrong file?)
- Any column with mixed types (some integer, some string — typical for "999"
  sentinel-coded missing data)
- Any column with all-identical values (low-info column, likely metadata that
  shouldn't be a column)

### 4. ID-column hygiene

Identify likely ID columns (first column, `id` / `gene` / `sample` /
`subject` in name) and check:
- Are values unique? (`df[col].duplicated().sum()`)
- Are there leading/trailing whitespace problems? (`df[col].str.strip() != df[col]`)
- Mixed namespaces? (e.g., a `gene` column with both `TP53` and `ENSG00000141510`)
- Hidden NULL/empty values (`""`, `"NA"`, `"NULL"`, `"null"`, `"."`)

### 5. Distribution sanity

For numeric columns, check:
- min/max — do they make biological sense? (negative counts, p-values >1, fold changes >1e10 → bug)
- Number of zeros — extreme zero-inflation (>80%) often means the data is filtered upstream
- Outliers (values >5 SD from mean) — list the top 3 most extreme rows

### 6. Cross-file consistency (if multiple files)

If a sample sheet + a count matrix are present:
- Sample IDs in the sheet match column headers in the matrix?
- Any sheet-only or matrix-only sample? Report counts and the missing IDs

### 7. Output: structured audit report

```
# Audit: <path>

## Files detected
- counts.csv (5,828 rows × 33 columns, UTF-8)
- meta.csv (32 rows × 6 columns, latin1) ⚠ encoding mismatch with counts.csv

## Format issues (BLOCKING)
- meta.csv has a UTF-8 BOM in column "Strain" — first row's strain reads as
  "﻿JBX1" instead of "JBX1". Fix before joining with counts.

## Format issues (WARN)
- counts.csv: column 1 is unnamed (`Unnamed: 0`); appears to contain gene IDs
  but pandas treats it as the index — be explicit with `index_col=0`

## Schema
- counts.csv looks like an RNA-seq count matrix:
  - 5,828 gene rows, 32 sample columns
  - Columns named like "resub-1", "resub-2", … "resub-33"
  - All integer values, range [0, 1.2M]
  - 12 columns have >50% zeros — possible technical replicates or low-depth samples

## ID hygiene
- meta.csv has an outlier sample list: resub-5, resub-10, resub-33 are
  flagged in column "outlier" with value "yes". If a published analysis
  exists, it likely DROPS these before DESeq2.

## Cross-file
- All 32 sample IDs in meta.csv are present as columns in counts.csv ✓
- counts.csv has a 33rd column "gene_length" that is not a sample — exclude
  from the count matrix when building DESeqDataSet

## Distribution sanity
- All values nonneg ✓
- 0 NA values in counts.csv ✓

## Recommended next step
1. Fix BOM in meta.csv (re-save as plain UTF-8)
2. Read counts.csv with `index_col=0`; exclude "gene_length" column
3. Drop outlier samples (resub-5/10/33) per meta.csv
4. Then invoke `tooluniverse-rnaseq-deseq2` skill for DE analysis

## Note: existing analysis pipeline
Folder contains `CapsuleNotebook-*_executed.ipynb`. If your question is about
this dataset, RULE ZERO applies — read the notebook's outputs first via
`tu run read_executed_notebook` instead of re-running the analysis.
```

The "Recommended next step" section is the most important — it tells the
user what to FIX before invoking the analysis skill, and which skill to
invoke after.

## Stop conditions

- File can't be opened with any tried encoding → report the error, suggest
  manual inspection
- Folder has 50+ files → audit a sample (the largest data files) and note
  that you stopped
- After 5 minutes of analysis, wrap up with what you have

## When NOT to use this command

- File is part of a benchmark capsule with a published `*_executed.ipynb` —
  RULE ZERO says read the notebook first; auditing is overkill
- File is from a known-good source (database export with documented schema) —
  you can trust the schema and skip to analysis
- You're just exploring — `head`, `tail`, `wc -l` are faster
