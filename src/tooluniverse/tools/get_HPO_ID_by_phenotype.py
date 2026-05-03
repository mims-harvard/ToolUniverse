"""
get_HPO_ID_by_phenotype

Retrieve the HPO ID of a phenotype or symptom.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def get_HPO_ID_by_phenotype(
    query: str,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Retrieve the HPO ID of a phenotype or symptom.

    Parameters
    ----------
    query : str
        One query phenotype or symptom.
    limit : int
        Number of entries to fetch.
    offset : int
        Number of initial entries to skip.
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
        for k, v in {"query": query, "limit": limit, "offset": offset}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "get_HPO_ID_by_phenotype",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["get_HPO_ID_by_phenotype"]
