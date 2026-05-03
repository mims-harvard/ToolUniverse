"""
PubTator3_EntityAutocomplete

Provides suggestions for the best‐matching standardized PubTator IDs for a partial biomedical ter...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PubTator3_EntityAutocomplete(
    text: str,
    entity_type: Optional[str] = None,
    max_results: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Provides suggestions for the best‐matching standardized PubTator IDs for a partial biomedical ter...

    Parameters
    ----------
    text : str
        A few characters or the full name of the biomedical concept you are trying to...
    entity_type : str
        Optional filter to restrict suggestions to a single category such as GENE, DI...
    max_results : int
        Maximum number of suggestions to return (1 - 50, default = 10).
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
    _args = {
        k: v
        for k, v in {
            "text": text,
            "entity_type": entity_type,
            "max_results": max_results,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "PubTator3_EntityAutocomplete",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PubTator3_EntityAutocomplete"]
