"""
UniChem_search_compound

Search UniChem for a chemical compound by InChIKey, source compound ID, or UCI (UniChem Compound ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def UniChem_search_compound(
    compound: str,
    type_: str,
    sourceID: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search UniChem for a chemical compound by InChIKey, source compound ID, or UCI (UniChem Compound ...

    Parameters
    ----------
    compound : str
        The compound identifier to search. Can be an InChIKey (e.g., 'BSYNRYMUTXBXSQ-...
    type_ : str
        Type of the compound identifier. One of: 'inchikey', 'sourceID', 'uci'. Defau...
    sourceID : int | Any
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
            "name": "UniChem_search_compound",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["UniChem_search_compound"]
