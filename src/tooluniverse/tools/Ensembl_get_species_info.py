"""
Ensembl_get_species_info

Search and page through species available in the Ensembl database with their genome assembly info...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Ensembl_get_species_info(
    search: Optional[str] = None,
    limit: Optional[int] = 50,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search and page through species available in the Ensembl database with their genome assembly info...

    Parameters
    ----------
    search : str
        Search term to filter species. Can be a species name ('mus_musculus'), common...
    limit : int
        Maximum matched species to return on this page.
    offset : int
        Zero-based offset into the filtered species list.
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
        for k, v in {"search": search, "limit": limit, "offset": offset}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Ensembl_get_species_info",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Ensembl_get_species_info"]
