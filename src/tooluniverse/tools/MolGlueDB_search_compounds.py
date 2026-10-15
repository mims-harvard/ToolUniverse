"""
MolGlueDB_search_compounds

Full-text search MolGlueDB for molecular glue degrader (MGD) compounds -- small molecules that in...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MolGlueDB_search_compounds(
    keyword: str,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Full-text search MolGlueDB for molecular glue degrader (MGD) compounds -- small molecules that in...

    Parameters
    ----------
    keyword : str
        Search term: target protein ('IKZF2'), recruiting protein ('CRBN'), or compou...
    limit : int
        Max compounds to return, 1-200. Default 30.
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
        k: v for k, v in {"keyword": keyword, "limit": limit}.items() if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "MolGlueDB_search_compounds",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MolGlueDB_search_compounds"]
