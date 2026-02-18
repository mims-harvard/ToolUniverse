"""
UniProtTaxonomy_get_taxon

Get detailed taxonomy information for a species by NCBI taxonomy ID from UniProt. Returns scienti...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def UniProtTaxonomy_get_taxon(
    taxon_id: int,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed taxonomy information for a species by NCBI taxonomy ID from UniProt. Returns scienti...

    Parameters
    ----------
    taxon_id : int
        NCBI taxonomy ID. Examples: 9606 (human), 10090 (mouse), 7227 (fruit fly), 62...
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
        {"name": "UniProtTaxonomy_get_taxon", "arguments": {"taxon_id": taxon_id}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["UniProtTaxonomy_get_taxon"]
