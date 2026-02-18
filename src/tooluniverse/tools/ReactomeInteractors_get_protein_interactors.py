"""
ReactomeInteractors_get_protein_interactors

Get protein-protein interaction partners for a specific protein from Reactome's IntAct-derived in...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ReactomeInteractors_get_protein_interactors(
    accession: str,
    page_size: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get protein-protein interaction partners for a specific protein from Reactome's IntAct-derived in...

    Parameters
    ----------
    accession : str
        UniProt accession number for the query protein. Examples: 'P04637' (TP53), 'Q...
    page_size : int | Any
        Maximum number of interactors to return (default: 20, max: 100).
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
            "name": "ReactomeInteractors_get_protein_interactors",
            "arguments": {"accession": accession, "page_size": page_size},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ReactomeInteractors_get_protein_interactors"]
