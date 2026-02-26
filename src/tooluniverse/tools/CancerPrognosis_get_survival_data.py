"""
CancerPrognosis_get_survival_data

Retrieve patient-level overall survival (OS) and disease-free survival (DFS) data from a TCGA or ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CancerPrognosis_get_survival_data(
    operation: str,
    cancer: str,
    max_patients: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Retrieve patient-level overall survival (OS) and disease-free survival (DFS) data from a TCGA or ...

    Parameters
    ----------
    operation : str
        Operation type
    cancer : str
        TCGA cancer type abbreviation (e.g., 'BRCA', 'LUAD', 'COAD', 'GBM') or cBioPo...
    max_patients : int | Any
        Maximum number of patient records to return (default 500, max 2000)
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

    return get_shared_client().run_one_function(
        {
            "name": "CancerPrognosis_get_survival_data",
            "arguments": {
                "operation": operation,
                "cancer": cancer,
                "max_patients": max_patients,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["CancerPrognosis_get_survival_data"]
