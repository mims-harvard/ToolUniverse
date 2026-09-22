# TCIA Tool Reference

All 10 tools live-tested against the real TCIA API
(`https://services.cancerimagingarchive.net/nbia-api/`) on 2026-09-17.
Every response below is real output (trimmed for length), not fabricated.

TCIA scope: public, de-identified cancer imaging metadata. These tools
return **metadata only** — collection/patient/study/series descriptors,
never pixel data. Dates are frequently shifted for de-identification
(observed: `StudyDate: "2000-01-01 00:00:00.0"` on a real LIDC-IDRI study).

## 1. `TCIA_list_collections`

No parameters.

```
tu run TCIA_list_collections '{}'
```

```json
{"status": "success", "data": [
  {"Collection": "4D-Lung"},
  {"Collection": "A091105"},
  {"Collection": "ACNS0332"},
  {"Collection": "ACRIN-6698"},
  {"Collection": "ACRIN-Contralateral-Breast-MR"}
]}
```

Hundreds of collections exist. TCGA-linked collections follow
`TCGA-<CANCERTYPE>` (e.g. `TCGA-GBM`, `TCGA-LUAD`, `TCGA-BRCA`); others use
study-specific names (e.g. `LIDC-IDRI` for the Lung Image Database
Consortium lung-nodule CT collection).

## 2. `TCIA_get_patients`

Params: `Collection` (optional; omit for all collections).

```
tu run TCIA_get_patients '{"Collection":"LIDC-IDRI"}'
```

```json
{"status": "success", "data": [
  {"PatientId": "LIDC-IDRI-0001", "PatientName": "", "Collection": "LIDC-IDRI",
   "Phantom": "NO", "SpeciesCode": "337915000", "SpeciesDescription": "Homo sapiens"},
  {"PatientId": "LIDC-IDRI-0002", "PatientName": "", "Collection": "LIDC-IDRI",
   "Phantom": "NO", "SpeciesCode": "337915000", "SpeciesDescription": "Homo sapiens"}
]}
```

`Phantom: "YES"` marks QA test objects, not real patients — filter these
out when the user wants a human-subject cohort count.

## 3. `TCIA_get_patient_studies`

Params: `Collection`, `PatientID`, `StudyInstanceUID` (all optional; combine
to narrow).

```
tu run TCIA_get_patient_studies '{"Collection":"LIDC-IDRI","PatientID":"LIDC-IDRI-0001"}'
```

```json
{"status": "success", "data": [
  {"StudyInstanceUID": "1.3.6.1.4.1.14519.5.2.1.6279.6001.175012972118199124641098335511",
   "StudyDate": "2000-01-01 00:00:00.0", "PatientID": "LIDC-IDRI-0001",
   "PatientName": "", "Collection": "LIDC-IDRI", "SeriesCount": 1},
  {"StudyInstanceUID": "1.3.6.1.4.1.14519.5.2.1.6279.6001.298806137288633453246975630178",
   "StudyDate": "2000-01-01 00:00:00.0", "PatientID": "LIDC-IDRI-0001",
   "PatientName": "", "Collection": "LIDC-IDRI", "SeriesCount": 9}
], "count": 2}
```

One patient here had two studies: a 1-series study and a 9-series study —
always check `SeriesCount` rather than assuming one series per study.

## 4. `TCIA_get_series`

Params: `Collection`, `PatientID`, `StudyInstanceUID`, `Modality`,
`BodyPartExamined` (all optional; combine to narrow). This is the main
filterable search across series.

```
tu run TCIA_get_series '{"Collection":"LIDC-IDRI","PatientID":"LIDC-IDRI-0001"}'
```

```json
{"status": "success", "data": [
  {"SeriesInstanceUID": "1.3.6.1.4.1.14519.5.2.1.6279.6001.141365756818074696859567662357",
   "StudyInstanceUID": "1.3.6.1.4.1.14519.5.2.1.6279.6001.175012972118199124641098335511",
   "Modality": "DX", "SeriesDate": "2000-01-01 00:00:00.0",
   "BodyPartExamined": "CHEST", "SeriesNumber": 3000923,
   "AnnotationsFlag": true, "Collection": "LIDC-IDRI",
   "PatientID": "LIDC-IDRI-0001", "Manufacturer": "GE MEDICAL SYSTEMS",
   "ManufacturerModelName": "Revolution XQi ADS_28.2",
   "ImageCount": 2, "FileSize": 16357620,
   "LicenseName": "Creative Commons Attribution 3.0 Unported License",
   "LicenseURI": "http://creativecommons.org/licenses/by/3.0/",
   "CollectionURI": "https://doi.org/10.7937/K9/TCIA.2015.LO9QL9SX"}
]}
```

