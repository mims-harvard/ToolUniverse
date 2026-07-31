"""
DataCite_search_datasets

Search for research datasets with DOIs across all repositories worldwide (Zenodo, Figshare, Dryad...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DataCite_search_datasets(
    query: str,
    resource_type: Optional[str] = "Dataset",
    publisher: Optional[str] = None,
    year: Optional[int] = None,
    page_size: Optional[int] = 10,
    page_number: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search for research datasets with DOIs across all repositories worldwide (Zenodo, Figshare, Dryad...

    Parameters
    ----------
    query : str
        Search query for datasets (e.g., 'iron intake physical function older adults'...
    resource_type : str
        Override resource type filter. Defaults to 'Dataset'. Other options: 'Softwar...
    publisher : str
        Filter by publisher/repository name (e.g., 'Zenodo', 'Dryad', 'figshare'). No...
    year : int
        Filter by publication year (e.g., 2024, 2023). Returns datasets published in ...
    page_size : int
        Number of results per page (default 10, max 100)
    page_number : int
        Page number for pagination (default 1)
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
            "resource_type": resource_type,
            "publisher": publisher,
            "year": year,
            "page_size": page_size,
            "page_number": page_number,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "DataCite_search_datasets",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DataCite_search_datasets"]
