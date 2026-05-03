"""
OMA_get_group

Get OMA Group details including member proteins. OMA Groups contain sets of strict 1:1 orthologs ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OMA_get_group(
    group_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get OMA Group details including member proteins. OMA Groups contain sets of strict 1:1 orthologs ...

    Parameters
    ----------
    group_id : str
        OMA Group number (numeric ID). Examples: '1388790' (p53 group), '839588' (EGF...
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
    _args = {k: v for k, v in {"group_id": group_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "OMA_get_group",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OMA_get_group"]
