"""
UCSC_search

Search the UCSC Genome Browser for genes, transcripts, or genomic features by name. Returns the t...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def UCSC_search(
    search_term: str,
    genome: Optional[str] = None,
    limit: Optional[int] = 50,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search the UCSC Genome Browser for genes, transcripts, or genomic features by name. Returns the t...

    Parameters
    ----------
    search_term : str
        Gene symbol, transcript ID, SNP rsID, or genomic feature to search. Examples:...
    genome : str
        UCSC genome assembly identifier. Default: 'hg38'. Others: 'hg19', 'mm10', 'mm...
    limit : int
        Maximum position matches per page (default 50, max 1000).
    offset : int
        Zero-based match offset. Continue with next_offset while has_more is true.
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
            "search_term": search_term,
            "genome": genome,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "UCSC_search",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["UCSC_search"]
