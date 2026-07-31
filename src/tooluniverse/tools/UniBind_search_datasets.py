"""
UniBind_search_datasets

Search the UniBind catalog of curated, experimentally derived direct transcription factor (TF)-DN...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def UniBind_search_datasets(
    operation: Optional[str] = "search_datasets",
    tf_name: Optional[str] = None,
    species: Optional[str] = None,
    cell_line: Optional[str] = None,
    collection: Optional[str] = None,
    order: Optional[str] = None,
    page: Optional[int] = 1,
    page_size: Optional[int] = 25,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search the UniBind catalog of curated, experimentally derived direct transcription factor (TF)-DN...

    Parameters
    ----------
    operation : str
        Operation selector. Must be 'search_datasets'.
    tf_name : str
        Transcription factor gene symbol to filter by, e.g. 'CTCF', 'SMAD3', 'ESR1'. ...
    species : str
        Species scientific name to filter by, e.g. 'Homo sapiens', 'Mus musculus', 'D...
    cell_line : str
        Cell type / tissue / condition name to filter by, e.g. 'neural stem cells', '...
    collection : str
        UniBind collection: 'Robust' (high-confidence, metadata-curated) or 'Permissi...
    order : str
        Field to order results by, e.g. 'tf_name' or '-tf_name' (prefix '-' for desce...
    page : int
        1-based page number for pagination.
    page_size : int
        Number of datasets per page (max 1000).
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
            "tf_name": tf_name,
            "species": species,
            "cell_line": cell_line,
            "collection": collection,
            "order": order,
            "page": page,
            "page_size": page_size,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "UniBind_search_datasets",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["UniBind_search_datasets"]
