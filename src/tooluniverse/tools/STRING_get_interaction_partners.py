"""
STRING_get_interaction_partners

Get ranked interaction partners for one protein from STRING. STRING's limit=0 returns the complet...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def STRING_get_interaction_partners(
    identifiers: str,
    species: Optional[int] = 9606,
    limit: Optional[int] = 10,
    offset: Optional[int] = 0,
    required_score: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get ranked interaction partners for one protein from STRING. STRING's limit=0 returns the complet...

    Parameters
    ----------
    identifiers : str
        Protein identifier (gene name or STRING ID). Examples: 'TP53', 'BRCA1', 'EGFR...
    species : int
        NCBI taxonomy ID (9606=human, 10090=mouse, 7227=fly, 6239=worm)
    limit : int
        Number of ranked partners in this client-side page (default 10)
    offset : int
        Zero-based ranked-partner offset. Continue with metadata.next_offset while me...
    required_score : int
        Minimum combined STRING score (0-1000). 400=medium, 700=high, 900=highest con...
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
            "offset": offset,
            "required_score": required_score,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "STRING_get_interaction_partners",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["STRING_get_interaction_partners"]
