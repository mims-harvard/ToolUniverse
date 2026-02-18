"""
UniParc_get_entry

Get a UniProt UniParc entry by its stable UPI identifier. UniParc is the most comprehensive, non-...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def UniParc_get_entry(
    upi: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get a UniProt UniParc entry by its stable UPI identifier. UniParc is the most comprehensive, non-...

    Parameters
    ----------
    upi : str
        UniParc identifier (e.g., 'UPI000002ED67' for TP53/P04637). Find UPIs via Uni...
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
        {"name": "UniParc_get_entry", "arguments": {"upi": upi}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["UniParc_get_entry"]
