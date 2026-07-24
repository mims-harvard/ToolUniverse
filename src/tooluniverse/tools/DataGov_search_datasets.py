"""
DataGov_search_datasets

Search the US federal open data catalog (Data.gov) for datasets from agencies like EPA, CDC, Cens...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DataGov_search_datasets(
    query: str,
    organization: Optional[str] = None,
    rows: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search the US federal open data catalog (Data.gov) for datasets from agencies like EPA, CDC, Cens...

    Parameters
    ----------
    query : str
        Search keywords for dataset discovery. Searches across dataset titles, descri...
    organization : str
        Optional CKAN organization slug to filter by federal agency. Examples: 'epa-g...
    rows : int
        Number of results to return. Default 10, maximum 100.
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
        for k, v in {"query": query, "organization": organization, "rows": rows}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "DataGov_search_datasets",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DataGov_search_datasets"]
