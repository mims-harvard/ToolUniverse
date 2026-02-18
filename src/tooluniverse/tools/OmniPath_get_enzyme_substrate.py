"""
OmniPath_get_enzyme_substrate

Get enzyme-substrate (post-translational modification) interactions from OmniPath. Integrates dat...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OmniPath_get_enzyme_substrate(
    enzymes: Optional[str | Any] = None,
    substrates: Optional[str | Any] = None,
    types: Optional[str | Any] = None,
    organisms: Optional[int | Any] = None,
    limit: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get enzyme-substrate (post-translational modification) interactions from OmniPath. Integrates dat...

    Parameters
    ----------
    enzymes : str | Any
        Gene symbol(s) or UniProt ID(s) for enzyme/kinase. Comma-separated for multip...
    substrates : str | Any
        Gene symbol(s) or UniProt ID(s) for substrate. Examples: 'STAT3', 'P40763'.
    types : str | Any
        Modification type filter. Options include: phosphorylation, ubiquitination, a...
    organisms : int | Any
        NCBI taxonomy ID. Default: 9606 (human).
    limit : int | Any
        Maximum number of results to return.
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
            "name": "OmniPath_get_enzyme_substrate",
            "arguments": {
                "enzymes": enzymes,
                "substrates": substrates,
                "types": types,
                "organisms": organisms,
                "limit": limit,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OmniPath_get_enzyme_substrate"]
