"""
UniParc_get_entry

Get a UniProt UniParc entry by its stable UPI identifier. Returns the full sequence plus explicit...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def UniParc_get_entry(
    upi: str,
    cross_reference_offset: Optional[int] = 0,
    cross_reference_limit: Optional[int] = 100,
    feature_offset: Optional[int] = 0,
    feature_limit: Optional[int] = 100,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get a UniProt UniParc entry by its stable UPI identifier. Returns the full sequence plus explicit...

    Parameters
    ----------
    upi : str
        UniParc identifier (e.g., 'UPI000002ED67' for TP53/P04637). Find UPIs via Uni...
    cross_reference_offset : int
        Zero-based offset into active cross-references. Continue with metadata.next_c...
    cross_reference_limit : int
        Maximum active cross-references returned in this response.
    feature_offset : int
        Zero-based offset into sequence features. Continue with metadata.next_feature...
    feature_limit : int
        Maximum sequence features returned in this response.
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
            "upi": upi,
            "cross_reference_offset": cross_reference_offset,
            "cross_reference_limit": cross_reference_limit,
            "feature_offset": feature_offset,
            "feature_limit": feature_limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "UniParc_get_entry",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["UniParc_get_entry"]
