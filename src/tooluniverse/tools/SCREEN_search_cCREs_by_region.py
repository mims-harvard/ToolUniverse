"""
SCREEN_search_cCREs_by_region

Query the ENCODE SCREEN Registry of candidate cis-Regulatory Elements (cCREs) overlapping a genom...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SCREEN_search_cCREs_by_region(
    chrom: str,
    start: int,
    end: int,
    assembly: Optional[str] = "GRCh38",
    element_type: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Query the ENCODE SCREEN Registry of candidate cis-Regulatory Elements (cCREs) overlapping a genom...

    Parameters
    ----------
    chrom : str
        Chromosome, e.g. 'chr8' or '8' (the 'chr' prefix is added automatically).
    start : int
        Region start coordinate (1-based).
    end : int
        Region end coordinate (1-based, must be greater than start).
    assembly : str
        Genome assembly: 'GRCh38' (human, default) or 'mm10' (mouse).
    element_type : str
        Optional element-type hint to bias results toward a class: 'PLS', 'pELS', 'dE...
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

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "chrom": chrom,
            "start": start,
            "end": end,
            "assembly": assembly,
            "element_type": element_type,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "SCREEN_search_cCREs_by_region",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SCREEN_search_cCREs_by_region"]
