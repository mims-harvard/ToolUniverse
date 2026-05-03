"""
PubChem_get_compound_synonyms_by_CID

Get complete list of synonyms for compound by CID.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PubChem_get_compound_synonyms_by_CID(
    cid: int,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get complete list of synonyms for compound by CID.

    Parameters
    ----------
    cid : int
        Compound ID to query synonyms for, e.g., 2244.
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
    _args = {k: v for k, v in {"cid": cid}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "PubChem_get_compound_synonyms_by_CID",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PubChem_get_compound_synonyms_by_CID"]
