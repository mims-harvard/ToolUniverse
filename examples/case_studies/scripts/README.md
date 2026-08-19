# `scripts/`

`prepare_ae_cohort.py` is the cohort-construction and statistics implementation
behind Case 3.

The `clinical_trial_ae_severity_test` tool wraps the equivalent script in the
repository's `skills/tooluniverse-statistical-modeling/scripts/` directory,
resolved relative to the repo root — so the tool only works from a git clone.
This copy lets `case3_bcg_ae_severity.py` produce the published numbers from a
plain `pip install` as well, and it runs on pandas 3, where
`dtype == object` no longer identifies string columns and integer indexing on a
labelled Series raises `KeyError`.

Run it directly if you want the analysis without ToolUniverse:

```bash
python prepare_ae_cohort.py \
    --dm ../data/TASK008_BCG-CORONA_DM.csv \
    --ae ../data/TASK008_BCG-CORONA_AE.csv \
    --test ordinal --group TRTGRP \
    --covariates patients_seen,expect_interact,work_hours
```
