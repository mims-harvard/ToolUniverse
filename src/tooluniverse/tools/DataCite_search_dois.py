"""
DataCite_search_dois

Search DataCite for research datasets, software, and other research outputs by keyword, subject, ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DataCite_search_dois(
    query: str,
    resource_type_general: Optional[str | Any] = None,
    page_size: Optional[int | Any] = None,
    page_number: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search DataCite for research datasets, software, and other research outputs by keyword, subject, ...

    Parameters
    ----------
    query : str
        Search query (e.g., 'RNA-seq transcriptomics', 'CRISPR knockout mouse', 'clim...
    resource_type_general : str | Any
        Filter by resource type: 'Dataset', 'Software', 'Text', 'Image', 'Workflow', ...
    page_size : int | Any
        Number of results per page (default 10, max 100)
    page_number : int | Any
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
            "resource_type_general": resource_type_general,
            "page_size": page_size,
            "page_number": page_number,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "DataCite_search_dois",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DataCite_search_dois"]
