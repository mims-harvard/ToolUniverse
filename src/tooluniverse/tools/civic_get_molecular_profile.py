"""
civic_get_molecular_profile

Get detailed information about a specific molecular profile in CIViC database by molecular profil...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def civic_get_molecular_profile(
    molecular_profile_id: int,
    evidence_limit: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get detailed information about a specific molecular profile in CIViC database by molecular profil...

    Parameters
    ----------
    molecular_profile_id : int
        CIViC molecular profile ID (e.g., 12 for BRAF V600E)
    evidence_limit : int
        Maximum number of evidence items to return (default: 10)
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
            "molecular_profile_id": molecular_profile_id,
            "evidence_limit": evidence_limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "civic_get_molecular_profile",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["civic_get_molecular_profile"]
