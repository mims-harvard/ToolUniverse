"""
CATH_list_funfams

List functional families (FunFams) within a CATH superfamily. FunFams group protein domains that ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CATH_list_funfams(
    superfamily_id: str,
    max_results: Optional[int] = 25,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    List functional families (FunFams) within a CATH superfamily. FunFams group protein domains that ...

    Parameters
    ----------
    superfamily_id : str
        CATH superfamily ID in C.A.T.H format. Examples: '1.10.510.10' (Globin-like),...
    max_results : int
        Maximum number of FunFams to return (default: 25).
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
            "max_results": max_results,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "CATH_list_funfams",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["CATH_list_funfams"]
