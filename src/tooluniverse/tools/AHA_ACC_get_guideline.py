"""
AHA_ACC_get_guideline

Fetch the full text (or a detailed snippet) of a specific AHA (American Heart Association) or ACC...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def AHA_ACC_get_guideline(
    pmid: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Fetch the full text (or a detailed snippet) of a specific AHA (American Heart Association) or ACC...

    Parameters
    ----------
    pmid : str
        PubMed ID (PMID) of the AHA/ACC guideline to retrieve (e.g., '37952199' for 2...
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
        "pmid": pmid
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "AHA_ACC_get_guideline",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["AHA_ACC_get_guideline"]
