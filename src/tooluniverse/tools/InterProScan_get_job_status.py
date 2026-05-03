"""
InterProScan_get_job_status

Check status of an InterProScan analysis job. Use if scan_sequence returns before completion. Sta...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def InterProScan_get_job_status(
    job_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Check status of an InterProScan analysis job. Use if scan_sequence returns before completion. Sta...

    Parameters
    ----------
    job_id : str
        InterProScan job ID returned from scan_sequence
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
            "name": "InterProScan_get_job_status",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["InterProScan_get_job_status"]
