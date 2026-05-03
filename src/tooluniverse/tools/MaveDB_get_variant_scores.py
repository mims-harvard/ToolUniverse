"""
MaveDB_get_variant_scores

Get functional variant effect scores from a MaveDB score set. Returns HGVS-annotated variants wit...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MaveDB_get_variant_scores(
    urn: str,
    hgvs_pro: Optional[str] = None,
    limit: Optional[int] = 50,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get functional variant effect scores from a MaveDB score set. Returns HGVS-annotated variants wit...

    Parameters
    ----------
    urn : str
        MaveDB score set URN (e.g., 'urn:mavedb:00001234-c-1'). Obtain from MaveDB_se...
    hgvs_pro : str
        Optional filter: HGVS protein notation substring (e.g., 'Arg175', 'p.Arg175Hi...
    limit : int
        Maximum variants to return (default 50, max 500).
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
        for k, v in {"urn": urn, "hgvs_pro": hgvs_pro, "limit": limit}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "MaveDB_get_variant_scores",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MaveDB_get_variant_scores"]
