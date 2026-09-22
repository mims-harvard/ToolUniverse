# What each tier actually supports

## Tier 1 — native `allotropy` parsing (preferred, opt-in dependency)

Only active if `allotropy` is installed (`pip install allotropy`). Its
supported vendor list is versioned and changes between allotropy releases —
do not trust a hardcoded list here. Enumerate the exact list installed in
the current environment with:

```bash
python -c "from allotropy.parser_factory import Vendor; [print(v.name) for v in Vendor]"
```

As of allotropy's public documentation this generally includes vendors
across these categories (verify against the command above before relying on
any specific one):

- Cell counting (e.g. Beckman Vi-CELL BLU/XR, ChemoMetec NucleoCounter)
- Spectrophotometry (e.g. Thermo Fisher NanoDrop One/Eight/8000, Unchained Lunatic)
- Plate readers (e.g. Molecular Devices SoftMax Pro, PerkinElmer EnVision, Agilent BioTek Gen5, BMG CLARIOstar)
- ELISA (e.g. Molecular Devices SoftMax Pro, BMG MARS, Meso Scale Discovery Workbench)
- qPCR (e.g. Applied Biosystems QuantStudio, Bio-Rad CFX)
- Electrophoresis / fragment analysis (e.g. Agilent TapeStation, Fragment Analyzer)
- Chromatography (e.g. Waters Empower, Thermo Chromeleon)

If the file's instrument isn't in the installed Vendor list, the skill falls
through to Tier 2 automatically — it does not error out.

## Tier 2 — fallback tabular parser (always available)

Implemented in `scripts/convert_instrument_data.py` using only
ToolUniverse's existing dependencies (`pandas`, `openpyxl`, `pdfplumber`).
Handles:

- **CSV / TSV** — any delimited table with a header row.
- **Excel (.xlsx)** — first sheet by default, or `--sheet` to pick another.
- **PDF** — tables extracted with `pdfplumber`; only works if the PDF has a
  genuine text-extractable table (not a scanned image — no OCR is bundled).

The fallback parser is genuinely generic: it does not know instrument
vendors, only tabular structure. It identifies likely sample/well/ID columns
by header-name heuristics, classifies remaining numeric columns as raw or
calculated using the heuristics in `field_classification_guide.md`, and
always tags its output `"tier": "fallback"` so nobody mistakes it for a
certified ASM conversion.

## Choosing between tiers

The skill always tries Tier 1 first (if `allotropy` is importable and the
file matches a known vendor format), and only uses Tier 2 when Tier 1 is
unavailable or doesn't recognize the file. This is automatic — you don't
need to specify a tier unless you want to force Tier 2 for testing
(`--force-fallback`).
