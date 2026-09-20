---

name: tooluniverse-medical-imaging-radiology
description: "Discover and characterize cancer radiology imaging cohorts from The Cancer Imaging Archive (TCIA) — list public collections (e.g. LIDC-IDRI, TCGA-GBM, TCGA-LUAD, TCGA-BRCA), enumerate patients/subjects and studies within a collection, browse DICOM series by modality (CT, MR, PT, CR, DX, US, NM) or body part (CHEST, BRAIN, ABDOMEN, ...), pull series-level DICOM metadata and scanner manufacturer, estimate download size before pulling data, and enumerate individual DICOM instance (slice) UIDs within a series. Use when someone asks to \"find a CT/MRI/PET imaging cohort for [cancer type]\", \"how many patients/studies/series are in [TCIA collection]\", \"what imaging modalities/body parts/scanners does [collection] have\", \"look up DICOM series metadata for [SeriesInstanceUID]\", \"estimate the size of this TCIA series before downloading\", or \"build a radiology imaging research cohort\". NOT for microscopy/cell imaging quantification (use tooluniverse-image-analysis), NOT for actual DICOM pixel..."
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

## References

- `references/tcia_tool_reference.md` — all 10 tools with real example
  calls and real (trimmed) responses captured live against the TCIA API
