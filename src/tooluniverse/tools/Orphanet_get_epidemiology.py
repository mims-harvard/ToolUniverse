"""
Orphanet_get_epidemiology

Get epidemiology data (prevalence, incidence) for a rare disease from Orphanet. Returns prevalenc...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Orphanet_get_epidemiology(
    operation: str,
    orpha_code: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get epidemiology data (prevalence, incidence) for a rare disease from Orphanet. Returns prevalenc...

    Parameters
    ----------
    operation : str
        Operation type (fixed: get_epidemiology)
    orpha_code : str
        Orphanet ORPHA code (e.g., 558 for Marfan, 586 for Cystic Fibrosis)
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

    return get_shared_client().run_one_function(
        {
            "name": "Orphanet_get_epidemiology",
            "arguments": {"operation": operation, "orpha_code": orpha_code},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Orphanet_get_epidemiology"]
