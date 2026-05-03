"""
EpiGraphDB_search_opengwas

Search the IEU OpenGWAS database for GWAS studies by trait name. Returns matching GWAS study IDs ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EpiGraphDB_search_opengwas(
    query: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search the IEU OpenGWAS database for GWAS studies by trait name. Returns matching GWAS study IDs ...

    Parameters
    ----------
    query : str
        Trait or phenotype name to search for in OpenGWAS (e.g., 'body mass index', '...
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
    _args = {k: v for k, v in {"query": query}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "EpiGraphDB_search_opengwas",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EpiGraphDB_search_opengwas"]
