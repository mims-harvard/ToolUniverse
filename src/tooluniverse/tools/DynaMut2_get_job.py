"""
DynaMut2_get_job

Retrieve results for a previously submitted DynaMut2 stability prediction job. If the job is stil...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DynaMut2_get_job(
    operation: str,
    job_id: str,
    endpoint: Optional[str | Any] = "prediction_single",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Retrieve results for a previously submitted DynaMut2 stability prediction job. If the job is stil...

    Parameters
    ----------
    operation : str
        Operation type
    job_id : str
        DynaMut2 job identifier returned from a previous predict_stability call.
    endpoint : str | Any
        API endpoint for the job type. Default: 'prediction_single'. Other options: '...
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
            "job_id": job_id,
            "endpoint": endpoint,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "DynaMut2_get_job",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DynaMut2_get_job"]
