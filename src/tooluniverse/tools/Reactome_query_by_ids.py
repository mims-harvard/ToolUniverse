"""
Reactome_query_by_ids

Query Reactome by providing a list of Reactome stable identifiers (R-HSA-*). Returns detailed inf...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Reactome_query_by_ids(
    ids: list[str],
    species: Optional[str] = None,
    types: Optional[list[str]] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Query Reactome by providing a list of Reactome stable identifiers (R-HSA-*). Returns detailed inf...

    Parameters
    ----------
    ids : list[str]
        List of Reactome stable identifiers (e.g., 'R-HSA-73817', 'R-HSA-111289'). Mu...
    species : str
        NOT SUPPORTED by this endpoint; supplying it returns an error. Reactome's /da...
    types : list[str]
        NOT SUPPORTED by this endpoint; supplying it returns an error. Reactome's /da...
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
        for k, v in {"ids": ids, "species": species, "types": types}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Reactome_query_by_ids",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Reactome_query_by_ids"]
