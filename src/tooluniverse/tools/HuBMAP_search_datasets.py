"""
HuBMAP_search_datasets

Search HuBMAP (Human BioMolecular Atlas Program) published datasets by organ, assay type, or free...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def HuBMAP_search_datasets(
    organ: Optional[str] = None,
    dataset_type: Optional[str] = None,
    query: Optional[str] = None,
    status: Optional[str] = "Published",
    limit: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search HuBMAP (Human BioMolecular Atlas Program) published datasets by organ, assay type, or free...

    Parameters
    ----------
    organ : str
        Organ code to filter by (e.g., 'LK' for left kidney, 'HT' for heart, 'LV' for...
    dataset_type : str
        Filter by assay/data type (e.g., 'RNAseq', 'CODEX', 'MALDI', 'snATACseq', 'LC...
    query : str
        Free text search across title, description, and anatomy fields
    status : str
        Dataset status filter. Default: 'Published'
    limit : int
        Maximum number of results (1-50, default 10)
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
            "organ": organ,
            "dataset_type": dataset_type,
            "query": query,
            "status": status,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "HuBMAP_search_datasets",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["HuBMAP_search_datasets"]
