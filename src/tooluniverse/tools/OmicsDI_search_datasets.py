"""
OmicsDI_search_datasets

Search across multiple omics repositories integrated in OmicsDI (Omics Discovery Index). Searches...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OmicsDI_search_datasets(
    query: str,
    start: Optional[int] = None,
    size: Optional[int] = None,
    omics_type: Optional[str] = None,
    organism: Optional[str] = None,
    tissue: Optional[str] = None,
    sortfield: Optional[str] = None,
    order: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search across multiple omics repositories integrated in OmicsDI (Omics Discovery Index). Searches...

    Parameters
    ----------
    query : str
        Search query text (e.g., 'Alzheimer brain', 'BRCA1 cancer', 'gut microbiome')
    start : int
        Offset for pagination (default 0)
    size : int
        Number of results to return (default 10, max 100)
    omics_type : str
        Filter by omics type: 'Transcriptomics', 'Proteomics', 'Metabolomics', 'Genom...
    organism : str
        Filter by organism (e.g., 'Homo sapiens', 'Mus musculus')
    tissue : str
        Filter by tissue/cell type (e.g., 'brain', 'liver', 'blood')
    sortfield : str
        Sort field: 'publication_date', 'id', 'title', 'views', 'downloads'
    order : str
        Sort order: 'desc' or 'asc'
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
            "start": start,
            "size": size,
            "omics_type": omics_type,
            "organism": organism,
            "tissue": tissue,
            "sortfield": sortfield,
            "order": order,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "OmicsDI_search_datasets",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OmicsDI_search_datasets"]
