---

name: tooluniverse-lab-data-standardization
description: "Convert lab instrument output files (CSV, TSV, Excel, PDF — plate readers, spectrophotometers like NanoDrop, qPCR instruments, cell counters, chromatography systems) into a standardized Allotrope-Simple-Model-inspired JSON document plus a flattened 2D CSV, for LIMS/ELN upload or downstream analysis. Use when someone asks to \"convert this instrument file\", \"standardize this lab data\", \"prepare this for LIMS upload\", \"what format is this plate reader/NanoDrop/qPCR output in\", \"turn this CSV into ASM/Allotrope format\", or \"separate the raw and calculated values in this instrument export\". NOT for general data wrangling of arbitrary tabular data unrelated to lab instruments (use tooluniverse-data-wrangling), NOT for genomics/proteomics-specific file formats like FASTQ/VCF/mzML (use tooluniverse-fastq-qc, tooluniverse-variant-analysis, or tooluniverse-proteomics-analysis). Honest: never fabricates a measurement value; if a vendor's native parser (allotropy) is unavailable it says so and..."
---

# Lab Instrument Data Standardization

Convert raw instrument output into a standardized, structured format —
distinguishing raw measurements from calculated/derived values with
explicit traceability — for LIMS/ELN upload, data lakes, or downstream
analysis.

## Honesty contract (read first)

1. **Never fabricate a value.** Every number in the output JSON/CSV must
   come directly from the source file. If a value can't be found or
   confidently parsed, it is omitted — never guessed.
2. **Never claim certified ASM output you didn't produce.** Tier 1 (native
   `allotropy` parsing) produces genuine Allotrope Simple Model documents.
   Tier 2 (fallback, this skill's own generic parser) produces a
   structurally similar but NOT validated document, and is always tagged
   `"tier": "fallback"` with an explanatory `"note"` — never presented as
   equivalent to a certified conversion.
3. **Traceability or it doesn't count.** A "calculated" value with no link
   back to the raw measurement it came from is not emitted as calculated —
   the fallback parser only classifies a value as calculated when it can
   also identify at least one raw column in the same row to point at.
4. **Say so if a dependency is missing.** If `allotropy` isn't installed,
   print the `pip install allotropy` instruction and proceed with the
   fallback tier — do not pretend Tier 1 ran.

## When to use vs. not

**Use this skill when the user wants to:**
- Convert a plate reader / spectrophotometer / qPCR / cell counter /
  chromatography export (CSV, TSV, XLSX, or a text-extractable PDF table)
  into a standardized structured format
- Separate raw instrument readings from calculated/derived values with
  traceability, ahead of a LIMS or data-lake upload
- Get a flattened 2D CSV version of an ASM-style document for spreadsheet
  import
- Validate that a produced JSON document is structurally sound (has proper
  traceability, numeric values, no duplicate IDs)

**Do NOT use this skill for (route elsewhere):**
- General-purpose tabular cleaning/reshaping unrelated to lab instruments
  -> `tooluniverse-data-wrangling`
- FASTQ QC -> `tooluniverse-fastq-qc`
- VCF / variant files -> `tooluniverse-variant-analysis`
- Proteomics raw files (mzML, RAW) -> `tooluniverse-proteomics-analysis`
- Single-cell matrices (h5ad, 10X) -> `tooluniverse-single-cell`

## Two-tier conversion strategy

| Tier | Trigger | Parser | Output tag |
|------|---------|--------|------------|
| 1. Native | `allotropy` is installed AND the file matches a supported vendor | Real `allotropy` library — certified ASM output | `tier: "native"` |
| 2. Fallback | `allotropy` missing, or vendor unrecognized | This skill's own generic tabular parser (pandas/openpyxl/pdfplumber only — already-declared ToolUniverse deps) | `tier: "fallback"` + explanatory note |

`allotropy` is an OPTIONAL dependency — it is not part of ToolUniverse's
declared package dependencies. The scripts detect it at runtime via
`try: import allotropy` and never error out if it's missing; they just
report the install command and use Tier 2. Never add `allotropy` to
`pyproject.toml` — it stays opt-in per-user.

See `references/supported_instruments.md` for exactly what each tier
covers, and how to enumerate the installed allotropy Vendor list yourself.

## Workflow

1. **Identify the input file** (CSV/TSV/XLSX/PDF) and, for Excel, which
   sheet if not the first.
2. **Run the converter**:
   ```bash
   python scripts/convert_instrument_data.py <input_file> --output-dir <out_dir>
   ```
   This auto-detects the tier (tries native `allotropy` first if installed
   and `--vendor` is given/inferrable, otherwise uses the fallback parser
   automatically) and writes `<stem>_asm.json` and `<stem>_flat.csv` into
   `<out_dir>`.
3. **Read the console output.** It states which tier ran and how many
   measurements/calculated values were found. Zero measurements is flagged
   as a warning, not silently reported as success.
4. **Validate the output**:
   ```bash
   python scripts/validate_output.py <out_dir>/<stem>_asm.json
   # or, to escalate every warning to a failure:
   python scripts/validate_output.py <out_dir>/<stem>_asm.json --strict
   ```
5. **Re-flatten on demand** (if you already have the JSON and just need the
   CSV regenerated, e.g. after hand-editing the JSON):
   ```bash
   python scripts/flatten_to_csv.py <out_dir>/<stem>_asm.json -o <path>.csv
   ```
   (Only supported for `tier: "fallback"` documents — a native `allotropy`
   document has its own internal ASM structure and needs allotropy's own
   flattening utilities, not this script.)
6. **Report** which tier ran, the measurement/calculated-value counts, any
   validator warnings/errors, and where the output files were written.
   Never report a value the tool didn't actually produce.

## Options reference (`convert_instrument_data.py`)

| Flag | Meaning |
|------|---------|
| `--output-dir` | Output directory (default: `<input_dir>/<stem>_asm_results`) |
| `--sheet` | Excel sheet name/index (xlsx only) |
| `--vendor` | Force a specific `allotropy` Vendor name for Tier 1 |
| `--force-fallback` | Skip Tier 1 even if `allotropy` is installed (useful for testing/consistency) |
| `--format {json,csv,both}` | Which output(s) to write (default: both) |

## References

- `references/schema_overview.md` — the JSON document shape and field rules
- `references/supported_instruments.md` — what Tier 1 vs. Tier 2 actually parse
- `references/field_classification_guide.md` — raw vs. calculated heuristics, with a table of common calculated fields by instrument type
