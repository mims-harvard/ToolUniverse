"""
PubMed_get_links

Get external links (LinkOut) for a specific PubMed article by its PMID using elink. Returns URLs ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PubMed_get_links(
    pmid: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get external links (LinkOut) for a specific PubMed article by its PMID using elink. Returns URLs ...

    Parameters
    ----------
    pmid : str
        PubMed ID (PMID) for which to retrieve external links (e.g., '19880848', '198...
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
    _args = {k: v for k, v in {"pmid": pmid}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "PubMed_get_links",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PubMed_get_links"]
