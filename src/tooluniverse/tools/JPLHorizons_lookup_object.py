"""
JPLHorizons_lookup_object

Search for solar system objects in the JPL Horizons database by name, partial name, or designatio...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def JPLHorizons_lookup_object(
    sstr: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search for solar system objects in the JPL Horizons database by name, partial name, or designatio...

    Parameters
    ----------
    sstr : str
        Object name or partial name to search. Examples: 'Mars', 'Jupiter', 'Ceres', ...
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
        {"name": "JPLHorizons_lookup_object", "arguments": {"sstr": sstr}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["JPLHorizons_lookup_object"]
