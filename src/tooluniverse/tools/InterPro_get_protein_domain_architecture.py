"""
InterPro_get_protein_domain_architecture

Get Pfam domain architecture for a protein with exact residue positions using the InterPro API. E...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def InterPro_get_protein_domain_architecture(
    accession: str,
    max_results: Optional[int] = 50,
    cursor: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get Pfam domain architecture for a protein with exact residue positions using the InterPro API. E...

    Parameters
    ----------
    accession : str
        UniProt protein accession. Examples: 'P04637' (TP53, 4 Pfam domains), 'P00533...
    max_results : int
        Maximum InterPro entries to return per page (default 50, max 200).
    cursor : str
        Opaque InterPro cursor returned as next_cursor by a previous call.
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
            "accession": accession,
            "max_results": max_results,
            "cursor": cursor,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "InterPro_get_protein_domain_architecture",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["InterPro_get_protein_domain_architecture"]
