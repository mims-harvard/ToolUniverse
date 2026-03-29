"""
STITCH_resolve_identifier

Resolve a chemical or protein name to STITCH database identifiers. Useful for mapping common name...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def STITCH_resolve_identifier(
    identifier: str,
    species: Optional[int] = 9606,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Resolve a chemical or protein name to STITCH database identifiers. Useful for mapping common name...

    Parameters
    ----------
    identifier : str
        Chemical or protein name to resolve (e.g., 'aspirin', 'TP53').
    species : int
        NCBI taxonomy ID.
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
        for k, v in {"identifier": identifier, "species": species}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "STITCH_resolve_identifier",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["STITCH_resolve_identifier"]
