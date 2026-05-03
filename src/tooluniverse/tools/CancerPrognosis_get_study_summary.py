"""
CancerPrognosis_get_study_summary

Get summary information for a cancer study including available molecular profiles (mutations, exp...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CancerPrognosis_get_study_summary(
    operation: Optional[str] = None,
    cancer: Optional[str] = None,
    cancer_type: Optional[str] = None,
    study_id: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get summary information for a cancer study including available molecular profiles (mutations, exp...

    Parameters
    ----------
    operation : str
        Operation type
    cancer : str
        TCGA cancer type abbreviation (e.g., 'BRCA', 'LUAD', 'COADREAD') or cBioPorta...
    cancer_type : str
        Alias for cancer. TCGA cancer type abbreviation (e.g., 'BRCA', 'LUAD', 'COADR...
    study_id : str
        Alias for cancer. cBioPortal study ID (e.g., 'brca_tcga', 'luad_tcga').
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    Any
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "operation": operation,
            "cancer": cancer,
            "cancer_type": cancer_type,
            "study_id": study_id,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "CancerPrognosis_get_study_summary",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["CancerPrognosis_get_study_summary"]
