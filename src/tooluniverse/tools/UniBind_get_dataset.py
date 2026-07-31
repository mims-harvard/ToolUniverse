"""
UniBind_get_dataset

Retrieve full direct transcription factor (TF)-DNA binding-site detail for one UniBind dataset by...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def UniBind_get_dataset(
    dataset_id: str,
    operation: Optional[str] = "get_dataset",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Retrieve full direct transcription factor (TF)-DNA binding-site detail for one UniBind dataset by...

    Parameters
    ----------
    operation : str
        Operation selector. Must be 'get_dataset'.
    dataset_id : str
        UniBind dataset identifier, e.g. 'EXP030726.neural_stem_cells.SMAD3'. Obtain ...
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
        for k, v in {"operation": operation, "dataset_id": dataset_id}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "UniBind_get_dataset",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["UniBind_get_dataset"]
