"""
UniChem_connectivity_search

Connectivity (cross-source) search in UniChem: find all compounds across the 40+ source databases...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def UniChem_connectivity_search(
    compound: str,
    type_: str,
    sourceID: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Connectivity (cross-source) search in UniChem: find all compounds across the 40+ source databases...

    Parameters
    ----------
    compound : str
        The compound identifier to search. Typically a (full or connectivity-layer) I...
    type_ : str
        Type of the compound identifier. One of: 'inchikey', 'sourceID', 'uci'. Defau...
    sourceID : int
        Required when type='sourceID'. The source database ID (e.g., 1=ChEMBL, 2=Drug...
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
        for k, v in {"compound": compound, "type": type_, "sourceID": sourceID}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "UniChem_connectivity_search",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["UniChem_connectivity_search"]
