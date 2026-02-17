"""
ENCODE_search_histone_experiments

Search ENCODE histone ChIP-seq experiments by histone modification mark, biosample, or organism. ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ENCODE_search_histone_experiments(
    histone_mark: Optional[str | Any] = None,
    biosample_term_name: Optional[str | Any] = None,
    organism: Optional[str] = "Homo sapiens",
    limit: Optional[int] = 25,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search ENCODE histone ChIP-seq experiments by histone modification mark, biosample, or organism. ...

    Parameters
    ----------
    histone_mark : str | Any
        Histone modification mark to filter by (e.g., 'H3K4me3', 'H3K27ac', 'H3K27me3...
    biosample_term_name : str | Any
        Biosample name filter (e.g., 'K562', 'HepG2', 'GM12878', 'liver', 'brain'). L...
    organism : str
        Organism scientific name (e.g., 'Homo sapiens', 'Mus musculus').
    limit : int
        Maximum number of results to return (1-100).
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
            "name": "ENCODE_search_histone_experiments",
            "arguments": {
                "histone_mark": histone_mark,
                "biosample_term_name": biosample_term_name,
                "organism": organism,
                "limit": limit,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ENCODE_search_histone_experiments"]
