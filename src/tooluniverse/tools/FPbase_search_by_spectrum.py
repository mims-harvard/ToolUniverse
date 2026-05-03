"""
FPbase_search_by_spectrum

Search FPbase for fluorescent proteins with specific spectral properties. Filter by excitation wa...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def FPbase_search_by_spectrum(
    name__icontains: Optional[str | Any] = None,
    agg_exc_max__gte: Optional[int | Any] = None,
    agg_exc_max__lte: Optional[int | Any] = None,
    agg_em_max__gte: Optional[int | Any] = None,
    agg_em_max__lte: Optional[int | Any] = None,
    switch_type: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search FPbase for fluorescent proteins with specific spectral properties. Filter by excitation wa...

    Parameters
    ----------
    name__icontains : str | Any
        Search by name (case-insensitive partial match, e.g., 'GFP', 'cherry', 'scarl...
    agg_exc_max__gte : int | Any
        Minimum excitation wavelength in nm (e.g., 480 for green range)
    agg_exc_max__lte : int | Any
        Maximum excitation wavelength in nm (e.g., 520 for green range)
    agg_em_max__gte : int | Any
        Minimum emission wavelength in nm
    agg_em_max__lte : int | Any
        Maximum emission wavelength in nm
    switch_type : str | Any
        Filter by photoswitching: 'b' (basic/constitutive), 'ps' (photoswitchable), '...
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
            "name__icontains": name__icontains,
            "agg_exc_max__gte": agg_exc_max__gte,
            "agg_exc_max__lte": agg_exc_max__lte,
            "agg_em_max__gte": agg_em_max__gte,
            "agg_em_max__lte": agg_em_max__lte,
            "switch_type": switch_type,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "FPbase_search_by_spectrum",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["FPbase_search_by_spectrum"]
