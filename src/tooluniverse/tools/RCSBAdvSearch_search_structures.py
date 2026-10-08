"""
RCSBAdvSearch_search_structures

Advanced search of RCSB Protein Data Bank structures by combining multiple attribute filters. Fil...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def RCSBAdvSearch_search_structures(
    query: Optional[str] = None,
    organism: Optional[str] = None,
    max_resolution: Optional[float] = None,
    experimental_method: Optional[str] = None,
    polymer_description: Optional[str] = None,
    min_deposition_date: Optional[str] = None,
    rows: Optional[int] = None,
    start: Optional[int] = None,
    sort_by: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Advanced search of RCSB Protein Data Bank structures by combining multiple attribute filters. Fil...

    Parameters
    ----------
    query : str
        Free-text search query. Examples: 'insulin receptor', 'CRISPR-Cas9', 'COVID s...
    organism : str
        Filter by source organism (exact match). Examples: 'Homo sapiens', 'Mus muscu...
    max_resolution : float
        Maximum resolution in Angstroms. Lower values mean higher resolution. Example...
    experimental_method : str
        Filter by experimental method. Must be EXACT value: 'X-RAY DIFFRACTION', 'ELE...
    polymer_description : str
        Filter by polymer entity description (contains words). Examples: 'kinase', 'h...
    min_deposition_date : str
        Only structures deposited after this date. Format: YYYY-MM-DD. Example: '2023...
    rows : int
        Number of results to return per page (default: 10, max: 50). Requests above 5...
    start : int
        Zero-based index of the first result to return, for paging through a result s...
    sort_by : str
        Sort results by: 'resolution' (best resolution first, default), 'date' (newes...
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
            "query": query,
            "organism": organism,
            "max_resolution": max_resolution,
            "experimental_method": experimental_method,
            "polymer_description": polymer_description,
            "min_deposition_date": min_deposition_date,
            "rows": rows,
            "start": start,
            "sort_by": sort_by,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "RCSBAdvSearch_search_structures",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["RCSBAdvSearch_search_structures"]
