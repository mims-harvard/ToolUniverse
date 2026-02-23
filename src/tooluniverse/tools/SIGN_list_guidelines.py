"""
SIGN_list_guidelines

List all SIGN (Scottish Intercollegiate Guidelines Network) clinical guidelines, optionally filte...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SIGN_list_guidelines(
    topic: Optional[str] = None,
    limit: Optional[int] = 20,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List all SIGN (Scottish Intercollegiate Guidelines Network) clinical guidelines, optionally filte...

    Parameters
    ----------
    topic : str
        Optional clinical topic/specialty to filter by (e.g., 'Cardiovascular', 'Canc...
    limit : int
        Maximum number of guidelines to return (default: 20)
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
        {"name": "SIGN_list_guidelines", "arguments": {"topic": topic, "limit": limit}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SIGN_list_guidelines"]
