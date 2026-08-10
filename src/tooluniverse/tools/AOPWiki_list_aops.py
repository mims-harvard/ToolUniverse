"""
AOPWiki_list_aops

List Adverse Outcome Pathways (AOPs) from AOPWiki. Returns AOP IDs, titles, and short names. AOPs...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def AOPWiki_list_aops(
    search: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    List Adverse Outcome Pathways (AOPs) from AOPWiki. Returns AOP IDs, titles, and short names. AOPs...

    Parameters
    ----------
    search : str, optional
        Case-insensitive keyword to filter AOPs by title or short name. Omit t...
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    list[Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {k: v for k, v in {"search": search}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "AOPWiki_list_aops",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["AOPWiki_list_aops"]
