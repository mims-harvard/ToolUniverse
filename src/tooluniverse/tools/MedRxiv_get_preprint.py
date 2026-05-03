"""
MedRxiv_get_preprint

Get full metadata for a specific medRxiv preprint by its DOI. Returns comprehensive metadata incl...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MedRxiv_get_preprint(
    doi: str,
    server: Optional[str] = "medrxiv",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get full metadata for a specific medRxiv preprint by its DOI. Returns comprehensive metadata incl...

    Parameters
    ----------
    doi : str
        medRxiv DOI. Can be full DOI (e.g., '10.1101/2021.04.29.21256344') or just th...
    server : str
        Server to query - always 'medrxiv' for this tool.
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
    _args = {k: v for k, v in {"doi": doi, "server": server}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "MedRxiv_get_preprint",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MedRxiv_get_preprint"]
