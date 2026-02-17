"""
ENCODE_search_chromatin_accessibility

Search ENCODE chromatin accessibility experiments (ATAC-seq and DNase-seq). ATAC-seq and DNase-se...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ENCODE_search_chromatin_accessibility(
    assay_type: Optional[str] = "ATAC-seq",
    biosample_term_name: Optional[str | Any] = None,
    organism: Optional[str] = "Homo sapiens",
    limit: Optional[int] = 25,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search ENCODE chromatin accessibility experiments (ATAC-seq and DNase-seq). ATAC-seq and DNase-se...

    Parameters
    ----------
    assay_type : str
        Chromatin accessibility assay: 'ATAC-seq' (Assay for Transposase-Accessible C...
    biosample_term_name : str | Any
        Biosample name filter (e.g., 'K562', 'GM12878', 'liver'). Leave empty for all.
    organism : str
        Organism scientific name.
    limit : int
        Maximum number of results to return.
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
            "name": "ENCODE_search_chromatin_accessibility",
            "arguments": {
                "assay_type": assay_type,
                "biosample_term_name": biosample_term_name,
                "organism": organism,
                "limit": limit,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ENCODE_search_chromatin_accessibility"]
