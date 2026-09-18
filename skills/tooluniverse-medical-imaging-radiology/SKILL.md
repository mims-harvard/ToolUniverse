---
name: tooluniverse-medical-imaging-radiology
description: Discover and characterize cancer imaging cohorts spanning radiology (CT/MR/PT/CR/DX/US/NM) AND digital pathology (whole-slide microscopy) from two NCI archives — The Cancer Imaging Archive (TCIA: list public collections like LIDC-IDRI/TCGA-GBM/TCGA-LUAD/TCGA-BRCA, enumerate patients/studies/series, series-level DICOM metadata, download-size estimates) and Image Data Commons (IDC: broader modality coverage including whole-slide pathology images, cohort-level filter/count sizing across the whole archive). Use when someone asks to "find a CT/MRI/PET imaging cohort for [cancer type]", "find whole-slide pathology images for [cancer type]", "how many patients/studies/series are in [collection]", "what imaging modalities/body parts/scanners does [collection] have", "look up DICOM series metadata for [SeriesInstanceUID]", "estimate the size of this cohort before downloading", or "build an imaging research cohort". NOT for microscopy/cell imaging quantification (use tooluniverse-image-analysis), NOT for actual DICOM pixel data analysis, segmentation, or diagnosis (both TCIA and IDC tools here return metadata only — no pixel access), NOT for tumor genomic/omics data (use tooluniverse-cancer-genomics-tcga).
disable-model-invocation: true
---

# Cancer Radiology Imaging Cohort Discovery (TCIA)

Discover and characterize public cancer imaging cohorts from The Cancer
Imaging Archive (TCIA, National Cancer Institute) — collection, patient,
study, and DICOM series-level metadata for building or scoping a radiology
research cohort.

## Scope: what this skill can and cannot do

**Can:** enumerate collections, patients, studies, and series; filter by
modality/body part/manufacturer; pull DICOM series-level metadata (scanner,
acquisition, license); estimate series download size; list individual DICOM
instance (slice) UIDs.

**Cannot:** download or view actual pixel data, run segmentation/detection
models, or interpret images. Every TCIA tool here returns metadata about
what imaging exists — not the images themselves. If the user wants the
actual pixels, tell them the DICOM download UI/API is a separate TCIA
service (`https://www.cancerimagingarchive.net/`) outside this tool set.

TCIA data is public, de-identified cancer imaging. Study/series dates are
frequently shifted to a placeholder (e.g. `2000-01-01`) as part of
de-identification — do not interpret these as real acquisition dates.

## When to Use This Skill

- Find a public radiology imaging collection for a given cancer type or
  organ (e.g. lung nodule CT, glioblastoma MRI, breast MRI)
- Count patients, studies, or series in a collection, optionally filtered by
  modality or body part
- Check which modalities (CT/MR/PT/CR/DX/US/NM), body parts, or scanner
  manufacturers are represented in a collection before committing to it
- Get DICOM series-level metadata (equipment, acquisition parameters,
  license) for a specific `SeriesInstanceUID`
- Estimate total download size (bytes, image count) for a series before
  retrieving it
- Distinguish real patients from phantom/QA test objects in a collection

**NOT for** (route elsewhere):
- Microscopy/cell imaging quantification (ImageJ/CellProfiler/QuPath
  measurements, colony counts, fluorescence intensity) -> `tooluniverse-image-analysis`
- Actual pixel-level image analysis, segmentation, or diagnostic
  interpretation of DICOM images -> not covered by any ToolUniverse skill;
  these tools are metadata-only
- Tumor genomic/transcriptomic/mutation data (even for the same TCGA
  collections that TCIA also has imaging for) -> `tooluniverse-cancer-genomics-tcga`

## Tool Reference

| Tool | Purpose | Key params |
|------|---------|------------|
| `TCIA_list_collections` | List all public collection names | none |
| `TCIA_get_patients` | List patients/subjects in a collection (incl. phantom flag, species) | `Collection` |
| `TCIA_get_patient_studies` | List a patient's (or collection's) studies | `Collection`, `PatientID`, `StudyInstanceUID` |
| `TCIA_get_series` | List DICOM series (the main filterable search) | `Collection`, `PatientID`, `StudyInstanceUID`, `Modality`, `BodyPartExamined` |
| `TCIA_get_modality_values` | Facet: distinct modalities in a collection/body part | `Collection`, `BodyPartExamined` |
| `TCIA_get_body_part_values` | Facet: distinct body parts in a collection/modality | `Collection`, `Modality` |
| `TCIA_get_manufacturer_values` | Facet: distinct scanner manufacturers | `Collection`, `Modality`, `BodyPartExamined` |
| `TCIA_get_series_metadata` | Full DICOM metadata for one series | `SeriesInstanceUID` (required) |
| `TCIA_get_series_size` | Download size + image count for one series | `SeriesInstanceUID` (required) |
| `TCIA_get_sop_instance_uids` | List every individual image (slice) UID in a series | `SeriesInstanceUID` (required) |

All 10 tools verified live against the real TCIA API. Full example
calls and real (trimmed) responses: `references/tcia_tool_reference.md`.

## Workflow

