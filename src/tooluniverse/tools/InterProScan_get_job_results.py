"""
InterProScan_get_job_results

Retrieve results from a completed InterProScan job. Returns domain predictions, GO annotations, a...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def InterProScan_get_job_results(
    job_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Retrieve results from a completed InterProScan job. Returns domain predictions, GO annotations, a...

    Parameters
    ----------
    job_id : str
        InterProScan job ID
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
    _args = {k: v for k, v in {"job_id": job_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "InterProScan_get_job_results",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["InterProScan_get_job_results"]
