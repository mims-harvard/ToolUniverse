"""
ReMap_get_peaks_in_region

Retrieve all ChIP-seq transcriptional-regulator (TR) binding peaks from the ReMap catalog that ov...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ReMap_get_peaks_in_region(
    region: str,
    operation: Optional[str] = "get_peaks_in_region",
    assembly: Optional[str] = "hg38",
    version: Optional[str] = "2022",
    datatype: Optional[str] = "all",
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Retrieve all ChIP-seq transcriptional-regulator (TR) binding peaks from the ReMap catalog that ov...

    Parameters
    ----------
    operation : str
        Operation selector. Must be 'get_peaks_in_region'.
    region : str
        Genomic interval as chrom:start-end (e.g. 'chr1:1000000-1100000'). Commas in ...
    assembly : str
        Genome assembly.
    version : str
        ReMap catalog release year.
    datatype : str
        Peak datatype: 'all' for the non-redundant merged peak set across all TFs.
    limit : int
        Optional cap on the number of peaks returned (peak_count still reports the tr...
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
            "operation": operation,
            "region": region,
            "assembly": assembly,
            "version": version,
            "datatype": datatype,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ReMap_get_peaks_in_region",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ReMap_get_peaks_in_region"]