1. **Find or confirm the collection.** If the user names a cancer
   type/organ rather than a TCIA collection name, call
   `TCIA_list_collections` and match against the name pattern (TCGA
   collections follow `TCGA-<CANCERTYPE>`, e.g. `TCGA-GBM`, `TCGA-LUAD`,
   `TCGA-BRCA`; other collections have their own names, e.g. `LIDC-IDRI`
   for lung nodule CT). Confirm the exact collection name with the user
   before proceeding — do not guess a collection name that wasn't returned
   by the tool.
2. **Facet the collection** (optional, to characterize it before
   committing): `TCIA_get_modality_values`, `TCIA_get_body_part_values`,
   `TCIA_get_manufacturer_values`, each filterable by `Collection`.
3. **Enumerate subjects.** `TCIA_get_patients` with `Collection` set —
   check the `Phantom` field to exclude QA phantom objects if the user
   wants only real human subjects, and `SpeciesDescription` if a
   non-human collection is possible.
4. **Drill into a subject's studies and series.** `TCIA_get_patient_studies`
   (by `Collection` + `PatientID`) then `TCIA_get_series` (by `Collection` +
   `PatientID`, optionally narrowed by `Modality`/`BodyPartExamined`) to get
   `SeriesInstanceUID`s.
5. **Inspect or size a specific series.** `TCIA_get_series_metadata` for
   full DICOM tags, `TCIA_get_series_size` to report download size/image
   count before recommending a download, `TCIA_get_sop_instance_uids` only
   if the user needs individual-slice-level references.
6. **Report** counts and facets actually returned by the tools — never
   estimate a patient/series count without calling the relevant tool.

## Notes

- `Collection`, `PatientID`, `Modality`, and `BodyPartExamined` are
  case-sensitive and must match TCIA's exact values — get them from
  `TCIA_list_collections` / `TCIA_get_modality_values` /
  `TCIA_get_body_part_values` rather than guessing capitalization.
- A single patient can have multiple studies, and a single study can have
  many series (observed: one LIDC-IDRI patient had a 1-series study and a
  9-series study) — always confirm which level (patient/study/series) the
  user actually wants counted.
- License varies by series (TCIA collections are typically CC-BY or
  CC-BY-NC) — surface the `LicenseName`/`LicenseURI` field from
  `TCIA_get_series` or `TCIA_get_series_metadata` if the user needs to know
  redistribution terms.

## Image Data Commons (IDC) — broader modalities, including digital pathology

IDC is a second, newer NCI archive (`api.imaging.datacommons.cancer.gov`,
no API key required) that overlaps with TCIA on radiology but additionally
covers **digital pathology / whole-slide microscopy** (DICOM modality `SM`),
which TCIA's NBIA API does not expose. Use IDC when the user wants pathology
slide images, or wants a fast cohort-size estimate across the whole archive
rather than TCIA's patient/study/series drill-down.

| Tool | Purpose | Key params |
|------|---------|------------|
| `IDC_list_collections` | List all IDC collections (cancer type, species, subject count) | none |
| `IDC_get_collection` | Detail for one collection: counts, size, modalities present, license | `collection_id` |
| `IDC_list_attributes` | List filterable attributes (name, type, categorical) | none |
| `IDC_list_attribute_values` | Real distinct values for a categorical attribute (e.g. `Modality`) | `attribute` |
| `IDC_get_cohort_counts` | Patient/study/series/instance counts + size (TB) for a filter, without downloading | `terms`, `ranges` (both optional) |

All 5 verified live. Real example: `IDC_list_attribute_values` with
`attribute="Modality"` returns real counts including `SM` (Slide
Microscopy) at 76,299 series — confirming genuine whole-slide pathology
coverage. `IDC_get_cohort_counts` with `terms={"Modality": ["SM"]}` returns
22,645 patients / 76,299 series / 49.02 TB for that filter alone.

**Cohort-count workflow:**
1. `IDC_list_attributes` to see what's filterable, then `IDC_list_attribute_values`
   on the attribute of interest (e.g. `Modality`, `BodyPartExamined`) to get
   real values — don't guess casing/spelling.
2. `IDC_get_cohort_counts` with `terms={"attribute": ["value", ...]}` for
   equality/IN filters, or `ranges={"attribute": {"gte": x, "lte": y}}` for
   numeric/date ranges. Combine multiple attributes in one call.
3. **Always check `filters_applied` and `warnings` in the response** before
   trusting the counts — an empty `filters_applied` means nothing was
   filtered and the numbers describe the *entire* IDC archive (99+ TB), not
   a cohort. This is a real, documented API behavior, not a bug: an empty
   filter is a valid way to ask "how big is IDC," but it's easy to mistake
   for "my filter matched everything."
4. `IDC_list_collections` / `IDC_get_collection` for collection-level
   browsing, parallel to TCIA's `TCIA_list_collections` /
   `TCIA_get_patients` pattern but without a patient/study drill-down —
   IDC's API is cohort-filter-oriented, not hierarchy-browse-oriented.

## References

- `references/tcia_tool_reference.md` — all 10 TCIA tools with real example
  calls and real (trimmed) responses captured live against the TCIA API
