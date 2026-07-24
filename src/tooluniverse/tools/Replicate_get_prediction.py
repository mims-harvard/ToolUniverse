"""
Replicate_get_prediction

Fetch the current state of a previously created Replicate prediction by its id (GET /v1/predictio...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Replicate_get_prediction(
    operation: str,
    prediction_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Fetch the current state of a previously created Replicate prediction by its id (GET /v1/predictio...

    Parameters
    ----------
    operation : str
        Operation selector (fixed).
    prediction_id : str
        The prediction id returned in the 'id' field of a prior Replicate_run_predict...
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
        for k, v in {"operation": operation, "prediction_id": prediction_id}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Replicate_get_prediction",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Replicate_get_prediction"]
