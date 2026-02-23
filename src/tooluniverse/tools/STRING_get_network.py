"""
STRING_get_network

Get the protein-protein interaction network for one or more proteins from STRING database. Return...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def STRING_get_network(
    identifiers: str,
    species: Optional[int] = 9606,
    limit: Optional[int] = 10,
    required_score: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get the protein-protein interaction network for one or more proteins from STRING database. Return...

    Parameters
    ----------
    identifiers : str
        Protein identifier(s). For multiple proteins, separate with '%0d' (URL-encode...
    species : int
        NCBI taxonomy ID. Examples: 9606 (human), 10090 (mouse), 7227 (Drosophila), 6...
    limit : int
        Maximum number of interaction partners to include (per protein). 0 = only int...
    required_score : int | Any
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

    return get_shared_client().run_one_function(
        {
            "name": "STRING_get_network",
            "arguments": {
                "identifiers": identifiers,
                "species": species,
                "limit": limit,
                "required_score": required_score,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["STRING_get_network"]
