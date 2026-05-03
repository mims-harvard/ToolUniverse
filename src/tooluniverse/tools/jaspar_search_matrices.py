"""
jaspar_search_matrices

Search/filter JASPAR matrices using common query parameters. Typical filters include `search` (fr...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def jaspar_search_matrices(
    search: Optional[str] = None,
    name: Optional[str] = None,
    collection: Optional[str] = None,
    tax_group: Optional[str] = None,
    species: Optional[str] = None,
    page: Optional[int] = 1,
    page_size: Optional[int] = 20,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search/filter JASPAR matrices using common query parameters. Typical filters include `search` (fr...

    Parameters
    ----------
    search : str
        Free-text search across matrices (e.g., 'CTCF').
    name : str
        Filter by TF name (e.g., 'CTCF').
    collection : str
        Filter by collection (e.g., 'CORE').
    tax_group : str
        Filter by taxonomic group (e.g., 'vertebrates').
    species : str
        Filter by NCBI taxonomy ID (e.g., '9606' for human).
    page : int
        Page number (1-based).
    page_size : int
        Results per page.
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
            "search": search,
            "name": name,
            "collection": collection,
            "tax_group": tax_group,
            "species": species,
            "page": page,
            "page_size": page_size,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "jaspar_search_matrices",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["jaspar_search_matrices"]
