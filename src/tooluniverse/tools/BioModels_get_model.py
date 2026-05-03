"""
BioModels_get_model

Get comprehensive metadata for a specific BioModels entry by its model identifier. Returns detail...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BioModels_get_model(
    model_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get comprehensive metadata for a specific BioModels entry by its model identifier. Returns detail...

    Parameters
    ----------
    model_id : str
        BioModels identifier (e.g., 'BIOMD0000000469', 'MODEL1707110000'). Find IDs u...
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
    _args = {k: v for k, v in {"model_id": model_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "BioModels_get_model",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BioModels_get_model"]
