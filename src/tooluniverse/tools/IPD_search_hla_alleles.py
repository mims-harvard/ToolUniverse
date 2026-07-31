"""
IPD_search_hla_alleles

Search the IPD-IMGT/HLA database for human HLA alleles by allele name prefix or substring (e.g. '...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def IPD_search_hla_alleles(
    name: str,
    match_: Optional[str] = "startsWith",
    limit: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search the IPD-IMGT/HLA database for human HLA alleles by allele name prefix or substring (e.g. '...

    Parameters
    ----------
    name : str
        HLA allele name or partial name to search (e.g. 'A*01:01', 'DRB1*15:01', 'B*0...
    match_ : str
        How to match the name: 'startsWith' (default, prefix match), 'contains' (subs...
    limit : int
        Maximum number of alleles to return (default 10, max 100).
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
    _args = {
        k: v
        for k, v in {"name": name, "match": match_, "limit": limit}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "IPD_search_hla_alleles",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["IPD_search_hla_alleles"]
