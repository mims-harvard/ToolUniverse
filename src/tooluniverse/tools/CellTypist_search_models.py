"""
CellTypist_search_models

Search the CellTypist catalog of pre-trained models for automated single-cell type annotation, co...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CellTypist_search_models(
    keyword: Optional[str] = None,
    min_celltypes: Optional[int] = None,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search the CellTypist catalog of pre-trained models for automated single-cell type annotation, co...

    Parameters
    ----------
    keyword : str
        Case-insensitive filter on model description or filename, e.g. 'lung', 'immun...
    min_celltypes : int
        Only return models resolving at least this many cell types, e.g. 50.
    limit : int
        Maximum models to return (default 25, max 100).
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
            "keyword": keyword,
            "min_celltypes": min_celltypes,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "CellTypist_search_models",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["CellTypist_search_models"]
