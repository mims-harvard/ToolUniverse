"""
GtoPdb_search_targets

Search the Guide to Pharmacology database (GtoPdb) for drug targets including GPCRs, ion channels...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GtoPdb_search_targets(
    name: Optional[str | Any] = None,
    type_: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search the Guide to Pharmacology database (GtoPdb) for drug targets including GPCRs, ion channels...

    Parameters
    ----------
    name : str | Any
        Target name or gene symbol to search. Examples: 'dopamine', 'serotonin recept...
    type_ : str | Any
        Target type filter. Values: 'GPCR', 'Ion channel', 'Nuclear receptor', 'Enzym...
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
        {"name": "GtoPdb_search_targets", "arguments": {"name": name, "type": type_}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GtoPdb_search_targets"]
