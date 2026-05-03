"""
BioRxiv_get_preprint

Get full metadata for a specific bioRxiv or medRxiv preprint by its DOI. Returns comprehensive me...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BioRxiv_get_preprint(
    doi: str,
    server: Optional[str] = "biorxiv",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get full metadata for a specific bioRxiv or medRxiv preprint by its DOI. Returns comprehensive me...

    Parameters
    ----------
    doi : str
        bioRxiv or medRxiv DOI. Can be full DOI (e.g., '10.1101/2023.12.01.569554') o...
    server : str
        Server to query: 'biorxiv' for bioRxiv preprints or 'medrxiv' for medRxiv pre...
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
            "name": "BioRxiv_get_preprint",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BioRxiv_get_preprint"]
