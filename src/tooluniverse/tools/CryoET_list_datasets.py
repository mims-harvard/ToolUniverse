"""
CryoET_list_datasets

Search and list cryo-electron tomography (cryo-ET) datasets from the CZ BioHub CryoET Data Portal...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CryoET_list_datasets(
    operation: str,
    organism_name: Optional[str | Any] = None,
    tissue_name: Optional[str | Any] = None,
    limit: Optional[int] = 10,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search and list cryo-electron tomography (cryo-ET) datasets from the CZ BioHub CryoET Data Portal...

    Parameters
    ----------
    operation : str
        Operation type
    organism_name : str | Any
        Filter by organism name (case-insensitive substring match). Examples: 'Homo s...
    tissue_name : str | Any
        Filter by tissue or cell type name (case-insensitive substring match). Exampl...
    limit : int
        Maximum number of datasets to return (default: 10, max recommended: 50).
    offset : int
        Number of datasets to skip for pagination (default: 0).
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
            "operation": operation,
            "organism_name": organism_name,
            "tissue_name": tissue_name,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "CryoET_list_datasets",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["CryoET_list_datasets"]
