"""
STITCH_get_interaction_partners

Get all interaction partners (chemicals and proteins) for a given identifier. Returns network of ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def STITCH_get_interaction_partners(
    identifiers: list[str],
    species: Optional[int] = 9606,
    limit: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get all interaction partners (chemicals and proteins) for a given identifier. Returns network of ...

    Parameters
    ----------
    identifiers : list[str]
        Chemical or protein identifiers to query.
    species : int
        NCBI taxonomy ID.
    limit : int
        Maximum number of partners.
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
            "identifiers": identifiers,
            "species": species,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "STITCH_get_interaction_partners",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["STITCH_get_interaction_partners"]
