# Response Format Examples

Verified JSON response structures for key tools used in multi-omics disease characterization.

---

## OpenTargets Associated Targets
```json
{
  "data": {
    "disease": {
      "id": "MONDO_0004975",
      "name": "Alzheimer disease",
      "associatedTargets": {
        "count": 2456,
        "rows": [
          {
            "target": {"id": "ENSG00000080815", "approvedSymbol": "PSEN1"},
            "score": 0.87
          }
        ]
      }
    }
  }
}
```

## GWAS Catalog Associations
```json
{
  "data": [
    {
      "association_id": 216440893,
      "p_value": 2e-09,
      "or_per_copy_num": 0.94,
      "or_value": "0.94",
      "efo_traits": [{"..."}],
      "risk_frequency": "NR"
    }
  ],
  "metadata": {"pagination": {"totalElements": 1061816}}
}
```

## STRING Interactions
```json
{
  "status": "success",
  "data": [
    {
      "stringId_A": "9606.ENSP00000252486",
      "stringId_B": "9606.ENSP00000466775",
      "preferredName_A": "APOE",
      "preferredName_B": "APOC2",
      "score": 0.999
    }
  ]
}
```

## Reactome Enrichment
```json
{
  "data": {
    "token": "...",
    "pathways_found": 154,
    "pathways": [
      {
        "pathway_id": "R-HSA-1251985",
        "name": "Nuclear signaling by ERBB4",
        "species": "Homo sapiens",
        "is_disease": false,
        "is_lowest_level": true,
        "entities_found": 3,
        "entities_total": 47,
        "entities_ratio": 0.00291,
        "p_value": 4.0e-06,
        "fdr": 0.00068,
        "reactions_found": 3,
        "reactions_total": 34
      }
    ]
  }
}
```

## HPA RNA Expression
```json
{
  "status": "success",
  "data": {
    "gene_name": "APOE",
    "source_type": "tissue",
    "source_name": "brain",
    "expression_value": "2714.9",
    "expression_level": "very high",
    "expression_unit": "nTPM"
  }
}
```

## Enrichr Results
```json
{
  "status": "success",
  "data": "{\"connected_paths\": {\"Path: ...\": \"Total Weight: ...\"}}"
}
```
**NOTE**: The `data` field is a JSON string that needs parsing.
