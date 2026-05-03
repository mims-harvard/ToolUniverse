"""
Wikidata_get_entity

Get detailed structured data for one or more specific Wikidata entities by their Q-numbers. Retur...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Wikidata_get_entity(
    ids: str,
    languages: Optional[str | Any] = None,
    props: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed structured data for one or more specific Wikidata entities by their Q-numbers. Retur...

    Parameters
    ----------
    ids : str
        Wikidata entity ID(s) to retrieve. Use pipe | separator for multiple. Example...
    languages : str | Any
        Language code(s) for labels and descriptions. Default: 'en'. Pipe-separated f...
    props : str | Any
        Which properties to return (pipe-separated). Options: 'labels', 'descriptions...
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
        for k, v in {"ids": ids, "languages": languages, "props": props}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Wikidata_get_entity",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Wikidata_get_entity"]
