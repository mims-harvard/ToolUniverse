"""
BioImageArchive_search_studies

Search the BioImage Archive (EBI BioStudies) for biological imaging datasets. The BioImage Archiv...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BioImageArchive_search_studies(
    query: str,
    page_size: Optional[int | Any] = None,
    page: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search the BioImage Archive (EBI BioStudies) for biological imaging datasets. The BioImage Archiv...

    Parameters
    ----------
    query : str
        Search query - imaging modality, organism, technique, or topic. Examples: 'cr...
    page_size : int | Any
        Number of results per page. Default: 10. Max: 100.
    page : int | Any
        Page number (1-indexed). Default: 1.
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
        for k, v in {"query": query, "page_size": page_size, "page": page}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "BioImageArchive_search_studies",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BioImageArchive_search_studies"]
