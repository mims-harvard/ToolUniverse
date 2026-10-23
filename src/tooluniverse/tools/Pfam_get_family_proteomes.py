"""
Pfam_get_family_proteomes

Get the proteome (organism) distribution for a Pfam protein family, including organism names, tax...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Pfam_get_family_proteomes(
    pfam_accession: str,
    max_results: Optional[int] = 20,
    cursor: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get the proteome (organism) distribution for a Pfam protein family, including organism names, tax...

    Parameters
    ----------
    pfam_accession : str
        Pfam family accession. Examples: 'PF00001' (7tm_1, found in 1890 proteomes), ...
    max_results : int
        Maximum number of proteomes to return (default 20, max 100).
    cursor : str
        Opaque InterPro cursor returned as next_cursor by a previous call. Omit for t...
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
        for k, v in {
            "pfam_accession": pfam_accession,
            "max_results": max_results,
            "cursor": cursor,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Pfam_get_family_proteomes",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Pfam_get_family_proteomes"]
