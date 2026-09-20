# Output JSON schema

Every conversion produces one JSON document shaped like this (Allotrope
Simple Model-INSPIRED — not a certified ASM file unless produced via Tier 1
`allotropy`):

```json
{
  "asm_like": true,
  "tier": "native" | "fallback",
  "note": "<present only for tier=fallback: 'not ASM-validated, best-effort structural parse'>",
  "manifest": "http://purl.allotrope.org/... (Tier 1 only)",
  "source_file": "plate_reader_run1.csv",
  "detected_instrument": "generic-plate-reader" | "<allotropy Vendor name>",
  "device_system_document": {
    "device_identifier": "<from file if present, else null>",
    "model_number": null,
    "asset_management_identifier": null
  },
  "measurement_documents": [
    {
      "measurement_identifier": "M0001",
      "sample_document": {
        "sample_identifier": "S1",
        "well_location_identifier": "A1",
        "well_plate_identifier": null
      },
      "raw_measurements": {
        "absorbance_450nm": {"value": 0.842, "unit": "AU"}
      },
      "device_control_document": {},
      "measurement_time": null
    }
  ],
  "calculated_data_aggregate_document": {
    "calculated_data_document": [
      {
        "calculated_data_identifier": "C0001",
        "calculated_data_name": "concentration",
        "calculated_result": {"value": 12.4, "unit": "ng/uL"},
        "data_source_aggregate_document": {
          "data_source_document": [
            {"data_source_identifier": "M0001", "data_source_feature": "absorbance_450nm"}
          ]
        }
      }
    ]
  }
}
```

## Field rules

- `measurement_documents[].raw_measurements` holds ONLY values read directly
  from an instrument channel/column in the source file.
- `calculated_data_aggregate_document` holds ONLY values that are themselves
  derived from other columns in the same file (e.g. a `concentration` column
  computed by the instrument's own software from absorbance). Every entry
  here MUST carry a `data_source_aggregate_document` pointing at the
  `measurement_identifier` (and feature name) it was derived from. If the
  fallback parser cannot establish that link with confidence, the value is
  left in `raw_measurements` instead and never guessed at.
- Tier 2 (fallback) output additionally sets `"tier": "fallback"` and a
  `"note"` field so downstream consumers can tell it was not produced by
  allotropy's vendor-certified parser.
- No field is ever populated with a fabricated value. If a value can't be
  found in the source file, the key is omitted (or set to `null`) — never
  invented.

See `field_classification_guide.md` for how to decide raw vs. calculated,
and `supported_instruments.md` for what each tier actually parses.
