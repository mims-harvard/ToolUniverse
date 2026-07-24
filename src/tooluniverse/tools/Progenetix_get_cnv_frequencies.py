"""
Progenetix_get_cnv_frequencies

Get the genome-wide aggregate CNV frequency profile for a cancer type from Progenetix — the signa...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Progenetix_get_cnv_frequencies(
    filters: str,
    dataset_ids: Optional[str] = "progenetix",
    max_intervals: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get the genome-wide aggregate CNV frequency profile for a cancer type from Progenetix — the signa...

    Parameters
    ----------
    filters : str
        NCIt ontology code identifying the cancer-type collation. Examples: 'NCIT:C40...
    dataset_ids : str
        Progenetix dataset to query (default 'progenetix').
    max_intervals : int
        Optional cap on the number of interval bins returned (default: all ~3000 bins).
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
            "filters": filters,
            "dataset_ids": dataset_ids,
            "max_intervals": max_intervals,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Progenetix_get_cnv_frequencies",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Progenetix_get_cnv_frequencies"]
