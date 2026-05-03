"""
ClinGenAllele_get_allele

Get detailed information for a canonical allele by its ClinGen Allele Registry CA ID. Returns cro...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ClinGenAllele_get_allele(
    ca_id: Optional[str | Any] = None,
    allele_id: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get detailed information for a canonical allele by its ClinGen Allele Registry CA ID. Returns cro...

    Parameters
    ----------
    ca_id : str | Any
        ClinGen canonical allele identifier (e.g., 'CA000387'). Obtain from ClinGenAl...
    allele_id : str | Any
        Alias for ca_id. ClinGen canonical allele identifier (e.g., 'CA000387').
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
        for k, v in {"ca_id": ca_id, "allele_id": allele_id}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ClinGenAllele_get_allele",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ClinGenAllele_get_allele"]
