"""
Replicate_run_prediction

Run a prediction on any model hosted on Replicate (https://replicate.com), the platform serving t...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Replicate_run_prediction(
    operation: str,
    input: dict[str, Any],
    model: Optional[str] = None,
    version: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Run a prediction on any model hosted on Replicate (https://replicate.com), the platform serving t...

    Parameters
    ----------
    operation : str
        Operation selector (fixed).
    model : str
        Model in 'owner/name' form, e.g. 'replicate/hello-world'. Runs the model's la...
    version : str
        A specific 64-char hex version hash from the model's API page. Pins an exact ...
    input : dict[str, Any]
        Object of the model's inputs, e.g. {'text': 'hello'} for replicate/hello-worl...
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
            "model": model,
            "version": version,
            "input": input,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Replicate_run_prediction",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Replicate_run_prediction"]
