"""
SCXA_list_experiments

List a resumable page of single-cell RNA-seq experiments from EBI Single Cell Expression Atlas, w...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SCXA_list_experiments(
    species: Optional[str] = None,
    keyword: Optional[str] = None,
    limit: Optional[int] = 20,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    List a resumable page of single-cell RNA-seq experiments from EBI Single Cell Expression Atlas, w...

    Parameters
    ----------
    species : str
        Species name to filter by (e.g., 'Homo sapiens', 'Mus musculus', 'Drosophila ...
    keyword : str
        Keyword to search in experiment descriptions and factors (e.g., 'pancreas', '...
    limit : int
        Page size (default 20, max 100).
    offset : int
        Zero-based experiment offset. Continue with metadata.next_offset.
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    list[Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "species": species,
            "keyword": keyword,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "SCXA_list_experiments",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SCXA_list_experiments"]
