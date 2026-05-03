"""
SwissDock_retrieve_results

Retrieve results for a completed SwissDock docking job. Returns download URL and metadata for doc...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SwissDock_retrieve_results(
    session_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Retrieve results for a completed SwissDock docking job. Returns download URL and metadata for doc...

    Parameters
    ----------
    session_id : str
        Session identifier from dock_ligand or check_job_status call (same alphanumer...
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
    _args = {k: v for k, v in {"session_id": session_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "SwissDock_retrieve_results",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SwissDock_retrieve_results"]
