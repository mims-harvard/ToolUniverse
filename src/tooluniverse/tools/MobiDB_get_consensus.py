"""
MobiDB_get_consensus

Get consensus disorder analysis for a protein from MobiDB, focusing on merged/consensus predictio...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MobiDB_get_consensus(
    accession: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get consensus disorder analysis for a protein from MobiDB, focusing on merged/consensus predictio...

    Parameters
    ----------
    accession : str
        UniProt accession (e.g., 'P04637' for TP53, 'P00533' for EGFR).
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
        {"name": "MobiDB_get_consensus", "arguments": {"accession": accession}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MobiDB_get_consensus"]
