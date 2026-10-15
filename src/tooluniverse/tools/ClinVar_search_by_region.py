"""
ClinVar_search_by_region

Find ClinVar variants that OVERLAP a genomic region, including large copy-number variants that be...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ClinVar_search_by_region(
    region: Optional[str] = None,
    chrom: Optional[str] = None,
    start: Optional[int] = None,
    end: Optional[int] = None,
    assembly: Optional[str] = "GRCh37",
    clinical_significance: Optional[str] = None,
    margin: Optional[int] = 2000000,
    max_results: Optional[int] = 50,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Find ClinVar variants that OVERLAP a genomic region, including large copy-number variants that be...

    Parameters
    ----------
    region : str
        Region as written, e.g. 'chr7:155593770-155593780'. Alternative to chrom/star...
    chrom : str
        Chromosome, e.g. '7' or 'chr7'.
    start : int
        Region start (1-based).
    end : int
        Region end (1-based, inclusive).
    assembly : str
        Assembly the coordinates are in. Default GRCh37.
    clinical_significance : str
        Optional filter, e.g. 'pathogenic'.
    margin : int
        How far upstream to look for variants that start before the region and span i...
    max_results : int
        Maximum overlapping variants to return; the full number found is reported as ...
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
            "region": region,
            "chrom": chrom,
            "start": start,
            "end": end,
            "assembly": assembly,
            "clinical_significance": clinical_significance,
            "margin": margin,
            "max_results": max_results,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ClinVar_search_by_region",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ClinVar_search_by_region"]
