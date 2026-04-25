"""
Dataverse_get_dataset

Get detailed metadata for a specific Harvard Dataverse dataset by its persistent DOI identifier. ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Dataverse_get_dataset(
    persistentId: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed metadata for a specific Harvard Dataverse dataset by its persistent DOI identifier. ...

    Parameters
    ----------
    persistentId : str
        Persistent DOI identifier for the dataset (e.g., 'doi:10.7910/DVN/DUWBBU', 'd...
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
    _args = {k: v for k, v in {
        "persistentId": persistentId
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "Dataverse_get_dataset",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["Dataverse_get_dataset"]
