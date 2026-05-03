"""
MassIVE_search_datasets

Search the MassIVE proteomics repository for mass spectrometry datasets. MassIVE hosts thousands ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MassIVE_search_datasets(
    page_size: Optional[int] = 10,
    species: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Search the MassIVE proteomics repository for mass spectrometry datasets. MassIVE hosts thousands ...

    Parameters
    ----------
    page_size : int
        Number of results to return (max 100)
    species : str | Any
        NCBI taxonomy ID to filter by species (e.g., '9606' for human, '10090' for mo...
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    list[Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {"page_size": page_size, "species": species}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "MassIVE_search_datasets",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MassIVE_search_datasets"]
