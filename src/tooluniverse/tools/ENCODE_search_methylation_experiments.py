"""
ENCODE_search_methylation_experiments

Search ENCODE whole-genome bisulfite sequencing (WGBS) and reduced-representation bisulfite seque...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ENCODE_search_methylation_experiments(
    assay_type: Optional[str] = "WGBS",
    biosample_term_name: Optional[str | Any] = None,
    organism: Optional[str] = "Homo sapiens",
    limit: Optional[int] = 25,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search ENCODE whole-genome bisulfite sequencing (WGBS) and reduced-representation bisulfite seque...

    Parameters
    ----------
    assay_type : str
        Methylation assay type: 'WGBS' (whole-genome bisulfite sequencing, comprehens...
    biosample_term_name : str | Any
        Biosample name filter (e.g., 'K562', 'liver', 'brain', 'motor neuron'). Leave...
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

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "assay_type": assay_type,
            "biosample_term_name": biosample_term_name,
            "organism": organism,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ENCODE_search_methylation_experiments",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ENCODE_search_methylation_experiments"]
