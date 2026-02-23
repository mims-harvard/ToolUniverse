"""
SASBDB_search_entries

Search SASBDB for small-angle scattering entries by molecular type (protein, rna, dna, heterocomp...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SASBDB_search_entries(
    molecular_type: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Search SASBDB for small-angle scattering entries by molecular type (protein, rna, dna, heterocomp...

    Parameters
    ----------
    molecular_type : str | Any
        Filter by molecule type: 'protein', 'rna', 'dna', 'heterocomplex', 'other'. L...
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

    return get_shared_client().run_one_function(
        {
            "name": "SASBDB_search_entries",
            "arguments": {"molecular_type": molecular_type},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SASBDB_search_entries"]
