"""
Rfam_search_sequence

Search RNA sequence against all Rfam families using Infernal cmscan. Submits sequence to batch se...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Rfam_search_sequence(
    operation: str,
    sequence: str,
    max_wait_seconds: Optional[int] = 120,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search RNA sequence against all Rfam families using Infernal cmscan. Submits sequence to batch se...

    Parameters
    ----------
    operation : str
        Operation type
    sequence : str
        Required: RNA sequence to search (can be multi-line, no FASTA header needed)
    max_wait_seconds : int
        Maximum time to wait for results (default: 120s). Job continues running if ti...
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
            "sequence": sequence,
            "max_wait_seconds": max_wait_seconds,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Rfam_search_sequence",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Rfam_search_sequence"]
