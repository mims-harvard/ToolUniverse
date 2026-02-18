"""
MobiDB_get_protein

Get comprehensive protein disorder data from MobiDB for a UniProt accession. MobiDB integrates cu...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MobiDB_get_protein(
    accession: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get comprehensive protein disorder data from MobiDB for a UniProt accession. MobiDB integrates cu...

    Parameters
    ----------
    accession : str
        UniProt accession (e.g., 'P04637' for TP53, 'P00533' for EGFR, 'P38398' for B...
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
        {"name": "MobiDB_get_protein", "arguments": {"accession": accession}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MobiDB_get_protein"]
