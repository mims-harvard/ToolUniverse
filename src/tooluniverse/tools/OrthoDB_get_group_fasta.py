"""
OrthoDB_get_group_fasta

Retrieve a resumable structured page of member protein sequences for an OrthoDB orthologous group...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OrthoDB_get_group_fasta(
    group_id: str,
    species: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Retrieve a resumable structured page of member protein sequences for an OrthoDB orthologous group...

    Parameters
    ----------
    group_id : str
        OrthoDB orthologous group ID, e.g. '794361at2759' (BRCA2 at Eukaryota level)....
    species : str
        Optional NCBI taxon ID to restrict members to one species, e.g. '9606' (human...
    limit : int
        Structured page size (default: 50, max: 500). The full raw FASTA is always re...
    offset : int
        Zero-based structured sequence offset. Continue with data.next_offset.
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
            "group_id": group_id,
            "species": species,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "OrthoDB_get_group_fasta",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OrthoDB_get_group_fasta"]
