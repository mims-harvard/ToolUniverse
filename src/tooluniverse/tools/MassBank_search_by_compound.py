"""
MassBank_search_by_compound

Search MassBank Europe spectra by compound name. MassBank returns the full matching array and ign...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MassBank_search_by_compound(
    compound_name: str,
    limit: Optional[int] = 10,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search MassBank Europe spectra by compound name. MassBank returns the full matching array and ign...

    Parameters
    ----------
    compound_name : str
        Compound name to search for (e.g., 'aspirin', 'caffeine', 'glucose', 'PFAS')
    limit : int
        Number of spectra in this client-side page (default 10)
    offset : int
        Zero-based spectrum offset. Continue with metadata.next_offset while metadata...
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
            "compound_name": compound_name,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "MassBank_search_by_compound",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MassBank_search_by_compound"]
