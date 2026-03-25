"""
CATH_get_funfam

Get details for a specific functional family (FunFam) within a CATH superfamily. Returns FunFam n...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CATH_get_funfam(
    superfamily_id: str,
    funfam_number: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get details for a specific functional family (FunFam) within a CATH superfamily. Returns FunFam n...

    Parameters
    ----------
    superfamily_id : str
        CATH superfamily ID (e.g., '1.10.510.10').
    funfam_number : str
        FunFam number within the superfamily (e.g., '1', '83'). Get from CATH_list_fu...
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
            "superfamily_id": superfamily_id,
            "funfam_number": funfam_number,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "CATH_get_funfam",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["CATH_get_funfam"]
