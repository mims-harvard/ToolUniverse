"""
MassBank_search_by_compound

Search MassBank Europe mass spectrometry spectral library by compound name. MassBank is an open-a...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MassBank_search_by_compound(
    compound_name: str,
    limit: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search MassBank Europe mass spectrometry spectral library by compound name. MassBank is an open-a...

    Parameters
    ----------
    compound_name : str
        Compound name to search for (e.g., 'aspirin', 'caffeine', 'glucose', 'PFAS')
    limit : int | Any
        Maximum number of spectra to return (default 10)
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

    return get_shared_client().run_one_function(
        {
            "name": "MassBank_search_by_compound",
            "arguments": {"compound_name": compound_name, "limit": limit},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MassBank_search_by_compound"]
