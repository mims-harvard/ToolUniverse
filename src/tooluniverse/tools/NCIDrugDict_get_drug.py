"""
NCIDrugDict_get_drug

Get detailed information for a specific drug from the NCI Drug Dictionary by its term ID. Returns...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NCIDrugDict_get_drug(
    term_id: int,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed information for a specific drug from the NCI Drug Dictionary by its term ID. Returns...

    Parameters
    ----------
    term_id : int
        NCI Drug Dictionary term ID (e.g., 37862 for imatinib mesylate, 695789 for pe...
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
    _args = {k: v for k, v in {"term_id": term_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "NCIDrugDict_get_drug",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NCIDrugDict_get_drug"]
