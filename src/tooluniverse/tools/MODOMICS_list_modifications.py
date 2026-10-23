"""
MODOMICS_list_modifications

List known RNA modifications from MODOMICS with chemical properties. The complete catalog is reco...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MODOMICS_list_modifications(
    limit: Optional[int] = 50,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    List known RNA modifications from MODOMICS with chemical properties. The complete catalog is reco...

    Parameters
    ----------
    limit : int
        Maximum number of modifications to return (default: 50, max: 500)
    offset : int
        Zero-based catalog offset. Continue with data.next_offset.
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    dict[str, Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v for k, v in {"limit": limit, "offset": offset}.items() if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "MODOMICS_list_modifications",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MODOMICS_list_modifications"]
