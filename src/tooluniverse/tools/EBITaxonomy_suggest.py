"""
EBITaxonomy_suggest

Get taxonomy name suggestions matching a partial query from EBI Taxonomy. Type-ahead style search...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EBITaxonomy_suggest(
    query: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get taxonomy name suggestions matching a partial query from EBI Taxonomy. Type-ahead style search...

    Parameters
    ----------
    query : str
        Partial organism name to get suggestions for. Examples: 'human', 'streptococc...
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
    _args = {k: v for k, v in {"query": query}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "EBITaxonomy_suggest",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EBITaxonomy_suggest"]