Note this patient's first study is a chest DX (digital radiograph), not a
CT — confirm modality per series rather than assuming a collection is
uniformly one modality.

## 5. `TCIA_get_modality_values`

Params: `Collection`, `BodyPartExamined` (both optional).

```
tu run TCIA_get_modality_values '{"Collection":"LIDC-IDRI"}'
```

```json
{"status": "success", "data": [
  {"Modality": "CR"}, {"Modality": "CT"}, {"Modality": "DX"},
  {"Modality": "SEG"}, {"Modality": "..."}
]}
```

LIDC-IDRI itself is not CT-only — it also has CR/DX radiographs and `SEG`
(DICOM segmentation objects, i.e. annotation overlays), not just the raw
CT series.

## 6. `TCIA_get_body_part_values`

Params: `Collection`, `Modality` (both optional).

```
tu run TCIA_get_body_part_values '{"Modality":"CT"}'
```

```json
{"status": "success", "data": [
  {}, {"BodyPartExamined": "ABDOMEN"}, {"BodyPartExamined": "ABDOMENPELVIS"},
  {"BodyPartExamined": "ADRENAL"}, {"BodyPartExamined": "AORTA"},
  {"BodyPartExamined": "BLADDER"}
]}
```

Note the real response includes an empty `{}` entry (series with no
`BodyPartExamined` tag set) — handle this rather than assuming every
element has the key.

## 7. `TCIA_get_manufacturer_values`

Params: `Collection`, `Modality`, `BodyPartExamined` (all optional).

```
tu run TCIA_get_manufacturer_values '{"Collection":"LIDC-IDRI","Modality":"CT"}'
```

```json
{"status": "success", "data": [
  {"Manufacturer": "GE MEDICAL SYSTEMS"}, {"Manufacturer": "Philips"},
  {"Manufacturer": "SIEMENS"}
]}
```

## 8. `TCIA_get_series_metadata`

Params: `SeriesInstanceUID` (required).

```
tu run TCIA_get_series_metadata '{"SeriesInstanceUID":"1.3.6.1.4.1.14519.5.2.1.6279.6001.141365756818074696859567662357"}'
```

```json
{"status": "success", "data": [
  {"Series UID": "1.3.6.1.4.1.14519.5.2.1.6279.6001.141365756818074696859567662357",
   "Collection": "LIDC-IDRI",
   "Data Description URI": "https://doi.org/10.7937/K9/TCIA.2015.LO9QL9SX",
   "Subject ID": "LIDC-IDRI-0001",
   "Study UID": "1.3.6.1.4.1.14519.5.2.1.6279.6001.175012972118199124641098335511",
   "Study Date": "01-01-2000", "Manufacturer": "GE MEDICAL SYSTEMS",
   "Modality": "DX", "SOP Class UID": "1.2.840.10008.5.1.4.1.1.1.1",
   "Number of Images": "2", "File Size": "16357620",
   "Series Number": "3000923.000000",
   "License Name": "Creative Commons Attribution 3.0 Unported License"}
]}
```

Note the field naming here (`"Series UID"`, `"Study Date"`, spaced keys)
differs from `TCIA_get_series`'s camelCase field names (`SeriesInstanceUID`,
`StudyDate`) — this is a different underlying NBIA endpoint with its own
field-naming convention; do not assume the two tools share a schema.

## 9. `TCIA_get_series_size`

Params: `SeriesInstanceUID` (required). Use before recommending a download.

```
tu run TCIA_get_series_size '{"SeriesInstanceUID":"1.3.6.1.4.1.14519.5.2.1.6279.6001.141365756818074696859567662357"}'
```

```json
{"status": "success", "data": [{"TotalSizeInBytes": 16357620, "ObjectCount": 2}], "count": 1}
```

Matches the `FileSize`/`ImageCount` fields already visible in
`TCIA_get_series`'s response for the same series (16357620 bytes, 2
images) — both are legitimate ways to get the same numbers.

## 10. `TCIA_get_sop_instance_uids`

Params: `SeriesInstanceUID` (required). Deepest granularity — one entry per
individual DICOM image/slice.

```
tu run TCIA_get_sop_instance_uids '{"SeriesInstanceUID":"1.3.6.1.4.1.14519.5.2.1.6279.6001.141365756818074696859567662357"}'
```

```json
{"status": "success", "data": [
  {"SOPInstanceUID": "1.3.6.1.4.1.14519.5.2.1.6279.6001.307896144859643716158189196068"},
  {"SOPInstanceUID": "1.3.6.1.4.1.14519.5.2.1.6279.6001.257944242390114100388269195181"}
]}
```

Two SOP instances for this series, matching `ImageCount: 2` from
`TCIA_get_series` — consistent across tools.
