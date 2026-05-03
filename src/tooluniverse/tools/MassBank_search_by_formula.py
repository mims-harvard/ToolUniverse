"""
MassBank_search_by_formula

Search MassBank Europe spectral library by molecular formula. Returns all mass spectra records fo...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MassBank_search_by_formula(
    formula: str,
    limit: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search MassBank Europe spectral library by molecular formula. Returns all mass spectra records fo...

    Parameters
    ----------
    formula : str
        Molecular formula (e.g., 'C9H8O4' for aspirin, 'C8H10N4O2' for caffeine, 'C6H...
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

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v for k, v in {"formula": formula, "limit": limit}.items() if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "MassBank_search_by_formula",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MassBank_search_by_formula"]
