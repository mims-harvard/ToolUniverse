Responses recorded from https://api.cellmodelpassports.sanger.ac.uk on
2026-11-25, without a key. Used by tests/unit/test_depmap_gene_dependency_scores.py.

- `crispr_ko_KRAS_5_models.json`: `/genes/SIDG13960/datasets/crispr_ko` with
  the `include` and `fields` parameters the tool sends, plus a `filter` that
  keeps 5 models (HT-29, A549, SW626, HCC461 and the organoid
  WTSI-COLIVM_005), so the file is 6 kB. It is complete for those models:
  7 records, because HT-29 and A549 were screened by Sanger and by Broad.
  The unfiltered answer has 1,269 records (955 kB).
- `crispr_ko_OR4F5_none.json`: the same route for OR4F5 (SIDG22950), a gene
  with no knockout record. HTTP 200, `meta.count` 0.
- `crispr_ko_gene_404.json`: the same route for the gene id SIDG99999. HTTP 404.
- `model_SIDM01774.json`: `/models/SIDM01774` (PK-59), a model with no
  CRISPR knockout data.
- `model_unknown.json`: `/models/SIDM99999`. HTTP 200 with `"data": null`.
