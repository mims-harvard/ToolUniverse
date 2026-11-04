"""
clinical_trial_ae_severity_test

Merge clinical trial demographics (DM) and adverse-events (AE) CSVs and run a statistical test on...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def clinical_trial_ae_severity_test(
    dm_file: str,
    ae_file: str,
    test: str,
    group_col: Optional[str] = None,
    subgroup: Optional[str] = None,
    covariates: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Merge clinical trial demographics (DM) and adverse-events (AE) CSVs and run a statistical test on...

    Parameters
    ----------
    dm_file : str
        Path to demographics CSV. Must contain USUBJID and the group_col.
    ae_file : str
        Path to adverse-events CSV. Must contain USUBJID and AESEV.
    test : str
        Statistical test to run. 'prepare' returns only the merged cohort stats.
    group_col : str
        Column in DM identifying treatment/exposure group. Default: TRTGRP.
    subgroup : str
        Optional filter expression 'col=value' (e.g. 'expect_interact=Yes').
    covariates : str
        Comma-separated covariate column names for ordinal regression (e.g. 'patients...
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    dict[str, Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "dm_file": dm_file,
            "ae_file": ae_file,
            "test": test,
            "group_col": group_col,
            "subgroup": subgroup,
            "covariates": covariates,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "clinical_trial_ae_severity_test",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["clinical_trial_ae_severity_test"]
