"""
Orphadata_search_by_name

Find rare diseases in Orphanet by name or synonym, returning ORPHAcodes for use with the other Or...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Orphadata_search_by_name(
    name: str,
    lang: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Find rare diseases in Orphanet by name or synonym, returning ORPHAcodes for use with the other Or...

    Parameters
    ----------
    name : str
        Disease name or synonym, e.g. 'Marfan syndrome'.
    lang : str
        Language code. Default en.
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
    _args = {k: v for k, v in {"name": name, "lang": lang}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "Orphadata_search_by_name",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Orphadata_search_by_name"]
