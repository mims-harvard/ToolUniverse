"""
FourDN_search_data

Search 4DN Data Portal for Hi-C chromatin conformation files and experiments. Access 350+ uniform...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def FourDN_search_data(
    operation: str,
    query: Optional[str] = "*",
    item_type: Optional[str] = "File",
    file_type: Optional[str] = None,
    assay_title: Optional[str] = None,
    biosource_name: Optional[str] = None,
    limit: Optional[int] = 25,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search 4DN Data Portal for Hi-C chromatin conformation files and experiments. Access 350+ uniform...

    Parameters
    ----------
    operation : str

    query : str
        Search query (default: '*' for all)
    item_type : str
        Type of item to search
    file_type : str
        Filter by file type. Common types: 'contact list' (processed contact matrices...
    assay_title : str
        Filter by assay (e.g., 'Hi-C', 'Micro-C', 'Capture Hi-C')
    biosource_name : str
        Filter by cell type (e.g., 'H1-hESC', 'HFFc6', 'GM12878')
    limit : int
        Maximum results to return
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    dict[str, Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "operation": operation,
            "query": query,
            "item_type": item_type,
            "file_type": file_type,
            "assay_title": assay_title,
            "biosource_name": biosource_name,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "FourDN_search_data",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["FourDN_search_data"]
